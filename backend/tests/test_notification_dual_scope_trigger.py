"""Analyst sign-off reaching both scopes (#1053).

`ai_report_reviewed` was emitted by `submit_review` from #1036 onward and could
not be selected on any route, so every one of those events matched nothing. It
is now the first **dual-scope** trigger: one sign-off can reach an internal
route and a customer-facing route through separate routes.

That configuration is the reason the trigger exists — run an internal route the
moment a report lands, and hold the customer's route until a human has checked
it. Every other trigger is one scope or the other, so this is the first time
`routes_for_event` returns a mixed pool, and these tests pin the three things
that can go wrong with it:

**Internal routes must not be tenant-filtered.** They carry `customer_code =
NULL`. Applying the customer filter to the whole query — the obvious way to
write it — silently returns nothing for the internal half.

**Customer routes must still be tenant-filtered.** Widening the scope must not
widen the tenant boundary: another customer's review must never reach this
customer's route.

**The AI opt-out still applies to the customer half only.** #1014 governs what
reaches an *end customer*. Keeping findings internal while investigations run is
a supported configuration, so the internal half is deliberately exempt — and the
gate has to survive a batch that contains both.

Uses a real in-memory SQLite database rather than a mocked session, because what
is being tested here IS the query: a mock that returns a canned list would pass
against a WHERE clause that filters out every internal route.

Run with: cd backend && python -m pytest tests/test_notification_dual_scope_trigger.py
"""

import asyncio
import os
from datetime import datetime

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.notifications.services.notifications as svc  # noqa: E402
from app.db.universal_models import CustomerNotificationRoute  # noqa: E402
from app.notifications.schema.events import EntityType  # noqa: E402
from app.notifications.schema.events import NotificationEvent  # noqa: E402
from app.notifications.schema.notifications import DUAL_SCOPE_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import INTERNAL_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.event_builders import (  # noqa: E402
    ai_report_reviewed_event,
)

CC = "TENANT_A"
OTHER = "TENANT_B"


async def _make_session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    table = SQLModel.metadata.tables["customer_notification_route"]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=[table]))
    return AsyncSession(engine)


def _route(name, *, scope, customer_code, trigger="ai_report_reviewed", **over):
    base = dict(
        name=name,
        scope=scope,
        customer_code=customer_code,
        trigger=trigger,
        channel="webhook",
        # Superseded by `config` since #1023, but still NOT NULL on the table.
        destination="",
        enabled=True,
        min_severity="Informational",
        recipient_mode="static",
        config="{}",
        created_at=datetime(2026, 8, 4, 12, 0, 0),
        created_by="admin",
    )
    base.update(over)
    return CustomerNotificationRoute(**base)


async def _seed(session: AsyncSession) -> None:
    session.add_all(
        [
            _route("internal review", scope="internal", customer_code=None),
            _route("customer review", scope="customer", customer_code=CC),
            _route("other tenant review", scope="customer", customer_code=OTHER),
            _route("internal assignment", scope="internal", customer_code=None, trigger="alert_assigned"),
            _route("customer alerts", scope="customer", customer_code=CC, trigger="alert_created"),
        ],
    )
    await session.commit()


def _event(trigger=NotificationTrigger.AI_REPORT_REVIEWED, customer_code=CC):
    return NotificationEvent(
        customer_code=customer_code,
        trigger=trigger,
        severity=NotificationSeverity.HIGH,
        subject="Reviewed: Administrators Group Changed",
        summary="An analyst reviewed the AI investigation for this alert.",
        entity_type=EntityType.ALERT,
        entity_id=14,
        dedupe_key="alert:14:ai_report_reviewed",
        context={"reviewer": "asmith", "verdict": "up"},
    )


def _names(routes):
    return sorted(r.name for r in routes)


def _resolve(event):
    """The candidate pool — what `routes_for_event` decides, which is scope and
    tenancy only. Trigger and severity filtering happen after it, in
    `dispatch_event`."""

    async def run():
        session = await _make_session()
        try:
            await _seed(session)
            return await svc.routes_for_event(event, session)
        finally:
            await session.close()

    return asyncio.run(run())


def _matched(event):
    """The routes that would actually fire — candidates, then the same trigger
    and severity filters `dispatch_event` applies."""
    return [
        r
        for r in _resolve(event)
        if r.enabled and svc._trigger_applies(event.trigger.value, r.trigger) and svc._severity_meets(event.severity.value, r.min_severity)
    ]


# ── the scope model ───────────────────────────────────────────────────────


def test_the_review_trigger_is_declared_dual_scope():
    assert "ai_report_reviewed" in DUAL_SCOPE_TRIGGERS


def test_the_review_trigger_is_not_internal_only():
    """Putting it in INTERNAL_TRIGGERS would look like it works and would quietly
    cut the customer half off — and would also drag it into the assignment
    wording and the self-assignment suppression, neither of which apply."""
    assert "ai_report_reviewed" not in INTERNAL_TRIGGERS


# ── resolution ────────────────────────────────────────────────────────────


def test_a_review_fires_both_an_internal_and_a_customer_route():
    """The whole point of #1053."""
    assert _names(_matched(_event())) == ["customer review", "internal review"]


def test_the_internal_half_is_not_tenant_filtered():
    """Internal routes carry customer_code = NULL. Applying the customer filter
    across the whole query is the obvious way to write this and returns nothing
    for the internal half."""
    internal = [r for r in _matched(_event()) if r.scope == "internal"]

    assert len(internal) == 1
    assert internal[0].customer_code is None


def test_another_tenants_customer_route_is_never_included():
    """Widening the scope must not widen the tenant boundary."""
    assert "other tenant review" not in _names(_resolve(_event()))


def test_a_review_for_a_customer_with_no_customer_route_still_reaches_the_soc():
    """Keeping findings internal while investigations run is supported, so the
    internal half must not depend on a customer route existing."""
    assert _names(_matched(_event(customer_code="TENANT_WITH_NO_ROUTES"))) == ["internal review"]


# ── the other triggers are unchanged ──────────────────────────────────────


def test_an_assignment_still_resolves_internal_only():
    """Candidates, not matches — the pool is what scope decides."""
    routes = _resolve(_event(trigger=NotificationTrigger.ALERT_ASSIGNED))

    assert all(r.scope == "internal" for r in routes)
    assert _names(_matched(_event(trigger=NotificationTrigger.ALERT_ASSIGNED))) == ["internal assignment"]


def test_alert_creation_still_resolves_customer_only():
    routes = _resolve(_event(trigger=NotificationTrigger.ALERT_CREATED))

    assert all(r.scope == "customer" for r in routes)
    assert _names(_matched(_event(trigger=NotificationTrigger.ALERT_CREATED))) == ["customer alerts"]


# ── the event builder ─────────────────────────────────────────────────────


def test_the_review_event_carries_the_reviewers_name_not_their_id():
    """This used to be `str(reviewer_user_id)`, so a notification read
    "Reviewed by: 3"."""
    event = ai_report_reviewed_event(
        alert_id=14,
        report_id=3,
        customer_code=CC,
        severity="Medium",
        summary="s",
        reviewer="asmith",
        verdict="up",
        alert_name="Administrators Group Changed",
    )

    assert event.context["reviewer"] == "asmith"
    assert event.actor_username == "asmith"


def test_the_review_event_names_the_alert():
    """`Reviewed: alert #14` is unreadable in a channel carrying several
    customers."""
    event = ai_report_reviewed_event(
        alert_id=14,
        report_id=3,
        customer_code=CC,
        severity="Medium",
        summary="s",
        alert_name="Administrators Group Changed",
    )

    assert event.subject == "Reviewed: Administrators Group Changed"
    assert event.context["alert_name"] == "Administrators Group Changed"


def test_the_review_event_falls_back_when_the_alert_name_is_unknown():
    event = ai_report_reviewed_event(alert_id=14, report_id=3, customer_code=CC, severity="Medium", summary="s")

    assert event.subject == "Reviewed: alert #14"


def test_a_review_dedupes_on_the_alert_not_the_report():
    """A second reviewer, or a revision, must not re-notify. Deliberate — see
    the builder's docstring."""
    first = ai_report_reviewed_event(alert_id=14, report_id=3, customer_code=CC, severity="Medium", summary="s")
    second = ai_report_reviewed_event(alert_id=14, report_id=9, customer_code=CC, severity="Medium", summary="s")

    assert first.dedupe_key == second.dedupe_key


# ── the default body ──────────────────────────────────────────────────────


def test_the_default_body_says_reviewed_not_investigation_complete():
    """Falling through to the investigation branch would announce "AI
    investigation complete" a second time about the same alert and bury what
    actually changed."""
    body = svc._format_default_body(_event())

    assert body.startswith("*AI report reviewed*")
    assert "Reviewed by: asmith" in body
    assert "Verdict: up" in body


def test_the_default_body_survives_a_review_with_no_verdict():
    """An overall verdict is optional on the review form."""
    event = _event()
    event.context = {"reviewer": "asmith"}
    body = svc._format_default_body(event)

    assert "Verdict:" not in body
    assert "Reviewed by: asmith" in body
