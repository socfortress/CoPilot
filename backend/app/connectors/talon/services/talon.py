from typing import Any
from typing import Dict
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.talon.schema.talon import TalonInvestigateRequest
from app.connectors.talon.schema.talon import TalonInvestigateResponse
from app.connectors.talon.schema.talon import TalonJobResponse
from app.connectors.talon.schema.talon import TalonMessageRequest
from app.connectors.talon.schema.talon import TalonMessageResponse
from app.connectors.talon.schema.talon import TalonSessionContextResponse
from app.connectors.talon.schema.talon import TalonSessionResetResponse
from app.connectors.talon.schema.talon import TalonStatusResponse
from app.connectors.talon.schema.talon import TalonTemplatesResponse
from app.connectors.talon.services import talon_triggers
from app.connectors.talon.utils.universal import send_get_request
from app.connectors.talon.utils.universal import send_post_request
from app.connectors.talon.utils.universal import send_post_request_sse
from app.db.universal_models import AiAnalystJob
from app.incidents.models import Alert
from app.middleware.customer_access import customer_access_handler

#: The sender for investigations an analyst starts from the alert page ("Investigate with AI
#: Analyst"). Set here, not taken from the request, so Talon can tell a click from the ingest
#: trigger (``copilot``) and start a fresh investigation instead of returning one that completed
#: a few minutes ago.
ANALYST_SENDER = "copilot-analyst"


def _message_payload(
    request: TalonMessageRequest,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build the Talon /message body.

    user_id selects the caller's conversation lane in Talon: their own session,
    queue slot and response stream. Omitting it drops the caller into the
    shared anonymous lane, where concurrent analysts are batched into one
    prompt and can receive each other's replies — so it is always stamped from
    the authenticated user rather than taken from the request body.
    """
    payload: Dict[str, Any] = {"message": request.message, "sender": request.sender}
    if user_id is not None:
        payload["user_id"] = str(user_id)
    if user_name:
        payload["user_name"] = user_name
    return payload


async def send_talon_message(
    request: TalonMessageRequest,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
) -> TalonMessageResponse:
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
        data=_message_payload(request, user_id, user_name),
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


async def stream_talon_message(
    request: TalonMessageRequest,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
):
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
        data=_message_payload(request, user_id, user_name),
    ):
        yield chunk


async def reset_talon_session(user_id: int) -> TalonSessionResetResponse:
    """
    Clear the calling analyst's Talon conversation.

    Talon holds the conversation, not CoPilot: the chat UI sends only the
    current message and the agent resumes its own stored session. Clearing the
    browser therefore leaves the agent remembering every prior turn, which is
    both the surprise ("I cleared the chat and it still knows") and the cost —
    a resumed session grows without bound and eventually takes minutes to
    answer.

    Scoped to this user's lane. An analyst starting a fresh conversation must
    not discard a colleague's.
    """
    logger.info(f"Resetting Talon session for user {user_id}")
    response = await send_post_request(
        endpoint="/session/reset",
        data={"scope": "chat", "user_id": str(user_id)},
    )
    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to reset Talon session"),
        )
    data = response.get("data") or {}
    return TalonSessionResetResponse(
        success=True,
        message="Talon session cleared",
        lanes_cleared=data.get("cleared", 0),
    )


async def get_talon_session_context(user_id: int) -> TalonSessionContextResponse:
    """
    Size of the calling analyst's Talon conversation.

    Resolved server-side so the caller only ever learns about its own lane —
    Talon's /status lists every lane, and with per-user conversations those
    figures are another analyst's activity, not this one's.

    Advisory: a Talon that is down or has no record of the lane yields a null
    rather than an error, because this only decorates the chat header.
    """
    response = await send_get_request(endpoint="/status")
    if not response.get("success"):
        return TalonSessionContextResponse(success=True, message="Talon session context unavailable")

    sessions = (response.get("data") or {}).get("sessions") or []
    lane = next((s for s in sessions if str(s.get("user_id") or "") == str(user_id)), None)
    if lane is None:
        return TalonSessionContextResponse(success=True, message="No active Talon conversation")

    return TalonSessionContextResponse(
        success=True,
        message="Talon session context retrieved",
        input_tokens=lane.get("input_tokens"),
        updated_at=lane.get("updated_at"),
    )


async def investigate_alert(request: TalonInvestigateRequest, *, source: str, user: Optional[User] = None) -> TalonInvestigateResponse:
    """
    Trigger an investigation for a specific alert.

    Args:
        request: The investigation request containing the alert ID, customer code, and sender.
        source: Who is sending it (``talon_triggers``: ``pipeline``, ``analyst`` or ``portal``), set
            by the calling code path; recorded with ``user`` before the call.

    Returns:
        TalonInvestigateResponse with the investigation result.
    """
    logger.info(f"Triggering Talon investigation for alert ID: {request.alert_id}")
    await talon_triggers.record_before_sending(request.alert_id, request.customer_code, source, user)
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


async def investigate_alert_for_user(request: TalonInvestigateRequest, user: User, session: AsyncSession) -> TalonInvestigateResponse:
    """``investigate_alert`` for an analyst: the alert must exist and be one of the caller's customers.

    The body names both the alert and its customer; trusting the second would let a scoped
    analyst start an investigation of another tenant's alert, or send Talon a customer
    code that does not match the alert it reads.
    """
    alert = (await session.execute(select(Alert).where(Alert.id == request.alert_id))).scalars().first()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {request.alert_id} not found")
    await customer_access_handler.enforce_customer_access(user, alert.customer_code, session)
    if request.customer_code != alert.customer_code:
        raise HTTPException(
            status_code=400,
            detail=f"customer_code mismatch: alert {alert.id} belongs to {alert.customer_code}, got {request.customer_code}",
        )
    return await investigate_alert(request.model_copy(update={"sender": ANALYST_SENDER}), source=talon_triggers.ANALYST, user=user)


def _own_lane_only(data: Any, user_id: int) -> Optional[Dict[str, Any]]:
    """Talon's /status narrowed to one caller.

    Talon lists every conversation lane (``sessions[]``: each analyst's user id and
    conversation size) and, on NanoClaw, deployment-wide ``scheduled_tasks``. A caller
    who is not an admin keeps only their own lane, matched on ``user_id`` as
    ``get_talon_session_context`` does, and no scheduled tasks. The service-level
    figures (status, uptime, queue depth) are kept: they describe Talon, not a tenant.
    """
    if not isinstance(data, dict):
        return None
    sessions = data.get("sessions") if isinstance(data.get("sessions"), list) else []
    narrowed = dict(data)
    narrowed["sessions"] = [s for s in sessions if isinstance(s, dict) and str(s.get("user_id") or "") == str(user_id)]
    if "scheduled_tasks" in narrowed:
        narrowed["scheduled_tasks"] = []
    return narrowed


async def get_talon_status(user: User) -> TalonStatusResponse:
    """
    Get the current status of the Talon service including queue and job overview.

    An admin sees every conversation lane; anyone else sees only their own
    (``_own_lane_only``).

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
    data = response.get("data")
    if user.role_id != RoleEnum.admin:
        data = _own_lane_only(data, user.id)
    return TalonStatusResponse(
        success=True,
        message="Talon status retrieved successfully",
        data=data,
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
        for r in j.reports or []:
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


async def replay_investigation(
    alert_id: int,
    customer_code: str,
    template_override: str,
    sender: str = "copilot-replay",
    user: Optional[User] = None,
) -> Dict[str, Any]:
    """
    Trigger an investigation replay with a forced template via Talon's
    POST /investigate endpoint.

    Args:
        alert_id: CoPilot alert ID to re-investigate.
        customer_code: Customer code for the alert.
        template_override: Template filename to force (validated upstream).
        sender: Audit identifier for the replay.
        user: Who replayed it, recorded with the ``replay`` trigger before the call.

    Returns:
        Raw Talon response envelope (success, message, data).
    """
    logger.info(
        f"Replaying Talon investigation for alert {alert_id} " f"with template_override={template_override}",
    )
    await talon_triggers.record_before_sending(alert_id, customer_code, talon_triggers.REPLAY, user)
    response = await send_post_request(
        endpoint="/investigate",
        data={
            "alert_id": alert_id,
            "customer_code": customer_code,
            "template_override": template_override,
            "sender": sender,
        },
    )
    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to replay Talon investigation"),
        )
    return response


async def list_talon_templates() -> TalonTemplatesResponse:
    """
    List the prompt templates available in NanoClaw's CoPilot group.
    Powers the "Re-run with different template" picker in the review UI.

    NanoClaw returns {templates: [{filename, size_bytes, modified_at, first_line}]}.
    We surface that envelope directly — template bodies stay server-side.
    """
    logger.info("Fetching Talon templates list")
    response = await send_get_request(endpoint="/templates")
    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to list Talon templates"),
        )
    data = response.get("data") or {}
    raw_templates = data.get("templates") if isinstance(data, dict) else None
    if raw_templates is None:
        raw_templates = []
    return TalonTemplatesResponse(
        success=True,
        message=f"{len(raw_templates)} templates retrieved",
        templates=raw_templates,
    )


async def search_palace_lessons(
    customer_code: str,
    query: str,
    room: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Preview similar MemPalace lessons via Talon's GET /palace/search endpoint.
    Read-only — never mutates the palace.

    Args:
        customer_code: Customer whose wing to search.
        query: Semantic search query.
        room: Optional room filter (environment, false_positives, assets, threat_intel, alerts).
        limit: Max hits to return (clamped 1–25 upstream).

    Returns:
        Raw Talon response envelope (success, message, data).
    """
    logger.info(
        f"Searching MemPalace for customer={customer_code} room={room} query={query!r} limit={limit}",
    )
    params: Dict[str, Any] = {
        "customer_code": customer_code,
        "query": query,
        "limit": limit,
    }
    if room:
        params["room"] = room
    response = await send_get_request(endpoint="/palace/search", params=params)
    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to search MemPalace"),
        )
    return response
