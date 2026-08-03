"""Sending a specific alert or case to a channel on demand.

Every other notification in this system is *triggered* — something happened and
routes matching it fire. This one is *chosen*: an analyst decides to push a
particular alert somewhere, bypassing the trigger and severity filters that
govern everything else.

That makes it a **data egress control point**, not a convenience feature, and
the guardrails below are the substance of the module rather than boilerplate:

**Configured routes only.** There is deliberately no free-text destination. A
route is admin-managed and carries validated config; a "send to this address"
box would turn the button into an arbitrary exfiltration tool.

**Admin for customer-facing targets.** Sending out to an end customer skips the
filters by definition, so it gets a second pair of eyes. Internal sharing stays
open to analysts.

**Server-side re-validation of everything.** The route picker filters to the
entity's own customer plus internal routes, but nothing here trusts that — the
cross-tenant pairing the UI would never offer is exactly the one worth checking.

**Object-level authorization.** Without it, manual send is a read primitive:
sending an alert to a channel you can read is a way to see alerts the tag rules
deny you.

**The AI opt-out still applies.** Otherwise this is the hole in the control
established by #1014 — an analyst hand-delivering AI findings to a customer who
declined them.
"""

from __future__ import annotations

from typing import Any
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.customer_portal.services.ai_reports import is_ai_reports_enabled
from app.db.universal_models import CustomerNotificationRoute
from app.incidents.models import Alert
from app.incidents.models import Case
from app.incidents.services.alert_severity import severity_of
from app.notifications.channels.base import RenderedMessage
from app.notifications.schema.events import EntityType
from app.notifications.schema.events import NotificationEvent
from app.notifications.schema.notifications import DispatchOutcome
from app.notifications.schema.notifications import DispatchStatus
from app.notifications.schema.notifications import NotificationScope
from app.notifications.schema.notifications import NotificationSeverity
from app.notifications.schema.notifications import NotificationTrigger

SUPPORTED_ENTITY_TYPES = (EntityType.ALERT, EntityType.CASE)


async def _load_entity(entity_type: str, entity_id: int, session: AsyncSession) -> Optional[Any]:
    """Fetch the alert or case being sent."""
    model = {EntityType.ALERT: Alert, EntityType.CASE: Case}.get(entity_type)
    if model is None:
        raise HTTPException(status_code=400, detail=f"Cannot send a '{entity_type}'; expected one of {SUPPORTED_ENTITY_TYPES}.")
    result = await session.execute(select(model).where(model.id == entity_id))
    return result.scalars().first()


async def _load_route(route_id: int, session: AsyncSession) -> Optional[CustomerNotificationRoute]:
    result = await session.execute(select(CustomerNotificationRoute).where(CustomerNotificationRoute.id == route_id))
    return result.scalars().first()


def build_manual_event(*, entity_type: str, entity_id: int, entity: Any, user: Any) -> NotificationEvent:
    """The envelope for one manual send.

    **The dedupe key carries a uuid, which is a deliberate exception to the
    engine's core idempotency rule.** Every other trigger dedupes so a repeat is
    a no-op; manual send must be repeatable, because clicking "send" twice on
    purpose has to send twice. Each click therefore becomes its own dispatch-log
    row — which is what an audit trail wants anyway.

    Do not "fix" this to match the other triggers. Repeat sends would break
    silently, and `test_every_manual_send_gets_a_unique_dedupe_key` exists to
    catch that.
    """
    is_alert = entity_type == EntityType.ALERT
    title = getattr(entity, "alert_name", None) if is_alert else getattr(entity, "case_name", None)
    label = title or f"{entity_type} #{entity_id}"

    # An alert carries a real severity (#1040); a case has none of its own, so a
    # manual case send is Informational rather than an invented value.
    severity = NotificationSeverity(severity_of(entity)) if is_alert else NotificationSeverity.INFORMATIONAL

    return NotificationEvent(
        customer_code=getattr(entity, "customer_code", None),
        # Reuses the entity's natural trigger for body rendering; the fact that
        # this was hand-sent is recorded on the log row, not in the trigger.
        trigger=NotificationTrigger.ALERT_CREATED if is_alert else NotificationTrigger.CASE_ASSIGNED,
        severity=severity,
        subject=label,
        summary=f"{label} was sent to this channel by {getattr(user, 'username', 'unknown')}.",
        entity_type=entity_type,
        entity_id=entity_id,
        dedupe_key=f"{entity_type}:{entity_id}:manual:{uuid4()}",
        actor_username=getattr(user, "username", None),
        context={"alert_name": title, "title": title, "manual": True},
    )


def _require_send_permission(user: Any, route: CustomerNotificationRoute) -> None:
    """Who may send, and where.

    Customer-facing sends are admin-only: they push data to an end customer
    outside the filters that normally govern it. Internal routes stay open to
    analysts so routine sharing isn't gated behind an escalation.
    """
    role_id = getattr(user, "role_id", None)

    if role_id == RoleEnum.customer_user.value:
        raise HTTPException(status_code=403, detail="Portal users cannot send notifications.")

    if role_id not in (RoleEnum.admin.value, RoleEnum.analyst.value):
        raise HTTPException(status_code=403, detail="You do not have permission to send notifications.")

    if route.scope == NotificationScope.CUSTOMER.value and role_id != RoleEnum.admin.value:
        raise HTTPException(
            status_code=403,
            detail=("Sending to a customer-facing route requires admin. " "An internal route is available for sharing within the SOC."),
        )


def _require_route_matches_entity(route: CustomerNotificationRoute, entity: Any) -> None:
    """Re-validate the submitted route against the entity's tenant.

    The picker only offers the entity's own customer plus internal routes, but
    the route_id arrives from the client. This is the check the UI can't be
    trusted to have made.
    """
    if route.scope == NotificationScope.INTERNAL.value:
        # Belongs to no tenant, so there is nothing to match against.
        return

    entity_customer = getattr(entity, "customer_code", None)
    if route.customer_code != entity_customer:
        raise HTTPException(
            status_code=400,
            detail=(
                f"That route belongs to customer {route.customer_code!r}, but this item belongs to "
                f"{entity_customer!r}. A customer-facing route can only receive its own customer's data."
            ),
        )


async def _require_object_access(entity_type: str, entity: Any, user: Any, session: AsyncSession) -> None:
    """The caller must be able to *see* the item before sending it anywhere.

    Without this the button is a read primitive — sending an alert to a channel
    you can read reveals alerts the tag rules deny you.
    """
    from app.incidents.middleware.tag_access import tag_access_handler
    from app.middleware.customer_access import customer_access_handler

    customer_code = getattr(entity, "customer_code", None)
    if customer_code and not await customer_access_handler.check_customer_access(user, customer_code, session):
        raise HTTPException(status_code=403, detail="Access denied — insufficient customer permissions for this item.")

    if entity_type == EntityType.ALERT:
        if not await tag_access_handler.can_user_access_alert(user, entity.id, session):
            raise HTTPException(status_code=403, detail="Access denied — this alert is outside your tag access.")


async def _require_ai_report_permitted(
    route: CustomerNotificationRoute,
    entity: Any,
    include_ai_report: bool,
    session: AsyncSession,
) -> None:
    """The #1014 opt-out applies to hand-delivered AI content too.

    Only customer-facing sends are gated. Keeping AI findings internal while
    still running investigations is a supported configuration.
    """
    if not include_ai_report or route.scope != NotificationScope.CUSTOMER.value:
        return

    customer_code = getattr(entity, "customer_code", None)
    if not await is_ai_reports_enabled(customer_code, session):
        raise HTTPException(
            status_code=400,
            detail=(
                "AI reports are not enabled for this customer, so the AI report cannot be included. "
                "Send without it, or enable AI reports for the customer first."
            ),
        )


async def _deliver(route: CustomerNotificationRoute, event: NotificationEvent, session: AsyncSession):
    """Hand off to the channel provider and record the outcome.

    Split out so the authorization path above can be tested without stubbing the
    whole dispatch stack.
    """
    from app.notifications.services.notifications import deliver_one

    return await deliver_one(route, event, session, trigger_source="manual")


async def preview_manual(
    *,
    entity_type: str,
    entity_id: int,
    route_id: int,
    user: Any,
    session: AsyncSession,
    include_ai_report: bool = False,
) -> RenderedMessage:
    """Render what a send would deliver, without delivering it.

    Runs the **same authorization** as `send_manual`. A preview that skipped the
    checks would be a read primitive of its own — showing an alert's contents to
    someone who may not see the alert — which is precisely the hole the object
    access check exists to close.

    Renders against the real item rather than a sample event: the operator is
    about to push this specific data outward and should see exactly what leaves.
    """
    from app.notifications.services.notifications import _render_body

    entity = await _load_entity(entity_type, entity_id, session)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"{entity_type} {entity_id} not found")

    route = await _load_route(route_id, session)
    if route is None:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")

    _require_send_permission(user, route)
    _require_route_matches_entity(route, entity)
    await _require_object_access(entity_type, entity, user, session)
    await _require_ai_report_permitted(route, entity, include_ai_report, session)

    event = build_manual_event(entity_type=entity_type, entity_id=entity_id, entity=entity, user=user)
    message, _template_error = await _render_body(route, event, session)
    # The whole message, not just the body: a named template can carry a
    # subject, and a preview that hid it would misrepresent what an email
    # recipient actually sees.
    return message


async def send_manual(
    *,
    entity_type: str,
    entity_id: int,
    route_id: int,
    user: Any,
    session: AsyncSession,
    include_ai_report: bool = False,
) -> DispatchOutcome:
    """Send one alert or case to one route, now.

    Order matters: every check runs before anything leaves the process, and each
    failure is an HTTPException the caller surfaces rather than a logged
    dispatch — a refused send is a permissions answer, not a delivery outcome.
    """
    entity = await _load_entity(entity_type, entity_id, session)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"{entity_type} {entity_id} not found")

    route = await _load_route(route_id, session)
    if route is None:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")

    _require_send_permission(user, route)
    _require_route_matches_entity(route, entity)
    await _require_object_access(entity_type, entity, user, session)
    await _require_ai_report_permitted(route, entity, include_ai_report, session)

    event = build_manual_event(entity_type=entity_type, entity_id=entity_id, entity=entity, user=user)
    logger.info(
        f"Manual send: {entity_type}#{entity_id} -> route {route.id} ({route.channel}, {route.scope}) "
        f"by {getattr(user, 'username', 'unknown')}",
    )

    result = await _deliver(route, event, session)
    return DispatchOutcome(
        route_id=route.id,
        route_name=route.name,
        channel=route.channel,
        status=DispatchStatus(result.status),
        error_message=result.error_message,
        latency_ms=result.latency_ms,
        provider_reference=result.provider_reference,
    )
