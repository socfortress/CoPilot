from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.connectors.talon.schema.talon import TalonInvestigateRequest
from app.connectors.talon.schema.talon import TalonInvestigateResponse
from app.connectors.talon.schema.talon import TalonJobResponse
from app.connectors.talon.schema.talon import TalonMessageRequest
from app.connectors.talon.schema.talon import TalonMessageResponse
from app.connectors.talon.schema.talon import TalonStatusResponse
from app.connectors.talon.utils.universal import send_get_request
from app.connectors.talon.utils.universal import send_post_request
from app.connectors.talon.utils.universal import send_post_request_sse
from app.db.universal_models import AiAnalystJob


async def send_talon_message(request: TalonMessageRequest) -> TalonMessageResponse:
    """
    Send a message to Talon for ad-hoc analyst prompts.

    Args:
        request: The message request containing the message and sender.

    Returns:
        TalonMessageResponse with the Talon response.
    """
    logger.info(f"Sending message to Talon: {request.message}")
    response = await send_post_request(
        endpoint="/message",
        data=request.dict(),
        timeout=600,
    )
    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to send message to Talon"),
        )
    return TalonMessageResponse(
        success=True,
        message="Message sent to Talon successfully",
        data=response.get("data"),
    )


async def stream_talon_message(request: TalonMessageRequest):
    """
    Stream a message response from Talon via SSE.

    Args:
        request: The message request containing the message and sender.

    Yields:
        str: SSE lines from Talon.
    """
    logger.info(f"Streaming message to Talon: {request.message}")
    async for chunk in send_post_request_sse(
        endpoint="/message",
        data=request.dict(),
    ):
        yield chunk


async def investigate_alert(request: TalonInvestigateRequest) -> TalonInvestigateResponse:
    """
    Trigger an investigation for a specific alert.

    Args:
        request: The investigation request containing the alert ID, customer code, and sender.

    Returns:
        TalonInvestigateResponse with the investigation result.
    """
    logger.info(f"Triggering Talon investigation for alert ID: {request.alert_id}")
    response = await send_post_request(
        endpoint="/investigate",
        data={"alert_id": request.alert_id, "customer_code": request.customer_code, "sender": request.sender},
    )
    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to trigger Talon investigation"),
        )
    return TalonInvestigateResponse(
        success=True,
        message="Investigation triggered successfully",
        data=response.get("data"),
    )


async def get_talon_status() -> TalonStatusResponse:
    """
    Get the current status of the Talon service including queue and job overview.

    Returns:
        TalonStatusResponse with the status data.
    """
    logger.info("Fetching Talon status")
    response = await send_get_request(endpoint="/status")
    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to get Talon status"),
        )
    return TalonStatusResponse(
        success=True,
        message="Talon status retrieved successfully",
        data=response.get("data"),
    )


async def get_talon_job(alert_id: int, session: AsyncSession) -> TalonJobResponse:
    """
    Get the job status and report for a specific alert from the database.

    Args:
        alert_id: The alert ID to look up.
        session: The database session.

    Returns:
        TalonJobResponse with the job data.
    """
    logger.info(f"Fetching Talon job for alert ID: {alert_id}")
    result = await session.execute(
        select(AiAnalystJob)
        .where(AiAnalystJob.alert_id == alert_id)
        .options(selectinload(AiAnalystJob.reports))
        .order_by(AiAnalystJob.created_at.desc()),
    )
    jobs = result.scalars().all()
    if not jobs:
        raise HTTPException(
            status_code=404,
            detail=f"No job found for alert {alert_id}",
        )
    # Use the most recent job for top-level metadata
    job = jobs[0]
    # Aggregate reports from all jobs
    all_reports = []
    for j in jobs:
        for r in (j.reports or []):
            all_reports.append(
                {
                    "id": r.id,
                    "job_id": j.id,
                    "alert_id": j.alert_id,
                    "customer_code": j.customer_code,
                    "severity_assessment": r.severity_assessment,
                    "summary": r.summary,
                    "report_markdown": r.report_markdown,
                    "recommended_actions": r.recommended_actions,
                    "created_at": r.created_at.isoformat(),
                },
            )
    return TalonJobResponse(
        success=True,
        message="Talon job retrieved successfully",
        data={
            "id": job.id,
            "alert_id": job.alert_id,
            "customer_code": job.customer_code,
            "status": job.status,
            "alert_type": job.alert_type,
            "triggered_by": job.triggered_by,
            "template_used": job.template_used,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "reports": all_reports,
        },
    )
