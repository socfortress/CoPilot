"""
Notification routing service — CRUD for routes, the dispatch loop, and
a read-only view over the dispatch log.

The dispatch loop is the heart of the module. It's called via
`POST /notifications/dispatch` (Talon's after-investigation hook) and
walks every enabled route for the customer, filters by trigger and
severity, formats the message body per channel, calls the appropriate
dispatcher, and records the outcome in `notification_dispatch_log`. The
log row is what gives us idempotency — re-dispatching the same
(customer, alert, route, trigger) is a no-op.
"""

from __future__ import annotations

from datetime import datetime
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.utils import get_connector_info_from_db
from app.db.universal_models import CustomerNotificationRoute
from app.db.universal_models import CustomerShuffleIntegration
from app.db.universal_models import NotificationDispatchLog
from app.notifications.schema.notifications import SEVERITY_ORDER
from app.notifications.schema.notifications import DispatchOutcome
from app.notifications.schema.notifications import DispatchRequest
from app.notifications.schema.notifications import DispatchResponse
from app.notifications.schema.notifications import DispatchStatus
from app.notifications.schema.notifications import NotificationChannel
from app.notifications.schema.notifications import NotificationRouteCreate
from app.notifications.schema.notifications import NotificationRouteUpdate
from app.notifications.schema.notifications import NotificationTrigger
from app.notifications.schema.notifications import ShuffleApp
from app.notifications.schema.notifications import ShuffleIntegrationCreate
from app.notifications.schema.notifications import ShuffleIntegrationUpdate
from app.notifications.schema.notifications import ShuffleOrg
from app.notifications.services.dispatchers import dispatch_shuffle
from app.notifications.services.dispatchers import dispatch_smtp_email
from app.notifications.services.dispatchers import (
    list_shuffle_apps as shuffle_apps_client,
)
from app.notifications.services.dispatchers import (
    list_shuffle_orgs as shuffle_orgs_client,
)
from app.notifications.services.dispatchers import (
    verify_shuffle_org as verify_shuffle_org_client,
)

# Name of the Shuffle row in CoPilot's connectors table. The
# `connector_url` (Shuffle base URL) and `connector_api_key` (admin
# Bearer token) are read fresh on every dispatch so a key rotation
# takes effect without restarting the backend.
_SHUFFLE_CONNECTOR_NAME = "Shuffle"


async def _get_shuffle_connector(session: AsyncSession) -> tuple[str, str]:
    """Fetch (base_url, api_key) for the Shuffle connector. Raises
    HTTPException if the connector row is missing or unconfigured —
    surfaces a clear 4xx in the dispatch endpoint instead of a generic
    500 when an admin forgets to configure Shuffle."""
    info = await get_connector_info_from_db(_SHUFFLE_CONNECTOR_NAME, session)
    if not info:
        raise HTTPException(
            status_code=503,
            detail=(
                "Shuffle connector is not configured in CoPilot. "
                "Add the Shuffle connector with a valid API key before "
                "creating Shuffle-channel notification routes."
            ),
        )
    api_key = info.get("connector_api_key") or ""
    base_url = info.get("connector_url") or "https://shuffler.io"
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Shuffle connector is configured but has no API key set.",
        )
    return (base_url, api_key)


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

    route = CustomerNotificationRoute(
        customer_code=customer_code,
        name=payload.name,
        trigger=payload.trigger.value,
        channel=payload.channel.value,
        destination=payload.destination,
        min_severity=payload.min_severity.value,
        format_template=payload.format_template,
        enabled=payload.enabled,
        created_by=created_by,
        shuffle_integration_id=payload.shuffle_integration_id,
        shuffle_app_id=payload.shuffle_app_id,
        shuffle_app_name=payload.shuffle_app_name,
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
    data = payload.dict(exclude_unset=True)

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

    for field, value in data.items():
        # Enums: write the underlying string into the DB column.
        if hasattr(value, "value"):
            value = value.value
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
    data = payload.dict(exclude_unset=True)
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
    base_url, api_key = await _get_shuffle_connector(session)
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
    base_url, api_key = await _get_shuffle_connector(session)
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
    base_url, api_key = await _get_shuffle_connector(session)
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


def _format_default_body(req: DispatchRequest) -> str:
    """Plain default formatter when a route has no `format_template`.

    Markdown-ish but readable in both Slack and email — both channels
    render this acceptably without extra structure. Phase 4 swaps for
    per-channel templates.
    """
    parts = [
        f"*AI investigation complete* — severity: *{req.severity_assessment.value}*",
        "",
        f"Customer: `{req.customer_code}`",
        f"Alert: #{req.alert_id}" + (f" — {req.alert_name}" if req.alert_name else ""),
        "",
        req.summary.strip(),
    ]
    if req.report_url:
        parts.extend(["", f"Full report: {req.report_url}"])
    return "\n".join(parts)


def _format_default_subject(req: DispatchRequest) -> str:
    return (
        f"[{req.severity_assessment.value}] AI investigation — "
        f"alert #{req.alert_id}"
        f"{(' ' + req.alert_name) if req.alert_name else ''}"
    )


def _render_body(route: CustomerNotificationRoute, req: DispatchRequest) -> str:
    """Apply the route's `format_template` if set, else fall back.

    Phase 1's templating is intentionally minimal — `{{ variable }}`
    substitution only, no Jinja control flow. Real Jinja can come in
    Phase 4 when the per-channel templates land.
    """
    if not route.format_template:
        return _format_default_body(req)

    body = route.format_template
    substitutions = {
        "{{customer_code}}": req.customer_code,
        "{{alert_id}}": str(req.alert_id),
        "{{alert_name}}": req.alert_name or "",
        "{{severity}}": req.severity_assessment.value,
        "{{summary}}": req.summary,
        "{{report_url}}": req.report_url or "",
    }
    for token, value in substitutions.items():
        body = body.replace(token, value)
    return body


async def _record_log(
    session: AsyncSession,
    *,
    customer_code: str,
    alert_id: int,
    route_id: int,
    trigger: str,
    status: str,
    error_message: Optional[str],
    latency_ms: Optional[int],
    payload_preview: Optional[str],
    shuffle_execution_id: Optional[str] = None,
) -> bool:
    """Record a dispatch outcome. Returns False ONLY when the dispatch
    has already been recorded as `sent` — i.e. a true idempotency hit
    against a successful prior dispatch. Returns True in all other
    cases, including overwriting a previous failed/skipped attempt
    with the new result so retries land cleanly.

    Idempotency model:
      - One row per (customer_code, alert_id, route_id, trigger) tuple
        (enforced by a unique index)
      - If the existing row's status is `sent`, refuse the new write
        (caller treats as "already done, skip")
      - If the existing row's status is `failed`/`skipped`, overwrite
        with the new outcome — a previous failure must not block a
        retry
      - If no row exists yet, insert a fresh one
    """
    # Pre-flight: check whether a row already exists for this
    # (customer, alert, route, trigger) tuple. Doing the check up front
    # lets us update-in-place when needed — avoids the rollback path
    # whose `session.rollback()` expires every loaded object in the
    # session (route, integrations, etc.) and breaks subsequent
    # attribute access in async context.
    result = await session.execute(
        select(NotificationDispatchLog).where(
            NotificationDispatchLog.customer_code == customer_code,
            NotificationDispatchLog.alert_id == alert_id,
            NotificationDispatchLog.route_id == route_id,
            NotificationDispatchLog.trigger == trigger,
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
        existing.shuffle_execution_id = shuffle_execution_id
        existing.dispatched_at = datetime.utcnow()
        await session.commit()
        return True

    # No prior record — insert fresh.
    log = NotificationDispatchLog(
        customer_code=customer_code,
        alert_id=alert_id,
        route_id=route_id,
        trigger=trigger,
        status=status,
        error_message=error_message,
        latency_ms=latency_ms,
        payload_preview=payload_preview[:500] if payload_preview else None,
        shuffle_execution_id=shuffle_execution_id,
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


async def dispatch(req: DispatchRequest, session: AsyncSession) -> DispatchResponse:
    """Walk the customer's routes, fire each match, log each outcome.

    Idempotency is enforced at the log table — we attempt the insert
    *before* calling the provider, so a re-dispatch sees the existing
    row and short-circuits without sending. (The cost is one wasted
    INSERT in the race case, which is fine.)
    """
    routes = await list_routes(req.customer_code, session)

    matched_routes = [
        r
        for r in routes
        if r.enabled and _trigger_applies(req.trigger.value, r.trigger) and _severity_meets(req.severity_assessment.value, r.min_severity)
    ]

    outcomes: List[DispatchOutcome] = []
    sent = failed = skipped = 0

    # Shuffle dispatch needs the deployment's connector creds. We fetch
    # them once per dispatch call (before the per-route loop) so a
    # whole batch of Shuffle routes shares one DB read. The fetch
    # itself is gated by "is any matched route Shuffle" — for SMTP-only
    # customers we never touch the connector row.
    shuffle_creds: Optional[tuple[str, str]] = None
    if any(r.channel == NotificationChannel.SHUFFLE.value for r in matched_routes):
        try:
            shuffle_creds = await _get_shuffle_connector(session)
        except HTTPException as e:
            # Connector misconfigured — the dispatch endpoint exposes
            # the helper's 503, but for a batch dispatch we'd rather
            # mark each Shuffle route as failed in the log than abort
            # the whole loop. SMTP routes in the same batch still go.
            logger.warning(f"Shuffle connector unavailable: {e.detail}")
            shuffle_creds = None
            shuffle_creds_error = str(e.detail)
        else:
            shuffle_creds_error = None
    else:
        shuffle_creds_error = None

    for route in matched_routes:
        # Cache every route attribute we'll need into locals UP FRONT.
        # Once we cross any `await` (let alone any rollback) the route
        # SQLAlchemy state can be expired and a synchronous attribute
        # access then triggers an implicit refresh query — which in
        # AsyncSession throws MissingGreenlet. Caching here means the
        # rest of the loop is plain-Python access on locals.
        route_id = route.id
        route_name = route.name
        route_channel = route.channel
        route_destination = route.destination
        route_shuffle_app_id = route.shuffle_app_id
        route_shuffle_integration_id = route.shuffle_integration_id

        body = _render_body(route, req)
        body_preview = body[:500]

        latency_ms: Optional[int] = None
        result_status = "sent"
        error_message: Optional[str] = None
        shuffle_execution_id: Optional[str] = None

        try:
            if route_channel == NotificationChannel.SMTP_EMAIL.value:
                recipients = [r.strip() for r in route_destination.split(",") if r.strip()]
                subject = _format_default_subject(req)
                result_status, error_message, latency_ms = await dispatch_smtp_email(recipients, subject, body)
            elif route_channel == NotificationChannel.SHUFFLE.value:
                # Phase 2: Shuffle hosted MCP. Fire-and-record — we POST
                # to /api/v1/apps/{app_id}/mcp with the deployment's
                # admin Bearer + the customer's Org-Id, capture the
                # execution_id, and consider the dispatch "sent" on
                # HTTP 200. We do NOT poll for the downstream app's
                # terminal state.
                if shuffle_creds is None:
                    result_status = "failed"
                    error_message = shuffle_creds_error or "Shuffle connector unavailable"
                    latency_ms = 0
                elif not route_shuffle_app_id:
                    result_status = "failed"
                    error_message = "Route has no shuffle_app_id (data integrity issue)"
                    latency_ms = 0
                else:
                    integration = await session.get(CustomerShuffleIntegration, route_shuffle_integration_id)
                    if not integration or integration.customer_code != req.customer_code:
                        # Defense-in-depth: we already enforce tenant
                        # isolation at create/update time, but a hand-
                        # edited row could still slip through. Refusing
                        # at dispatch time prevents cross-tenant leaks.
                        result_status = "failed"
                        error_message = (
                            "Route's shuffle_integration is missing or belongs to a " "different customer; refusing to dispatch."
                        )
                        latency_ms = 0
                    elif not integration.enabled:
                        result_status = "skipped"
                        error_message = "Shuffle integration is disabled"
                        latency_ms = 0
                    else:
                        base_url, api_key = shuffle_creds
                        # Cache integration attrs too — same reason as
                        # the route caching above.
                        integration_org_id = integration.shuffle_org_id
                        # Shuffle's input_text is natural language. We
                        # prepend a "send to {destination}" hint so the
                        # Shuffle app agent knows where to deliver, and
                        # follow with the formatted body.
                        if route_destination:
                            input_text = f"Send to {route_destination}: {body}"
                        else:
                            input_text = body
                        (
                            result_status,
                            error_message,
                            latency_ms,
                            shuffle_execution_id,
                        ) = await dispatch_shuffle(
                            base_url=base_url,
                            api_key=api_key,
                            org_id=integration_org_id,
                            app_id=route_shuffle_app_id,
                            input_text=input_text,
                        )
            else:
                # Unknown channel — preserved as a failure rather than
                # silently dropped so a misconfigured row surfaces in
                # the dispatch log.
                result_status = "failed"
                error_message = f"Unsupported channel: {route_channel}"
                latency_ms = None
        except Exception as e:  # noqa: BLE001 — best-effort, never raise
            logger.exception(f"Dispatcher raised for route {route_id}: {e!r}")
            result_status = "failed"
            error_message = f"Dispatcher exception: {type(e).__name__}: {e}"

        # Record (or update) the dispatch outcome. _record_log handles
        # the retry-after-failure case in-place so a previous failed
        # row doesn't block a new attempt — the only way we get back
        # `False` here is a true idempotency hit on a previously-sent
        # dispatch.
        recorded = await _record_log(
            session,
            customer_code=req.customer_code,
            alert_id=req.alert_id,
            route_id=route_id,
            trigger=req.trigger.value,
            status=result_status,
            error_message=error_message,
            latency_ms=latency_ms,
            payload_preview=body_preview,
            shuffle_execution_id=shuffle_execution_id,
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
            # Bump the integration's last_used_at on a successful
            # Shuffle dispatch — gives the integration list a "fired
            # 2h ago" signal without a join against the log.
            if route_channel == NotificationChannel.SHUFFLE.value and route_shuffle_integration_id:
                await session.execute(
                    update(CustomerShuffleIntegration)
                    .where(CustomerShuffleIntegration.id == route_shuffle_integration_id)
                    .values(last_used_at=datetime.utcnow()),
                )
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
                shuffle_execution_id=shuffle_execution_id,
            ),
        )

    return DispatchResponse(
        success=True,
        message=(f"Dispatched {sent} of {len(matched_routes)} matching route(s) " f"for customer {req.customer_code} alert {req.alert_id}"),
        routes_matched=len(matched_routes),
        dispatched=sent,
        skipped=skipped,
        failed=failed,
        outcomes=outcomes,
    )
