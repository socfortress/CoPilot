"""A customer answering an item the SOC is waiting on hands it back to the SOC (#1187).

``PENDING_CUSTOMER`` stops an item's SLA clocks until the customer replies. The reply is
a comment from a portal user, and leaving the item waiting after it would keep the
clocks stopped on work that is now the SOC's again — so the comment itself moves the
item back to ``IN_PROGRESS``, which resumes the clocks. A case takes back the alerts that
were waiting with it (``status_cascade``).

Only a ``customer_user`` reply resumes: an analyst's note on a waiting item ("chased the
customer by phone") must not restart the clock.

The other direction is closed: a customer cannot *set* ``PENDING_CUSTOMER``. It is the SOC
asking the customer for something, and a customer choosing it would only stop the SOC's
clock on their own item (``ensure_customer_may_set_status``).
"""

from typing import Any
from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.incidents.models import Alert
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.schema.db_operations import AlertStatus
from app.incidents.schema.db_operations import UpdateAlertStatus
from app.incidents.schema.db_operations import UpdateCaseStatus
from app.incidents.services.db_operations import update_alert_status
from app.incidents.services.db_operations import update_case_status
from app.incidents.services.status_cascade import cascade_for
from app.soc_management.domain.lifecycle import Actor
from app.soc_management.domain.lifecycle import LifecycleAction
from app.soc_management.services.lifecycle import SlaLifecycleRecorder

RESUMED = AlertStatus.IN_PROGRESS


def is_customer_reply(user: Any) -> bool:
    role = getattr(user.role_id, "value", user.role_id)
    return role == RoleEnum.customer_user.value


#: Why a portal user is refused PENDING_CUSTOMER — phrased for the person who tried.
CUSTOMER_CANNOT_WAIT = "Only the SOC can set an item to Waiting on customer; reply with a comment to hand it back to the SOC"


def ensure_customer_may_set_status(user: Any, status: Any) -> None:
    """403 when a ``customer_user`` tries to put an alert or case on hold for themselves."""
    value = getattr(status, "value", status)
    if value == AlertStatus.PENDING_CUSTOMER.value and is_customer_reply(user):
        raise HTTPException(status_code=403, detail=CUSTOMER_CANNOT_WAIT)


async def resume_alert_on_reply(alert_id: int, user: Any, db: AsyncSession) -> bool:
    """Move a waiting alert back to the SOC after its customer replied. True if it moved."""
    if not is_customer_reply(user):
        return False
    status = (await db.execute(select(Alert.status).where(Alert.id == alert_id))).scalar_one_or_none()
    if status != AlertStatus.PENDING_CUSTOMER.value:
        return False
    await update_alert_status(UpdateAlertStatus(alert_id=alert_id, status=RESUMED), db)
    await SlaLifecycleRecorder().alert_action(alert_id, LifecycleAction.STATUS_CHANGED, Actor.from_user(user), to_status=RESUMED.value)
    logger.info(f"Alert {alert_id} resumed: {user.username} replied while it waited on the customer")
    return True


async def resume_case_on_reply(case_id: int, user: Any, db: AsyncSession) -> bool:
    """Move a waiting case (and the alerts waiting with it) back to the SOC. True if it moved."""
    if not is_customer_reply(user):
        return False
    status = (await db.execute(select(Case.case_status).where(Case.id == case_id))).scalar_one_or_none()
    if status != AlertStatus.PENDING_CUSTOMER.value:
        return False
    cascade = cascade_for(status, RESUMED.value)
    linked = (
        await db.execute(
            select(CaseAlertLink.alert_id, Alert.status)
            .join(Alert, Alert.id == CaseAlertLink.alert_id)
            .where(CaseAlertLink.case_id == case_id),
        )
    ).all()
    alert_ids: List[int] = [alert_id for alert_id, alert_status in linked if cascade and cascade.applies_to(alert_status)]
    for alert_id in alert_ids:
        await update_alert_status(UpdateAlertStatus(alert_id=alert_id, status=RESUMED), db)
    await update_case_status(UpdateCaseStatus(case_id=case_id, status=RESUMED), db)

    actor = Actor.from_user(user)
    recorder = SlaLifecycleRecorder()
    await recorder.case_action(case_id, LifecycleAction.STATUS_CHANGED, actor, to_status=RESUMED.value)
    await recorder.alerts_action(alert_ids, LifecycleAction.STATUS_CHANGED, actor, to_status=RESUMED.value)

    from app.incidents.schema.case_templates import CaseEventType
    from app.incidents.services.case_events import emit_case_event
    from app.incidents.services.case_events import payload_status_change

    await emit_case_event(
        session=db,
        case_id=case_id,
        event_type=CaseEventType.CASE_STATUS_CHANGED,
        actor=user.username,
        payload=payload_status_change(from_status=status, to_status=RESUMED.value, forced=False),
        commit=True,
    )
    logger.info(f"Case {case_id} resumed with {len(alert_ids)} alert(s): {user.username} replied while it waited on the customer")
    return True
