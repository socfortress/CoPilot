"""File Analysis API — submit, poll, fetch result, previews, cache lookup.

Endpoints are thin: validate input, kick the orchestrator as a background task,
and read job/result state back from MinIO (state_store). No DB session, no ORM —
persistence is object storage. Guarded to admin/analyst scope; customer_user
support (own-tenant read) is a follow-up.
"""
from __future__ import annotations

import hashlib
import io

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Security
from fastapi import UploadFile
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.db.universal_models import Agents
from app.file_analysis.schema.analysis import AgentInfo
from app.file_analysis.schema.analysis import AgentsResponse
from app.file_analysis.schema.analysis import EnumerateRequest
from app.file_analysis.schema.analysis import EnumerateResponse
from app.file_analysis.schema.analysis import DeleteResponse
from app.file_analysis.schema.analysis import HistoryItem
from app.file_analysis.schema.analysis import HistoryResponse
from app.file_analysis.schema.analysis import MatchInfo
from app.file_analysis.schema.analysis import AnalysisJob
from app.file_analysis.schema.analysis import AnalysisResult
from app.file_analysis.schema.analysis import JobResponse
from app.file_analysis.schema.analysis import ResultResponse
from app.file_analysis.schema.analysis import SearchResponse
from app.file_analysis.schema.analysis import SubmitRequest
from app.file_analysis.schema.analysis import SubmitResponse
from app.file_analysis.schema.analysis import Tier
from app.file_analysis.services import orchestrator
from app.file_analysis.services import state_store

file_analysis_router = APIRouter()

_ANALYST = Security(AuthHandler().require_any_scope("admin", "analyst"))
_MAX_UPLOAD_MB = 100


@file_analysis_router.get("/velociraptor/agents", response_model=AgentsResponse, dependencies=[_ANALYST])
async def velociraptor_agents(customer_code: str, session: AsyncSession = Depends(get_db)) -> AgentsResponse:
    """List a customer's Velociraptor-enrolled endpoints for the submit dropdown.

    Tenant-scoped: agents come from CoPilot's ``Agents`` table filtered by
    ``customer_code`` (only those with a ``velociraptor_id``). Online status is
    overlaid from a live Velociraptor ``clients()`` query since the table's
    last-seen lags.
    """
    if not customer_code:
        raise HTTPException(status_code=400, detail="customer_code is required")
    from app.file_analysis.services import velociraptor_fetch as vf

    # This customer's agents, plus unassigned (orphan) endpoints so they stay usable.
    result = await session.execute(
        select(Agents).filter(
            Agents.velociraptor_id.is_not(None),
            or_(Agents.customer_code == customer_code, Agents.customer_code.is_(None)),
        ),
    )
    db_agents = result.scalars().all()

    try:
        live = await vf.live_last_seen_map()
    except Exception as exc:
        logger.warning(f"live agent status unavailable: {exc}")
        live = {}

    agents = []
    for a in db_agents:
        cid = vf.bare_client_id(a.velociraptor_id)
        last = live.get(cid, 0)
        agents.append(
            AgentInfo(
                client_id=cid,
                hostname=a.hostname or "",
                os=a.os or "",
                online=vf.is_online(last),
                last_seen=last or None,
                unassigned=a.customer_code is None,
            )
        )
    # Online first, then this customer's own agents before unassigned, then by name.
    agents.sort(key=lambda x: (not x.online, x.unassigned, (x.hostname or "").lower()))
    return AgentsResponse(agents=agents, message=f"{len(agents)} agents for {customer_code}")


@file_analysis_router.post("/velociraptor/enumerate", response_model=EnumerateResponse, dependencies=[_ANALYST])
async def velociraptor_enumerate(body: EnumerateRequest) -> EnumerateResponse:
    """List files matching a path/glob on an endpoint (hashes only, no bytes pulled).

    Backs the multi-file picker: the operator enters a path, sees the matches, then
    submits the chosen exact path(s) for analysis via ``/submit`` (source=host_path).
    """
    from app.file_analysis.services import velociraptor_fetch as vf

    if not (body.client_id and body.target_path):
        raise HTTPException(status_code=400, detail="client_id and target_path are required")
    try:
        matches = await vf.enumerate_matches(body.client_id, body.target_path)
    except Exception as exc:
        logger.error(f"enumerate failed: {exc}")
        raise HTTPException(status_code=502, detail="could not enumerate files on the endpoint")
    return EnumerateResponse(
        matches=[MatchInfo(**m) for m in matches],
        message=f"{len(matches)} match(es)" if matches else "no files matched",
    )


@file_analysis_router.post("/submit", response_model=SubmitResponse, dependencies=[_ANALYST])
async def submit(body: SubmitRequest, background: BackgroundTasks) -> SubmitResponse:
    """Collect a file from an endpoint via Velociraptor and analyze it (async).

    The operator picks an endpoint by hostname (or client_id) and a file path;
    resolution, OS-aware collection, fetch and analysis all run in the background.
    """
    if body.source != "host_path":
        raise HTTPException(status_code=400, detail="use /upload for source=upload")
    if not (body.hostname or body.client_id):
        raise HTTPException(status_code=400, detail="host_path source requires hostname or client_id")
    if not body.target_path:
        raise HTTPException(status_code=400, detail="host_path source requires target_path")

    job_id, needs_run = await orchestrator.create_and_dispatch(
        source=body.source,
        customer_code=body.customer_code,
        tiers=body.tiers,
    )
    if needs_run:
        refs = {
            "client_id": body.client_id,
            "target_path": body.target_path,
            "hostname": body.hostname,
        }
        background.add_task(
            orchestrator.run,
            job_id,
            sample_bytes=None,
            tiers=body.tiers,
            refs=refs,
            reputation_mode=body.reputation_mode,
        )
    return SubmitResponse(job_id=job_id, message="analysis queued")


@file_analysis_router.post("/upload", response_model=SubmitResponse, dependencies=[_ANALYST])
async def upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    customer_code: str = Form(...),
    sandbox: bool = Form(True),
    reputation_mode: str = Form("lookup"),
) -> SubmitResponse:
    """Direct analyst upload (multipart). Bytes stay in memory for the job.

    ``sandbox`` toggles Tier-2 detonation; ``reputation_mode`` picks the VirusTotal
    phase (``off`` | ``lookup`` | ``upload``) — chosen by the analyst before submit.
    """
    data = await file.read()
    if len(data) > _MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"file exceeds {_MAX_UPLOAD_MB} MB")
    if reputation_mode not in ("off", "lookup", "upload"):
        raise HTTPException(status_code=400, detail="reputation_mode must be off|lookup|upload")
    sha256 = hashlib.sha256(data).hexdigest()
    tiers = [Tier.STATIC, Tier.DYNAMIC] if sandbox else [Tier.STATIC]

    job_id, needs_run = await orchestrator.create_and_dispatch(
        source="upload",
        customer_code=customer_code,
        tiers=tiers,
        sample_bytes=data,
        filename=file.filename or "sample",
        sha256=sha256,
    )
    # Only a COMPLETE cached result skips the re-run; incomplete → re-analyze.
    if needs_run:
        background.add_task(
            orchestrator.run,
            job_id,
            sample_bytes=data,
            tiers=tiers,
            reputation_mode=reputation_mode,
        )
    return SubmitResponse(job_id=job_id, message="analysis queued")


@file_analysis_router.get("/job/{job_id}", response_model=JobResponse, dependencies=[_ANALYST])
async def get_job(job_id: str) -> JobResponse:
    job = await state_store.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse(job=AnalysisJob(**job))


@file_analysis_router.get("/result/{job_id}", response_model=ResultResponse, dependencies=[_ANALYST])
async def get_result(job_id: str) -> ResultResponse:
    job = await state_store.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    result = await state_store.load_result(job["customer_code"], job.get("sha256", ""))
    if not result:
        raise HTTPException(status_code=404, detail="result not ready")
    return ResultResponse(result=AnalysisResult(**result))


@file_analysis_router.get("/result/{job_id}/cape-report", dependencies=[_ANALYST])
async def cape_report(job_id: str) -> JSONResponse:
    """The COMPLETE raw CAPE report for this analysis (every API call, all behaviour)
    — fetched on demand so analysts can inspect literally everything without bloating
    the stored result. Served straight from CAPE by the detonation task id.
    """
    job = await state_store.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    result = await state_store.load_result(job["customer_code"], job.get("sha256", ""))
    task_id = ((result or {}).get("sandbox") or {}).get("task_id")
    if not task_id:
        raise HTTPException(status_code=404, detail="this analysis has no detonation report")
    from app.file_analysis.services.sandbox import get_backend

    try:
        report = await get_backend().get_report(str(task_id))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"could not fetch the CAPE report: {exc}")
    return JSONResponse(content=report)


@file_analysis_router.get("/result/{job_id}/report.pdf", dependencies=[_ANALYST])
async def report_pdf(job_id: str):
    """A shareable PDF analyst report — file identity, verdict, static findings,
    reputation, and detonation behaviour (with sandbox screenshots embedded).
    Rendered on demand via the shared Jinja2 -> wkhtmltopdf pipeline.
    """
    job = await state_store.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    result = await state_store.load_result(job["customer_code"], job.get("sha256", ""))
    if not result:
        raise HTTPException(status_code=404, detail="result not ready")

    # Screenshots live on the sandbox, not in our stored result — fetch them on
    # demand (best-effort; the report renders fine without them).
    screenshots: list = []
    task_id = ((result.get("sandbox") or {}).get("task_id"))
    if task_id:
        from app.file_analysis.services.sandbox import get_backend

        try:
            screenshots = await get_backend().get_screenshots(str(task_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"screenshot fetch failed for job {job_id}: {exc}")

    from app.file_analysis.services import report_pdf as report_pdf_service

    try:
        return report_pdf_service.generate_report_pdf(result, screenshots=screenshots)
    except FileNotFoundError as exc:
        # wkhtmltopdf missing on this host — actionable message, not a 500.
        raise HTTPException(status_code=503, detail=f"PDF renderer unavailable: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"PDF report generation failed for job {job_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"could not generate the PDF report: {exc}")


@file_analysis_router.delete("/analysis/{job_id}", response_model=DeleteResponse, dependencies=[_ANALYST])
async def delete_analysis(job_id: str) -> DeleteResponse:
    """Delete a stored analysis (result, summary, previews, job) so the history
    table can drop old files. Scoped to this job's own (customer, sha) — the CAPE
    detonation task is intentionally left, so re-analysing the same file reuses it.
    """
    job = await state_store.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="analysis not found")
    removed = await state_store.delete_analysis(job["customer_code"], job.get("sha256", ""), job_id)
    return DeleteResponse(removed=removed, message="analysis deleted")


@file_analysis_router.get("/result/{job_id}/preview/{name}", dependencies=[_ANALYST])
async def get_preview(job_id: str, name: str) -> StreamingResponse:
    job = await state_store.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    result = await state_store.load_result(job["customer_code"], job.get("sha256", ""))
    # Path-traversal defense: name must be a known preview for this result.
    if not result or name not in (result.get("preview_urls") or []):
        raise HTTPException(status_code=404, detail="preview not found")
    data = await state_store.load_preview(job["customer_code"], job["sha256"], name)
    if data is None:
        raise HTTPException(status_code=404, detail="preview not found")
    return StreamingResponse(io.BytesIO(data), media_type="image/png")


@file_analysis_router.get("/history", response_model=HistoryResponse, dependencies=[_ANALYST])
async def history(customer_code: str, limit: int = 50) -> HistoryResponse:
    """Recent analyses for a customer (newest first) — powers the history table."""
    if not customer_code:
        raise HTTPException(status_code=400, detail="customer_code is required")
    items = await state_store.list_history(customer_code, limit=limit)
    return HistoryResponse(items=[HistoryItem(**i) for i in items], message=f"{len(items)} analyses")


@file_analysis_router.get("/search/{sha256}", response_model=SearchResponse, dependencies=[_ANALYST])
async def search(sha256: str, customer_code: str | None = None) -> SearchResponse:
    # Cache is tenant-scoped, so a lookup needs the customer_code; without it we
    # can't answer and report "not analyzed" rather than leak across tenants.
    if not customer_code:
        return SearchResponse(job_id=None, message="customer_code required for cache lookup")
    job_id = await state_store.find_cached_job_id(customer_code, sha256)
    return SearchResponse(job_id=job_id, message="cache hit" if job_id else "not analyzed")
