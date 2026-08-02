"""
Notification routing service — CRUD for routes, the dispatch loop, and
a read-only view over the dispatch log.

The dispatch loop is the heart of the module. It's called via
`POST /notifications/dispatch` (Talon's after-investigation hook) and
walks every enabled route for the customer, filters by trigger and
severity, formats the message body per channel, calls the appropriate
dispatcher, and records the outcome in `notification_dispatch_log`. The
log row is what gives us idempotency — re-dispatching the same
(route, dedupe_key) pair is a no-op. The key travels on the event, so
each trigger decides its own dedupe semantics.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import List
from typing import Optional
from typing import Tuple
from uuid import uuid4

from fastapi import HTTPException
from loguru import logger
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.customer_portal.services.ai_reports import is_ai_reports_enabled
from app.db.universal_models import CustomerNotificationRoute
from app.db.universal_models import CustomerShuffleIntegration
from app.db.universal_models import NotificationDispatchLog
from app.notifications.channels import DispatchContext
from app.notifications.channels import SendResult
from app.notifications.channels import get_channel
from app.notifications.channels.shuffle import get_shuffle_connector
from app.notifications.schema.events import EntityType
from app.notifications.schema.events import NotificationEvent
from app.notifications.schema.events import event_from_dispatch_request
from app.notifications.schema.notifications import AI_SOURCED_TRIGGERS
from app.notifications.schema.notifications import INTERNAL_TRIGGERS
from app.notifications.schema.notifications import SEVERITY_ORDER
from app.notifications.schema.notifications import DispatchOutcome
from app.notifications.schema.notifications import DispatchRequest
from app.notifications.schema.notifications import DispatchResponse
from app.notifications.schema.notifications import DispatchStatus
from app.notifications.schema.notifications import NotificationChannel
from app.notifications.schema.notifications import NotificationRouteCreate
from app.notifications.schema.notifications import NotificationRouteUpdate
from app.notifications.schema.notifications import NotificationScope
from app.notifications.schema.notifications import NotificationSeverity
from app.notifications.schema.notifications import NotificationTrigger
from app.notifications.schema.notifications import ShuffleApp
from app.notifications.schema.notifications import ShuffleIntegrationCreate
from app.notifications.schema.notifications import ShuffleIntegrationUpdate
from app.notifications.schema.notifications import ShuffleOrg
from app.notifications.services.dispatchers import (
    list_shuffle_apps as shuffle_apps_client,
)
from app.notifications.services.dispatchers import (
    list_shuffle_orgs as shuffle_orgs_client,
)
from app.notifications.services.dispatchers import (
    verify_shuffle_org as verify_shuffle_org_client,
)
from app.notifications.services.rendering import render_body

# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def list_routes(customer_code: str, session: AsyncSession) -> List[CustomerNotificationRoute]:
    """All routes for a customer, newest-first. UI list source."""
    result = await session.execute(
        select(CustomerNotificationRoute)
        .where(CustomerNotificationRoute.customer_code == customer_code)
        .order_by(desc(CustomerNotificationRoute.created_at)),
    )
    return result.scalars().all()


async def get_route(route_id: int, customer_code: str, session: AsyncSession) -> CustomerNotificationRoute:
    """Single route, scoped by customer to keep the tenant boundary
    explicit at lookup time."""
    result = await session.execute(
        select(CustomerNotificationRoute).where(
            CustomerNotificationRoute.id == route_id,
            CustomerNotificationRoute.customer_code == customer_code,
        ),
    )
    route = result.scalars().first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


def _enforce_scope_invariant(scope: str, customer_code: Optional[str]) -> Optional[str]:
    """A customer route must name a tenant; an internal route must not.

    Returning the coerced code keeps the two callers from drifting. Raising a
    400 rather than silently fixing it: a client sending scope='internal' with a
    customer_code has a bug worth surfacing.
    """
    if scope == NotificationScope.INTERNAL.value:
        if customer_code:
            raise HTTPException(status_code=400, detail="An internal-scope route must not name a customer.")
        return None
    if not customer_code:
        raise HTTPException(status_code=400, detail="A customer-scope route requires a customer_code.")
    return customer_code


async def list_internal_routes(session: AsyncSession) -> List[CustomerNotificationRoute]:
    """Every internal-scope route. Deployment-wide — they belong to no tenant."""
    result = await session.execute(
        select(CustomerNotificationRoute)
        .where(CustomerNotificationRoute.scope == NotificationScope.INTERNAL.value)
        .order_by(desc(CustomerNotificationRoute.created_at)),
    )
    return result.scalars().all()


async def get_internal_route(route_id: int, session: AsyncSession) -> CustomerNotificationRoute:
    """Single internal route. Scoped in the query rather than trusting the id,
    so a customer route's id can't be reached through the internal endpoints."""
    result = await session.execute(
        select(CustomerNotificationRoute).where(
            CustomerNotificationRoute.id == route_id,
            CustomerNotificationRoute.scope == NotificationScope.INTERNAL.value,
        ),
    )
    route = result.scalars().first()
    if not route:
        raise HTTPException(status_code=404, detail="Internal route not found")
    return route


def _reject_shuffle_for_internal(payload_channel: Optional[str]) -> None:
    """Shuffle is unavailable to internal routes.

    `shuffle_integration_id` is an FK to `customer_shuffle_integration`, which is
    per-customer — a route belonging to no tenant has no integration to point
    at. Caught here rather than at dispatch, where it would surface as a
    confusing "integration is missing" failure.
    """
    if payload_channel == NotificationChannel.SHUFFLE.value:
        raise HTTPException(
            status_code=400,
            detail=(
                "Shuffle is not available for internal routes: a Shuffle integration belongs to a "
                "specific customer, and an internal route belongs to none. Use webhook or email."
            ),
        )


async def create_internal_route(
    payload: NotificationRouteCreate,
    created_by: Optional[str],
    session: AsyncSession,
) -> CustomerNotificationRoute:
    """Create a route that belongs to no tenant.

    Forces scope='internal' rather than trusting the payload — these endpoints
    are the internal surface by definition, and honouring a 'customer' scope
    here would create a route with no customer_code that the customer-scoped
    dispatch path could never find.
    """
    _reject_shuffle_for_internal(payload.channel.value)
    if payload.scope != NotificationScope.INTERNAL:
        raise HTTPException(status_code=400, detail="This endpoint creates internal-scope routes only.")

    route = CustomerNotificationRoute(
        customer_code=None,
        scope=NotificationScope.INTERNAL.value,
        recipient_mode=payload.recipient_mode.value,
        notify_on_self_assign=payload.notify_on_self_assign,
        name=payload.name,
        trigger=payload.trigger.value,
        channel=payload.channel.value,
        destination=payload.destination or "",
        min_severity=payload.min_severity.value,
        format_template=payload.format_template,
        enabled=payload.enabled,
        created_by=created_by,
        shuffle_integration_id=None,
        config=json.dumps(payload.config or {}),
    )
    session.add(route)
    await session.commit()
    await session.refresh(route)
    return route


async def update_internal_route(
    route_id: int,
    payload: NotificationRouteUpdate,
    session: AsyncSession,
) -> CustomerNotificationRoute:
    route = await get_internal_route(route_id, session)
    data = payload.model_dump(exclude_unset=True)

    new_channel = data.get("channel")
    new_channel_value = new_channel.value if hasattr(new_channel, "value") else (new_channel or route.channel)
    _reject_shuffle_for_internal(new_channel_value)

    # Scope and customer_code are fixed for these routes; silently ignoring an
    # attempt to change them would let a PATCH strand the route in a scope its
    # dispatch path can't reach.
    if "scope" in data and data["scope"] != NotificationScope.INTERNAL:
        raise HTTPException(status_code=400, detail="An internal route's scope cannot be changed.")
    data.pop("scope", None)

    if "config" in data or "channel" in data or "recipient_mode" in data:
        provider = get_channel(new_channel_value)
        if provider is None:
            raise HTTPException(status_code=400, detail=f"Unsupported channel: {new_channel_value}")
        raw_config = data.get("config")
        if raw_config is None and "config" not in data:
            raw_config = json.loads(route.config) if route.config else {}
        try:
            data["config"] = provider.config_schema.model_validate(raw_config or {}).model_dump()
        except PydanticValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid config for channel '{new_channel_value}': {e}") from e

        mode = data.get("recipient_mode")
        mode_value = mode.value if hasattr(mode, "value") else (mode or route.recipient_mode)
        if mode_value not in provider.supports_recipient_modes:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Channel '{new_channel_value}' does not support recipient_mode '{mode_value}' "
                    f"(supported: {sorted(provider.supports_recipient_modes)})"
                ),
            )

    for field, value in data.items():
        if hasattr(value, "value"):
            value = value.value
        if field == "config":
            value = json.dumps(value or {})
        if field == "destination" and value is None:
            value = ""
        setattr(route, field, value)
    route.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(route)
    return route


async def delete_internal_route(route_id: int, session: AsyncSession) -> None:
    route = await get_internal_route(route_id, session)
    await session.delete(route)
    await session.commit()


async def create_route(
    customer_code: str,
    payload: NotificationRouteCreate,
    created_by: Optional[str],
    session: AsyncSession,
) -> CustomerNotificationRoute:
    # Shuffle-channel sanity check: the integration must exist AND
    # belong to the same customer. Pydantic validators caught the "is
    # the field present" question; this catches the cross-tenant version.
    if payload.channel == NotificationChannel.SHUFFLE:
        await _ensure_integration_belongs_to_customer(payload.shuffle_integration_id, customer_code, session)

    resolved_code = _enforce_scope_invariant(payload.scope.value, customer_code)

    route = CustomerNotificationRoute(
        customer_code=resolved_code,
        scope=payload.scope.value,
        recipient_mode=payload.recipient_mode.value,
        notify_on_self_assign=payload.notify_on_self_assign,
        name=payload.name,
        trigger=payload.trigger.value,
        channel=payload.channel.value,
        # `destination` is non-null in the DB; webhook routes may omit it,
        # so coalesce to empty string rather than NULL.
        destination=payload.destination or "",
        min_severity=payload.min_severity.value,
        format_template=payload.format_template,
        enabled=payload.enabled,
        created_by=created_by,
        shuffle_integration_id=payload.shuffle_integration_id,
        config=json.dumps(payload.config or {}),
    )
    session.add(route)
    await session.commit()
    await session.refresh(route)
    return route


async def update_route(
    route_id: int,
    customer_code: str,
    payload: NotificationRouteUpdate,
    session: AsyncSession,
) -> CustomerNotificationRoute:
    route = await get_route(route_id, customer_code, session)

    # Pydantic v1 vs v2 parity — exclude_unset returns only the fields
    # the client actually sent so a PATCH that omits `enabled` doesn't
    # accidentally re-flag it.
    data = payload.model_dump(exclude_unset=True)

    # If the PATCH switches the channel to Shuffle (or re-points an
    # existing Shuffle route at a different integration), the new
    # integration must belong to the same customer.
    new_integration_id = data.get("shuffle_integration_id", route.shuffle_integration_id)
    new_channel = data.get("channel")
    if hasattr(new_channel, "value"):
        new_channel_value = new_channel.value
    else:
        new_channel_value = new_channel or route.channel
    if new_channel_value == NotificationChannel.SHUFFLE.value and new_integration_id:
        await _ensure_integration_belongs_to_customer(new_integration_id, customer_code, session)

    # `config` is validated against the channel the route will HAVE after this
    # PATCH — which may be the row's current channel when the PATCH doesn't
    # change it. NotificationRouteUpdate can't do this itself: it has no view of
    # the stored row.
    if "config" in data or "channel" in data or "recipient_mode" in data:
        provider = get_channel(new_channel_value)
        if provider is None:
            raise HTTPException(status_code=400, detail=f"Unsupported channel: {new_channel_value}")
        raw_config = data.get("config")
        if raw_config is None and "config" not in data:
            # Channel changed but config didn't — re-validate what's stored, so
            # switching to a channel the existing config can't satisfy is caught
            # here rather than at dispatch time.
            raw_config = json.loads(route.config) if route.config else {}
        try:
            data["config"] = provider.config_schema.model_validate(raw_config or {}).model_dump()
        except PydanticValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid config for channel '{new_channel_value}': {e}") from e

        mode = data.get("recipient_mode")
        mode_value = mode.value if hasattr(mode, "value") else (mode or route.recipient_mode)
        if mode_value not in provider.supports_recipient_modes:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Channel '{new_channel_value}' does not support recipient_mode '{mode_value}' "
                    f"(supported: {sorted(provider.supports_recipient_modes)})"
                ),
            )

    # Scope and customer_code have to move together.
    new_scope = data.get("scope")
    new_scope_value = new_scope.value if hasattr(new_scope, "value") else (new_scope or route.scope)
    if "scope" in data:
        data["customer_code"] = _enforce_scope_invariant(
            new_scope_value,
            None if new_scope_value == NotificationScope.INTERNAL.value else (route.customer_code or customer_code),
        )

    for field, value in data.items():
        # Enums: write the underlying string into the DB column.
        if hasattr(value, "value"):
            value = value.value
        # config is a dict in the schema but a JSON-string column in the DB.
        if field == "config":
            value = json.dumps(value or {})
        # destination is NOT NULL in the DB; a webhook PATCH legitimately
        # sends it as null (webhooks don't use it) — coalesce to "".
        if field == "destination" and value is None:
            value = ""
        setattr(route, field, value)

    route.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(route)
    return route


async def delete_route(route_id: int, customer_code: str, session: AsyncSession) -> None:
    route = await get_route(route_id, customer_code, session)
    await session.delete(route)
    await session.commit()


# ---------------------------------------------------------------------------
# Shuffle integrations (Phase 2)
# ---------------------------------------------------------------------------


async def _ensure_integration_belongs_to_customer(
    integration_id: int,
    customer_code: str,
    session: AsyncSession,
) -> CustomerShuffleIntegration:
    """Tenant-boundary check for Shuffle integration references.

    Used at route create/update time. Without this, a malicious or
    typo'd `shuffle_integration_id` could silently route customer A's
    notifications through customer B's Shuffle org. Failing closed with
    a 400 is the right answer — the route never persists.
    """
    result = await session.execute(
        select(CustomerShuffleIntegration).where(
            CustomerShuffleIntegration.id == integration_id,
            CustomerShuffleIntegration.customer_code == customer_code,
        ),
    )
    integration = result.scalars().first()
    if not integration:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Shuffle integration {integration_id} not found for "
                f"customer {customer_code}. Cross-tenant references are "
                f"refused — create the integration on the target customer first."
            ),
        )
    return integration


async def list_shuffle_integrations(customer_code: str, session: AsyncSession) -> List[CustomerShuffleIntegration]:
    result = await session.execute(
        select(CustomerShuffleIntegration)
        .where(CustomerShuffleIntegration.customer_code == customer_code)
        .order_by(desc(CustomerShuffleIntegration.created_at)),
    )
    return result.scalars().all()


async def get_shuffle_integration(integration_id: int, customer_code: str, session: AsyncSession) -> CustomerShuffleIntegration:
    return await _ensure_integration_belongs_to_customer(integration_id, customer_code, session)


async def create_shuffle_integration(
    customer_code: str,
    payload: ShuffleIntegrationCreate,
    created_by: Optional[str],
    session: AsyncSession,
) -> CustomerShuffleIntegration:
    integration = CustomerShuffleIntegration(
        customer_code=customer_code,
        display_name=payload.display_name,
        shuffle_org_id=payload.shuffle_org_id,
        enabled=payload.enabled,
        created_by=created_by,
    )
    session.add(integration)
    await session.commit()
    await session.refresh(integration)
    return integration


async def update_shuffle_integration(
    integration_id: int,
    customer_code: str,
    payload: ShuffleIntegrationUpdate,
    session: AsyncSession,
) -> CustomerShuffleIntegration:
    integration = await _ensure_integration_belongs_to_customer(integration_id, customer_code, session)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(integration, field, value)
    integration.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(integration)
    return integration


async def delete_shuffle_integration(integration_id: int, customer_code: str, session: AsyncSession) -> None:
    integration = await _ensure_integration_belongs_to_customer(integration_id, customer_code, session)
    # Refuse if any routes still reference this integration — better to
    # surface the dependency than silently leave routes pointing at a
    # missing FK that the dispatch loop will then have to skip.
    result = await session.execute(
        select(CustomerNotificationRoute).where(CustomerNotificationRoute.shuffle_integration_id == integration_id),
    )
    referencing = result.scalars().all()
    if referencing:
        names = ", ".join(r.name for r in referencing[:5])
        raise HTTPException(
            status_code=409,
            detail=(
                f"Integration is referenced by {len(referencing)} route(s) "
                f"({names}{'…' if len(referencing) > 5 else ''}). Delete "
                f"or re-point those routes first."
            ),
        )
    await session.delete(integration)
    await session.commit()


async def list_apps_for_integration(
    integration_id: int,
    customer_code: str,
    session: AsyncSession,
) -> List[ShuffleApp]:
    """Fetch the Shuffle app catalog scoped to this customer's org.

    Used by the route form's app picker. Roundtrip is short (Shuffle
    returns the catalog quickly) and the result is small, so we don't
    cache — fresh data on every form open is fine for v1.
    """
    integration = await _ensure_integration_belongs_to_customer(integration_id, customer_code, session)
    base_url, api_key = await get_shuffle_connector(session)
    ok, apps_raw, error = await shuffle_apps_client(
        base_url=base_url,
        api_key=api_key,
        org_id=integration.shuffle_org_id,
    )
    if not ok:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch apps from Shuffle: {error}",
        )
    # Forward only the fields the UI needs; ignore extra metadata that
    # Shuffle returns (versioning, ownership info, internal ids).
    apps: List[ShuffleApp] = []
    for raw in apps_raw:
        if not isinstance(raw, dict):
            continue
        if not raw.get("id") or not raw.get("name"):
            continue
        apps.append(
            ShuffleApp(
                id=str(raw.get("id")),
                name=str(raw.get("name")),
                description=raw.get("description"),
                large_image=raw.get("large_image"),
            ),
        )
    return apps


async def verify_integration(integration_id: int, customer_code: str, session: AsyncSession) -> dict:
    integration = await _ensure_integration_belongs_to_customer(integration_id, customer_code, session)
    base_url, api_key = await get_shuffle_connector(session)
    ok, app_count, error = await verify_shuffle_org_client(
        base_url=base_url,
        api_key=api_key,
        org_id=integration.shuffle_org_id,
    )
    return {
        "success": ok,
        "message": "Shuffle integration reachable" if ok else "Shuffle integration check failed",
        "org_id": integration.shuffle_org_id,
        "app_count": app_count,
        "error": error,
    }


async def list_orgs(session: AsyncSession) -> List[ShuffleOrg]:
    """List every Shuffle org the deployment's admin Bearer can see.

    Used by the integration form's org-picker dropdown so admins pick
    a real org instead of pasting a UUID. Not customer-scoped — the
    caller's auth gate (admin/analyst scope) is the only access check;
    each org is then attached to a specific customer via the
    integration row at create time.
    """
    base_url, api_key = await get_shuffle_connector(session)
    ok, orgs_raw, error = await shuffle_orgs_client(base_url=base_url, api_key=api_key)
    if not ok:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch orgs from Shuffle: {error}",
        )
    # Forward only the fields the UI needs. Shuffle's full org payload
    # carries internal billing/users/region state we don't want leaking
    # through.
    orgs: List[ShuffleOrg] = []
    for raw in orgs_raw:
        if not isinstance(raw, dict):
            continue
        if not raw.get("id") or not raw.get("name"):
            continue
        # `creator_org` is set on sub-orgs to the parent's UUID and
        # empty/None on top-level orgs. We forward it as-is so the UI
        # can render a "(sub-org)" hint without re-querying.
        creator_org = raw.get("creator_org")
        if creator_org in ("", "PARENT_ORG_ID"):  # ignore placeholder fixtures
            creator_org = None
        orgs.append(
            ShuffleOrg(
                id=str(raw.get("id")),
                name=str(raw.get("name")),
                description=raw.get("description") or None,
                role=raw.get("role") or None,
                creator_org=creator_org,
            ),
        )
    return orgs


# ---------------------------------------------------------------------------
# Dispatch log (read-only)
# ---------------------------------------------------------------------------


async def list_dispatch_log(
    customer_code: str,
    session: AsyncSession,
    limit: int = 100,
) -> List[NotificationDispatchLog]:
    """Recent dispatch history for a customer. Defaults to 100 rows
    so the audit-log tab in the UI loads quickly even for noisy
    customers."""
    result = await session.execute(
        select(NotificationDispatchLog)
        .where(NotificationDispatchLog.customer_code == customer_code)
        .order_by(desc(NotificationDispatchLog.dispatched_at))
        .limit(limit),
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Dispatch — the core loop Talon invokes
# ---------------------------------------------------------------------------


def _severity_meets(report_severity: str, route_min: str) -> bool:
    """Inclusive severity comparison.

    A route with `min_severity="High"` fires when the report is High or
    Critical. SEVERITY_ORDER is sorted ascending — a higher index = more
    severe.
    """
    try:
        return SEVERITY_ORDER.index(report_severity) >= SEVERITY_ORDER.index(route_min)
    except ValueError:
        # Unknown severity string — fail closed. Better to drop a
        # notification than fire it on bad input.
        logger.warning(
            f"Unknown severity in routing comparison " f"(report={report_severity!r}, route_min={route_min!r}); " f"skipping route.",
        )
        return False


def _trigger_applies(report_trigger: str, route_trigger: str) -> bool:
    """Decide whether a route's trigger matches the dispatch event type.

    Triggers represent the kind of event that caused the dispatch
    (currently only `investigation_complete`, with more event types
    arriving as we add hooks for analyst review / IOC enrichment /
    scheduled sweeps). Severity filtering lives in `min_severity`,
    not here — this function is purely an event-type equality check.

    Routes with stale `severity_critical_or_high` values from earlier
    schemas are treated as `investigation_complete` so they keep
    firing instead of being silently filtered out.
    """
    if route_trigger == "severity_critical_or_high":
        # Backward compat: legacy enum value, treat as the catch-all
        # event type so existing routes don't go dark on upgrade.
        return report_trigger == NotificationTrigger.INVESTIGATION_COMPLETE.value
    return route_trigger == report_trigger


async def _ai_reports_permitted(trigger: str, customer_code: str, session: AsyncSession) -> bool:
    """Whether AI-written findings may be delivered to this customer.

    `customer_portal_ai_report_settings` is the operator's opt-in switch for
    publishing AI analyst output to an end customer. It is enforced on the
    portal's read paths (`app/customer_portal/services/ai_reports.py`), but a
    notification route is a *second* way the same content reaches the same
    customer — so the same switch has to gate it, or the notification channel
    becomes a way around the opt-out. See issue #1001.

    We call the portal service's own predicate rather than re-querying the
    table, so the two enforcement points cannot drift apart. (This is the
    auth-scope sidestep pattern from CLAUDE.md: scope checks live on the route
    handler, so calling the service function directly is both safe and the
    documented approach.)

    Returns True for non-AI triggers — the switch governs AI-written content,
    not alert-creation or assignment notifications.
    """
    if trigger not in AI_SOURCED_TRIGGERS:
        return True
    return await is_ai_reports_enabled(customer_code, session)


def _format_default_body(event: NotificationEvent) -> str:
    """Default message body when a route sets no `format_template`.

    Markdown-ish: readable as-is in Slack, Teams and a plaintext email. Per-
    trigger wording, because "AI investigation complete" is wrong for an
    assignment and "assigned to" is wrong for an alert landing.

    The investigation_complete branch reproduces the pre-#1006 text exactly —
    it is what existing customers already receive.
    """
    trig = event.trigger.value
    ctx = event.context or {}

    if trig in INTERNAL_TRIGGERS:
        what = {
            "alert_assigned": "Alert",
            "case_assigned": "Case",
            "case_task_assigned": "Task",
        }.get(trig, "Item")
        label = ctx.get("title") or event.subject
        parts = [
            f"*{what} assigned* — {event.assignee_username or 'unassigned'}",
            "",
            f"{what}: #{event.entity_id}" + (f" — {label}" if label else ""),
        ]
        if event.customer_code:
            parts.append(f"Customer: `{event.customer_code}`")
        if event.actor_username:
            parts.append(f"Assigned by: {event.actor_username}")
        if event.summary:
            parts.extend(["", event.summary.strip()])
        if event.link_url:
            parts.extend(["", f"Open in CoPilot: {event.link_url}"])
        return "\n".join(parts)

    if trig == NotificationTrigger.ALERT_CREATED.value:
        parts = [
            f"*New alert* — severity: *{event.severity.value}*",
            "",
            f"Customer: `{event.customer_code}`",
            f"Alert: #{event.entity_id}" + (f" — {event.subject}" if event.subject else ""),
        ]
        if ctx.get("asset_name"):
            parts.append(f"Asset: {ctx['asset_name']}")
        if ctx.get("rule_level") is not None:
            parts.append(f"Rule level: {ctx['rule_level']}")
        if event.summary:
            parts.extend(["", event.summary.strip()])
        if event.link_url:
            parts.extend(["", f"Open in CoPilot: {event.link_url}"])
        return "\n".join(parts)

    # investigation_complete — unchanged wording, existing customers see this.
    alert_name = ctx.get("alert_name")
    parts = [
        f"*AI investigation complete* — severity: *{event.severity.value}*",
        "",
        f"Customer: `{event.customer_code}`",
        f"Alert: #{event.entity_id}" + (f" — {alert_name}" if alert_name else ""),
        "",
        event.summary.strip(),
    ]
    if event.link_url:
        parts.extend(["", f"Full report: {event.link_url}"])
    return "\n".join(parts)


def _render_body(route: CustomerNotificationRoute, event: NotificationEvent) -> Tuple[str, Optional[str]]:
    """Render this route's message body.

    Returns `(body, template_error)`. The error is non-None only when a custom
    template failed and the channel default was sent instead — it is appended to
    the dispatch-log row so a broken template is visible without reproducing it.

    Templates are real Jinja since #1037: conditionals, loops over an alert's
    IOCs, filters. The original token names remain top-level context with
    unchanged meaning, so templates written against the old string-substitution
    renderer keep working.

    One behaviour change worth knowing: an *unknown* token used to survive as a
    literal `{{foo}}` in the output. Under `StrictUndefined` it now raises, and
    the route falls back to the channel default with the reason logged. That is
    louder, and deliberately so — a message with a stray `{{foo}}` in it was
    already broken, just silently.
    """
    fallback = _format_default_body(event)
    return render_body(route.format_template, event, fallback)


async def _record_log(
    session: AsyncSession,
    *,
    event: NotificationEvent,
    route_id: int,
    status: str,
    error_message: Optional[str],
    latency_ms: Optional[int],
    payload_preview: Optional[str],
    provider_reference: Optional[str] = None,
) -> bool:
    """Record a dispatch outcome. Returns False ONLY when the dispatch
    has already been recorded as `sent` — i.e. a true idempotency hit
    against a successful prior dispatch. Returns True in all other
    cases, including overwriting a previous failed/skipped attempt
    with the new result so retries land cleanly.

    Idempotency model:
      - One row per (route_id, dedupe_key) pair (enforced by a unique
        index). The key comes off the event, so each trigger owns its
        own semantics — reassigning A → B → A re-notifies A, while a
        no-op write does not, and manual sends (#1010) stay repeatable
        by generating a per-invocation key.
      - If the existing row's status is `sent`, refuse the new write
        (caller treats as "already done, skip")
      - If the existing row's status is `failed`/`skipped`, overwrite
        with the new outcome — a previous failure must not block a
        retry
      - If no row exists yet, insert a fresh one
    """
    # Pre-flight: check whether a row already exists for this
    # (route, dedupe_key) pair. Doing the check up front lets us
    # update-in-place when needed — avoids the rollback path whose
    # `session.rollback()` expires every loaded object in the session
    # (route, integrations, etc.) and breaks subsequent attribute
    # access in async context.
    result = await session.execute(
        select(NotificationDispatchLog).where(
            NotificationDispatchLog.route_id == route_id,
            NotificationDispatchLog.dedupe_key == event.dedupe_key,
        ),
    )
    existing = result.scalars().first()

    if existing is not None and existing.status == "sent":
        # True idempotency hit — don't overwrite a successful dispatch.
        return False

    if existing is not None:
        # Previous failed/skipped attempt — overwrite it so the log
        # reflects the latest outcome and the retry path is clean.
        existing.status = status
        existing.error_message = error_message
        existing.latency_ms = latency_ms
        existing.payload_preview = payload_preview[:500] if payload_preview else None
        existing.provider_reference = provider_reference
        existing.dispatched_at = datetime.utcnow()
        await session.commit()
        return True

    # No prior record — insert fresh.
    log = NotificationDispatchLog(
        customer_code=event.customer_code,
        # Populated only for alert-shaped events; a case-task assignment
        # leaves it NULL and carries its identity in entity_type/entity_id.
        alert_id=event.entity_id if event.entity_type == EntityType.ALERT else None,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        dedupe_key=event.dedupe_key,
        route_id=route_id,
        trigger=event.trigger.value,
        status=status,
        error_message=error_message,
        latency_ms=latency_ms,
        payload_preview=payload_preview[:500] if payload_preview else None,
        provider_reference=provider_reference,
    )
    session.add(log)
    try:
        await session.commit()
        return True
    except IntegrityError:
        # Race: another concurrent dispatch slipped in between our
        # SELECT and INSERT. Roll back, treat as idempotency hit. The
        # caller's outcome will be `skipped` and the route's attrs
        # will be expired — but the caller has already cached them
        # into locals so this is safe.
        await session.rollback()
        return False


def _sample_event_for(route: CustomerNotificationRoute) -> NotificationEvent:
    """A realistic-looking event for a test send.

    Deliberately built from the route's own trigger so the operator sees the
    body they'll actually get, not a generic "hello". The dedupe key carries a
    uuid so repeated tests always send — a test that silently no-ops the second
    time would be worse than useless.
    """
    trigger = (
        NotificationTrigger(route.trigger)
        if route.trigger in {t.value for t in NotificationTrigger}
        else NotificationTrigger.INVESTIGATION_COMPLETE
    )

    is_assignment = trigger.value in INTERNAL_TRIGGERS
    entity_type = EntityType.ALERT
    if trigger == NotificationTrigger.CASE_ASSIGNED:
        entity_type = EntityType.CASE
    elif trigger == NotificationTrigger.CASE_TASK_ASSIGNED:
        entity_type = EntityType.CASE_TASK

    return NotificationEvent(
        customer_code=route.customer_code,
        trigger=trigger,
        severity=NotificationSeverity.HIGH,
        subject="Test notification from CoPilot",
        summary=(
            "This is a test notification triggered from the CoPilot route form. "
            "If you are reading it, this route is configured correctly."
        ),
        entity_type=entity_type,
        entity_id=0,
        dedupe_key=f"test:{route.id}:{uuid4()}",
        link_url=None,
        assignee_username=route.created_by if is_assignment else None,
        actor_username=route.created_by,
        context={"alert_name": "Test notification from CoPilot", "title": "Test notification from CoPilot"},
    )


async def send_test_notification(route: CustomerNotificationRoute, session: AsyncSession) -> DispatchOutcome:
    """Deliver one test message through the route's real provider.

    Uses the normal send path rather than a bespoke per-provider probe, because
    a probe tests the wrong thing: the Resend key in use here is send-only
    restricted, so an account-state check 401s while sending works fine. What an
    operator wants to know is "will a real notification arrive", and only a real
    send answers that.

    The outcome IS logged. A test send consumes provider quota exactly like a
    real one — leaving it out of the dispatch log would make the Resend monthly
    counter under-report, and hide test traffic from the audit trail.
    """
    provider = get_channel(route.channel)
    if provider is None:
        return DispatchOutcome(
            route_id=route.id,
            route_name=route.name,
            channel=route.channel,
            status=DispatchStatus.FAILED,
            error_message=f"Unsupported channel: {route.channel}",
        )

    event = _sample_event_for(route)
    ctx = DispatchContext(session=session, event=event)
    body, template_error = _render_body(route, event)

    try:
        result = await provider.send(route=route, event=event, rendered_body=body, ctx=ctx)
    except Exception as e:  # noqa: BLE001 — a test must report, never 500
        logger.exception(f"Test dispatch raised for route {route.id}: {e!r}")
        result = SendResult.failed(f"Dispatcher exception: {type(e).__name__}: {e}")

    await _record_log(
        session,
        event=event,
        route_id=route.id,
        status=result.status,
        error_message=(
            f"{result.error_message}; {template_error}"
            if result.error_message and template_error
            else (result.error_message or template_error)
        ),
        latency_ms=result.latency_ms,
        payload_preview=body[:500],
        provider_reference=result.provider_reference,
    )

    return DispatchOutcome(
        route_id=route.id,
        route_name=route.name,
        channel=route.channel,
        status=DispatchStatus(result.status),
        error_message=result.error_message,
        latency_ms=result.latency_ms,
        provider_reference=result.provider_reference,
    )


async def routes_for_event(event: NotificationEvent, session: AsyncSession) -> List[CustomerNotificationRoute]:
    """Candidate routes for an event, before trigger/severity filtering.

    Scope decides the pool, and the split is the point of the whole dimension:
    an assignment is about *who is working on something*, so it resolves against
    internal routes and never reaches the customer whose alert it was. Anything
    else is about the customer's security posture and resolves against theirs.
    """
    if event.trigger.value in INTERNAL_TRIGGERS:
        stmt = select(CustomerNotificationRoute).where(
            CustomerNotificationRoute.scope == NotificationScope.INTERNAL.value,
        )
    else:
        stmt = select(CustomerNotificationRoute).where(
            CustomerNotificationRoute.scope == NotificationScope.CUSTOMER.value,
            CustomerNotificationRoute.customer_code == event.customer_code,
        )
    result = await session.execute(stmt.order_by(desc(CustomerNotificationRoute.created_at)))
    return result.scalars().all()


def _self_assignment_suppressed(route: CustomerNotificationRoute, event: NotificationEvent) -> bool:
    """Whether to drop a self-assignment for this route.

    An analyst picking up their own alert doesn't need a notification about it.
    Opt-in per route because some teams do want the audit trail.
    """
    if event.trigger.value not in INTERNAL_TRIGGERS:
        return False
    if not event.actor_username or not event.assignee_username:
        return False
    if event.actor_username != event.assignee_username:
        return False
    return not bool(getattr(route, "notify_on_self_assign", False))


async def dispatch(req: DispatchRequest, session: AsyncSession) -> DispatchResponse:
    """Talon's entry point. Adapts the wire format and delegates.

    Kept as a thin shim because `DispatchRequest` is an external contract; every
    CoPilot-originated trigger builds a `NotificationEvent` directly and calls
    `dispatch_event`.
    """
    return await dispatch_event(event_from_dispatch_request(req), session)


async def dispatch_event(event: NotificationEvent, session: AsyncSession) -> DispatchResponse:
    """Walk the matching routes, fire each, log every outcome.

    Idempotency is enforced at the log table — the insert is attempted *before*
    the provider call, so a re-dispatch sees the existing row and short-circuits
    without sending.
    """
    routes = await routes_for_event(event, session)

    matched_routes = [
        r
        for r in routes
        if r.enabled
        and _trigger_applies(event.trigger.value, r.trigger)
        and _severity_meets(event.severity.value, r.min_severity)
        and not _self_assignment_suppressed(r, event)
    ]

    outcomes: List[DispatchOutcome] = []
    sent = failed = skipped = 0

    # AI-report opt-out gate. Checked AFTER matching so the dispatch log still
    # records which routes *would* have fired — "suppressed by the AI switch"
    # is far easier to debug than silence — but BEFORE the connector fetch and
    # any provider call, so nothing leaves the process.
    #
    # Only customer-facing routes are gated. Internal routes are deliberately
    # exempt: running investigations while keeping the results internal is a
    # supported configuration, and the switch governs what reaches the CUSTOMER.
    # (routes_for_event already returns one scope or the other, so in practice
    # this filter is all-or-nothing — it is written per-route so it stays
    # correct if a future trigger mixes scopes.)
    gated_routes = [r for r in matched_routes if r.scope == NotificationScope.CUSTOMER.value]
    if gated_routes and not await _ai_reports_permitted(event.trigger.value, event.customer_code, session):
        logger.info(
            f"AI reports are not enabled for customer {event.customer_code}; "
            f"suppressing {len(gated_routes)} matched notification route(s) "
            f"for alert {event.entity_id}.",
        )
        reason = "AI reports are not enabled for this customer; notification suppressed."
        for route in gated_routes:
            # Cache before the await — see the attribute-caching note in the
            # main loop below.
            route_id = route.id
            route_name = route.name
            route_channel = route.channel
            await _record_log(
                session,
                event=event,
                route_id=route_id,
                status=DispatchStatus.SKIPPED.value,
                error_message=reason,
                latency_ms=None,
                payload_preview=None,
            )
            skipped += 1
            outcomes.append(
                DispatchOutcome(
                    route_id=route_id,
                    route_name=route_name,
                    channel=route_channel,
                    status=DispatchStatus.SKIPPED,
                    error_message=reason,
                ),
            )
        return DispatchResponse(
            success=True,
            message="Dispatch suppressed — AI reports are not enabled for this customer",
            routes_matched=len(gated_routes),
            dispatched=0,
            skipped=skipped,
            failed=0,
            outcomes=outcomes,
        )

    # Per-call context. Expensive lookups a provider needs (the Shuffle
    # connector row, an alert's AI report) are memoized on it, so a batch of
    # routes shares one read — the property the pre-refactor prefetch gave us,
    # now lazy: nothing is read unless a route actually reaches that provider.
    ctx = DispatchContext(session=session, event=event)

    for route in matched_routes:
        # Cache every route attribute the LOOP needs into locals UP FRONT.
        # Once we cross any `await` (let alone any rollback) the route
        # SQLAlchemy state can be expired and a synchronous attribute
        # access then triggers an implicit refresh query — which in
        # AsyncSession throws MissingGreenlet. Providers do the same for
        # the attributes they read; see ChannelProvider.send's docstring.
        route_id = route.id
        route_name = route.name
        route_channel = route.channel

        body, template_error = _render_body(route, event)
        body_preview = body[:500]

        latency_ms: Optional[int] = None
        result_status = "sent"
        error_message: Optional[str] = None
        provider_reference: Optional[str] = None
        # Stays None when the channel is unknown or send() raised. after_send
        # guards on it rather than inferring from result_status — the two can
        # only diverge via a future edit, and this way that edit is safe.
        result: Optional[SendResult] = None

        provider = get_channel(route_channel)

        try:
            if provider is None:
                # Unknown channel — recorded as a failure rather than silently
                # dropped, so a misconfigured row surfaces in the dispatch log.
                result_status = "failed"
                error_message = f"Unsupported channel: {route_channel}"
                latency_ms = None
            else:
                result = await provider.send(
                    route=route,
                    event=event,
                    rendered_body=body,
                    ctx=ctx,
                )
                result_status = result.status
                error_message = result.error_message
                latency_ms = result.latency_ms
                provider_reference = result.provider_reference
        except Exception as e:  # noqa: BLE001 — best-effort, never raise
            logger.exception(f"Dispatcher raised for route {route_id}: {e!r}")
            result_status = "failed"
            error_message = f"Dispatcher exception: {type(e).__name__}: {e}"

        # A template failure is worth recording even when delivery succeeded:
        # the operator got the channel default, not what they wrote, and would
        # otherwise have no signal that their template is broken.
        if template_error:
            error_message = f"{error_message}; {template_error}" if error_message else template_error

        # Record (or update) the dispatch outcome. _record_log handles
        # the retry-after-failure case in-place so a previous failed
        # row doesn't block a new attempt — the only way we get back
        # `False` here is a true idempotency hit on a previously-sent
        # dispatch.
        recorded = await _record_log(
            session,
            event=event,
            route_id=route_id,
            status=result_status,
            error_message=error_message,
            latency_ms=latency_ms,
            payload_preview=body_preview,
            provider_reference=provider_reference,
        )

        if not recorded:
            skipped += 1
            outcomes.append(
                DispatchOutcome(
                    route_id=route_id,
                    route_name=route_name,
                    channel=route_channel,
                    status=DispatchStatus.SKIPPED,
                    error_message="Already dispatched (idempotency)",
                    latency_ms=None,
                ),
            )
            continue

        # Maintain denorm columns for the UI list. Cheaper than joining
        # the log table on every render. We do this via an explicit
        # UPDATE statement rather than mutating the loaded route
        # object, so route's expiration state can't bite us.
        if result_status == "sent":
            sent += 1
            await session.execute(
                update(CustomerNotificationRoute)
                .where(CustomerNotificationRoute.id == route_id)
                .values(
                    dispatch_count=CustomerNotificationRoute.dispatch_count + 1,
                    last_dispatched_at=datetime.utcnow(),
                ),
            )
            # Channel-specific post-send side effects, inside the same commit.
            # Shuffle stamps last_used_at on the integration row so its list can
            # show "fired 2h ago" without joining the dispatch log.
            if provider is not None and result is not None:
                await provider.after_send(route=route, result=result, ctx=ctx)
            await session.commit()
        elif result_status == "skipped":
            skipped += 1
        else:
            failed += 1

        outcomes.append(
            DispatchOutcome(
                route_id=route_id,
                route_name=route_name,
                channel=route_channel,
                status=DispatchStatus(result_status),
                error_message=error_message,
                latency_ms=latency_ms,
                provider_reference=provider_reference,
            ),
        )

    return DispatchResponse(
        success=True,
        message=(
            f"Dispatched {sent} of {len(matched_routes)} matching route(s) " f"for customer {event.customer_code} alert {event.entity_id}"
        ),
        routes_matched=len(matched_routes),
        dispatched=sent,
        skipped=skipped,
        failed=failed,
        outcomes=outcomes,
    )
