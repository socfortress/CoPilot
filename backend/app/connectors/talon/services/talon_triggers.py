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

**The binding** (``lock_triggers`` then ``check``, called by ``/api/artifacts/collect/start`` for the
Talon service account when the body names ``alert_id``), all in the start's own transaction, around
the host's lock:

1. the alert exists, and its newest row for the alert's customer was sent within ``WINDOW``;
2. that row's source is ``pipeline`` or ``analyst`` (a portal request or a replay is refused);
3. the host is one of the alert's assets in that row (by name, as ``agents`` matches it, and with the
   asset's Velociraptor client, when it has one), and its locked ``agents`` row is the alert's
   customer's;
4. fewer than ``PER_ALERT_CAP`` collections bound to the alert started in the last ``WINDOW``, all
   jobs together (a new ``ai_analyst_job`` never resets it), counted from the ``ARTIFACT_COLLECT``
   audit rows whose ``new_value`` names the alert, until AP-2's ``talon_automation_start`` exists.

The alert's rows are locked for the start's transaction (``FOR UPDATE``, before the host's), so two
starts for one alert are counted one after the other. Every refusal is a fixed text with no part of the request.
"""
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditLog
from app.connectors.talon.models.talon_v2 import AUTOMATION_SOURCES
from app.connectors.talon.models.talon_v2 import TRIGGER_SOURCES
from app.connectors.talon.models.talon_v2 import TalonInvestigationTrigger
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

NO_TRIGGER = "not started: CoPilot has not sent this alert to Talon in the last 2 hours"
PORTAL_TRIGGER = "not started: this alert was last sent to Talon from the customer portal, which never leads to an automated action"
REPLAY_TRIGGER = "not started: this alert was last sent to Talon as a replay, which never leads to an automated action"
NOT_ALERT_HOST = "not started: the host is not one of the alert's assets"
ALERT_CAP = "not started: this alert has reached its cap of automated collections"
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


async def record(alert_id: int, customer_code: str, source: str, user: Any = None) -> TalonInvestigationTrigger:
    """Write the row for one ``/investigate`` CoPilot is about to send, in a session of its own,
    committed before the call (talon-analyst may start a collection before the call returns)."""
    if source not in TRIGGER_SOURCES:
        raise ValueError(f"unknown trigger source {source!r}")
    async with new_session() as session:
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


async def record_before_sending(alert_id: int, customer_code: str, source: str, user: Any = None) -> None:
    """``record``, with the failure rule in the module docstring: a ``portal`` or ``replay`` send is
    refused (500, a fixed text) when its row can't be written; a ``pipeline`` or ``analyst`` one goes
    ahead, and nothing can be bound to it."""
    try:
        await record(alert_id, customer_code, source, user)
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


async def started_for_alert(session: AsyncSession, alert_id: int, since: datetime) -> int:
    """Collections bound to the alert since ``since``: its ``ARTIFACT_COLLECT`` audit rows (only a
    bound start writes ``alert_id`` into one)."""
    return (
        await session.execute(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action == AuditAction.ARTIFACT_COLLECT.value,
                AuditLog.timestamp >= since,
                AuditLog.new_value["alert_id"].as_integer() == alert_id,
            ),
        )
    ).scalar_one()


async def lock_triggers(session: AsyncSession, alert_id: int) -> List[TalonInvestigationTrigger]:
    """The alert's records, newest first, locked for ``session``'s transaction (``FOR UPDATE``): a
    second start for the alert waits here until the first's transaction ends. Call it first in the
    transaction, before the host's lock: under REPEATABLE READ the snapshot is taken by the first
    plain read, which must come after every lock, so that ``check`` counts the audit rows of a start
    that held these locks before us and the start function sees the host as it was locked."""
    return list(
        (
            await session.execute(
                select(TalonInvestigationTrigger)
                .where(TalonInvestigationTrigger.alert_id == alert_id)
                .order_by(TalonInvestigationTrigger.sent_at.desc(), TalonInvestigationTrigger.id.desc())
                .with_for_update(),
            )
        )
        .scalars()
        .all(),
    )


async def check(
    session: AsyncSession,
    rows: List[TalonInvestigationTrigger],
    alert_id: int,
    hostname: str,
    client: str,
    host_customer: Optional[str],
) -> Binding:
    """The binding (module docstring) from the alert's locked records (``lock_triggers``), once the
    host's ``agents`` row (of ``host_customer``) is locked too. ``hostname`` is validated and
    ``client`` canonical. A fixed 403 (429 over the cap) otherwise."""
    customer_code = (await session.execute(select(Alert.customer_code).where(Alert.id == alert_id))).scalars().first()
    if customer_code is None:
        logger.warning(f"Refused a bound collection start for alert {alert_id}: no such alert")
        raise HTTPException(status_code=403, detail=NO_TRIGGER)
    since = utcnow() - WINDOW
    newest = next((row for row in rows if row.customer_code == customer_code), None)
    if newest is None or newest.sent_at < since:
        logger.warning(f"Refused a bound collection start for alert {alert_id}: CoPilot sent it no investigation in the window")
        raise HTTPException(status_code=403, detail=NO_TRIGGER)
    if newest.source not in AUTOMATION_SOURCES:
        logger.warning(f"Refused a bound collection start for alert {alert_id}: its newest trigger is {newest.source}")
        raise HTTPException(status_code=403, detail=_REFUSED_SOURCE.get(newest.source, NO_TRIGGER))
    if host_customer != customer_code or not _host_is_an_asset(newest.assets, hostname, client):
        logger.warning(f"Refused a bound collection start for alert {alert_id}: {hostname} ({client}) is not one of its assets")
        raise HTTPException(status_code=403, detail=NOT_ALERT_HOST)
    if await started_for_alert(session, alert_id, since) >= PER_ALERT_CAP:
        logger.warning(f"Refused a bound collection start for alert {alert_id}: the per-alert cap ({PER_ALERT_CAP}) is reached")
        raise HTTPException(status_code=429, detail=ALERT_CAP)
    return Binding(
        alert_id=alert_id,
        customer_code=customer_code,
        trigger_id=newest.id,
        source=newest.source,
        user_id=newest.user_id,
        username=newest.username,
    )
