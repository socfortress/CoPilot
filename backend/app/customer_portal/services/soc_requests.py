"""'Ask the SOC' from the Customer Portal (#1305): a portal user's question about an alert or a case.

A portal user asks the SOC about one of their alerts or cases. The question becomes a comment
on its target, signed by the user, so the SOC answers where it already works, and a
``customer_portal_soc_request`` row, ``open`` until the SOC answers (``soc_request_answers``).
The SOC hears about it through CoPilot's notification routing (the internal trigger
``customer_question``), never through the customer's own channels.

- **On an alert the user chooses**: on a case (the alert's open case when it has one, else a new
  case made from the alert: the SOC works cases) or on the alert itself.
- **Opt-in per customer** (``customer_portal_soc_request_settings``, a missing row = off), with an
  optional daily limit per customer, and ``REQUEST_COOLDOWN`` between two questions on the same
  alert or case. The checks and the request row run under a lock on the customer's settings row,
  so two clicks cannot both pass them; the lock is released before the comment and the case are
  written, and the row is removed again if they fail, so a failure costs the customer nothing.
- **Through the incidents routes**, called directly as the user (as Talon's approved actions do):
  a case made from the alert and the comment get every side effect a portal user's own case or
  comment gets (case events, SLA clocks, a waiting item handed back to the SOC). Imported inside
  the functions: those routes import ``soc_request_answers``, and this module must not be
  imported at their import time.
- **The portal sees** its own questions and whether the SOC answered, never who answered.
"""

from datetime import datetime
from datetime import timedelta
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.auth.services.read_only import READ_ONLY
from app.auth.services.read_only import is_read_only_for
from app.customer_portal.schema.soc_requests import AskOnAlertRequest
from app.customer_portal.schema.soc_requests import AskOnCaseRequest
from app.customer_portal.schema.soc_requests import PortalSocRequest
from app.customer_portal.schema.soc_requests import SocRequestOut
from app.customer_portal.services.ai_reports import ensure_alert_visible
from app.customer_portal.services.soc_request_answers import ANSWERED
from app.customer_portal.services.soc_request_answers import OPEN
from app.customer_portal.services.soc_request_answers import VIA_MANUAL
from app.db.universal_models import CustomerPortalSocRequest
from app.db.universal_models import CustomerPortalSocRequestSettings
from app.incidents.models import Alert
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.middleware.customer_access import customer_access_handler
from app.middleware.customer_access import scoped_customer_codes
from app.notifications.schema.events import EntityType
from app.notifications.services.emit import emit
from app.notifications.services.event_builders import customer_question_event
from app.time_utils import now_utc

#: Between two questions on the same alert or case, whoever asked the last one.
REQUEST_COOLDOWN = timedelta(minutes=10)
#: The window a customer's daily limit counts over.
LIMIT_WINDOW = timedelta(hours=24)
#: The most questions the SOC list answers with at once.
SOC_LIST_LIMIT = 500

URGENCY_LABELS = {"low": "Low", "normal": "Normal", "high": "High"}

NOT_ENABLED = "Asking the SOC is not enabled for your organization"
FAILED = "Your question could not be sent. Please try again later."


def _now() -> datetime:
    return now_utc().replace(tzinfo=None)


def _iso(moment: Optional[datetime]) -> Optional[str]:
    return moment.replace(microsecond=0).isoformat() + "Z" if moment else None


def comment_text(question: str, urgency: str) -> str:
    """The comment left on the target: what the SOC reads in its timeline."""
    return f"Question for the SOC (urgency: {URGENCY_LABELS.get(urgency, 'Normal')}):\n\n{question}"


# ── the switch ────────────────────────────────────────────────────────────────


async def get_settings(customer_code: str, session: AsyncSession, *, lock: bool = False) -> Optional[CustomerPortalSocRequestSettings]:
    query = select(CustomerPortalSocRequestSettings).where(CustomerPortalSocRequestSettings.customer_code == customer_code)
    if lock:
        query = query.with_for_update()
    return (await session.execute(query)).scalars().first()


async def upsert_settings(
    customer_code: str,
    enabled: bool,
    daily_request_limit: Optional[int],
    session: AsyncSession,
    user_id: Optional[int] = None,
) -> CustomerPortalSocRequestSettings:
    """Create or replace a customer's switch and limit. Caller commits."""
    settings = await get_settings(customer_code, session)
    if settings is None:
        settings = CustomerPortalSocRequestSettings(customer_code=customer_code)
        session.add(settings)
    settings.enabled = enabled
    settings.daily_request_limit = daily_request_limit
    settings.updated_at = now_utc()
    settings.updated_by = user_id
    return settings


async def enabled_customer_codes(user: User, session: AsyncSession) -> List[str]:
    """The customers ``user`` may see whose portal users may ask the SOC."""
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    query = select(CustomerPortalSocRequestSettings.customer_code).where(CustomerPortalSocRequestSettings.enabled.is_(True))
    if "*" not in accessible:
        if not accessible:
            return []
        query = query.where(CustomerPortalSocRequestSettings.customer_code.in_(accessible))
    return sorted((await session.execute(query)).scalars().all())


async def availability(user: User, session: AsyncSession, customer_code: Optional[str] = None) -> Tuple[Optional[str], bool]:
    """Whether 'Ask the SOC' shows: for one customer the caller may see, else for any."""
    if customer_code:
        if not await customer_access_handler.check_customer_access(user, customer_code, session):
            raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
        settings = await get_settings(customer_code, session)
        return customer_code, bool(settings and settings.enabled)
    return None, bool(await enabled_customer_codes(user, session))


# ── the rules (pure) ──────────────────────────────────────────────────────────


def refusal(
    settings: Optional[CustomerPortalSocRequestSettings],
    last_request_at: Optional[datetime],
    recent_requests: int,
    now: datetime,
) -> Optional[HTTPException]:
    """Why a question cannot be asked now, or ``None``. Pure, so the rules test without a DB."""
    if settings is None or not settings.enabled:
        return HTTPException(status_code=403, detail=NOT_ENABLED)
    if last_request_at is not None and now - last_request_at < REQUEST_COOLDOWN:
        minutes = max(1, -(-int((last_request_at + REQUEST_COOLDOWN - now).total_seconds()) // 60))
        return HTTPException(
            status_code=429,
            detail=f"A question about this was sent a moment ago. You can ask again in {minutes} minute{'s' if minutes != 1 else ''}.",
        )
    if settings.daily_request_limit is not None and recent_requests >= settings.daily_request_limit:
        return HTTPException(status_code=429, detail="Your organization has reached its daily limit of questions. Please try again later.")
    return None


# ── reads ─────────────────────────────────────────────────────────────────────


async def _latest_question_at(
    session: AsyncSession,
    *,
    case_id: Optional[int] = None,
    alert_id: Optional[int] = None,
) -> Optional[datetime]:
    """When the last question about this case, or this alert (on it or filed from it), was asked."""
    request = CustomerPortalSocRequest
    where = request.case_id == case_id if case_id is not None else or_(request.alert_id == alert_id, request.origin_alert_id == alert_id)
    return (await session.execute(select(func.max(request.requested_at)).where(where))).scalar_one_or_none()


async def _recent_count(customer_code: str, now: datetime, session: AsyncSession) -> int:
    request = CustomerPortalSocRequest
    return (
        await session.execute(
            select(func.count(request.id)).where(request.customer_code == customer_code, request.requested_at >= now - LIMIT_WINDOW),
        )
    ).scalar_one()


async def open_case_for_alert(alert_id: int, customer_code: str, session: AsyncSession) -> Optional[int]:
    """The newest case not closed that holds this alert, of the alert's own customer."""
    result = await session.execute(
        select(Case.id)
        .join(CaseAlertLink, CaseAlertLink.case_id == Case.id)
        .where(CaseAlertLink.alert_id == alert_id, Case.customer_code == customer_code, Case.case_status != "CLOSED")
        .order_by(Case.id.desc())
        .limit(1),
    )
    return result.scalar_one_or_none()


async def ensure_case_visible(case_id: int, user: User, session: AsyncSession) -> Case:
    """The case, when it is one of the caller's customers'; 404 or 403 otherwise."""
    case = (await session.execute(select(Case).where(Case.id == case_id))).scalars().first()
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    if not await customer_access_handler.check_customer_access(user, case.customer_code, session):
        raise HTTPException(status_code=403, detail=f"Access denied to case {case_id} - insufficient customer permissions")
    return case


def to_portal(request: CustomerPortalSocRequest) -> PortalSocRequest:
    return PortalSocRequest(
        id=request.id,
        case_id=request.case_id,
        alert_id=request.alert_id,
        origin_alert_id=request.origin_alert_id,
        question=request.question,
        urgency=request.urgency if request.urgency in URGENCY_LABELS else "normal",
        status=request.status if request.status in (OPEN, ANSWERED) else OPEN,
        requested_by=request.requested_by,
        requested_at=_iso(request.requested_at),
        answered_at=_iso(request.answered_at),
    )


async def list_for_alert(alert_id: int, user: User, session: AsyncSession) -> Tuple[List[PortalSocRequest], Optional[int]]:
    """The questions about an alert (on it, or filed on a case from it), newest first, and its open case."""
    alert = await ensure_alert_visible(alert_id, user, session)
    request = CustomerPortalSocRequest
    rows = (
        (
            await session.execute(
                select(request)
                .where(or_(request.alert_id == alert_id, request.origin_alert_id == alert_id))
                .order_by(request.requested_at.desc(), request.id.desc()),
            )
        )
        .scalars()
        .all()
    )
    return [to_portal(row) for row in rows], await open_case_for_alert(alert_id, alert.customer_code, session)


async def list_for_case(case_id: int, user: User, session: AsyncSession) -> List[PortalSocRequest]:
    await ensure_case_visible(case_id, user, session)
    request = CustomerPortalSocRequest
    rows = (
        (await session.execute(select(request).where(request.case_id == case_id).order_by(request.requested_at.desc(), request.id.desc())))
        .scalars()
        .all()
    )
    return [to_portal(row) for row in rows]


async def _titles(rows: Iterable[CustomerPortalSocRequest], session: AsyncSession) -> Tuple[dict, dict]:
    case_ids = {row.case_id for row in rows if row.case_id}
    alert_ids = {row.alert_id for row in rows if row.alert_id}
    cases = dict((await session.execute(select(Case.id, Case.case_name).where(Case.id.in_(case_ids)))).all()) if case_ids else {}
    alerts = dict((await session.execute(select(Alert.id, Alert.alert_name).where(Alert.id.in_(alert_ids)))).all()) if alert_ids else {}
    return cases, alerts


def to_soc(request: CustomerPortalSocRequest, cases: dict, alerts: dict) -> SocRequestOut:
    title = cases.get(request.case_id) if request.case_id else alerts.get(request.alert_id)
    return SocRequestOut(
        **to_portal(request).model_dump(),
        customer_code=request.customer_code,
        title=title,
        answered_by=request.answered_by,
        answered_via=request.answered_via if request.answered_via in ("comment", "manual") else None,
    )


async def list_for_soc(
    user: User,
    session: AsyncSession,
    *,
    status: Optional[str] = None,
    customer_codes: Optional[List[str]] = None,
    case_id: Optional[int] = None,
    alert_id: Optional[int] = None,
) -> Tuple[List[SocRequestOut], int, int]:
    """The SOC's view: the questions of the caller's customers, newest first, with the counts."""
    codes = await scoped_customer_codes(user, customer_codes, session)
    if codes == []:
        return [], 0, 0
    request = CustomerPortalSocRequest
    where = []
    if codes is not None:
        where.append(request.customer_code.in_(codes))
    if case_id is not None:
        where.append(request.case_id == case_id)
    if alert_id is not None:
        where.append(or_(request.alert_id == alert_id, request.origin_alert_id == alert_id))
    counts = dict((await session.execute(select(request.status, func.count(request.id)).where(*where).group_by(request.status))).all())
    if status:
        where.append(request.status == status)
    rows = (
        (
            await session.execute(
                select(request).where(*where).order_by(request.requested_at.desc(), request.id.desc()).limit(SOC_LIST_LIMIT),
            )
        )
        .scalars()
        .all()
    )
    cases, alerts = await _titles(rows, session)
    return [to_soc(row, cases, alerts) for row in rows], sum(counts.values()), counts.get(OPEN, 0)


# ── asking ────────────────────────────────────────────────────────────────────


async def _reserve(
    user: User,
    customer_code: str,
    session: AsyncSession,
    *,
    question: str,
    urgency: str,
    case_id: Optional[int] = None,
    alert_id: Optional[int] = None,
    cooldown_case: Optional[int] = None,
    cooldown_alert: Optional[int] = None,
) -> CustomerPortalSocRequest:
    """Check the rules under the customer's settings lock and write the request row, or raise.

    The transaction of the reads before (the visibility checks) ends first: under MySQL's
    REPEATABLE READ a transaction reads the snapshot of its first plain read, so a request that
    waited for the lock would otherwise count the questions as they were before it waited, and
    two users could both take the last slot of the day.
    """
    if await is_read_only_for(user, customer_code, session):
        # A question is a comment on the alert or case: not for a user who may only read (#1312).
        await _audit(
            user,
            customer_code,
            "case" if cooldown_case else "alert",
            cooldown_case or cooldown_alert,
            AuditResult.FAILURE,
            READ_ONLY,
        )
        raise HTTPException(status_code=403, detail=READ_ONLY)
    await session.commit()
    now = _now()
    settings = await get_settings(customer_code, session, lock=True)
    last = await _latest_question_at(session, case_id=cooldown_case, alert_id=cooldown_alert)
    recent = await _recent_count(customer_code, now, session) if settings and settings.daily_request_limit is not None else 0
    refused = refusal(settings, last, recent, now)
    if refused is not None:
        await session.rollback()
        await _audit(
            user,
            customer_code,
            "case" if cooldown_case else "alert",
            cooldown_case or cooldown_alert,
            AuditResult.FAILURE,
            refused.detail,
        )
        raise refused
    request = CustomerPortalSocRequest(
        customer_code=customer_code,
        case_id=case_id,
        alert_id=alert_id,
        question=question,
        urgency=urgency,
        status=OPEN,
        requested_by_user_id=getattr(user, "id", None),
        requested_by=user.username,
        requested_at=now,
    )
    session.add(request)
    await session.commit()  # releases the settings lock before the case and the comment are written
    await session.refresh(request)
    return request


async def _forget(request_id: int, session: AsyncSession) -> None:
    await session.rollback()
    await session.execute(delete(CustomerPortalSocRequest).where(CustomerPortalSocRequest.id == request_id))
    await session.commit()


async def _comment_on_case(case_id: int, text: str, user: User, session: AsyncSession) -> int:
    from app.incidents.routes.db_operations import create_case_comment_endpoint
    from app.incidents.schema.db_operations import CaseCommentCreate

    response = await create_case_comment_endpoint(CaseCommentCreate(case_id=case_id, comment=text, user_name=user.username), user, session)
    return response.comment.id


async def _comment_on_alert(alert_id: int, text: str, user: User, session: AsyncSession) -> int:
    from app.incidents.routes.db_operations import create_comment_endpoint
    from app.incidents.schema.db_operations import CommentCreate

    response = await create_comment_endpoint(CommentCreate(alert_id=alert_id, comment=text, user_name=user.username), user, session)
    return response.comment.id


async def _case_from_alert(alert_id: int, user: User, session: AsyncSession) -> int:
    from app.incidents.routes.db_operations import create_case_from_alert_endpoint
    from app.incidents.schema.db_operations import CaseCreateFromAlert

    response = await create_case_from_alert_endpoint(CaseCreateFromAlert(alert_id=alert_id), None, user, session)
    link = getattr(response, "case_alert_link", None)
    if link is None:
        raise RuntimeError("the case could not be created from the alert")
    return link.case_id


async def ask_on_alert(alert_id: int, body: AskOnAlertRequest, user: User, session: AsyncSession) -> PortalSocRequest:
    """A portal user's question about one of their alerts: on a case (open or new) or on the alert."""
    alert = await ensure_alert_visible(alert_id, user, session)
    customer_code, title = alert.customer_code, alert.alert_name
    on_case = body.target == "case"
    request = await _reserve(
        user,
        customer_code,
        session,
        question=body.question,
        urgency=body.urgency,
        alert_id=None if on_case else alert_id,
        cooldown_alert=alert_id,
    )
    try:
        if on_case:
            case_id = await open_case_for_alert(alert_id, customer_code, session) or await _case_from_alert(alert_id, user, session)
            comment_id = await _comment_on_case(case_id, comment_text(body.question, body.urgency), user, session)
            stored = await session.get(CustomerPortalSocRequest, request.id)
            stored.case_id, stored.origin_alert_id, stored.comment_id = case_id, alert_id, comment_id
            title = (await session.execute(select(Case.case_name).where(Case.id == case_id))).scalar_one_or_none() or title
        else:
            comment_id = await _comment_on_alert(alert_id, comment_text(body.question, body.urgency), user, session)
            stored = await session.get(CustomerPortalSocRequest, request.id)
            stored.comment_id = comment_id
        await session.commit()
        await session.refresh(stored)
    except Exception as e:  # noqa: BLE001 - the SOC's plumbing never reaches the customer
        logger.error(f"Could not file {user.username}'s question about alert {alert_id} ({customer_code}): {e}")
        await _forget(request.id, session)
        await _audit(user, customer_code, "alert", alert_id, AuditResult.FAILURE, "The question could not be filed")
        raise HTTPException(status_code=502, detail=FAILED)
    return await _sent(stored, title, user, session)


async def ask_on_case(case_id: int, body: AskOnCaseRequest, user: User, session: AsyncSession) -> PortalSocRequest:
    """A portal user's question about one of their cases, left on the case."""
    case = await ensure_case_visible(case_id, user, session)
    customer_code, title = case.customer_code, case.case_name
    request = await _reserve(
        user,
        customer_code,
        session,
        question=body.question,
        urgency=body.urgency,
        case_id=case_id,
        cooldown_case=case_id,
    )
    try:
        comment_id = await _comment_on_case(case_id, comment_text(body.question, body.urgency), user, session)
        stored = await session.get(CustomerPortalSocRequest, request.id)
        stored.comment_id = comment_id
        await session.commit()
        await session.refresh(stored)
    except Exception as e:  # noqa: BLE001 - the SOC's plumbing never reaches the customer
        logger.error(f"Could not file {user.username}'s question about case {case_id} ({customer_code}): {e}")
        await _forget(request.id, session)
        await _audit(user, customer_code, "case", case_id, AuditResult.FAILURE, "The question could not be filed")
        raise HTTPException(status_code=502, detail=FAILED)
    return await _sent(stored, title, user, session)


async def _sent(request: CustomerPortalSocRequest, title: Optional[str], user: User, session: AsyncSession) -> PortalSocRequest:
    """Tell the SOC and record it: after the question is filed, never before."""
    entity_type, entity_id = (EntityType.CASE, request.case_id) if request.case_id else (EntityType.ALERT, request.alert_id)
    emit(
        customer_question_event(
            request_id=request.id,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            customer_code=request.customer_code,
            urgency=request.urgency,
            asked_by=request.requested_by,
            question=request.question,
        ),
    )
    await _audit(
        user,
        request.customer_code,
        str(entity_type),
        entity_id,
        AuditResult.SUCCESS,
        None,
        new_value={"request_id": request.id, "urgency": request.urgency, "origin_alert_id": request.origin_alert_id},
    )
    logger.info(f"Portal user {user.username} asked the SOC about {entity_type} {entity_id} ({request.customer_code})")
    return to_portal(request)


# ── the SOC ───────────────────────────────────────────────────────────────────


async def mark_answered(request_id: int, user: User, session: AsyncSession) -> SocRequestOut:
    """An analyst marks a question answered by hand (a reply by phone). Idempotent."""
    request = await session.get(CustomerPortalSocRequest, request_id)
    if request is None or not await customer_access_handler.check_customer_access(user, request.customer_code, session):
        raise HTTPException(status_code=404, detail="Question not found")
    if request.status != ANSWERED:
        request.status = ANSWERED
        request.answered_at = _now()
        request.answered_by = user.username
        request.answered_via = VIA_MANUAL
        await session.commit()
        await session.refresh(request)
        await record_audit_event(
            action=AuditAction.SOC_REQUEST_ANSWER,
            actor_user_id=getattr(user, "id", None),
            actor_username=user.username,
            customer_code=request.customer_code,
            entity_type="soc_request",
            entity_id=request.id,
            new_value={"status": ANSWERED, "via": VIA_MANUAL},
        )
    cases, alerts = await _titles([request], session)
    return to_soc(request, cases, alerts)


async def _audit(
    user: User,
    customer_code: str,
    entity_type: str,
    entity_id: Optional[int],
    result: AuditResult,
    details: Optional[str],
    new_value: Optional[dict] = None,
) -> None:
    await record_audit_event(
        action=AuditAction.SOC_REQUEST_CREATE,
        actor_user_id=getattr(user, "id", None),
        actor_username=user.username,
        customer_code=customer_code,
        entity_type=entity_type,
        entity_id=entity_id,
        result=result,
        details=details,
        new_value=new_value,
    )
