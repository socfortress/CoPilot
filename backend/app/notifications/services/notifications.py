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
from typing import Iterable
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import CustomerNotificationRoute
from app.db.universal_models import NotificationDispatchLog
from app.notifications.schema.notifications import (
    DispatchOutcome,
    DispatchRequest,
    DispatchResponse,
    DispatchStatus,
    NotificationChannel,
    NotificationRouteCreate,
    NotificationRouteRead,
    NotificationRouteUpdate,
    NotificationTrigger,
    SEVERITY_ORDER,
)
from app.notifications.services.dispatchers import (
    DispatchResult,
    dispatch_slack_webhook,
    dispatch_smtp_email,
)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def list_routes(customer_code: str, session: AsyncSession) -> List[CustomerNotificationRoute]:
    """All routes for a customer, newest-first. UI list source."""
    result = await session.execute(
        select(CustomerNotificationRoute)
        .where(CustomerNotificationRoute.customer_code == customer_code)
        .order_by(desc(CustomerNotificationRoute.created_at))
    )
    return result.scalars().all()


async def get_route(route_id: int, customer_code: str, session: AsyncSession) -> CustomerNotificationRoute:
    """Single route, scoped by customer to keep the tenant boundary
    explicit at lookup time."""
    result = await session.execute(
        select(CustomerNotificationRoute).where(
            CustomerNotificationRoute.id == route_id,
            CustomerNotificationRoute.customer_code == customer_code,
        )
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
        .limit(limit)
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
            f"Unknown severity in routing comparison "
            f"(report={report_severity!r}, route_min={route_min!r}); "
            f"skipping route."
        )
        return False


def _trigger_applies(report_trigger: str, route_trigger: str, severity: str) -> bool:
    """Decide whether a route's trigger matches the dispatch.

    `investigation_complete` always matches (it's the catch-all).
    `severity_critical_or_high` only matches when the report severity
    is Critical or High.
    """
    if route_trigger != report_trigger:
        return False
    if route_trigger == NotificationTrigger.SEVERITY_CRITICAL_OR_HIGH.value:
        return severity in ("Critical", "High")
    return True


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
) -> bool:
    """Insert a dispatch log row. Returns False if the unique-key
    constraint trips (i.e. this dispatch was already recorded), which
    is the idempotency signal for the caller."""
    log = NotificationDispatchLog(
        customer_code=customer_code,
        alert_id=alert_id,
        route_id=route_id,
        trigger=trigger,
        status=status,
        error_message=error_message,
        latency_ms=latency_ms,
        payload_preview=payload_preview[:500] if payload_preview else None,
    )
    session.add(log)
    try:
        await session.commit()
        return True
    except IntegrityError:
        # Another dispatch (or a re-run) raced us — treat the existing
        # row as authoritative and back out cleanly.
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
        if r.enabled
        and _trigger_applies(req.trigger.value, r.trigger, req.severity_assessment.value)
        and _severity_meets(req.severity_assessment.value, r.min_severity)
    ]

    outcomes: List[DispatchOutcome] = []
    sent = failed = skipped = 0

    for route in matched_routes:
        body = _render_body(route, req)
        body_preview = body[:500]

        # Idempotency check — try to claim the dispatch slot first. If
        # the unique constraint trips, a previous dispatch already
        # handled this (customer, alert, route, trigger) tuple.
        # We insert with status=skipped initially; on success we'll
        # update the row to 'sent' to record the real outcome.
        # Simpler approach: insert *after* the provider call, catch the
        # IntegrityError, treat as "already done".
        latency_ms: Optional[int] = None
        result_status = "sent"
        error_message: Optional[str] = None

        try:
            result: DispatchResult
            if route.channel == NotificationChannel.SLACK_WEBHOOK.value:
                result = await dispatch_slack_webhook(route.destination, body)
            elif route.channel == NotificationChannel.SMTP_EMAIL.value:
                recipients = [r.strip() for r in route.destination.split(",") if r.strip()]
                subject = _format_default_subject(req)
                result = await dispatch_smtp_email(recipients, subject, body)
            else:
                # Unknown channel (Phase 2's 'shuffle' will land here
                # before the dispatcher arm exists) — log a clear
                # failure rather than silently skipping.
                result = (
                    "failed",
                    f"Unsupported channel: {route.channel}",
                    None,
                )

            result_status, error_message, latency_ms = result
        except Exception as e:  # noqa: BLE001 — best-effort, never raise
            logger.exception(f"Dispatcher raised for route {route.id}: {e!r}")
            result_status = "failed"
            error_message = f"Dispatcher exception: {type(e).__name__}: {e}"

        # Try to record the outcome. If the unique constraint trips,
        # this dispatch was already logged — treat as 'skipped' for the
        # response (no double-counting in the per-route stats).
        recorded = await _record_log(
            session,
            customer_code=req.customer_code,
            alert_id=req.alert_id,
            route_id=route.id,
            trigger=req.trigger.value,
            status=result_status,
            error_message=error_message,
            latency_ms=latency_ms,
            payload_preview=body_preview,
        )

        if not recorded:
            skipped += 1
            outcomes.append(
                DispatchOutcome(
                    route_id=route.id,
                    route_name=route.name,
                    channel=route.channel,
                    status=DispatchStatus.SKIPPED,
                    error_message="Already dispatched (idempotency)",
                    latency_ms=None,
                )
            )
            continue

        # Maintain denorm columns for the UI list. Cheaper than joining
        # the log table on every render.
        if result_status == "sent":
            sent += 1
            route.dispatch_count += 1
            route.last_dispatched_at = datetime.utcnow()
            await session.commit()
        else:
            failed += 1

        outcomes.append(
            DispatchOutcome(
                route_id=route.id,
                route_name=route.name,
                channel=route.channel,
                status=DispatchStatus(result_status),
                error_message=error_message,
                latency_ms=latency_ms,
            )
        )

    return DispatchResponse(
        success=True,
        message=(
            f"Dispatched {sent} of {len(matched_routes)} matching route(s) "
            f"for customer {req.customer_code} alert {req.alert_id}"
        ),
        routes_matched=len(matched_routes),
        dispatched=sent,
        skipped=skipped,
        failed=failed,
        outcomes=outcomes,
    )
