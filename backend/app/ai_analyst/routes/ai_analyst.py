from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_analyst.schema.ai_analyst import AlertAnalysisResponse
from app.ai_analyst.schema.ai_analyst import AlertsWithReportsListResponse
from app.ai_analyst.schema.ai_analyst import CreateJobRequest
from app.ai_analyst.schema.ai_analyst import CreateJobResponse
from app.ai_analyst.schema.ai_analyst import IocListResponse
from app.ai_analyst.schema.ai_analyst import JobListResponse
from app.ai_analyst.schema.ai_analyst import PalaceSearchResponse
from app.ai_analyst.schema.ai_analyst import QueuePalaceLessonRequest
from app.ai_analyst.schema.ai_analyst import QueuePalaceLessonResponse
from app.ai_analyst.schema.ai_analyst import ReplayRequest
from app.ai_analyst.schema.ai_analyst import ReplayResponse
from app.ai_analyst.schema.ai_analyst import ReportListResponse
from app.ai_analyst.schema.ai_analyst import ReviewListResponse
from app.ai_analyst.schema.ai_analyst import SubmitIocsRequest
from app.ai_analyst.schema.ai_analyst import SubmitIocsResponse
from app.ai_analyst.schema.ai_analyst import SubmitReportRequest
from app.ai_analyst.schema.ai_analyst import SubmitReportResponse
from app.ai_analyst.schema.ai_analyst import SubmitReviewRequest
from app.ai_analyst.schema.ai_analyst import SubmitReviewResponse
from app.ai_analyst.schema.ai_analyst import UpdateJobRequest
from app.ai_analyst.schema.ai_analyst import UpdateJobResponse
from app.ai_analyst.services.ai_analyst import create_job
from app.ai_analyst.services.ai_analyst import get_alert_analysis
from app.ai_analyst.services.ai_analyst import get_job
from app.ai_analyst.services.ai_analyst import list_alerts_with_reports
from app.ai_analyst.services.ai_analyst import list_iocs_by_alert
from app.ai_analyst.services.ai_analyst import list_iocs_by_customer
from app.ai_analyst.services.ai_analyst import list_iocs_by_report
from app.ai_analyst.services.ai_analyst import list_jobs_by_alert
from app.ai_analyst.services.ai_analyst import list_jobs_by_customer
from app.ai_analyst.services.ai_analyst import list_reports_by_alert
from app.ai_analyst.services.ai_analyst import list_reviews_by_customer
from app.ai_analyst.services.ai_analyst import queue_palace_lesson
from app.ai_analyst.services.ai_analyst import submit_iocs
from app.ai_analyst.services.ai_analyst import submit_report
from app.ai_analyst.services.ai_analyst import submit_review
from app.ai_analyst.services.ai_analyst import update_job
from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.services.talon import replay_investigation as talon_replay_investigation
from app.connectors.talon.services.talon import search_palace_lessons as talon_search_palace_lessons
from app.db.db_session import get_db
from app.db.universal_models import AiAnalystReport

ai_analyst_router = APIRouter()


# --- Job endpoints ---


@ai_analyst_router.post(
    "/jobs",
    response_model=CreateJobResponse,
    description="Register a new AI analyst investigation job",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_job_route(
    request: CreateJobRequest,
    session: AsyncSession = Depends(get_db),
) -> CreateJobResponse:
    logger.info(f"Creating AI analyst job for alert {request.alert_id}")
    return await create_job(request, session)


@ai_analyst_router.patch(
    "/jobs/{job_id}",
    response_model=UpdateJobResponse,
    description="Update an AI analyst job status",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_job_route(
    job_id: str,
    request: UpdateJobRequest,
    session: AsyncSession = Depends(get_db),
) -> UpdateJobResponse:
    logger.info(f"Updating AI analyst job {job_id}")
    return await update_job(job_id, request, session)


@ai_analyst_router.get(
    "/jobs/{job_id}",
    response_model=CreateJobResponse,
    description="Get a specific AI analyst job",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_job_route(
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> CreateJobResponse:
    job = await get_job(job_id, session)
    return CreateJobResponse(success=True, message="Job retrieved", job=job)


@ai_analyst_router.get(
    "/jobs/alert/{alert_id}",
    response_model=JobListResponse,
    description="List all AI analyst jobs for an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_jobs_by_alert_route(
    alert_id: int,
    session: AsyncSession = Depends(get_db),
) -> JobListResponse:
    jobs = await list_jobs_by_alert(alert_id, session)
    return JobListResponse(success=True, message="Jobs retrieved", jobs=jobs)


@ai_analyst_router.get(
    "/jobs/customer/{customer_code}",
    response_model=JobListResponse,
    description="List all AI analyst jobs for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_jobs_by_customer_route(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> JobListResponse:
    jobs = await list_jobs_by_customer(customer_code, session)
    return JobListResponse(success=True, message="Jobs retrieved", jobs=jobs)


# --- Report endpoints ---


@ai_analyst_router.post(
    "/reports",
    response_model=SubmitReportResponse,
    description="Submit an AI analyst investigation report",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def submit_report_route(
    request: SubmitReportRequest,
    session: AsyncSession = Depends(get_db),
) -> SubmitReportResponse:
    logger.info(f"Submitting AI analyst report for job {request.job_id}")
    return await submit_report(request, session)


@ai_analyst_router.get(
    "/reports/alert/{alert_id}",
    response_model=ReportListResponse,
    description="List all AI analyst reports for an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_reports_by_alert_route(
    alert_id: int,
    session: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    reports = await list_reports_by_alert(alert_id, session)
    return ReportListResponse(success=True, message="Reports retrieved", reports=reports)


# --- IOC endpoints ---


@ai_analyst_router.post(
    "/iocs",
    response_model=SubmitIocsResponse,
    description="Submit extracted IOCs for a report",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def submit_iocs_route(
    request: SubmitIocsRequest,
    session: AsyncSession = Depends(get_db),
) -> SubmitIocsResponse:
    logger.info(f"Submitting IOCs for report {request.report_id}")
    return await submit_iocs(request, session)


@ai_analyst_router.get(
    "/iocs/report/{report_id}",
    response_model=IocListResponse,
    description="List IOCs for a specific report",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_iocs_by_report_route(
    report_id: int,
    session: AsyncSession = Depends(get_db),
) -> IocListResponse:
    iocs = await list_iocs_by_report(report_id, session)
    return IocListResponse(success=True, message="IOCs retrieved", iocs=iocs)


@ai_analyst_router.get(
    "/iocs/alert/{alert_id}",
    response_model=IocListResponse,
    description="List all IOCs for an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_iocs_by_alert_route(
    alert_id: int,
    session: AsyncSession = Depends(get_db),
) -> IocListResponse:
    iocs = await list_iocs_by_alert(alert_id, session)
    return IocListResponse(success=True, message="IOCs retrieved", iocs=iocs)


@ai_analyst_router.get(
    "/iocs/customer/{customer_code}",
    response_model=IocListResponse,
    description="List IOCs for a customer, optionally filtered by VT verdict",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_iocs_by_customer_route(
    customer_code: str,
    vt_verdict: Optional[str] = Query(None, description="Filter by VirusTotal verdict"),
    session: AsyncSession = Depends(get_db),
) -> IocListResponse:
    iocs = await list_iocs_by_customer(customer_code, session, vt_verdict=vt_verdict)
    return IocListResponse(success=True, message="IOCs retrieved", iocs=iocs)


# --- Alerts with reports ---


@ai_analyst_router.get(
    "/alerts_with_reports",
    response_model=AlertsWithReportsListResponse,
    description="List all alerts that have an AI analyst report",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_alerts_with_reports_route(
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    session: AsyncSession = Depends(get_db),
) -> AlertsWithReportsListResponse:
    alerts = await list_alerts_with_reports(session, customer_code=customer_code)
    return AlertsWithReportsListResponse(
        success=True,
        message=f"{len(alerts)} alerts with reports found",
        alerts=alerts,
    )


# --- Combined alert analysis endpoint ---


@ai_analyst_router.get(
    "/alert/{alert_id}",
    response_model=AlertAnalysisResponse,
    description="Get the full AI analysis for an alert (job, report, IOCs)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_alert_analysis_route(
    alert_id: int,
    session: AsyncSession = Depends(get_db),
) -> AlertAnalysisResponse:
    job, report, iocs = await get_alert_analysis(alert_id, session)
    if not job:
        return AlertAnalysisResponse(success=False, message="No AI analysis found for this alert")
    return AlertAnalysisResponse(
        success=True,
        message="Alert analysis retrieved",
        job=job,
        report=report,
        iocs=iocs,
    )


# --- Review / Palace lesson / Replay endpoints ---


@ai_analyst_router.post(
    "/reports/{report_id}/review",
    response_model=SubmitReviewResponse,
    description="Submit an analyst review (rubric + IOC corrections) for a report",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def submit_review_route(
    report_id: int,
    request: SubmitReviewRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SubmitReviewResponse:
    """
    Persist an analyst review rubric + per-IOC corrections. Scope gated
    (admin OR analyst) via require_any_scope; the authenticated user's id is
    captured as reviewer_user_id for audit.
    """
    logger.info(f"User {current_user.id} submitting review for report {report_id}")
    return await submit_review(
        report_id=report_id,
        request=request,
        reviewer_user_id=current_user.id,
        session=session,
    )


@ai_analyst_router.post(
    "/reports/{report_id}/replay",
    response_model=ReplayResponse,
    description="Replay an investigation for the given report's alert with a forced template override",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def replay_report_route(
    report_id: int,
    request: ReplayRequest,
    session: AsyncSession = Depends(get_db),
) -> ReplayResponse:
    """
    Triggers Talon POST /investigate with template_override. The new run will
    create its own AiAnalystJob/Report via Talon's existing webhook callbacks —
    this endpoint does not mutate local DB itself.
    """
    report = await session.get(AiAnalystReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    # Guard: customer_code from the client must match the report's, preventing
    # replay injection across tenants
    if request.customer_code != report.customer_code:
        raise HTTPException(
            status_code=400,
            detail=(
                f"customer_code mismatch: report belongs to {report.customer_code}, "
                f"got {request.customer_code}"
            ),
        )

    logger.info(
        f"Replaying investigation for report {report_id} (alert {report.alert_id}) "
        f"with template_override={request.template_override}",
    )
    talon_response = await talon_replay_investigation(
        alert_id=report.alert_id,
        customer_code=request.customer_code,
        template_override=request.template_override,
        sender=request.sender,
    )
    return ReplayResponse(
        success=True,
        message="Replay triggered",
        data=talon_response.get("data"),
    )


@ai_analyst_router.post(
    "/palace_lessons",
    response_model=QueuePalaceLessonResponse,
    description="Queue a MemPalace lesson for async ingestion by the NanoClaw drainer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def queue_palace_lesson_route(
    request: QueuePalaceLessonRequest,
    session: AsyncSession = Depends(get_db),
) -> QueuePalaceLessonResponse:
    logger.info(f"Queuing palace lesson for customer {request.customer_code}")
    return await queue_palace_lesson(request, session)


@ai_analyst_router.get(
    "/reviews/customer/{customer_code}",
    response_model=ReviewListResponse,
    description="Review dashboard feed for a customer (newest first, with per-IOC reviews)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_reviews_by_customer_route(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> ReviewListResponse:
    reviews = await list_reviews_by_customer(customer_code, session)
    return ReviewListResponse(
        success=True,
        message=f"{len(reviews)} reviews retrieved",
        reviews=reviews,
    )


@ai_analyst_router.get(
    "/palace_lessons/customer/{customer_code}",
    response_model=PalaceSearchResponse,
    description="Preview similar MemPalace lessons for a customer (proxies to Talon /palace/search)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def search_palace_lessons_route(
    customer_code: str,
    query: str = Query(..., min_length=1, description="Semantic search query"),
    room: Optional[str] = Query(None, description="Optional room filter"),
    limit: int = Query(5, ge=1, le=25, description="Max hits"),
) -> PalaceSearchResponse:
    logger.info(
        f"Searching palace for customer={customer_code} query={query!r} room={room} limit={limit}",
    )
    talon_response = await talon_search_palace_lessons(
        customer_code=customer_code,
        query=query,
        room=room,
        limit=limit,
    )
    # Talon returns {data: {...}} — try to extract the lessons list regardless of shape
    data = talon_response.get("data") or {}
    raw_lessons = data.get("lessons") if isinstance(data, dict) else None
    if raw_lessons is None and isinstance(data, list):
        raw_lessons = data
    if raw_lessons is None:
        raw_lessons = []
    return PalaceSearchResponse(
        success=True,
        message=f"{len(raw_lessons)} palace lessons matched",
        lessons=raw_lessons,
    )
