"""A Customer Portal user asking Talon to analyse one of their alerts (#1215).

The only portal write on the AI Analyst surface, and it is gated twice per customer:
the AI report switch (the customer can read the result) and ``allow_customer_requests``
(the customer may ask). Both are operator decisions in CoPilot, off by default.

What a request has to clear, in order:

1. the alert is one the caller may see (customer *and* tags: ``ensure_alert_visible``);
2. both switches are on for the alert's customer — taken from the alert, never the body;
3. no analysis of the alert is still pending or running (a job stuck longer than
   ``STALE_INVESTIGATION_AFTER`` no longer counts, or one dead job would block it for good);
4. the alert was not analysed or asked about in the last ``REQUEST_COOLDOWN``;
5. the customer is under its daily limit, when one is set.

The checks and the request row run under a lock on the customer's settings row, so
two clicks (or two users of one customer) cannot both pass them. The lock is released
before Talon is called, which can take a while; if Talon refuses, the row is removed
again so a failure costs the customer neither a request nor the cooldown.

The customer never sees the limit itself: a request over it is refused with a message.
"""

from datetime import datetime
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_analyst.schema.ai_analyst import JobStatus
from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.connectors.talon.schema.talon import TalonInvestigateRequest
from app.connectors.talon.services.talon import investigate_alert
from app.customer_portal.services.ai_reports import count_recent_requests
from app.customer_portal.services.ai_reports import ensure_alert_visible
from app.customer_portal.services.ai_reports import requests_allowed
from app.db.universal_models import AiAnalystJob
from app.db.universal_models import CustomerPortalAiReportSettings
from app.db.universal_models import CustomerPortalAiRequest
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.services.db_operations import create_comment
from app.time_utils import now_utc

# Between two analyses of the same alert, whoever started the last one.
REQUEST_COOLDOWN = timedelta(minutes=30)

# A job still pending/running after this long is taken as dead (Talon restarted, the
# agent crashed) rather than in progress.
STALE_INVESTIGATION_AFTER = timedelta(hours=2)

# How Talon is told the request came from the portal.
PORTAL_SENDER = "customer-portal"

IN_PROGRESS = {JobStatus.PENDING.value, JobStatus.RUNNING.value}


def _minutes_until(moment: datetime, now: datetime) -> int:
    return max(1, -(-int((moment - now).total_seconds()) // 60))


async def _locked_settings(customer_code: str, session: AsyncSession) -> Optional[CustomerPortalAiReportSettings]:
    result = await session.execute(
        select(CustomerPortalAiReportSettings).where(CustomerPortalAiReportSettings.customer_code == customer_code).with_for_update(),
    )
    return result.scalars().first()


async def _latest_job(alert_id: int, session: AsyncSession) -> Optional[AiAnalystJob]:
    result = await session.execute(select(AiAnalystJob).where(AiAnalystJob.alert_id == alert_id).order_by(AiAnalystJob.created_at.desc()))
    return result.scalars().first()


async def _latest_request(alert_id: int, session: AsyncSession) -> Optional[CustomerPortalAiRequest]:
    result = await session.execute(
        select(CustomerPortalAiRequest)
        .where(CustomerPortalAiRequest.alert_id == alert_id)
        .order_by(CustomerPortalAiRequest.requested_at.desc()),
    )
    return result.scalars().first()


def refusal(
    settings: Optional[CustomerPortalAiReportSettings],
    job: Optional[AiAnalystJob],
    last_request: Optional[CustomerPortalAiRequest],
    recent_requests: int,
    now: datetime,
) -> Optional[HTTPException]:
    """Why a request cannot go ahead now, or ``None``. Pure, so the rules test without a DB."""
    if not requests_allowed(settings):
        return HTTPException(status_code=403, detail="Requesting an AI analysis is not enabled for this customer")

    if job is not None and job.status in IN_PROGRESS and now - job.created_at < STALE_INVESTIGATION_AFTER:
        return HTTPException(status_code=409, detail="An AI analysis of this alert is already in progress")

    last = max(
        (moment for moment in (job.created_at if job else None, last_request.requested_at if last_request else None) if moment),
        default=None,
    )
    if last is not None and now - last < REQUEST_COOLDOWN:
        minutes = _minutes_until(last + REQUEST_COOLDOWN, now)
        return HTTPException(
            status_code=429,
            detail=f"This alert was analysed recently. You can request a new analysis in {minutes} minute{'s' if minutes != 1 else ''}.",
        )

    if settings.daily_request_limit is not None and recent_requests >= settings.daily_request_limit:
        return HTTPException(
            status_code=429,
            detail="Your organization has reached its daily limit of AI analyses. Please try again later.",
        )

    return None


async def request_alert_analysis(alert_id: int, user: User, session: AsyncSession) -> CustomerPortalAiRequest:
    """Ask Talon to analyse ``alert_id`` for a portal user, or raise why not."""
    alert = await ensure_alert_visible(alert_id, user, session)
    customer_code = alert.customer_code
    now = now_utc().replace(tzinfo=None)

    settings = await _locked_settings(customer_code, session)
    refused = refusal(
        settings,
        await _latest_job(alert_id, session),
        await _latest_request(alert_id, session),
        await count_recent_requests(customer_code, session) if settings and settings.daily_request_limit is not None else 0,
        now,
    )
    if refused is not None:
        await session.rollback()
        await _audit(user, customer_code, alert_id, AuditResult.FAILURE, refused.detail)
        raise refused

    request = CustomerPortalAiRequest(
        customer_code=customer_code,
        alert_id=alert_id,
        requested_by_user_id=getattr(user, "id", None),
        requested_by=user.username,
        requested_at=now,
    )
    session.add(request)
    await session.commit()  # releases the settings lock before the (slow) call to Talon
    await session.refresh(request)

    try:
        await investigate_alert(TalonInvestigateRequest(alert_id=alert_id, customer_code=customer_code, sender=PORTAL_SENDER))
    except Exception as e:  # noqa: BLE001 - Talon's error text is SOC plumbing, never shown to the customer
        logger.error(f"Talon refused the portal request for alert {alert_id} ({customer_code}): {e}")
        await session.execute(delete(CustomerPortalAiRequest).where(CustomerPortalAiRequest.id == request.id))
        await session.commit()
        await _audit(user, customer_code, alert_id, AuditResult.FAILURE, "The AI analyst could not start the analysis")
        raise HTTPException(status_code=502, detail="The AI analyst could not start the analysis. Please try again later.")

    await _audit(user, customer_code, alert_id, AuditResult.SUCCESS, None)
    await _comment(alert_id, user.username, session)
    logger.info(f"Portal user {user.username} requested an AI analysis of alert {alert_id} ({customer_code})")
    return request


async def _comment(alert_id: int, username: str, session: AsyncSession) -> None:
    """Leave the request in the alert's timeline, where analysts look. Best-effort."""
    try:
        await create_comment(
            CommentCreate(alert_id=alert_id, comment="AI analysis requested from the Customer Portal.", user_name=username),
            session,
        )
    except Exception as e:  # noqa: BLE001 - the request already went through; the note is a courtesy
        logger.warning(f"Could not note the AI analysis request on alert {alert_id}: {e}")
        await session.rollback()


async def _audit(user: User, customer_code: str, alert_id: int, result: AuditResult, details: Optional[str]) -> None:
    await record_audit_event(
        action=AuditAction.AI_ANALYSIS_REQUEST,
        actor_user_id=getattr(user, "id", None),
        actor_username=user.username,
        customer_code=customer_code,
        entity_type="alert",
        entity_id=alert_id,
        result=result,
        details=details,
    )
