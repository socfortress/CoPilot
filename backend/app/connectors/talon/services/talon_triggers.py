"""CoPilot's own record of every alert it sends to Talon, and the binding of the Talon service
account's automated collections to it (talon-analyst plan AP-2a; SPEC D85 (l), D86 (j)).

**The record** (``talon_investigation_trigger``). CoPilot sends ``POST /investigate`` from four
places, and each writes a row before the call (``record``), its ``source`` set by the calling code
path, never parsed from the ``sender`` string:

- ``pipeline``: the alert pipeline (``incidents/services/incident_alert.py``, through
  ``services/talon.py:investigate_alert``);
- ``analyst``: "Investigate with AI Analyst" (``investigate_alert_for_user``), with the analyst;
- ``portal``: a customer portal request (``customer_portal/services/ai_requests.py``), with the user;
- ``replay``: a report replay (``replay_investigation``), with whoever replayed it.

Each row also keeps the alert's assets as they were when it was sent. ``ai_analyst_job`` and its
``triggered_by`` are never evidence here: talon-analyst writes them.

If the row can't be written, a ``portal`` or ``replay`` send is refused (a missing row would leave an
older pipeline or analyst row as the alert's newest, and with it an automation window), while a
``pipeline`` or ``analyst`` send goes ahead: without its row, nothing can be bound to it.

**The binding** (``check``, then ``reserve``, called by ``/api/artifacts/collect/start`` for the Talon
service account once the host's ``agents`` row is locked; its start without ``alert_id`` is refused
before anything else, ``ALERT_REQUIRED``, so leaving the field out never skips the binding):

1. the alert exists, and its newest row (by id) was sent within ``WINDOW``, for the alert's own
   customer;
2. that row's source is ``pipeline`` or ``analyst`` (a portal request or a replay is refused), and it
   wasn't sent by the Talon service account (refused on every sending route; refused here too);
3. the host is one of the alert's assets in that row (by name, as ``agents`` matches it, and with the
   asset's Velociraptor client, when it has one), and its locked ``agents`` row is the alert's
   customer's;
4. a slot under ``PER_ALERT_CAP`` for the alert's current ``WINDOW``, every job together (a new
   ``ai_analyst_job`` never resets it), taken from ``talon_automation_alert_cap`` by one guarded
   ``UPDATE`` and committed before the flow starts; a slot that can't be recorded is no start. Never
   counted from the audit log, whose writes are best-effort. The window starts at the alert's first
   bound start and lasts ``WINDOW``.

Every refusal is a fixed text with no part of the request.
"""
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import case
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.talon.models.talon_v2 import AUTOMATION_SOURCES
from app.connectors.talon.models.talon_v2 import TRIGGER_SOURCES
from app.connectors.talon.models.talon_v2 import TalonAutomationAlertCap
from app.connectors.talon.models.talon_v2 import TalonInvestigationTrigger
from app.connectors.talon.services.talon_service_account import is_service_account
from app.connectors.talon.services.talon_service_account import settings_row
from app.db.db_session import AsyncSessionLocal
from app.incidents.models import Alert
from app.incidents.models import Asset
from app.time_utils import now_utc
from app.time_utils import to_naive_utc

PIPELINE, ANALYST, PORTAL, REPLAY = TRIGGER_SOURCES
#: How long after CoPilot sends an alert an automated collection may be bound to it.
WINDOW = timedelta(hours=2)
#: Automated collections per alert per ``WINDOW``, every job together: level 1's per-run cap (D77,
#: plan Q9), enforced per alert here since CoPilot can't trust a job boundary talon-analyst draws.
PER_ALERT_CAP = 2

ALERT_REQUIRED = "not started: the Talon service account must name the alert its collection is for (alert_id)"
NO_TRIGGER = "not started: CoPilot has not sent this alert to Talon in the last 2 hours"
PORTAL_TRIGGER = "not started: this alert was last sent to Talon from the customer portal, which never leads to an automated action"
REPLAY_TRIGGER = "not started: this alert was last sent to Talon as a replay, which never leads to an automated action"
OTHER_CUSTOMER = "not started: the alert's newest record names another customer than the alert's"
SERVICE_TRIGGER = "not started: this alert was last sent to Talon by the Talon service account, which never leads to an automated action"
NOT_ALERT_HOST = "not started: the host is not one of the alert's assets"
ALERT_CAP = "not started: this alert has reached its cap of automated collections"
CAP_UNRECORDED = "not started: CoPilot could not record the start against this alert's cap"
NOT_RECORDED = "CoPilot could not record the investigation request, so it was not sent"

_REFUSED_SOURCE = {PORTAL: PORTAL_TRIGGER, REPLAY: REPLAY_TRIGGER}


def new_session() -> AsyncSession:
    """A short session of the record's own (tests point this at their database)."""
    return AsyncSessionLocal()


def utcnow() -> datetime:
    """Now as the naive UTC the ``DATETIME`` columns hold."""
    return to_naive_utc(now_utc())


# ── the record ────────────────────────────────────────────────────────────────


async def _assets(session: AsyncSession, alert_id: int, customer_code: str) -> List[Dict[str, Optional[str]]]:
    rows = (
        await session.execute(
            select(Asset.asset_name, Asset.velociraptor_id)
            .where(Asset.alert_linked == alert_id, Asset.customer_code == customer_code)
            .order_by(Asset.id),
        )
    ).all()
    return [{"asset_name": name, "velociraptor_id": vid} for name, vid in rows]


async def record(alert_id: int, source: str, user: Any = None) -> TalonInvestigationTrigger:
    """Write the row for one ``/investigate`` CoPilot is about to send, in a session of its own,
    committed before the call (talon-analyst may start a collection before the call returns). The
    customer is the alert's own, read from CoPilot's row, never the caller's; no alert, no row."""
    if source not in TRIGGER_SOURCES:
        raise ValueError(f"unknown trigger source {source!r}")
    async with new_session() as session:
        customer_code = (await session.execute(select(Alert.customer_code).where(Alert.id == alert_id))).scalars().first()
        if customer_code is None:
            raise LookupError("no such alert")
        row = TalonInvestigationTrigger(
            alert_id=alert_id,
            customer_code=customer_code,
            source=source,
            user_id=getattr(user, "id", None),
            username=getattr(user, "username", None),
            assets=await _assets(session, alert_id, customer_code),
            sent_at=utcnow(),
        )
        session.add(row)
        await session.commit()
        return row


async def record_before_sending(alert_id: int, source: str, user: Any = None) -> None:
    """``record``, with the failure rule in the module docstring: a ``portal`` or ``replay`` send is
    refused (500, a fixed text) when its row can't be written; a ``pipeline`` or ``analyst`` one goes
    ahead, and nothing can be bound to it."""
    try:
        await record(alert_id, source, user)
    except Exception as e:  # noqa: BLE001 - the rule below decides, whatever the database said
        logger.error(f"Could not record the Talon investigation trigger for alert {alert_id} ({source}): {type(e).__name__}")
        if source not in AUTOMATION_SOURCES:
            raise HTTPException(status_code=500, detail=NOT_RECORDED) from None


# ── the binding ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Binding:
    """The trigger an automated collection is bound to: what its audit event names."""

    alert_id: int
    customer_code: str
    trigger_id: int
    source: str
    user_id: Optional[int]
    username: Optional[str]

    def audit_values(self, job_id: Optional[str]) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "job_id": job_id,
            "trigger_id": self.trigger_id,
            "trigger_source": self.source,
            "trigger_user_id": self.user_id,
            "trigger_username": self.username,
        }


def _host_is_an_asset(assets: Any, hostname: str, client: str) -> bool:
    # Imported here: ``talon_action_execution`` imports the incident routes, which import the alert
    # pipeline, which imports ``services/talon.py``, which imports this module to record.
    from app.connectors.talon.services.talon_action_execution import claimed_client_id

    for asset in assets if isinstance(assets, list) else []:
        if not isinstance(asset, dict) or not isinstance(asset.get("asset_name"), str):
            continue
        if asset["asset_name"].lower() != hostname.lower():
            continue
        vid = asset.get("velociraptor_id")
        if not vid or claimed_client_id(vid) == client:
            return True
    return False


async def check(session: AsyncSession, alert_id: int, hostname: str, client: str, host_customer: Optional[str]) -> Binding:
    """Checks 1-3 of the binding (module docstring), in ``session``'s transaction once the host's
    ``agents`` row (of ``host_customer``) is locked: its plain reads come after the lock, so the
    start function sees the host as it was locked. ``hostname`` is validated and ``client``
    canonical. A fixed 403 otherwise; the cap is ``reserve``'s."""
    customer_code = (await session.execute(select(Alert.customer_code).where(Alert.id == alert_id))).scalars().first()
    if customer_code is None:
        logger.warning(f"Refused a bound collection start for alert {alert_id}: no such alert")
        raise HTTPException(status_code=403, detail=NO_TRIGGER)
    # The alert's newest record, whatever its customer (by id: rows are written in send order).
    newest = (
        (
            await session.execute(
                select(TalonInvestigationTrigger)
                .where(TalonInvestigationTrigger.alert_id == alert_id)
                .order_by(TalonInvestigationTrigger.id.desc())
                .limit(1),
            )
        )
        .scalars()
        .first()
    )
    if newest is None or newest.sent_at < utcnow() - WINDOW:
        logger.warning(f"Refused a bound collection start for alert {alert_id}: CoPilot sent it no investigation in the window")
        raise HTTPException(status_code=403, detail=NO_TRIGGER)
    if newest.customer_code != customer_code:
        logger.warning(f"Refused a bound collection start for alert {alert_id}: its newest record names another customer")
        raise HTTPException(status_code=403, detail=OTHER_CUSTOMER)
    if newest.source not in AUTOMATION_SOURCES:
        logger.warning(f"Refused a bound collection start for alert {alert_id}: its newest trigger is {newest.source}")
        raise HTTPException(status_code=403, detail=_REFUSED_SOURCE.get(newest.source, NO_TRIGGER))
    if (newest.user_id is not None or newest.username is not None) and is_service_account(
        SimpleNamespace(id=newest.user_id, username=newest.username),
        await settings_row(session),
    ):
        # Belt and braces: the service account is refused on every route that sends an alert to Talon.
        logger.warning(f"Refused a bound collection start for alert {alert_id}: its newest trigger was sent by the Talon service account")
        raise HTTPException(status_code=403, detail=SERVICE_TRIGGER)
    if host_customer != customer_code or not _host_is_an_asset(newest.assets, hostname, client):
        logger.warning(f"Refused a bound collection start for alert {alert_id}: {hostname} ({client}) is not one of its assets")
        raise HTTPException(status_code=403, detail=NOT_ALERT_HOST)
    return Binding(
        alert_id=alert_id,
        customer_code=customer_code,
        trigger_id=newest.id,
        source=newest.source,
        user_id=newest.user_id,
        username=newest.username,
    )


async def _take_slot(session: AsyncSession, alert_id: int, customer_code: str, now: datetime, cap: int = PER_ALERT_CAP) -> bool:
    """One guarded UPDATE: a slot while the window holds fewer than ``cap``, or a new window once it
    has passed (a cap of 0 gives none). Atomic on its own, so two starts at the cap minus one can't
    both take the last slot."""
    if cap < 1:
        return False
    expired = TalonAutomationAlertCap.window_started_at < now - WINDOW
    result = await session.execute(
        update(TalonAutomationAlertCap).where(
            TalonAutomationAlertCap.alert_id == alert_id,
            or_(expired, TalonAutomationAlertCap.starts < cap),
        )
        # ``starts`` first. MySQL and MariaDB assign a single-table UPDATE's SET left to right, each
        # later expression seeing the earlier columns' new values; SQLite and standard SQL use the
        # old row throughout. With ``starts`` first, both read the old window. Reversed, MySQL
        # would see the new window and count on from the old ``starts``.
        .ordered_values(
            (TalonAutomationAlertCap.starts, case((expired, 1), else_=TalonAutomationAlertCap.starts + 1)),
            (TalonAutomationAlertCap.window_started_at, case((expired, now), else_=TalonAutomationAlertCap.window_started_at)),
        ),
    )
    return result.rowcount == 1


async def ensure_cap_row(session: AsyncSession, binding: Binding) -> None:
    """The alert's cap row, created empty in a transaction of its own if it is missing (a concurrent
    creator's duplicate is ignored), and the session's transaction ended, so a guarded UPDATE that
    follows finds an existing row (``reserve``'s docstring: gap locks on MySQL otherwise)."""
    if await session.get(TalonAutomationAlertCap, binding.alert_id) is None:
        session.add(
            TalonAutomationAlertCap(
                alert_id=binding.alert_id,
                customer_code=binding.customer_code,
                starts=0,
                window_started_at=utcnow(),
            ),
        )
        try:
            await session.commit()
        except IntegrityError:  # a concurrent start created it
            await session.rollback()
    else:
        await session.rollback()  # ends the read's snapshot before the UPDATE


async def reserve(binding: Binding) -> None:
    """**Not on any route since AP-2**: ``talon_automation.reserve_start`` takes the slot inside its
    own transaction (``ensure_cap_row`` and ``_take_slot``). Kept, with AP-2a's tests and
    ``tests/e2e/talon_alert_cap_mysql_e2e.py``, as the slot's reference behaviour on its own.

    Check 4: take one of the alert's ``PER_ALERT_CAP`` slots for this ``WINDOW``, every job
    together (a new ``ai_analyst_job`` never resets it), in a session of its own, committed before
    the flow starts. Over the cap, a fixed 429; if the slot can't be recorded, a fixed 500 and no
    start. A slot is spent once taken, whether the start then succeeds or not.

    The alert's row is created first, empty, in a transaction of its own (a concurrent creator's
    duplicate is ignored), and the slot is then taken from the existing row. On MySQL, a guarded
    UPDATE of a missing row takes gap locks, and concurrent INSERTs after it deadlock; an UPDATE of
    an existing row only waits for its row lock (``tests/e2e/talon_alert_cap_mysql_e2e.py``)."""
    try:
        async with new_session() as session:
            await ensure_cap_row(session, binding)
            if await _take_slot(session, binding.alert_id, binding.customer_code, utcnow()):
                await session.commit()
                return
            await session.rollback()
    except Exception as e:  # noqa: BLE001 - no slot recorded, no start
        logger.error(f"Could not record a bound collection start for alert {binding.alert_id}: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=CAP_UNRECORDED) from None
    logger.warning(f"Refused a bound collection start for alert {binding.alert_id}: the per-alert cap ({PER_ALERT_CAP}) is reached")
    raise HTTPException(status_code=429, detail=ALERT_CAP)
