"""When a customer's question to the SOC (#1305) counts as answered.

Kept apart from ``soc_requests.py``, which calls the incidents routes: the incidents comment
routes call ``mark_answered_by_comment`` here, and must not import a module that imports them.

A question is answered by the SOC's first comment on its target after it was asked: a SOC
user's comment on the case (or the alert) the question is filed on. A portal user's comment,
the question's own included, never answers anything. An analyst can also mark one answered by
hand (a reply by phone): ``soc_requests.mark_answered``.
"""

from typing import Any

from loguru import logger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import SOC_ROLES
from app.auth.models.users import RoleEnum
from app.db.universal_models import CustomerPortalSocRequest
from app.time_utils import now_utc

OPEN = "open"
ANSWERED = "answered"
VIA_COMMENT = "comment"
VIA_MANUAL = "manual"


def is_soc_user(user: Any) -> bool:
    role = getattr(getattr(user, "role_id", None), "value", getattr(user, "role_id", None))
    try:
        return RoleEnum(role) in SOC_ROLES
    except ValueError:
        return False


async def mark_answered_by_comment(entity_type: str, entity_id: int, user: Any, session: AsyncSession) -> int:
    """Mark the open questions filed on this alert or case answered, when a SOC user commented.

    Returns how many moved. Best-effort: a failure is logged and rolled back, never raised, so
    the comment the SOC just wrote is never refused because of it.
    """
    if not is_soc_user(user):
        return 0
    column = CustomerPortalSocRequest.case_id if entity_type == "case" else CustomerPortalSocRequest.alert_id
    try:
        result = await session.execute(
            update(CustomerPortalSocRequest)
            .where(column == entity_id, CustomerPortalSocRequest.status == OPEN)
            .values(status=ANSWERED, answered_at=now_utc().replace(tzinfo=None), answered_by=user.username, answered_via=VIA_COMMENT),
        )
        await session.commit()
    except Exception as e:  # noqa: BLE001 - the comment went through; the question's state is a courtesy
        logger.warning(f"Could not mark the customer questions on {entity_type} {entity_id} answered: {e}")
        await session.rollback()
        return 0
    moved = result.rowcount or 0
    if moved:
        logger.info(f"{user.username} answered {moved} customer question(s) on {entity_type} {entity_id}")
    return moved
