"""
A verdict given on the UBA page, written back to the CoPilot incident alert (#1239).

UBA already reads verdicts the other way: its worker polls the incident alerts it
created and applies their verdict. A verdict given on a UBA alert went to UBA only,
which also marks that alert's delivery so the poller never applies it twice, so the
incident alert stayed untriaged. This writes the same verdict onto it, once UBA has
accepted it. Every outcome other than ``recorded`` leaves the incident alert alone and
says why; none of them undoes the verdict UBA already holds.

Things to keep in mind:

- **CoPilot merges a UBA entity's alerts into one incident alert** (the title is per
  entity). UBA's poller applies an incident verdict to every merged UBA alert still
  without one, *always* suppressing on FALSE_POSITIVE. So a false positive saved
  without suppression is not written back while another of the incident's UBA alerts
  is still open: the poller would suppress the rules the analyst chose to keep.
- **An incident verdict already set is never overwritten.** It is an analyst's decision
  made in CoPilot; the response reports it so the UI can show a disagreement.
- **The incident alert must belong to the path's customer** (the one
  ``verify_customer_code_access`` authorised) and be visible to the caller under tag
  RBAC, the same checks ``PUT /incidents/db_operations/alert/verdict`` makes.
"""

from typing import Literal
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.connectors.uba.schema.uba import UbaFeedbackRequest
from app.connectors.uba.services import uba as svc
from app.incidents.models import Alert
from app.incidents.schema.db_operations import FalsePositiveReason
from app.incidents.services.db_operations import get_alert_by_id
from app.incidents.services.db_operations import update_alert_verdict

SyncStatus = Literal["recorded", "already_set", "not_linked", "skipped", "failed"]


class UbaIncidentVerdict(BaseModel):
    """What happened to the linked incident alert. ``verdict`` is the incident's verdict afterwards."""

    status: SyncStatus
    incident_alert_id: Optional[int] = None
    verdict: Optional[str] = None
    message: str = ""


def incident_reason(verdict: str, reason: Optional[str]) -> Optional[str]:
    """CoPilot's reason for a UBA verdict: required on FALSE_POSITIVE and a closed vocabulary,
    while UBA takes free text. The UBA page offers CoPilot's own list; anything else is OTHER."""
    if verdict != "FALSE_POSITIVE":
        return None
    valid = {r.value for r in FalsePositiveReason}
    return reason if reason in valid else FalsePositiveReason.OTHER.value


async def _open_siblings(customer_code: str, entity_key: str, uba_alert_id: str, incident_id: int) -> int:
    """The incident's other UBA alerts that have no verdict yet (the poller would give them this one)."""
    page = await svc.list_alerts(customer_code, entity_key=entity_key, status="open", page_size=500)
    alerts = (page.model_extra or {}).get("alerts") or []
    return sum(1 for a in alerts if a.get("copilot_alert_id") == incident_id and a.get("id") != uba_alert_id)


async def record_on_incident(
    customer_code: str,
    uba_alert_id: str,
    body: UbaFeedbackRequest,
    user: User,
    db: AsyncSession,
) -> Tuple[UbaIncidentVerdict, Optional[Alert], Optional[dict]]:
    """Write the UBA verdict onto the linked incident alert. Returns the outcome and, when it was
    recorded, the updated alert and its previous verdict (for the caller's audit record)."""
    uba_alert = (await svc.get_alert(customer_code, uba_alert_id)).model_extra.get("alert") or {}
    incident_id = uba_alert.get("copilot_alert_id")
    if not incident_id:
        return UbaIncidentVerdict(status="not_linked", message="This UBA alert has no incident alert in CoPilot."), None, None

    def outcome(status: SyncStatus, message: str, verdict: Optional[str] = None) -> UbaIncidentVerdict:
        return UbaIncidentVerdict(status=status, incident_alert_id=incident_id, verdict=verdict, message=message)

    if body.verdict == "FALSE_POSITIVE" and not body.suppress:
        siblings = await _open_siblings(customer_code, uba_alert.get("entity_key") or "", uba_alert_id, incident_id)
        if siblings:
            return (
                outcome(
                    "skipped",
                    f"Incident alert #{incident_id} also holds {siblings} other open UBA alert(s) for this entity; "
                    "a false positive there would suppress their rules, so it was left untriaged.",
                ),
                None,
                None,
            )

    try:
        incident = await get_alert_by_id(incident_id, db, user=user)
    except HTTPException as e:
        if e.status_code == 404:
            return outcome("not_linked", f"Incident alert #{incident_id} no longer exists."), None, None
        return outcome("skipped", f"You cannot see incident alert #{incident_id}."), None, None
    if incident.customer_code != customer_code:
        return outcome("skipped", f"Incident alert #{incident_id} belongs to another customer."), None, None
    if incident.verdict:
        return outcome("already_set", f"Incident alert #{incident_id} already has a verdict.", incident.verdict), None, None

    updated, previous = await update_alert_verdict(
        alert_id=incident_id,
        verdict=body.verdict,
        verdict_reason=incident_reason(body.verdict, body.reason),
        verdict_note=body.note,
        actor=user.username,
        db=db,
    )
    return outcome("recorded", f"Also recorded on incident alert #{incident_id}.", updated.verdict), updated, previous
