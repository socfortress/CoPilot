from datetime import datetime
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.ai_analyst.schema.ai_analyst import AlertWithReportResponse
from app.ai_analyst.schema.ai_analyst import CreateJobRequest
from app.ai_analyst.schema.ai_analyst import CreateJobResponse
from app.ai_analyst.schema.ai_analyst import IocResponse
from app.ai_analyst.schema.ai_analyst import IocReviewResponse
from app.ai_analyst.schema.ai_analyst import JobResponse
from app.ai_analyst.schema.ai_analyst import PalaceLessonResponse
from app.ai_analyst.schema.ai_analyst import QueuePalaceLessonRequest
from app.ai_analyst.schema.ai_analyst import QueuePalaceLessonResponse
from app.ai_analyst.schema.ai_analyst import ReportResponse
from app.ai_analyst.schema.ai_analyst import ReviewResponse
from app.ai_analyst.schema.ai_analyst import SubmitIocsRequest
from app.ai_analyst.schema.ai_analyst import SubmitIocsResponse
from app.ai_analyst.schema.ai_analyst import SubmitReportRequest
from app.ai_analyst.schema.ai_analyst import SubmitReportResponse
from app.ai_analyst.schema.ai_analyst import SubmitReviewRequest
from app.ai_analyst.schema.ai_analyst import SubmitReviewResponse
from app.ai_analyst.schema.ai_analyst import UpdateJobRequest
from app.ai_analyst.schema.ai_analyst import UpdateJobResponse
from app.db.universal_models import AiAnalystIoc
from app.db.universal_models import AiAnalystIocReview
from app.db.universal_models import AiAnalystJob
from app.db.universal_models import AiAnalystPalaceLesson
from app.db.universal_models import AiAnalystReport
from app.db.universal_models import AiAnalystReview
from app.incidents.models import Alert


def _job_to_response(job: AiAnalystJob) -> JobResponse:
    return JobResponse(
        id=job.id,
        alert_id=job.alert_id,
        customer_code=job.customer_code,
        status=job.status,
        alert_type=job.alert_type,
        triggered_by=job.triggered_by,
        template_used=job.template_used,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


def _report_to_response(report: AiAnalystReport) -> ReportResponse:
    return ReportResponse(
        id=report.id,
        job_id=report.job_id,
        alert_id=report.alert_id,
        customer_code=report.customer_code,
        severity_assessment=report.severity_assessment,
        summary=report.summary,
        report_markdown=report.report_markdown,
        recommended_actions=report.recommended_actions,
        created_at=report.created_at,
    )


def _ioc_to_response(ioc: AiAnalystIoc) -> IocResponse:
    return IocResponse(
        id=ioc.id,
        report_id=ioc.report_id,
        alert_id=ioc.alert_id,
        customer_code=ioc.customer_code,
        ioc_value=ioc.ioc_value,
        ioc_type=ioc.ioc_type,
        vt_verdict=ioc.vt_verdict,
        vt_score=ioc.vt_score,
        details=ioc.details,
        created_at=ioc.created_at,
    )


# --- Job operations ---


async def create_job(request: CreateJobRequest, session: AsyncSession) -> CreateJobResponse:
    logger.info(f"Creating AI analyst job {request.id} for alert {request.alert_id}")

    # Check if job already exists (may have been auto-created by an early status update)
    existing = await session.get(AiAnalystJob, request.id)
    if existing:
        logger.info(f"Job {request.id} already exists, updating fields")
        if request.alert_type is not None:
            existing.alert_type = request.alert_type
        if request.template_used is not None:
            existing.template_used = request.template_used
        existing.triggered_by = request.triggered_by.value
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return CreateJobResponse(success=True, message="Job updated", job=_job_to_response(existing))

    job = AiAnalystJob(
        id=request.id,
        alert_id=request.alert_id,
        customer_code=request.customer_code,
        status="pending",
        alert_type=request.alert_type,
        triggered_by=request.triggered_by.value,
        template_used=request.template_used,
        created_at=datetime.utcnow(),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    logger.info(f"AI analyst job {job.id} created successfully")
    return CreateJobResponse(success=True, message="Job created", job=_job_to_response(job))


async def _auto_create_job_from_id(job_id: str, session: AsyncSession) -> Optional[AiAnalystJob]:
    """
    Parse a job ID in the format 'copilot-inv-{alert_id}-{timestamp}' and
    auto-create the job record by looking up the alert for customer_code.
    Returns the created job, or None if parsing/lookup fails.
    """
    import re

    match = re.match(r"^copilot-inv-(\d+)-\d+$", job_id)
    if not match:
        logger.warning(f"Cannot parse alert_id from job ID: {job_id}")
        return None

    alert_id = int(match.group(1))
    alert = await session.get(Alert, alert_id)
    if not alert:
        logger.warning(f"Alert {alert_id} not found, cannot auto-create job {job_id}")
        return None

    job = AiAnalystJob(
        id=job_id,
        alert_id=alert_id,
        customer_code=alert.customer_code,
        status="pending",
        triggered_by="webhook",
        created_at=datetime.utcnow(),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    logger.info(f"Auto-created AI analyst job {job_id} for alert {alert_id}")
    return job


async def update_job(job_id: str, request: UpdateJobRequest, session: AsyncSession) -> UpdateJobResponse:
    logger.info(f"Updating AI analyst job {job_id} to status {request.status}")

    job = await session.get(AiAnalystJob, job_id)
    if not job:
        # Auto-create the job if it doesn't exist yet (handles race condition
        # where Talon sends a status update before the create request arrives)
        logger.info(f"Job {job_id} not found, attempting to auto-create from job ID")
        job = await _auto_create_job_from_id(job_id, session)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found and could not be auto-created")

    job.status = request.status.value

    if request.alert_type is not None:
        job.alert_type = request.alert_type
    if request.template_used is not None:
        job.template_used = request.template_used
    if request.error_message is not None:
        job.error_message = request.error_message

    if request.status.value == "running" and job.started_at is None:
        job.started_at = datetime.utcnow()
    elif request.status.value in ("completed", "failed"):
        job.completed_at = datetime.utcnow()

    session.add(job)
    await session.commit()
    await session.refresh(job)

    logger.info(f"AI analyst job {job_id} updated to {request.status}")
    return UpdateJobResponse(success=True, message="Job updated", job=_job_to_response(job))


async def get_job(job_id: str, session: AsyncSession) -> JobResponse:
    job = await session.get(AiAnalystJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _job_to_response(job)


async def list_jobs_by_alert(alert_id: int, session: AsyncSession) -> List[JobResponse]:
    result = await session.execute(
        select(AiAnalystJob).where(AiAnalystJob.alert_id == alert_id).order_by(AiAnalystJob.created_at.desc()),
    )
    jobs = result.scalars().all()
    return [_job_to_response(j) for j in jobs]


async def list_jobs_by_customer(customer_code: str, session: AsyncSession) -> List[JobResponse]:
    result = await session.execute(
        select(AiAnalystJob).where(AiAnalystJob.customer_code == customer_code).order_by(AiAnalystJob.created_at.desc()),
    )
    jobs = result.scalars().all()
    return [_job_to_response(j) for j in jobs]


# --- Report operations ---


async def submit_report(request: SubmitReportRequest, session: AsyncSession) -> SubmitReportResponse:
    logger.info(f"Submitting AI analyst report for job {request.job_id}, alert {request.alert_id}")

    # Verify the job exists
    job = await session.get(AiAnalystJob, request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found")

    report = AiAnalystReport(
        job_id=request.job_id,
        alert_id=request.alert_id,
        customer_code=request.customer_code,
        severity_assessment=request.severity_assessment.value if request.severity_assessment else None,
        summary=request.summary,
        report_markdown=request.report_markdown,
        recommended_actions=request.recommended_actions,
        created_at=datetime.utcnow(),
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)

    logger.info(f"AI analyst report {report.id} created for job {request.job_id}")
    return SubmitReportResponse(success=True, message="Report submitted", report=_report_to_response(report))


async def get_report_by_job(job_id: str, session: AsyncSession) -> Optional[ReportResponse]:
    result = await session.execute(
        select(AiAnalystReport).where(AiAnalystReport.job_id == job_id),
    )
    report = result.scalars().first()
    if not report:
        return None
    return _report_to_response(report)


async def list_reports_by_alert(alert_id: int, session: AsyncSession) -> List[ReportResponse]:
    result = await session.execute(
        select(AiAnalystReport).where(AiAnalystReport.alert_id == alert_id).order_by(AiAnalystReport.created_at.desc()),
    )
    reports = result.scalars().all()
    return [_report_to_response(r) for r in reports]


# --- IOC operations ---


async def submit_iocs(request: SubmitIocsRequest, session: AsyncSession) -> SubmitIocsResponse:
    logger.info(f"Submitting {len(request.iocs)} IOCs for report {request.report_id}, alert {request.alert_id}")

    # Verify the report exists
    report = await session.get(AiAnalystReport, request.report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {request.report_id} not found")

    created_iocs = []
    for ioc_data in request.iocs:
        ioc = AiAnalystIoc(
            report_id=request.report_id,
            alert_id=request.alert_id,
            customer_code=request.customer_code,
            ioc_value=ioc_data.ioc_value,
            ioc_type=ioc_data.ioc_type.value,
            vt_verdict=ioc_data.vt_verdict.value,
            vt_score=ioc_data.vt_score,
            details=ioc_data.details,
            created_at=datetime.utcnow(),
        )
        session.add(ioc)
        created_iocs.append(ioc)

    await session.commit()
    for ioc in created_iocs:
        await session.refresh(ioc)

    logger.info(f"{len(created_iocs)} IOCs created for report {request.report_id}")
    return SubmitIocsResponse(
        success=True,
        message=f"{len(created_iocs)} IOCs submitted",
        iocs_created=len(created_iocs),
        iocs=[_ioc_to_response(i) for i in created_iocs],
    )


async def list_iocs_by_report(report_id: int, session: AsyncSession) -> List[IocResponse]:
    result = await session.execute(
        select(AiAnalystIoc).where(AiAnalystIoc.report_id == report_id).order_by(AiAnalystIoc.created_at.desc()),
    )
    iocs = result.scalars().all()
    return [_ioc_to_response(i) for i in iocs]


async def list_iocs_by_alert(alert_id: int, session: AsyncSession) -> List[IocResponse]:
    result = await session.execute(
        select(AiAnalystIoc).where(AiAnalystIoc.alert_id == alert_id).order_by(AiAnalystIoc.created_at.desc()),
    )
    iocs = result.scalars().all()
    return [_ioc_to_response(i) for i in iocs]


async def list_iocs_by_customer(
    customer_code: str,
    session: AsyncSession,
    vt_verdict: Optional[str] = None,
) -> List[IocResponse]:
    query = select(AiAnalystIoc).where(AiAnalystIoc.customer_code == customer_code)
    if vt_verdict:
        query = query.where(AiAnalystIoc.vt_verdict == vt_verdict)
    query = query.order_by(AiAnalystIoc.created_at.desc())
    result = await session.execute(query)
    iocs = result.scalars().all()
    return [_ioc_to_response(i) for i in iocs]


# --- Alerts with reports ---


async def list_alerts_with_reports(
    session: AsyncSession,
    customer_code: Optional[str] = None,
) -> List[AlertWithReportResponse]:
    """Return all alerts that have at least one AI analyst report."""
    query = (
        select(Alert, AiAnalystReport)
        .join(AiAnalystReport, AiAnalystReport.alert_id == Alert.id)
        .order_by(AiAnalystReport.created_at.desc())
    )
    if customer_code:
        query = query.where(Alert.customer_code == customer_code)

    result = await session.execute(query)
    rows = result.all()

    return [
        AlertWithReportResponse(
            alert_id=alert.id,
            alert_name=alert.alert_name,
            customer_code=alert.customer_code,
            status=alert.status,
            source=alert.source,
            assigned_to=alert.assigned_to,
            alert_creation_time=alert.alert_creation_time,
            report=_report_to_response(report),
        )
        for alert, report in rows
    ]


# --- Combined alert analysis lookup ---


async def get_alert_analysis(alert_id: int, session: AsyncSession):
    """Get the latest job, report, and IOCs for a given alert."""
    # Get latest job
    job_result = await session.execute(
        select(AiAnalystJob).where(AiAnalystJob.alert_id == alert_id).order_by(AiAnalystJob.created_at.desc()),
    )
    job = job_result.scalars().first()
    if not job:
        return None, None, []

    # Get report for this job
    report_result = await session.execute(
        select(AiAnalystReport).where(AiAnalystReport.job_id == job.id),
    )
    report = report_result.scalars().first()

    # Get IOCs for this report
    iocs = []
    if report:
        ioc_result = await session.execute(
            select(AiAnalystIoc).where(AiAnalystIoc.report_id == report.id),
        )
        iocs = ioc_result.scalars().all()

    return (
        _job_to_response(job),
        _report_to_response(report) if report else None,
        [_ioc_to_response(i) for i in iocs],
    )


# --- Review / Palace lesson helpers ---


def _ioc_review_to_response(ir: AiAnalystIocReview) -> IocReviewResponse:
    return IocReviewResponse(
        id=ir.id,
        review_id=ir.review_id,
        ioc_id=ir.ioc_id,
        verdict_correct=ir.verdict_correct,
        note=ir.note,
        created_at=ir.created_at,
    )


def _review_to_response(review: AiAnalystReview) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        report_id=review.report_id,
        alert_id=review.alert_id,
        customer_code=review.customer_code,
        reviewer_user_id=review.reviewer_user_id,
        overall_verdict=review.overall_verdict,
        template_choice=review.template_choice,
        template_used=review.template_used,
        rating_instructions=review.rating_instructions,
        rating_artifacts=review.rating_artifacts,
        rating_severity=review.rating_severity,
        missing_steps=review.missing_steps,
        suggested_edits=review.suggested_edits,
        created_at=review.created_at,
        ioc_reviews=[_ioc_review_to_response(ir) for ir in (review.ioc_reviews or [])],
    )


def _palace_lesson_to_response(lesson: AiAnalystPalaceLesson) -> PalaceLessonResponse:
    return PalaceLessonResponse(
        id=lesson.id,
        review_id=lesson.review_id,
        customer_code=lesson.customer_code,
        lesson_type=lesson.lesson_type,
        lesson_text=lesson.lesson_text,
        durability=lesson.durability,
        status=lesson.status,
        ingested_at=lesson.ingested_at,
        created_at=lesson.created_at,
    )


async def submit_review(
    report_id: int,
    request: SubmitReviewRequest,
    reviewer_user_id: int,
    session: AsyncSession,
) -> SubmitReviewResponse:
    """
    Persist an analyst review of an AI investigation report, plus any per-IOC
    verdict corrections. Writes AiAnalystReview and AiAnalystIocReview rows in
    a single transaction.
    """
    logger.info(f"Submitting review for report {report_id} by user {reviewer_user_id}")

    report = await session.get(AiAnalystReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    # If template_used wasn't supplied, inherit from the job for auditability
    template_used = request.template_used
    if template_used is None:
        job = await session.get(AiAnalystJob, report.job_id)
        if job is not None:
            template_used = job.template_used

    review = AiAnalystReview(
        report_id=report_id,
        alert_id=report.alert_id,
        customer_code=report.customer_code,
        reviewer_user_id=reviewer_user_id,
        overall_verdict=request.overall_verdict.value if request.overall_verdict else None,
        template_choice=request.template_choice.value if request.template_choice else None,
        template_used=template_used,
        rating_instructions=request.rating_instructions,
        rating_artifacts=request.rating_artifacts,
        rating_severity=request.rating_severity,
        missing_steps=request.missing_steps,
        suggested_edits=request.suggested_edits,
        created_at=datetime.utcnow(),
    )
    session.add(review)
    await session.flush()  # get review.id before inserting child rows

    # Validate each ioc_id is associated with this report, then insert corrections
    for correction in request.ioc_reviews:
        ioc = await session.get(AiAnalystIoc, correction.ioc_id)
        if ioc is None or ioc.report_id != report_id:
            raise HTTPException(
                status_code=400,
                detail=f"IOC {correction.ioc_id} not found or does not belong to report {report_id}",
            )
        session.add(
            AiAnalystIocReview(
                review_id=review.id,
                ioc_id=correction.ioc_id,
                verdict_correct=correction.verdict_correct,
                note=correction.note,
                created_at=datetime.utcnow(),
            ),
        )

    await session.commit()

    # Re-fetch with ioc_reviews eagerly loaded for the response
    result = await session.execute(
        select(AiAnalystReview)
        .where(AiAnalystReview.id == review.id)
        .options(selectinload(AiAnalystReview.ioc_reviews)),
    )
    review_loaded = result.scalars().first()

    logger.info(f"Review {review.id} created for report {report_id}")
    return SubmitReviewResponse(
        success=True,
        message="Review submitted",
        review=_review_to_response(review_loaded),
    )


async def queue_palace_lesson(
    request: QueuePalaceLessonRequest,
    session: AsyncSession,
) -> QueuePalaceLessonResponse:
    """
    Queue a MemPalace lesson for async drainer pickup. Does NOT call Talon
    directly — the drainer (roadmap item 17) reads status='pending' rows and
    POSTs to NanoClaw's /palace/lesson endpoint.
    """
    logger.info(
        f"Queuing palace lesson for customer {request.customer_code} "
        f"(type={request.lesson_type.value}, durability={request.durability.value})",
    )

    # If review_id supplied, validate it exists
    if request.review_id is not None:
        review = await session.get(AiAnalystReview, request.review_id)
        if review is None:
            raise HTTPException(
                status_code=404,
                detail=f"Review {request.review_id} not found",
            )

    lesson = AiAnalystPalaceLesson(
        review_id=request.review_id,
        customer_code=request.customer_code,
        lesson_type=request.lesson_type.value,
        lesson_text=request.lesson_text,
        durability=request.durability.value,
        status="pending",
        created_at=datetime.utcnow(),
    )
    session.add(lesson)
    await session.commit()
    await session.refresh(lesson)

    logger.info(f"Palace lesson {lesson.id} queued (status=pending)")
    return QueuePalaceLessonResponse(
        success=True,
        message="Palace lesson queued for ingestion",
        lesson=_palace_lesson_to_response(lesson),
    )


async def list_reviews_by_customer(
    customer_code: str,
    session: AsyncSession,
) -> List[ReviewResponse]:
    """Dashboard feed — reviews for a customer, newest first, with nested IOC reviews."""
    result = await session.execute(
        select(AiAnalystReview)
        .where(AiAnalystReview.customer_code == customer_code)
        .options(selectinload(AiAnalystReview.ioc_reviews))
        .order_by(AiAnalystReview.created_at.desc()),
    )
    reviews = result.scalars().all()
    return [_review_to_response(r) for r in reviews]
