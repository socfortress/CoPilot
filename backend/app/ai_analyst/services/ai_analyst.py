from datetime import datetime
from datetime import timedelta
from difflib import SequenceMatcher
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.ai_analyst.schema.ai_analyst import AlertWithReportResponse
from app.ai_analyst.schema.ai_analyst import CreateJobRequest
from app.ai_analyst.schema.ai_analyst import CreateJobResponse
from app.ai_analyst.schema.ai_analyst import IocResponse
from app.ai_analyst.schema.ai_analyst import IocReviewResponse
from app.ai_analyst.schema.ai_analyst import JobResponse
from app.ai_analyst.schema.ai_analyst import MyReviewResponse
from app.ai_analyst.schema.ai_analyst import PalaceConsolidationDuplicatePair
from app.ai_analyst.schema.ai_analyst import PalaceConsolidationLesson
from app.ai_analyst.schema.ai_analyst import PalaceConsolidationResponse
from app.ai_analyst.schema.ai_analyst import PalaceConsolidationRoomGroup
from app.ai_analyst.schema.ai_analyst import PalaceLessonResponse
from app.ai_analyst.schema.ai_analyst import QueuePalaceLessonRequest
from app.ai_analyst.schema.ai_analyst import QueuePalaceLessonResponse
from app.ai_analyst.schema.ai_analyst import ReportResponse
from app.ai_analyst.schema.ai_analyst import ReviewResponse
from app.ai_analyst.schema.ai_analyst import ReviewStatsIocAccuracy
from app.ai_analyst.schema.ai_analyst import ReviewStatsResponse
from app.ai_analyst.schema.ai_analyst import ReviewStatsTemplate
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
        updated_at=review.updated_at,
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
    Upsert an analyst review of an AI investigation report.

    Enforces one review per (report_id, reviewer_user_id) pair. If the user
    has already reviewed this report, their existing row is updated in place
    (and `updated_at` is set) and their per-IOC corrections are replaced
    wholesale. Otherwise a new row is inserted.
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

    # Validate every referenced IOC before mutating anything. A 400 here means
    # we don't half-write and then bail.
    for correction in request.ioc_reviews:
        ioc = await session.get(AiAnalystIoc, correction.ioc_id)
        if ioc is None or ioc.report_id != report_id:
            raise HTTPException(
                status_code=400,
                detail=f"IOC {correction.ioc_id} not found or does not belong to report {report_id}",
            )

    # Look up existing review by the unique (report_id, reviewer_user_id) key
    existing_result = await session.execute(
        select(AiAnalystReview)
        .where(AiAnalystReview.report_id == report_id)
        .where(AiAnalystReview.reviewer_user_id == reviewer_user_id)
        .options(selectinload(AiAnalystReview.ioc_reviews)),
    )
    review = existing_result.scalars().first()

    is_edit = review is not None

    if is_edit:
        # Update existing review in place
        review.overall_verdict = request.overall_verdict.value if request.overall_verdict else None
        review.template_choice = request.template_choice.value if request.template_choice else None
        review.template_used = template_used
        review.rating_instructions = request.rating_instructions
        review.rating_artifacts = request.rating_artifacts
        review.rating_severity = request.rating_severity
        review.missing_steps = request.missing_steps
        review.suggested_edits = request.suggested_edits
        review.updated_at = datetime.utcnow()
        session.add(review)

        # Replace per-IOC corrections wholesale — simpler than diffing and the
        # edit UI always submits the full set anyway.
        for old_ir in list(review.ioc_reviews or []):
            await session.delete(old_ir)
        await session.flush()
    else:
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

    # Insert the new per-IOC corrections
    for correction in request.ioc_reviews:
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
        select(AiAnalystReview).where(AiAnalystReview.id == review.id).options(selectinload(AiAnalystReview.ioc_reviews)),
    )
    review_loaded = result.scalars().first()

    action = "updated" if is_edit else "created"
    logger.info(f"Review {review.id} {action} for report {report_id}")
    return SubmitReviewResponse(
        success=True,
        message=f"Review {action}",
        review=_review_to_response(review_loaded),
    )


async def get_my_review(
    report_id: int,
    reviewer_user_id: int,
    session: AsyncSession,
) -> MyReviewResponse:
    """
    Look up the current user's existing review for a report.

    Used by the UI to decide whether to render the rubric in 'create' mode or
    'edit existing' mode. Returns success=True with review=None when no review
    exists yet (not an error).
    """
    # Ensure the report itself exists so the UI gets a real 404 for bad ids
    report = await session.get(AiAnalystReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    result = await session.execute(
        select(AiAnalystReview)
        .where(AiAnalystReview.report_id == report_id)
        .where(AiAnalystReview.reviewer_user_id == reviewer_user_id)
        .options(selectinload(AiAnalystReview.ioc_reviews)),
    )
    review = result.scalars().first()

    if review is None:
        return MyReviewResponse(
            success=True,
            message="No existing review for this user on this report",
            review=None,
        )

    return MyReviewResponse(
        success=True,
        message="Existing review retrieved",
        review=_review_to_response(review),
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
        f"(type={request.lesson_type.value}, durability={request.durability.value},
    )",
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


def _pct(numerator: int, denominator: int) -> Optional[float]:
    """Percentage helper — None when the denominator is 0 so the UI can
    render a dash instead of a misleading '0%'."""
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100, 2)


def _round_float(v) -> Optional[float]:
    """Avg helper — SQLAlchemy returns Decimal on some dialects; normalize to
    a 2-decimal float for JSON. Returns None if the source was NULL (no rows)."""
    if v is None:
        return None
    return round(float(v), 2)


async def get_review_stats(
    customer_code: str,
    session: AsyncSession,
    recent_limit: int = 10,
) -> ReviewStatsResponse:
    """Aggregate feedback metrics for the customer's review dashboard.

    Uses SQL-side COUNT/AVG/CASE aggregates so this scales with review count
    rather than pulling every row through Python — per the scale-first
    design call on Step 20.
    """
    # Main rollup: totals, verdict counts, template-choice counts, avg ratings.
    main_q = select(
        func.count(AiAnalystReview.id).label("total"),
        func.sum(case((AiAnalystReview.overall_verdict == "up", 1), else_=0)).label("thumbs_up"),
        func.sum(case((AiAnalystReview.overall_verdict == "down", 1), else_=0)).label("thumbs_down"),
        func.sum(case((AiAnalystReview.template_choice == "correct", 1), else_=0)).label("tpl_correct"),
        func.sum(case((AiAnalystReview.template_choice == "partial", 1), else_=0)).label("tpl_partial"),
        func.sum(case((AiAnalystReview.template_choice == "wrong", 1), else_=0)).label("tpl_wrong"),
        func.avg(AiAnalystReview.rating_instructions).label("avg_instr"),
        func.avg(AiAnalystReview.rating_artifacts).label("avg_artifacts"),
        func.avg(AiAnalystReview.rating_severity).label("avg_severity"),
    ).where(AiAnalystReview.customer_code == customer_code)
    main_row = (await session.execute(main_q)).one()

    total = int(main_row.total or 0)
    thumbs_up = int(main_row.thumbs_up or 0)
    thumbs_down = int(main_row.thumbs_down or 0)
    # Non-null denominator for the up% gauge — reviews that actually picked a
    # thumb. Skips reviews that left overall_verdict null.
    verdict_total = thumbs_up + thumbs_down

    # Per-template rollup, grouped by template_used (which may be NULL).
    per_template_q = (
        select(
            AiAnalystReview.template_used.label("template_used"),
            func.count(AiAnalystReview.id).label("total"),
            func.sum(case((AiAnalystReview.overall_verdict == "up", 1), else_=0)).label("thumbs_up"),
            func.sum(case((AiAnalystReview.overall_verdict == "down", 1), else_=0)).label("thumbs_down"),
            func.sum(case((AiAnalystReview.template_choice == "correct", 1), else_=0)).label("correct"),
            func.sum(case((AiAnalystReview.template_choice == "partial", 1), else_=0)).label("partial"),
            func.sum(case((AiAnalystReview.template_choice == "wrong", 1), else_=0)).label("wrong"),
            func.avg(AiAnalystReview.rating_instructions).label("avg_instr"),
            func.avg(AiAnalystReview.rating_artifacts).label("avg_artifacts"),
            func.avg(AiAnalystReview.rating_severity).label("avg_severity"),
        )
        .where(AiAnalystReview.customer_code == customer_code)
        .group_by(AiAnalystReview.template_used)
        .order_by(func.count(AiAnalystReview.id).desc())
    )
    per_template_rows = (await session.execute(per_template_q)).all()

    # IOC verdict accuracy — join IocReview rows back to the customer's reviews
    # so we only count corrections attached to this customer's reports.
    ioc_q = (
        select(
            func.count(AiAnalystIocReview.id).label("total"),
            func.sum(case((AiAnalystIocReview.verdict_correct.is_(True), 1), else_=0)).label("correct"),
            func.sum(case((AiAnalystIocReview.verdict_correct.is_(False), 1), else_=0)).label("incorrect"),
        )
        .join(AiAnalystReview, AiAnalystReview.id == AiAnalystIocReview.review_id)
        .where(AiAnalystReview.customer_code == customer_code)
    )
    ioc_row = (await session.execute(ioc_q)).one()
    ioc_total = int(ioc_row.total or 0)
    ioc_correct = int(ioc_row.correct or 0)
    ioc_incorrect = int(ioc_row.incorrect or 0)

    # Recent reviews (hydrated with ioc_reviews for drill-in).
    recent_q = (
        select(AiAnalystReview)
        .where(AiAnalystReview.customer_code == customer_code)
        .options(selectinload(AiAnalystReview.ioc_reviews))
        .order_by(AiAnalystReview.created_at.desc())
        .limit(recent_limit)
    )
    recent_reviews = (await session.execute(recent_q)).scalars().all()

    per_template: List[ReviewStatsTemplate] = [
        ReviewStatsTemplate(
            template_used=row.template_used,
            total=int(row.total or 0),
            thumbs_up=int(row.thumbs_up or 0),
            thumbs_down=int(row.thumbs_down or 0),
            correct=int(row.correct or 0),
            partial=int(row.partial or 0),
            wrong=int(row.wrong or 0),
            avg_rating_instructions=_round_float(row.avg_instr),
            avg_rating_artifacts=_round_float(row.avg_artifacts),
            avg_rating_severity=_round_float(row.avg_severity),
        )
        for row in per_template_rows
    ]

    return ReviewStatsResponse(
        success=True,
        message=f"Review stats for {customer_code}",
        customer_code=customer_code,
        total_reviews=total,
        thumbs_up=thumbs_up,
        thumbs_down=thumbs_down,
        thumbs_up_pct=_pct(thumbs_up, verdict_total),
        template_choice_correct=int(main_row.tpl_correct or 0),
        template_choice_partial=int(main_row.tpl_partial or 0),
        template_choice_wrong=int(main_row.tpl_wrong or 0),
        avg_rating_instructions=_round_float(main_row.avg_instr),
        avg_rating_artifacts=_round_float(main_row.avg_artifacts),
        avg_rating_severity=_round_float(main_row.avg_severity),
        ioc_accuracy=ReviewStatsIocAccuracy(
            total=ioc_total,
            correct=ioc_correct,
            incorrect=ioc_incorrect,
            accuracy_pct=_pct(ioc_correct, ioc_total),
        ),
        per_template=per_template,
        recent_reviews=[_review_to_response(r) for r in recent_reviews],
    )


# --- Palace consolidation (Step 21.B) ---

# Keep in sync with invoke_palace_lesson_sweeper.ONE_OFF_EXPIRY_DAYS —
# duplicated here rather than imported to avoid pulling a scheduler
# service into the synchronous route path at import time.
_ONE_OFF_EXPIRY_DAYS = 7
# Lessons within this many days of expiring are surfaced to the reviewer
# as "about to be swept" — gives a window to promote to durable.
_EXPIRY_SOON_WINDOW_DAYS = 2
# Similarity threshold for near-duplicate detection. 0.70 picks up
# paraphrases without flooding the reviewer with every shared phrase.
# difflib's SequenceMatcher on short strings is cheap — we can afford
# O(n²) pairs per room.
_DUPLICATE_SIMILARITY_THRESHOLD = 0.70


def _lesson_to_consolidation(
    lesson: AiAnalystPalaceLesson,
    now: datetime,
) -> PalaceConsolidationLesson:
    days_until_expiry: Optional[int] = None
    if lesson.durability == "one_off" and lesson.ingested_at is not None:
        expiry = lesson.ingested_at + timedelta(days=_ONE_OFF_EXPIRY_DAYS)
        days_until_expiry = (expiry - now).days
    return PalaceConsolidationLesson(
        id=lesson.id,
        lesson_type=lesson.lesson_type,
        lesson_text=lesson.lesson_text,
        durability=lesson.durability,
        status=lesson.status,
        drawer_id=lesson.drawer_id,
        created_at=lesson.created_at,
        ingested_at=lesson.ingested_at,
        days_until_expiry=days_until_expiry,
    )


def _find_duplicate_pairs(
    lessons: List[PalaceConsolidationLesson],
) -> List[PalaceConsolidationDuplicatePair]:
    """Pairwise SequenceMatcher within the same room. Only returns
    pairs above the threshold, sorted by similarity descending."""
    pairs: List[PalaceConsolidationDuplicatePair] = []
    # Group by room first so we only compare within-room.
    by_room: dict[str, List[PalaceConsolidationLesson]] = {}
    for lesson in lessons:
        by_room.setdefault(lesson.lesson_type, []).append(lesson)

    for room, room_lessons in by_room.items():
        # Normalize once up-front so SequenceMatcher has stable inputs.
        normalized = [(ls, ls.lesson_text.strip().lower()) for ls in room_lessons]
        for i in range(len(normalized)):
            a_lesson, a_text = normalized[i]
            if not a_text:
                continue
            for j in range(i + 1, len(normalized)):
                b_lesson, b_text = normalized[j]
                if not b_text:
                    continue
                ratio = SequenceMatcher(None, a_text, b_text).ratio()
                if ratio >= _DUPLICATE_SIMILARITY_THRESHOLD:
                    pairs.append(
                        PalaceConsolidationDuplicatePair(
                            room=room,
                            lesson_a_id=a_lesson.id,
                            lesson_b_id=b_lesson.id,
                            lesson_a_text=a_lesson.lesson_text,
                            lesson_b_text=b_lesson.lesson_text,
                            similarity=round(ratio, 3),
                        ),
                    )
    pairs.sort(key=lambda p: p.similarity, reverse=True)
    return pairs


def _render_consolidation_markdown(
    customer_code: str,
    generated_at: datetime,
    total_lessons: int,
    total_durable: int,
    total_one_off: int,
    rooms: List[PalaceConsolidationRoomGroup],
    duplicates: List[PalaceConsolidationDuplicatePair],
    upcoming: List[PalaceConsolidationLesson],
) -> str:
    """Pre-render the digest as markdown so the drawer can offer a
    one-click copy/export. Kept intentionally terse — headings + bullets."""
    lines: List[str] = []
    lines.append(f"# Palace consolidation — {customer_code}")
    lines.append(f"_Generated {generated_at.isoformat()} UTC_")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Total active lessons: **{total_lessons}**")
    lines.append(f"- Durable: {total_durable}  |  One-off: {total_one_off}")
    if upcoming:
        lines.append(
            f"- **{len(upcoming)} one-off lesson(s) expiring within "
            f"{_EXPIRY_SOON_WINDOW_DAYS} day(s)** — consider promoting to durable.",
        )
    if duplicates:
        lines.append(f"- **{len(duplicates)} near-duplicate pair(s)** flagged for review.")
    lines.append("")

    if upcoming:
        lines.append("## Upcoming expirations")
        for ls in upcoming:
            due = ls.days_until_expiry if ls.days_until_expiry is not None else "?"
            lines.append(f"- _{ls.lesson_type}_ (id {ls.id}, in {due}d): {ls.lesson_text}")
        lines.append("")

    if duplicates:
        lines.append("## Near-duplicate candidates")
        for pair in duplicates:
            pct = int(pair.similarity * 100)
            lines.append(f"- **{pair.room}** — {pct}% similar")
            lines.append(f"  - #{pair.lesson_a_id}: {pair.lesson_a_text}")
            lines.append(f"  - #{pair.lesson_b_id}: {pair.lesson_b_text}")
        lines.append("")

    lines.append("## Rooms")
    for group in rooms:
        lines.append(
            f"### {group.room}  ({group.total} total — " f"{group.durable} durable, {group.one_off} one-off)",
        )
        for ls in group.lessons:
            tag = "🧷" if ls.durability == "durable" else "⏳"
            suffix = ""
            if ls.durability == "one_off" and ls.days_until_expiry is not None:
                suffix = f" _(expires in {ls.days_until_expiry}d)_"
            lines.append(f"- {tag} #{ls.id}{suffix}: {ls.lesson_text}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


async def get_palace_consolidation(
    customer_code: str,
    session: AsyncSession,
) -> PalaceConsolidationResponse:
    """Build a point-in-time digest of a customer's active MemPalace
    lessons. Pure read-only, pure Python — no Talon round-trip. Used by
    the manual "Consolidate Lessons" button in the Feedback dashboard."""
    logger.info(f"Building palace consolidation digest for customer {customer_code}")

    # Exclude expired (already swept) and failed (never reached the palace)
    # rows — consolidation is about what's actually live right now.
    stmt = (
        select(AiAnalystPalaceLesson)
        .where(AiAnalystPalaceLesson.customer_code == customer_code)
        .where(AiAnalystPalaceLesson.status.in_(["pending", "ingested"]))
        .order_by(
            AiAnalystPalaceLesson.lesson_type.asc(),
            AiAnalystPalaceLesson.created_at.desc(),
        )
    )
    result = await session.execute(stmt)
    raw_lessons = result.scalars().all()

    now = datetime.utcnow()
    lessons = [_lesson_to_consolidation(ls, now) for ls in raw_lessons]

    total_lessons = len(lessons)
    total_durable = sum(1 for ls in lessons if ls.durability == "durable")
    total_one_off = sum(1 for ls in lessons if ls.durability == "one_off")
    total_pending = sum(1 for ls in lessons if ls.status == "pending")
    total_ingested = sum(1 for ls in lessons if ls.status == "ingested")

    upcoming = sorted(
        [
            ls
            for ls in lessons
            if ls.durability == "one_off" and ls.days_until_expiry is not None and ls.days_until_expiry <= _EXPIRY_SOON_WINDOW_DAYS
        ],
        key=lambda ls: ls.days_until_expiry if ls.days_until_expiry is not None else 0,
    )

    # Build per-room groups in deterministic room order.
    by_room: dict[str, List[PalaceConsolidationLesson]] = {}
    for ls in lessons:
        by_room.setdefault(ls.lesson_type, []).append(ls)
    rooms: List[PalaceConsolidationRoomGroup] = []
    for room in sorted(by_room.keys()):
        room_lessons = by_room[room]
        rooms.append(
            PalaceConsolidationRoomGroup(
                room=room,
                total=len(room_lessons),
                durable=sum(1 for ls in room_lessons if ls.durability == "durable"),
                one_off=sum(1 for ls in room_lessons if ls.durability == "one_off"),
                lessons=room_lessons,
            ),
        )

    duplicates = _find_duplicate_pairs(lessons)

    markdown = _render_consolidation_markdown(
        customer_code=customer_code,
        generated_at=now,
        total_lessons=total_lessons,
        total_durable=total_durable,
        total_one_off=total_one_off,
        rooms=rooms,
        duplicates=duplicates,
        upcoming=upcoming,
    )

    return PalaceConsolidationResponse(
        success=True,
        message=(
            f"Palace consolidation for {customer_code}: "
            f"{total_lessons} active lesson(s), "
            f"{len(duplicates)} duplicate pair(s), "
            f"{len(upcoming)} expiring soon"
        ),
        customer_code=customer_code,
        generated_at=now,
        total_lessons=total_lessons,
        total_durable=total_durable,
        total_one_off=total_one_off,
        total_pending=total_pending,
        total_ingested=total_ingested,
        upcoming_expirations=upcoming,
        rooms=rooms,
        duplicate_candidates=duplicates,
        markdown=markdown,
    )
