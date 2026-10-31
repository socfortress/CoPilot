"""Talon chat in the Customer Portal: the per-customer switch and whether the chat is available
(talon-analyst SPEC D97, §5.3 "Portal chat: CoPilot's side"; plan PC-3).

- **The settings row** (``customer_portal_chat_settings``, one per customer, a missing row is off):
  the chat switch, the log-search switch, the daily message limits and a ``version`` bumped by every
  write. Written by an admin only (by the token's scope and the database role), audited
  (``talon_portal_chat.update``) with the old and new values. Turning the chat on needs the
  customer's AI reports on and a daily message limit (first build). talon-analyst reads the same row
  itself before every model request, failing closed.
- **The cascade**: turning a customer's AI reports off turns its chat off in the same transaction
  (``cascade_ai_reports_off``, called by the AI Report PUT); turning them on again doesn't.
- **Available** (``customer_available``): the row's switch with a daily limit, the customer's AI
  reports on, CoPilot's "Talon v2" setting on, and talon-analyst's own ``TALON_PORTAL_CHAT``, read
  from ``config.portal_chat`` of its ``GET /v2/health`` (cached 60 s; an unknown answer reads as off).
  The availability route, the portal proxy on every request and the portal UI all use this one rule.
"""
import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.auth.services.read_only import is_read_only_for
from app.connectors.talon.services.talon_v2 import is_v2_enabled
from app.connectors.talon.utils import health_client
from app.connectors.talon.utils.v2_client import TALON_CONNECTOR
from app.connectors.utils import get_connector_info_from_db
from app.customer_portal.services import soc_requests
from app.customer_portal.services.ai_reports import get_ai_report_settings
from app.customer_portal.services.ai_reports import requests_allowed
from app.db.db_session import get_db_session
from app.db.universal_models import CustomerPortalChatSettings
from app.middleware.customer_access import customer_access_handler
from app.time_utils import now_utc

#: The form's proposals for a customer switched on for the first time (D97 (y)); editable.
PROPOSED_DAILY_MESSAGE_LIMIT = 200
PROPOSED_USER_DAILY_MESSAGE_LIMIT = 50
LIMIT_MIN = 1
LIMIT_MAX = 100_000

#: The PUT's validation texts (422, code ``invalid_request``). Fixed: they never echo input.
NEEDS_AI_REPORTS = "portal chat can only be turned on while the customer's AI reports are on"
NEEDS_DAILY_LIMIT = "portal chat can only be turned on with a daily message limit for the customer"
LIMIT_RANGE = f"daily message limits are whole numbers from {LIMIT_MIN} to {LIMIT_MAX:,}"
USER_OVER_CUSTOMER = "the per-user daily message limit can't be more than the customer's"
USER_WITHOUT_CUSTOMER = "set the customer's daily message limit before a per-user limit"

#: How long talon-analyst's ``config.portal_chat`` is trusted (SPEC §5.3: cached 60 s).
HEALTH_CACHE_SECONDS = 60.0
MAX_HEALTH_BYTES = 256 * 1024


# ── the row ───────────────────────────────────────────────────────────────────


async def get_settings(customer_code: str, session: AsyncSession, *, lock: bool = False) -> Optional[CustomerPortalChatSettings]:
    query = select(CustomerPortalChatSettings).where(CustomerPortalChatSettings.customer_code == customer_code)
    if lock:
        query = query.with_for_update()
    return (await session.execute(query)).scalars().first()


def values_of(row: Optional[CustomerPortalChatSettings]) -> Dict[str, Any]:
    """What an admin sets, as stored (no row: everything off)."""
    if row is None:
        return {"portal_chat_enabled": False, "log_search_enabled": False, "daily_message_limit": None, "user_daily_message_limit": None}
    return {
        "portal_chat_enabled": bool(row.portal_chat_enabled),
        "log_search_enabled": bool(row.log_search_enabled),
        "daily_message_limit": row.daily_message_limit,
        "user_daily_message_limit": row.user_daily_message_limit,
    }


def chat_switched_on(row: Optional[CustomerPortalChatSettings]) -> bool:
    """The row's own half of the rule: on, and with a customer limit (a row switched on without one
    reads as off, as talon-analyst reads it)."""
    return bool(row is not None and row.portal_chat_enabled and row.daily_message_limit is not None)


def validation_problem(values: Mapping[str, Any], ai_reports_enabled: bool) -> Optional[str]:
    """Why an admin's values can't be saved, or None. Pure, so the rules test without a database."""
    daily, per_user = values.get("daily_message_limit"), values.get("user_daily_message_limit")
    for limit in (daily, per_user):
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or not LIMIT_MIN <= limit <= LIMIT_MAX):
            return LIMIT_RANGE
    if per_user is not None and daily is None:
        return USER_WITHOUT_CUSTOMER
    if per_user is not None and per_user > daily:
        return USER_OVER_CUSTOMER
    if values.get("portal_chat_enabled"):
        if not ai_reports_enabled:
            return NEEDS_AI_REPORTS
        if daily is None:
            return NEEDS_DAILY_LIMIT
    return None


async def _audit(user: Optional[User], customer_code: str, old: Dict[str, Any], new: Dict[str, Any], details: Optional[str] = None) -> None:
    await record_audit_event(
        action=AuditAction.TALON_PORTAL_CHAT_UPDATE,
        actor_user_id=getattr(user, "id", None),
        actor_username=getattr(user, "username", None),
        customer_code=customer_code,
        entity_type="customer_portal_chat_settings",
        entity_id=customer_code,
        old_value=old,
        new_value=new,
        details=details,
    )


async def save_settings(
    customer_code: str,
    values: Mapping[str, Any],
    user: User,
    session: AsyncSession,
) -> Tuple[Optional[CustomerPortalChatSettings], Optional[str]]:
    """Validate and store an admin's values: ``(row, None)``, or ``(None, problem)`` with nothing
    written. Under a lock on the customer's row (and its AI Report row), so the AI-reports rule and
    the version bump hold against a concurrent write. Bumps ``version`` and audits, every write."""
    await session.commit()  # a fresh snapshot for the locked reads
    for attempt in range(2):
        ai = await get_ai_report_settings(customer_code, session, lock=True)
        row = await get_settings(customer_code, session, lock=True)
        problem = validation_problem(values, bool(ai and ai.enabled))
        if problem is not None:
            await session.rollback()
            return None, problem
        old = {**values_of(row), "version": row.version if row is not None else None}
        if row is None:
            row = CustomerPortalChatSettings(customer_code=customer_code, version=0)
            session.add(row)
        row.portal_chat_enabled = bool(values["portal_chat_enabled"])
        row.log_search_enabled = bool(values["log_search_enabled"])
        row.daily_message_limit = values.get("daily_message_limit")
        row.user_daily_message_limit = values.get("user_daily_message_limit")
        row.version = (row.version or 0) + 1
        row.updated_by = getattr(user, "id", None)
        row.updated_at = now_utc()
        try:
            await session.commit()
        except IntegrityError:  # two admins creating the row at once: the loser updates the winner's
            await session.rollback()
            if attempt:
                raise
            continue
        await session.refresh(row)
        await _audit(user, customer_code, old, {**values_of(row), "version": row.version})
        logger.info(f"Talon portal chat settings for {customer_code}: {values_of(row)} (version {row.version})")
        return row, None
    raise AssertionError("unreachable")


async def cascade_ai_reports_off(
    customer_code: str,
    user: Optional[User],
    session: AsyncSession,
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """The cascade (SPEC §5.3): the customer's AI reports are being turned off, so its portal chat
    is turned off too, in the caller's transaction (the caller commits, then calls
    ``audit_cascade``). Nothing happens when the chat is already off. Returns the old and new values
    to audit, or None."""
    row = await get_settings(customer_code, session, lock=True)
    if row is None or not row.portal_chat_enabled:
        return None
    old = {**values_of(row), "version": row.version}
    row.portal_chat_enabled = False
    row.version = (row.version or 0) + 1
    row.updated_by = getattr(user, "id", None)
    row.updated_at = now_utc()
    return old, {**values_of(row), "version": row.version}


async def audit_cascade(customer_code: str, user: Optional[User], change: Optional[Tuple[Dict[str, Any], Dict[str, Any]]]) -> None:
    if change is not None:
        old, new = change
        await _audit(user, customer_code, old, new, details="Portal chat turned off because the customer's AI reports were turned off")
        logger.info(f"Talon portal chat turned off for {customer_code}: its AI reports were turned off")


# ── talon-analyst's own switch (config.portal_chat of GET /v2/health) ─────────

_HEALTH_CACHE: Dict[str, Tuple[float, bool]] = {}
_HEALTH_LOCKS: Dict[str, asyncio.Lock] = {}


def clear_health_cache() -> None:
    _HEALTH_CACHE.clear()
    _HEALTH_LOCKS.clear()


def _health_key(attributes: Mapping[str, Any]) -> str:
    """Per connector state, as a digest (the key itself never sits in the dict's keys)."""
    material = "\x00".join(
        str(attributes.get(name) or "") for name in ("connector_name", "connector_url", "connector_api_key", "connector_last_updated")
    )
    return hashlib.sha256(material.encode()).hexdigest()


def portal_chat_from_health(status: Optional[int], body: bytes) -> bool:
    """``config.portal_chat`` of a ``/v2/health`` answer; anything but a 2xx whose value is ``true`` is off."""
    if status is None or not 200 <= status < 300:
        return False
    try:
        payload = json.loads(body)
    except (ValueError, RecursionError):
        return False
    config = payload.get("config") if isinstance(payload, dict) else None
    return isinstance(config, dict) and config.get("portal_chat") is True


async def _connector_attributes() -> Optional[Dict[str, Any]]:
    async with get_db_session() as session:
        return await get_connector_info_from_db(TALON_CONNECTOR, session)


async def talon_portal_chat_on() -> bool:
    """Whether talon-analyst's ``TALON_PORTAL_CHAT`` is on, from its ``/v2/health``; off when unknown."""
    try:
        attributes = await _connector_attributes()
    except Exception as e:  # noqa: BLE001 - no connector row readable: unknown, so off
        logger.warning(f"Talon portal chat: the Talon connector could not be read ({type(e).__name__})")
        return False
    url = str((attributes or {}).get("connector_url") or "").strip()
    if not url:
        return False
    key = _health_key(attributes)
    cached = _HEALTH_CACHE.get(key)
    if cached is not None and cached[0] > time.monotonic():
        return cached[1]
    lock = _HEALTH_LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _HEALTH_CACHE.get(key)
        if cached is not None and cached[0] > time.monotonic():
            return cached[1]
        probe = await health_client.get(
            url,
            "/v2/health",
            api_key=str(attributes.get("connector_api_key") or ""),
            max_body_bytes=MAX_HEALTH_BYTES,
        )
        on = portal_chat_from_health(probe.status, probe.body)
        now = time.monotonic()
        for stale in [k for k, (expires, _) in _HEALTH_CACHE.items() if expires <= now]:
            _HEALTH_CACHE.pop(stale, None)
        _HEALTH_CACHE[key] = (now + HEALTH_CACHE_SECONDS, on)
        return on


# ── availability: the one rule ────────────────────────────────────────────────


@dataclass(frozen=True)
class CustomerChat:
    """One customer's portal chat as CoPilot's tables say (talon-analyst's own switch apart)."""

    customer_code: str
    row: Optional[CustomerPortalChatSettings]
    ai_reports_enabled: bool
    analysis_requests: bool
    soc_requests_enabled: bool

    @property
    def switched_on(self) -> bool:
        return chat_switched_on(self.row) and self.ai_reports_enabled

    @property
    def log_search(self) -> bool:
        return bool(self.row is not None and self.row.log_search_enabled)


async def customer_chat(customer_code: str, session: AsyncSession) -> CustomerChat:
    ai = await get_ai_report_settings(customer_code, session)
    soc = await soc_requests.get_settings(customer_code, session)
    return CustomerChat(
        customer_code=customer_code,
        row=await get_settings(customer_code, session),
        ai_reports_enabled=bool(ai and ai.enabled),
        analysis_requests=requests_allowed(ai),
        soc_requests_enabled=bool(soc and soc.enabled),
    )


async def deployment_on(session: AsyncSession) -> bool:
    """The deployment's half: CoPilot's "Talon v2" setting, then talon-analyst's ``TALON_PORTAL_CHAT``."""
    return await is_v2_enabled(session) and await talon_portal_chat_on()


async def own_customers(user: User, session: AsyncSession) -> List[str]:
    """The customers ``user`` is assigned to, never ``*`` (a portal user's are always a list)."""
    return sorted(code for code in await customer_access_handler.get_user_accessible_customers(user, session) if code != "*")


async def enabled_customers(user: User, session: AsyncSession, *, deployment: Optional[bool] = None) -> List[str]:
    """The user's own customers whose portal chat is available now (the whole rule)."""
    codes = await own_customers(user, session)
    switched = [code for code in codes if (await customer_chat(code, session)).switched_on]
    if not switched:
        return []
    if deployment is None:
        deployment = await deployment_on(session)
    return switched if deployment else []


@dataclass(frozen=True)
class Availability:
    customer_code: Optional[str]
    enabled: bool
    log_search: bool
    can_draft: bool
    can_request_analysis: bool


async def availability(user: User, session: AsyncSession, customer_code: Optional[str]) -> Availability:
    """``GET /customer_portal/talon_chat/availability``: for one customer the caller may see, or,
    without one, the first of the caller's own customers where the chat is available (else the
    first of them, off). The caller's access is checked by the route."""
    if customer_code is None:
        codes = await own_customers(user, session)
        if not codes:
            return Availability(None, False, False, False, False)
        enabled = await enabled_customers(user, session)
        customer_code = enabled[0] if enabled else codes[0]
    chat = await customer_chat(customer_code, session)
    enabled = chat.switched_on and await deployment_on(session)
    writable = not await is_read_only_for(user, customer_code, session)
    return Availability(
        customer_code=customer_code,
        enabled=enabled,
        log_search=enabled and chat.log_search,
        can_draft=enabled and chat.soc_requests_enabled and writable,
        can_request_analysis=enabled and chat.analysis_requests and writable,
    )
