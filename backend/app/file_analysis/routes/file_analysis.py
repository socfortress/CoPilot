"""REST routes for Tier 1 static file analysis.

Admin and analyst only. ``customer_user`` is deliberately absent: Phase 1 has no
Customer Portal surface, and widening the scope here would expose every tenant's
submissions to every portal user, since these handlers trust the scope check.

Route order matters inside a single router -- the static ``/inspectors`` and
``/flags`` paths are declared before anything with a path parameter, because a
wildcard declared above them would swallow the literal and try to parse it as
the parameter.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import File
from fastapi import Query
from fastapi import Security
from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.file_analysis.schema.file_analysis import FileAnalysisFindingRead
from app.file_analysis.schema.file_analysis import FileAnalysisIoCRead
from app.file_analysis.schema.file_analysis import FileAnalysisJobDetail
from app.file_analysis.schema.file_analysis import FileAnalysisJobDetailResponse
from app.file_analysis.schema.file_analysis import FileAnalysisJobListResponse
from app.file_analysis.schema.file_analysis import FileAnalysisJobRead
from app.file_analysis.schema.file_analysis import FileAnalysisJobResponse
from app.file_analysis.schema.file_analysis import FlagCatalogueResponse
from app.file_analysis.schema.file_analysis import FlagDescriptor
from app.file_analysis.schema.file_analysis import InspectorDescriptor
from app.file_analysis.schema.file_analysis import InspectorListResponse
from app.file_analysis.services import analysis as svc
from app.file_analysis.services import scoring
from app.file_analysis.services.inspectors import all_inspectors
from app.middleware.customer_access import verify_customer_code_access
from app.middleware.customer_access import verify_optional_customer_code_access

file_analysis_router = APIRouter()


# ---------------------------------------------------------------------------
# Static metadata routes -- declared first, before any path parameter
# ---------------------------------------------------------------------------


@file_analysis_router.get(
    "/file_analysis/inspectors",
    response_model=InspectorListResponse,
    description="List the registered static inspectors and the types they claim.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_inspectors_route() -> InspectorListResponse:
    inspectors = [
        InspectorDescriptor(
            name=inspector.name,
            mime_types=list(inspector.mime_types),
            extensions=list(inspector.extensions),
        )
        for inspector in all_inspectors()
    ]
    return InspectorListResponse(
        success=True,
        message=f"{len(inspectors)} inspector(s) registered",
        inspectors=inspectors,
    )


@file_analysis_router.get(
    "/file_analysis/flags",
    response_model=FlagCatalogueResponse,
    description="The behaviour flag catalogue with weights and the verdict thresholds.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def flag_catalogue_route() -> FlagCatalogueResponse:
    flags = [
        FlagDescriptor(flag=flag, category=spec.category, title=spec.title, severity=spec.severity, weight=spec.weight)
        for flag, spec in sorted(scoring.FLAG_CATALOGUE.items())
    ]
    return FlagCatalogueResponse(
        success=True,
        message=f"{len(flags)} flag(s) in the catalogue",
        flags=flags,
        suspicious_threshold=scoring.SUSPICIOUS_THRESHOLD,
        malicious_threshold=scoring.MALICIOUS_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


@file_analysis_router.post(
    "/file_analysis/customers/{customer_code}/jobs",
    response_model=FileAnalysisJobResponse,
    status_code=202,
    description="Submit a file for Tier 1 static analysis. Returns as soon as the sample is stored; analysis runs out of band.",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def submit_job_route(
    customer_code: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="The sample to inspect"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> FileAnalysisJobResponse:
    submitted_by = getattr(current_user, "username", None) or str(current_user.id)
    logger.info(f"file_analysis: {submitted_by} submitting {file.filename} for customer {customer_code}")

    job = await svc.create_job(
        customer_code=customer_code,
        file=file,
        submitted_by=submitted_by,
        session=session,
    )

    background_tasks.add_task(svc.run_analysis, job.job_uuid)

    return FileAnalysisJobResponse(
        success=True,
        message="File accepted; analysis queued",
        job=FileAnalysisJobRead.model_validate(job),
    )


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


@file_analysis_router.get(
    "/file_analysis/jobs",
    response_model=FileAnalysisJobListResponse,
    description="List analysis jobs the caller may see, newest first.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_jobs_route(
    customer_code: Optional[str] = Depends(verify_optional_customer_code_access),
    status: Optional[str] = Query(None, description="pending | running | completed | failed"),
    verdict: Optional[str] = Query(None, description="clean | suspicious | malicious | unknown"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> FileAnalysisJobListResponse:
    jobs, total = await svc.list_jobs(
        user=current_user,
        session=session,
        customer_code=customer_code,
        status=status,
        verdict=verdict,
        limit=limit,
        offset=offset,
    )

    return FileAnalysisJobListResponse(
        success=True,
        message=f"{len(jobs)} job(s) retrieved",
        jobs=[FileAnalysisJobRead.model_validate(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@file_analysis_router.get(
    "/file_analysis/jobs/{job_uuid}",
    response_model=FileAnalysisJobDetailResponse,
    description="One analysis job with its findings and extracted indicators.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_job_route(
    job_uuid: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> FileAnalysisJobDetailResponse:
    # Tenancy is enforced inside the service, not by a route dependency: the
    # customer is a property of the job, not of the path, so it cannot be
    # checked until the row has been read.
    job = await svc.get_job(job_uuid, current_user, session)
    findings = await svc.get_findings(job, session)
    iocs = await svc.get_iocs(job, session)

    detail = FileAnalysisJobDetail.model_validate(job)
    detail.findings = [FileAnalysisFindingRead.model_validate(f) for f in findings]
    detail.iocs = [FileAnalysisIoCRead.model_validate(i) for i in iocs]

    return FileAnalysisJobDetailResponse(
        success=True,
        message="Job retrieved",
        job=detail,
    )
