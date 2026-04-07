from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.ai_analyst.schema.ai_analyst import AlertAnalysisResponse
from app.ai_analyst.schema.ai_analyst import CreateJobRequest
from app.ai_analyst.schema.ai_analyst import CreateJobResponse
from app.ai_analyst.schema.ai_analyst import IocListResponse
from app.ai_analyst.schema.ai_analyst import JobListResponse
from app.ai_analyst.schema.ai_analyst import JobResponse
from app.ai_analyst.schema.ai_analyst import ReportListResponse
from app.ai_analyst.schema.ai_analyst import SubmitIocsRequest
from app.ai_analyst.schema.ai_analyst import SubmitIocsResponse
from app.ai_analyst.schema.ai_analyst import SubmitReportRequest
from app.ai_analyst.schema.ai_analyst import SubmitReportResponse
from app.ai_analyst.schema.ai_analyst import UpdateJobRequest
from app.ai_analyst.schema.ai_analyst import UpdateJobResponse
from app.ai_analyst.services.ai_analyst import create_job
from app.ai_analyst.services.ai_analyst import get_alert_analysis
from app.ai_analyst.services.ai_analyst import get_job
from app.ai_analyst.services.ai_analyst import list_iocs_by_alert
from app.ai_analyst.services.ai_analyst import list_iocs_by_customer
from app.ai_analyst.services.ai_analyst import list_iocs_by_report
from app.ai_analyst.services.ai_analyst import list_jobs_by_alert
from app.ai_analyst.services.ai_analyst import list_jobs_by_customer
from app.ai_analyst.services.ai_analyst import list_reports_by_alert
from app.ai_analyst.services.ai_analyst import submit_iocs
from app.ai_analyst.services.ai_analyst import submit_report
from app.ai_analyst.services.ai_analyst import update_job

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
