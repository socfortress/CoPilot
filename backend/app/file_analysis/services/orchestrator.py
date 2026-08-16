"""Orchestrator — the pipeline that ties every piece together.

    resolve/fetch file -> Tier 1 inspect (always) -> [Tier 2 detonate if enabled
    and escalation warranted] -> reputation -> persist to MinIO.

State lives in MinIO (state_store), NOT a new DB table. Long work runs as a
FastAPI background task; the submit endpoint returns a job_id immediately and the
UI polls job status.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger

from app.file_analysis.schema.analysis import AnalysisJob
from app.file_analysis.schema.analysis import Status
from app.file_analysis.schema.analysis import Tier
from app.file_analysis.schema.analysis import Verdict
from app.file_analysis.services import state_store
from app.file_analysis.services.inspector_client import InspectorBusy
from app.file_analysis.services.inspector_client import inspect

# Flags on an inspected file that warrant auto-escalation to Tier 2 detonation.
_ESCALATION_FLAGS = {
    "encoded_powershell",
    "auto_execute_javascript",
    "launch_action",
    "autoopen_macro",
    "lnk_suspicious_args",
    "html_smuggling",
    "deobfuscation_incomplete",
    "analysis_incomplete",
}
# File families a sandbox can meaningfully DETONATE (CAPE auto-detects the package):
# native executables, scripts, Office/MSI (OLE), PDFs, shortcuts, archives, HTA/HTML.
_ESCALATION_TYPES = {"pe", "elf", "script", "office", "pdf", "lnk", "archive", "html"}
# Plain text / config / logs — there is nothing for a sandbox to execute, so never
# waste a VM run on them even when Tier-2 was requested.
_INERT_FILETYPES = {"text"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_job_id() -> str:
    return uuid.uuid4().hex


async def _save(job: AnalysisJob) -> None:
    job.updated_at = _now()
    await state_store.save_job(job.model_dump(mode="json"))


async def create_and_dispatch(
    *,
    source: str,
    customer_code: str,
    tiers: List[Tier],
    sample_bytes: Optional[bytes] = None,
    filename: str = "sample",
    sha256: str = "",
    refs: Optional[Dict[str, Any]] = None,
) -> tuple[str, bool]:
    """Return (job_id, needs_run).

    A COMPLETE cached result short-circuits (needs_run False). An incomplete/failed
    prior result, or no result at all, creates a fresh job and needs_run is True so
    the caller schedules :func:`run`.
    """
    if sha256:
        cached = await state_store.find_cached_job_id(customer_code, sha256)
        if cached:
            logger.info(f"cache hit (complete) for {sha256[:12]} ({customer_code}) -> job {cached}")
            return cached, False

    job = AnalysisJob(
        job_id=new_job_id(),
        sha256=sha256,
        filename=filename,
        customer_code=customer_code,
        source=source,
        status=Status.QUEUED,
        static_status=Status.QUEUED,
        created_at=_now(),
    )
    await _save(job)
    return job.job_id, True


async def run(
    job_id: str,
    *,
    sample_bytes: Optional[bytes],
    tiers: List[Tier],
    refs: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    reputation_mode: str = "lookup",
) -> None:
    """Execute the full pipeline for a job. Runs in the background.

    ``reputation_mode`` controls the VirusTotal phase, chosen per-submission:
      * ``"off"``    — skip VirusTotal entirely (nothing leaves the host).
      * ``"lookup"`` — hash lookup only; the file is NEVER uploaded (default).
      * ``"upload"`` — hash lookup, and upload the file if VT has not seen it
                        (this PUBLISHES the file on VirusTotal).
    Tier-2 detonation is gated by ``Tier.DYNAMIC in tiers``.
    """
    job_dict = await state_store.load_job(job_id)
    if not job_dict:
        logger.error(f"run: job {job_id} not found")
        return
    job = AnalysisJob(**job_dict)

    try:
        # 1. Resolve the sample bytes (upload passes them in; flow/host_path fetch).
        if sample_bytes is None:
            sample_bytes = await _resolve_sample(job, refs)
        if sample_bytes is None:
            job.status = Status.FAILED
            job.static_status = Status.FAILED
            job.error = "sample could not be retrieved (file gone?)"
            await _save(job)
            return

        # 2. Tier 1 — always.
        job.status = Status.RUNNING
        job.static_status = Status.RUNNING
        await _save(job)

        inspector_job = {
            "sha256": job.sha256,
            "filename": job.filename,
            "customer_code": job.customer_code,
            "context": context or {},
        }
        inspector, previews = await _inspect_with_retry(sample_bytes, inspector_job)

        job.sha256 = inspector.get("sha256", job.sha256)
        job.hardened = bool(inspector.get("hardened", True))
        static_verdict = inspector.get("verdict_hint", "clean")

        # Persist previews (as PNG objects) and collect their names.
        preview_names: List[str] = []
        for name, data in previews.items():
            await state_store.save_preview(job.customer_code, job.sha256, name, data)
            preview_names.append(name)

        # 3. FAST VirusTotal hash lookup — done BEFORE detonation, not after, so a
        #    file VT already knows (e.g. any signed system binary) resolves in ~1s
        #    instead of making the analyst wait minutes behind the sandbox VM. If VT
        #    has never seen the file and submission is enabled, the upload+scan runs
        #    DETACHED (step 7) and patches the result later.
        from app.file_analysis.services.reputation import virustotal_lookup_only

        reputation = None
        if reputation_mode == "off":
            # Explicit sentinel so the UI shows "not run" instead of a perpetual
            # "checking reputation…" (it otherwise can't tell "off" from "pending").
            reputation = {"source": "virustotal", "skipped": True, "note": "VirusTotal was turned off for this analysis."}
        else:
            try:
                reputation = await virustotal_lookup_only(job.sha256)
            except Exception as exc:
                logger.warning(f"reputation lookup failed for {job.sha256[:12]}: {exc}")

        # Upload ONLY when the analyst explicitly chose it — uploading publishes the
        # file on VirusTotal, so it is never the default (see CLAUDE.md golden rule 7).
        submit_pending = bool(
            reputation_mode == "upload"
            and reputation is not None
            and not reputation.get("found")
            and sample_bytes
        )
        if submit_pending:
            reputation = {
                "source": "virustotal",
                "found": False,
                "sha256": job.sha256,
                "submitted": True,
                "note": "uploading to VirusTotal — scan in progress…",
                "permalink": f"https://www.virustotal.com/gui/file/{job.sha256}",
            }

        # 4. Save an INTERIM result immediately (Tier-1 + reputation) so Preview/
        #    Content/Metadata AND VirusTotal show in seconds while the sandbox runs.
        job.sandbox_enabled = await _sandbox_available()
        job.static_status = Status.DONE
        job.verdict = Verdict(static_verdict)
        interim = {
            "job": job.model_dump(mode="json"),
            "inspector": inspector,
            "sandbox": None,
            "reputation": reputation,
            "preview_urls": preview_names,
            "engine_version": state_store.ENGINE_VERSION,
        }
        await state_store.save_result(job.customer_code, job.sha256, interim)
        await _save(job)

        # 5. Tier 2 — only if a backend is available AND escalation is warranted.
        sandbox_summary: Optional[Dict[str, Any]] = None
        if job.sandbox_enabled and Tier.DYNAMIC in tiers and _should_escalate(inspector, job.source):
            job.dynamic_status = Status.RUNNING
            await _save(job)
            sandbox_summary = await _detonate(sample_bytes, inspector, job)
            job.dynamic_status = Status.DONE if sandbox_summary is not None else Status.FAILED

        # 6. Final verdict + persist. Job is DONE now (previews/content stable).
        from app.file_analysis.services.verdict import explain_verdict

        result = {
            "job": None,  # filled below
            "inspector": inspector,
            "sandbox": sandbox_summary,
            "reputation": reputation,
            "preview_urls": preview_names,
            "engine_version": state_store.ENGINE_VERSION,
            "verdict_reason": explain_verdict(static_verdict, sandbox_summary, reputation, inspector),
        }
        job.verdict = Verdict(_merge_verdict(static_verdict, sandbox_summary, reputation))
        job.status = Status.DONE
        result["job"] = job.model_dump(mode="json")
        await state_store.save_result(job.customer_code, job.sha256, result)
        await _save(job)

        # 7. Detached VT upload+scan (does NOT block job completion).
        if submit_pending:
            import asyncio

            asyncio.create_task(_submit_and_patch(job.job_id, job.customer_code, job.sha256, sample_bytes, job.filename, static_verdict))

    except Exception as exc:  # never leave a job dangling
        logger.exception(f"orchestrator run failed for {job_id}: {exc}")
        job.status = Status.FAILED
        job.error = str(exc)
        await _save(job)


# --- steps -----------------------------------------------------------------
async def _resolve_sample(job: AnalysisJob, refs: Optional[Dict[str, Any]]) -> Optional[bytes]:
    """Collect and fetch bytes from an endpoint via Velociraptor (source=host_path)."""
    from app.file_analysis.services import velociraptor_fetch as vf

    refs = refs or {}
    try:
        if job.source != "host_path":
            return None
        # The UI sends a hostname (picked from the agent dropdown); resolve it to
        # a client_id here so the operator never deals with raw client_ids.
        client_id = refs.get("client_id")
        if not client_id and refs.get("hostname"):
            client_id = await vf.resolve_client_id(refs["hostname"])
        if not client_id:
            logger.error(f"host_path: could not resolve an agent from refs={refs}")
            return None
        local = await vf.collect_and_fetch(client_id, refs["target_path"], job.customer_code)
        if local is None:
            return None
        job.sha256 = local.sha256
        job.filename = local.original_filename
        with open(local.path, "rb") as fh:
            return fh.read()
    except Exception as exc:
        logger.error(f"sample resolve failed: {exc}")
        return None


async def _inspect_with_retry(sample_bytes: bytes, inspector_job: Dict[str, Any], attempts: int = 5):
    import asyncio

    for attempt in range(attempts):
        try:
            return await inspect(sample_bytes, inspector_job)
        except InspectorBusy:
            await asyncio.sleep(2 ** attempt)
    # Give up gracefully: incomplete result rather than a lost job.
    return (
        {**inspector_job, "filetype": "unknown", "analysis_incomplete": True, "flags": ["analysis_incomplete"], "verdict_hint": "suspicious"},
        {},
    )


async def _sandbox_available() -> bool:
    try:
        from app.file_analysis.services.sandbox import get_backend

        return await get_backend().available()
    except Exception:
        return False


def _should_escalate(inspector: Dict[str, Any], source: str) -> bool:
    """Whether to send this file to the sandbox.

    We only get here once Tier-2 has ALREADY been requested for the job (the analyst
    turned the sandbox on, or the source auto-selected it), so honour that intent:
    detonate any recognised runnable family, anything that raised a suspicious flag,
    OR any file we simply couldn't classify (an unrecognised binary is exactly what
    you want to detonate). The only thing skipped is plain inert text/config/logs.
    """
    filetype = inspector.get("filetype", "")
    if filetype in _ESCALATION_TYPES:
        return True
    if set(inspector.get("flags", [])) & _ESCALATION_FLAGS:
        return True
    return filetype not in _INERT_FILETYPES


async def _detonate(sample_bytes: bytes, inspector: Dict[str, Any], job: AnalysisJob) -> Optional[Dict[str, Any]]:
    import tempfile

    from app.file_analysis.services.sandbox import get_backend
    from app.file_analysis.services.sandbox import package_for  # noqa: F401 (kept for explicit-package override)
    from app.file_analysis.services.sandbox.cape import summarize

    backend = get_backend()
    tmp = None
    try:
        import os as _os

        fd, tmp = tempfile.mkstemp(prefix="deto_")
        with _os.fdopen(fd, "wb") as fh:
            fh.write(sample_bytes)
        existing = await backend.find_by_sha256(job.sha256)
        # Empty package => CAPE auto-detects the sample and routes it to a matching
        # guest (robust across Linux + Windows guests). Set CAPE_PACKAGE to force one
        # (e.g. package_for(filetype) once a Windows guest is added).
        package = os.getenv("CAPE_PACKAGE", "").strip()
        ref = existing or await backend.submit(tmp, package, job.customer_code, job.source)
        await backend.wait_for_report(ref)
        report = await backend.get_report(ref)
        return summarize(report).to_dict()
    except Exception as exc:
        logger.error(f"detonation failed for {job.sha256[:12]}: {exc}")
        return None
    finally:
        if tmp:
            try:
                import os as _os

                _os.remove(tmp)
            except OSError:
                pass


async def _submit_and_patch(
    job_id: str,
    customer_code: str,
    sha256: str,
    sample_bytes: Optional[bytes],
    filename: str,
    static_verdict: str,
) -> None:
    """Detached: upload to VT, wait for the scan, then patch the stored result."""
    try:
        from app.file_analysis.services.reputation import virustotal_submit_and_wait

        rep = await virustotal_submit_and_wait(sha256, sample_bytes, filename)
        if rep is None:
            return
        result = await state_store.load_result(customer_code, sha256)
        if not result:
            return
        from app.file_analysis.services.verdict import explain_verdict

        result["reputation"] = rep
        # Reputation just landed — the explanation must reflect it too.
        result["verdict_reason"] = explain_verdict(static_verdict, result.get("sandbox"), rep, result.get("inspector"))
        job_dict = result.get("job", {}) or {}
        job_dict["verdict"] = _merge_verdict(static_verdict, result.get("sandbox"), rep)
        job_dict["updated_at"] = _now()
        result["job"] = job_dict
        await state_store.save_result(customer_code, sha256, result)
        await state_store.save_job(job_dict)
        logger.info(f"[reputation] patched VirusTotal result for {sha256[:12]} (found={rep.get('found')})")
    except Exception as exc:
        logger.warning(f"detached VT submit failed for {sha256[:12]}: {exc}")


def _merge_verdict(static_verdict: str, sandbox: Optional[Dict[str, Any]], reputation: Optional[Dict[str, Any]] = None) -> str:
    from app.file_analysis.services.reputation import verdict_from_reputation
    from app.file_analysis.services.verdict import dynamic_verdict_from_report
    from app.file_analysis.services.verdict import merge_verdict

    dyn = dynamic_verdict_from_report(sandbox) if sandbox else None
    merged = merge_verdict(static_verdict, dyn)
    # Reputation raises only — fold it in as another tier.
    return merge_verdict(merged, verdict_from_reputation(reputation))


