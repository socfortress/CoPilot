"""The notification outbox: delivery that survives a restart (`notifications/services/outbox.py`).

Before it, `emit()` scheduled the dispatch as an in-memory task, so a restart or a crash between
the caller's commit and the dispatch lost the notification. These tests pin what replaced it:

- the AI report and its outbox row commit together, and a rollback leaves neither;
- the drain dispatches through the real `dispatch_event` and marks the row `done`;
- a row whose immediate delivery never ran (a crash after the commit) is delivered by the sweep;
- a row left `processing` past its lease returns to `pending`, without re-sending what was sent;
- transient failures back off and end `dead`; permanent ones are settled, not retried;
- a partial fan-out retries only the route that failed;
- two concurrent claims or drains take a row once;
- `emit()` never raises, and falls back to the old direct dispatch when the outbox is unavailable.

A real SQLite database in a file, each session on its own connection (`NullPool`), so commits,
rollbacks and the guarded claims run as separate transactions. MySQL's row locking under
`UPDATE … WHERE status='pending'` is exercised by `tests/e2e/notification_outbox_mysql_e2e.py`.

The providers are a fake channel (`FakeChannel`) behind the real dispatch loop and dispatch log;
the failure texts it returns are pinned against the real dispatchers in the classification tests.

Run with: cd backend && python -m pytest tests/test_notification_outbox.py
"""

import asyncio
import json
import os
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from loguru import logger  # noqa: E402
from sqlalchemy import func  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.dialects.mysql import LONGTEXT  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.notifications.services.emit as emit_module  # noqa: E402
import app.notifications.services.notifications as svc  # noqa: E402
from app.ai_analyst.schema.ai_analyst import SubmitReportRequest  # noqa: E402
from app.ai_analyst.services import ai_analyst as ai_svc  # noqa: E402
from app.db.universal_models import AiAnalystJob  # noqa: E402
from app.db.universal_models import AiAnalystReport  # noqa: E402
from app.db.universal_models import CustomerNotificationRoute  # noqa: E402
from app.db.universal_models import NotificationDispatchLog  # noqa: E402
from app.db.universal_models import NotificationOutbox  # noqa: E402
from app.notifications.channels import SendResult  # noqa: E402
from app.notifications.schema.events import EntityType  # noqa: E402
from app.notifications.schema.events import NotificationEvent  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services import dispatchers  # noqa: E402
from app.notifications.services import outbox  # noqa: E402


@compiles(LONGTEXT, "sqlite")
def _longtext_on_sqlite(type_, compiler, **kw):
    """`ai_analyst_report.report_markdown` is MySQL's LONGTEXT; SQLite stores it as TEXT."""
    return "TEXT"


CC = "TENANT_A"
#: The fake clock starts at the real one: the dispatch log's inserts take `dispatched_at` from
#: the model's own default (real `utcnow()`), so the two must agree until a test moves time on.
T0 = datetime.utcnow().replace(microsecond=0)
NO_JITTER = outbox.OutboxSettings(jitter=0.0)

TABLES = [
    "customers",
    "customer_shuffle_integration",
    "customer_notification_route",
    "notification_dispatch_log",
    "notification_outbox",
    "ai_analyst_job",
    "ai_analyst_report",
    "ai_analyst_ioc",
    "ai_analyst_review",
    "ai_analyst_ioc_review",
]


class Clock:
    """What `outbox._now` returns, and the dispatch log's `datetime.utcnow()`: moved by hand,
    whole seconds like MySQL's DATETIME. One clock, so "sent since the row was created" compares
    like with like."""

    def __init__(self, at=T0):
        self.at = at

    def __call__(self):
        return self.at

    def advance(self, **kw):
        self.at = self.at + timedelta(**kw)


class FakeChannel:
    """Every route's provider. `script[name]` is the results its sends return, in order (the last
    one repeats); a route with no script is sent. `delay` stretches each send so concurrent
    drains overlap."""

    key = "webhook"

    def __init__(self):
        self.script = {}
        self.sent = []
        self.delivery_ids = []
        self.delay = 0.0

    async def send(self, *, route, event, message, ctx):
        name = route.name  # before any await: the row may expire after one
        self.delivery_ids.append(ctx.delivery_id)
        if self.delay:
            await asyncio.sleep(self.delay)
        results = self.script.get(name) or [SendResult(status="sent", latency_ms=1)]
        result = results.pop(0) if len(results) > 1 else results[0]
        if result.status == "sent":
            self.sent.append((name, event.dedupe_key))
        return result

    async def after_send(self, *, route, result, ctx):
        return None

    def count(self, name):
        return sum(1 for sent_name, _ in self.sent if sent_name == name)


def failed(message):
    return SendResult(status="failed", error_message=message, latency_ms=1)


class Harness:
    def __init__(self, path, monkeypatch, *, tables=TABLES):
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.tables = tables
        self.channel = FakeChannel()
        self.clock = Clock()
        self.kicked = []
        monkeypatch.setattr(outbox, "new_session", self.sessions)
        monkeypatch.setattr(outbox, "_now", self.clock)
        clock = self.clock

        class _Datetime(datetime):
            @classmethod
            def utcnow(cls):
                return clock()

        monkeypatch.setattr(svc, "datetime", _Datetime)
        monkeypatch.setattr(svc, "get_channel", lambda channel: self.channel)

    async def create(self):
        tables = [SQLModel.metadata.tables[t] for t in self.tables]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self

    async def add_route(self, name, *, trigger="alert_created", scope="customer", customer_code=CC):
        async with self.sessions() as session:
            route = CustomerNotificationRoute(
                name=name,
                scope=scope,
                customer_code=customer_code if scope == "customer" else None,
                trigger=trigger,
                channel="webhook",
                destination="",
                enabled=True,
                min_severity="Informational",
                recipient_mode="static",
                config="{}",
                created_at=T0,
                created_by="admin",
            )
            session.add(route)
            await session.commit()
            return route.id

    async def rows(self):
        async with self.sessions() as session:
            return (await session.execute(select(NotificationOutbox).order_by(NotificationOutbox.id))).scalars().all()

    async def row(self):
        rows = await self.rows()
        assert len(rows) == 1, rows
        return rows[0]

    async def log(self):
        async with self.sessions() as session:
            result = await session.execute(select(NotificationDispatchLog).order_by(NotificationDispatchLog.route_id))
            return result.scalars().all()

    async def dispose(self):
        await self.engine.dispose()


def run(tmp_path, monkeypatch, scenario, **kw):
    async def inner():
        harness = await Harness(tmp_path / "outbox.db", monkeypatch, **kw).create()
        try:
            return await scenario(harness)
        finally:
            await harness.dispose()

    return asyncio.run(inner())


def _event(key="alert:14:alert_created", summary="A new alert was created.", trigger=NotificationTrigger.ALERT_CREATED):
    return NotificationEvent(
        customer_code=CC,
        trigger=trigger,
        severity=NotificationSeverity.HIGH,
        subject="Administrators Group Changed",
        summary=summary,
        entity_type=EntityType.ALERT,
        entity_id=14,
        dedupe_key=key,
        context={"alert_name": "Administrators Group Changed"},
    )


@pytest.fixture
def errors():
    """Every loguru ERROR record a test's code writes."""
    records = []
    sink = logger.add(lambda message: records.append(message.record["message"]), level="ERROR")
    yield records
    logger.remove(sink)


# ── the AI report and its notification commit together ───────────────────────


JOB = "copilot-inv-14-1"


def _report_request(job_id=JOB):
    return SubmitReportRequest(
        job_id=job_id,
        alert_id=14,
        customer_code=CC,
        severity_assessment="High",
        summary="Credential dumping observed.",
        report_markdown="# Report",
        recommended_actions="Isolate the host.",
    )


async def _seed_job(h):
    async with h.sessions() as session:
        session.add(AiAnalystJob(id=JOB, alert_id=14, customer_code=CC, triggered_by="webhook", created_at=T0))
        await session.commit()


def _patch_ai_path(monkeypatch, h, display=None):
    emitted = []
    monkeypatch.setattr(ai_svc.outbox, "kick", lambda event: h.kicked.append(event))
    monkeypatch.setattr(ai_svc, "emit", lambda event: emitted.append(event))

    async def fields(alert_id, session):
        if display is not None:
            await display(session)
        return ("Administrators Group Changed", "WIN-DC01")

    monkeypatch.setattr(ai_svc, "_alert_display_fields", fields)
    return emitted


def test_a_report_and_its_notification_commit_together(tmp_path, monkeypatch):
    async def scenario(h):
        await _seed_job(h)
        emitted = _patch_ai_path(monkeypatch, h)
        async with h.sessions() as session:
            response = await ai_svc.submit_report(_report_request(), session)
        async with h.sessions() as session:
            reports = (await session.execute(select(AiAnalystReport))).scalars().all()
        return response, reports, await h.rows(), emitted

    response, reports, rows, emitted = run(tmp_path, monkeypatch, scenario)
    assert response.success and len(reports) == 1
    assert len(rows) == 1
    row = rows[0]
    assert (row.status, row.attempts, row.queued_key) == ("pending", 0, "alert:14:investigation_complete")
    event = NotificationEvent.model_validate_json(row.event_json)
    assert event.trigger == NotificationTrigger.INVESTIGATION_COMPLETE
    assert (event.summary, event.context["asset_name"]) == ("Credential dumping observed.", "WIN-DC01")
    assert emitted == [], "queued in the report's transaction, so no fallback emit"


def test_the_kick_follows_the_commit(tmp_path, monkeypatch):
    async def scenario(h):
        await _seed_job(h)
        _patch_ai_path(monkeypatch, h)
        async with h.sessions() as session:
            await ai_svc.submit_report(_report_request(), session)
        return h.kicked

    kicked = run(tmp_path, monkeypatch, scenario)
    assert [e.dedupe_key for e in kicked] == ["alert:14:investigation_complete"]


def test_a_report_that_loses_the_race_leaves_no_notification(tmp_path, monkeypatch):
    """Another writer files the job's report between the pre-check and the commit: the unique index
    refuses ours, the 409 is unchanged, and the rollback takes our outbox row with it."""

    # MySQL's duplicate-key message names the index (`uq_ai_analyst_report_job_id`), which is what
    # the route recognises; SQLite's names the column instead.
    monkeypatch.setattr(ai_svc, "REPORT_JOB_UNIQUE", "ai_analyst_report.job_id")

    async def scenario(h):
        await _seed_job(h)

        async def racing_writer(_session):
            async with h.sessions() as other:
                other.add(AiAnalystReport(job_id=JOB, alert_id=14, customer_code=CC, summary="theirs", created_at=T0))
                await other.commit()

        emitted = _patch_ai_path(monkeypatch, h, display=racing_writer)
        async with h.sessions() as session:
            with pytest.raises(HTTPException) as refused:
                await ai_svc.submit_report(_report_request(), session)
        async with h.sessions() as session:
            summaries = (await session.execute(select(AiAnalystReport.summary))).scalars().all()
        return refused.value, summaries, await h.rows(), emitted

    refused, summaries, rows, emitted = run(tmp_path, monkeypatch, scenario)
    assert refused.status_code == 409
    assert summaries == ["theirs"]
    assert rows == [], "the rollback must take the outbox row with the report"
    assert emitted == []


def test_without_the_outbox_the_report_still_commits_and_emits(tmp_path, monkeypatch):
    """An outbox that can't be written to (here: no table) never costs the report: it commits and
    the notification falls back to `emit()`, durable but not atomic."""

    async def scenario(h):
        await _seed_job(h)
        emitted = _patch_ai_path(monkeypatch, h)
        async with h.sessions() as session:
            response = await ai_svc.submit_report(_report_request(), session)
        async with h.sessions() as session:
            reports = (await session.execute(select(AiAnalystReport))).scalars().all()
        return response, reports, emitted

    tables = [t for t in TABLES if t != "notification_outbox"]
    response, reports, emitted = run(tmp_path, monkeypatch, scenario, tables=tables)
    assert response.success and len(reports) == 1
    assert [e.dedupe_key for e in emitted] == ["alert:14:investigation_complete"]


def test_a_review_and_its_notification_commit_together_and_an_edit_queues_nothing(tmp_path, monkeypatch):
    from app.ai_analyst.schema.ai_analyst import SubmitReviewRequest

    async def scenario(h):
        await _seed_job(h)
        emitted = _patch_ai_path(monkeypatch, h)

        async def username(user_id, session):
            return "asmith"

        monkeypatch.setattr(ai_svc, "_username_for", username)
        async with h.sessions() as session:
            report = AiAnalystReport(job_id=JOB, alert_id=14, customer_code=CC, summary="s", severity_assessment="High", created_at=T0)
            session.add(report)
            await session.commit()
            report_id = report.id
        async with h.sessions() as session:
            await ai_svc.submit_review(report_id, SubmitReviewRequest(overall_verdict="up"), 3, session)
        after_create = await h.rows()
        async with h.sessions() as session:
            await ai_svc.submit_review(report_id, SubmitReviewRequest(overall_verdict="down"), 3, session)
        return after_create, await h.rows(), h.kicked, emitted

    after_create, after_edit, kicked, emitted = run(tmp_path, monkeypatch, scenario)
    assert len(after_create) == 1
    event = NotificationEvent.model_validate_json(after_create[0].event_json)
    assert (event.trigger, event.actor_username) == (NotificationTrigger.AI_REPORT_REVIEWED, "asmith")
    assert len(after_edit) == 1, "revising one's own review is not a new sign-off"
    assert [e.dedupe_key for e in kicked] == ["alert:14:ai_report_reviewed"]
    assert emitted == []


def test_a_case_task_assignment_is_queued_before_its_commit_and_kicked_after():
    from unittest.mock import AsyncMock
    from unittest.mock import MagicMock
    from unittest.mock import patch

    import app.incidents.services.case_tasks as tasks
    from app.incidents.schema.case_templates import CaseTaskUpdate

    order = []
    task = SimpleNamespace(
        id=7,
        case_id=3,
        alert_id=None,
        template_task_id=None,
        title="Contain the host",
        description=None,
        guidelines=None,
        mandatory=False,
        order_index=0,
        status="TODO",
        evidence_comment=None,
        assigned_to=None,
        completed_by=None,
        completed_at=None,
        created_by="system",
        created_at=T0,
        updated_at=T0,
    )
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = task
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.commit = AsyncMock(side_effect=lambda: order.append("commit"))

    async def enqueue(event, s):
        order.append(("enqueue", event.dedupe_key, s is session))
        return True

    with (
        patch.object(tasks, "select_all_users", AsyncMock(return_value=[SimpleNamespace(username="analyst_two")])),
        patch("app.incidents.services.case_events.emit_case_event", AsyncMock()),
        patch.object(outbox, "enqueue", enqueue),
        patch.object(outbox, "kick", lambda event: order.append(("kick", event.dedupe_key))),
    ):
        response = asyncio.run(tasks.update_case_task(7, CaseTaskUpdate(assigned_to="analyst_two"), "analyst_one", session))

    assert response.success is True
    key = "case_task:7:case_task_assigned:analyst_two"
    assert order == [("enqueue", key, True), "commit", ("kick", key)]


# ── the drain ────────────────────────────────────────────────────────────────


def test_the_drain_dispatches_and_marks_done(tmp_path, monkeypatch):
    async def scenario(h):
        route = await h.add_route("SOC webhook")
        assert await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        return route, await h.row(), await h.log(), h.channel.sent

    route, row, log, sent = run(tmp_path, monkeypatch, scenario)
    assert sent == [("SOC webhook", "alert:14:alert_created")]
    assert (row.status, row.attempts, row.queued_key, row.last_error) == ("done", 1, None, None)
    assert json.loads(row.route_outcomes) == {str(route): "sent"}
    assert [(entry.route_id, entry.status) for entry in log] == [(route, "sent")]


def test_a_trigger_nobody_routes_is_done_with_nothing_sent(tmp_path, monkeypatch):
    async def scenario(h):
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        return await h.row(), h.channel.sent

    row, sent = run(tmp_path, monkeypatch, scenario)
    assert (row.status, sent) == ("done", [])


def test_a_crash_after_the_commit_is_delivered_by_the_sweep(tmp_path, monkeypatch):
    """The caller committed its write and the outbox row, then CoPilot stopped before the kick ran.
    Nothing in memory survives that; the row does, and the scheduler's sweep delivers it."""

    async def scenario(h):
        await h.add_route("SOC webhook")
        async with h.sessions() as session:
            assert await outbox.enqueue(_event(), session)
            await session.commit()
        # …the process dies here: no kick. On restart, the sweep:
        before = list(h.channel.sent)
        counts = await outbox.drain(NO_JITTER)
        return before, counts, await h.row(), h.channel.sent

    before, counts, row, sent = run(tmp_path, monkeypatch, scenario)
    assert before == []
    assert counts["done"] == 1 and row.status == "done"
    assert sent == [("SOC webhook", "alert:14:alert_created")]


def test_an_emit_whose_delivery_never_ran_is_delivered_by_the_sweep(tmp_path, monkeypatch):
    """`emit()` queued the row, then its immediate delivery died (here: raised before claiming)."""

    async def scenario(h):
        await h.add_route("SOC webhook")

        async def dies(key, settings=None):
            raise RuntimeError("process stopped")

        monkeypatch.setattr(outbox, "drain_key", dies)
        emit_module.emit(_event())
        await asyncio.gather(*list(emit_module._IN_FLIGHT), return_exceptions=True)
        queued = await h.row()
        await outbox.drain(NO_JITTER)
        return queued, await h.row(), h.channel.sent

    queued, row, sent = run(tmp_path, monkeypatch, scenario)
    assert queued.status == "pending"
    assert row.status == "done"
    assert sent == [("SOC webhook", "alert:14:alert_created")]


def test_a_rolled_back_enqueue_leaves_nothing(tmp_path, monkeypatch):
    async def scenario(h):
        async with h.sessions() as session:
            assert await outbox.enqueue(_event(), session)
            await session.rollback()
        return await h.rows()

    assert run(tmp_path, monkeypatch, scenario) == []


# ── one queued row per key ───────────────────────────────────────────────────


def test_a_key_still_queued_takes_the_newer_event(tmp_path, monkeypatch):
    async def scenario(h):
        await outbox.queue(_event(summary="first"))
        async with h.sessions() as session:
            assert await outbox.enqueue(_event(summary="second"), session)
            await session.commit()
        return await h.rows()

    rows = run(tmp_path, monkeypatch, scenario)
    assert len(rows) == 1
    assert NotificationEvent.model_validate_json(rows[0].event_json).summary == "second"


def test_once_delivery_started_the_key_can_be_queued_again(tmp_path, monkeypatch):
    """A → B → A: the second assignment to A is news, as it was before the outbox."""

    async def scenario(h):
        await h.add_route("SOC webhook")
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        return await h.rows(), h.channel.count("SOC webhook")

    rows, sends = run(tmp_path, monkeypatch, scenario)
    assert [r.status for r in rows] == ["done", "done"]
    assert sends == 2


def test_different_keys_queue_apart(tmp_path, monkeypatch):
    async def scenario(h):
        await outbox.queue(_event(key="test:1:a"))
        await outbox.queue(_event(key="test:1:b"))
        return await h.rows()

    assert len(run(tmp_path, monkeypatch, scenario)) == 2


# ── failures: what is retried, and how ───────────────────────────────────────


def test_a_partial_fan_out_retries_only_the_failed_route(tmp_path, monkeypatch):
    async def scenario(h):
        teams = await h.add_route("Teams")
        webhook = await h.add_route("Webhook")
        h.channel.script["Webhook"] = [failed("Webhook returned 503: upstream unavailable"), SendResult(status="sent")]
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        first = await h.row()
        h.clock.advance(minutes=2)
        await outbox.drain(NO_JITTER)
        return teams, webhook, first, await h.row(), await h.log(), h.channel

    teams, webhook, first, row, log, channel = run(tmp_path, monkeypatch, scenario)
    assert (first.status, first.attempts) == ("pending", 1)
    assert json.loads(first.route_outcomes) == {str(teams): "sent"}
    assert first.next_attempt_at == T0 + timedelta(seconds=90)
    assert f"route {webhook}: Webhook returned 503" in first.last_error
    assert (row.status, row.attempts) == ("done", 2)
    assert channel.count("Teams") == 1, "the route that was sent is not sent again"
    assert channel.count("Webhook") == 1
    assert sorted((entry.route_id, entry.status) for entry in log) == [(teams, "sent"), (webhook, "sent")]


def test_transient_failures_back_off_then_die(tmp_path, monkeypatch, errors):
    settings = outbox.OutboxSettings(jitter=0.0, max_attempts=3)

    async def scenario(h):
        await h.add_route("Webhook")
        h.channel.script["Webhook"] = [failed("ConnectTimeout: timed out")]
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", settings)
        seen = [await h.row()]
        h.clock.advance(seconds=89)
        assert (await outbox.drain(settings))["pending"] == 0, "not due yet"
        h.clock.advance(seconds=1)
        await outbox.drain(settings)
        seen.append(await h.row())
        h.clock.advance(seconds=360)
        await outbox.drain(settings)
        seen.append(await h.row())
        h.clock.advance(days=2)
        await outbox.drain(settings)
        seen.append(await h.row())
        return seen

    seen = run(tmp_path, monkeypatch, scenario)
    assert [(r.status, r.attempts) for r in seen] == [("pending", 1), ("pending", 2), ("dead", 3), ("dead", 3)]
    assert seen[0].next_attempt_at == T0 + timedelta(seconds=90)
    assert seen[1].next_attempt_at == T0 + timedelta(seconds=90 + 360)
    assert "ConnectTimeout" in seen[2].last_error
    assert any("is dead after 3 attempt(s)" in message for message in errors)


def test_the_default_policy_spans_about_a_day():
    policy = outbox.OutboxSettings()
    waits = [policy.backoff(k, rng=lambda low, high: 1.0).total_seconds() for k in range(1, policy.max_attempts)]
    assert waits[:4] == [90, 360, 1440, 5760]
    assert max(waits) == 8 * 3600
    assert 22 * 3600 < sum(waits) < 27 * 3600
    jittered = policy.backoff(2, rng=lambda low, high: high).total_seconds()
    assert jittered == pytest.approx(360 * 1.2)


@pytest.mark.parametrize(
    "result",
    [
        failed("Resend returned 403: The example.com domain is not verified."),
        failed("Webhook returned 404: Not Found"),
        failed("Invalid webhook config: url is required"),
        failed("Resend connector is configured but has no API key set."),
        SendResult.skipped("Shuffle integration is disabled"),
    ],
)
def test_permanent_outcomes_are_settled_not_retried(tmp_path, monkeypatch, result):
    async def scenario(h):
        await h.add_route("Webhook")
        h.channel.script["Webhook"] = [result]
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        return await h.row()

    row = run(tmp_path, monkeypatch, scenario)
    assert (row.status, row.attempts) == ("done", 1)
    assert list(json.loads(row.route_outcomes).values()) == [result.status]


def test_the_ai_report_switch_is_a_skip_not_a_retry(tmp_path, monkeypatch):
    async def scenario(h):
        await h.add_route("Customer email", trigger="investigation_complete")

        async def off(trigger, customer_code, session):
            return False

        monkeypatch.setattr(svc, "_ai_reports_permitted", off)
        await outbox.queue(_event(key="alert:14:investigation_complete", trigger=NotificationTrigger.INVESTIGATION_COMPLETE))
        await outbox.drain_key("alert:14:investigation_complete", NO_JITTER)
        return await h.row(), h.channel.sent

    row, sent = run(tmp_path, monkeypatch, scenario)
    assert row.status == "done" and sent == []


def test_a_dispatch_that_raises_is_retried(tmp_path, monkeypatch, errors):
    async def scenario(h):
        await h.add_route("Webhook")
        calls = []
        real = svc.routes_for_event

        async def flaky(event, session):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("database went away")
            return await real(event, session)

        monkeypatch.setattr(svc, "routes_for_event", flaky)
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        first = await h.row()
        h.clock.advance(minutes=2)
        await outbox.drain(NO_JITTER)
        return first, await h.row(), h.channel.sent

    first, row, sent = run(tmp_path, monkeypatch, scenario)
    assert (first.status, first.attempts) == ("pending", 1)
    assert "RuntimeError" in first.last_error
    assert row.status == "done" and len(sent) == 1
    assert any("database went away" in message for message in errors)


def test_a_dispatch_that_times_out_keeps_what_it_sent(tmp_path, monkeypatch):
    """The first route was delivered, then the attempt hung and was abandoned: the retry finds that
    route `sent` in the dispatch log since the claim and doesn't send it again."""

    async def scenario(h):
        await h.add_route("Fast")
        await h.add_route("Hangs")
        hang = asyncio.Event()

        class Hanging(FakeChannel):
            async def send(self, *, route, event, message, ctx):
                if route.name == "Hangs" and not hang.is_set():
                    hang.set()
                    await asyncio.sleep(10)
                return await super().send(route=route, event=event, message=message, ctx=ctx)

        h.channel = Hanging()
        monkeypatch.setattr(svc, "get_channel", lambda channel: h.channel)
        settings = outbox.OutboxSettings(jitter=0.0, dispatch_timeout_seconds=0.5)
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", settings)
        first = await h.row()
        h.clock.advance(minutes=2)
        await outbox.drain(settings)
        return first, await h.row(), h.channel

    first, row, channel = run(tmp_path, monkeypatch, scenario)
    assert (first.status, first.attempts) == ("pending", 1)
    assert "timed out" in first.last_error
    assert row.status == "done"
    assert (channel.count("Fast"), channel.count("Hangs")) == (1, 1)


def test_an_unreadable_row_is_dead_at_once(tmp_path, monkeypatch, errors):
    async def scenario(h):
        await outbox.queue(_event())
        async with h.sessions() as session:
            await session.execute(update(NotificationOutbox).values(event_json="{not json"))
            await session.commit()
        await outbox.drain(NO_JITTER)
        return await h.row()

    row = run(tmp_path, monkeypatch, scenario)
    assert (row.status, row.attempts) == ("dead", 1)
    assert errors


# ── leases ───────────────────────────────────────────────────────────────────


def test_an_expired_lease_returns_the_row_without_resending(tmp_path, monkeypatch):
    """A worker claimed the row, delivered route A, and died before recording anything."""

    async def scenario(h):
        a = await h.add_route("A")
        b = await h.add_route("B")
        await outbox.queue(_event())
        async with h.sessions() as session:
            row_id = (await session.execute(select(NotificationOutbox.id))).scalar_one()
        claim = await outbox._claim(row_id, h.clock())
        # What the dead worker managed: route A's send and its log row.
        async with h.sessions() as session:
            session.add(
                NotificationDispatchLog(
                    customer_code=CC,
                    alert_id=14,
                    entity_type="alert",
                    entity_id=14,
                    dedupe_key="alert:14:alert_created",
                    route_id=a,
                    trigger="alert_created",
                    status="sent",
                    dispatched_at=h.clock() + timedelta(seconds=1),
                ),
            )
            await session.commit()
        h.clock.advance(seconds=120)
        early = await outbox.drain(NO_JITTER)
        h.clock.advance(seconds=300)
        late = await outbox.drain(NO_JITTER)
        recovered = await h.row()
        h.clock.advance(seconds=600)
        await outbox.drain(NO_JITTER)
        return claim, early, late, recovered, await h.row(), h.channel, (a, b)

    claim, early, late, recovered, row, channel, (a, b) = run(tmp_path, monkeypatch, scenario)
    assert claim is not None and claim.attempts == 1
    assert early["recovered"] == 0, "within the lease: still the other worker's"
    assert late["recovered"] == 1
    assert (recovered.status, recovered.claimed_by) == ("pending", None)
    assert json.loads(recovered.route_outcomes) == {str(a): "sent"}
    assert (row.status, row.attempts) == ("done", 2)
    assert (channel.count("A"), channel.count("B")) == (0, 1)


def test_a_worker_whose_lease_was_taken_over_cannot_overwrite(tmp_path, monkeypatch):
    async def scenario(h):
        await outbox.queue(_event())
        async with h.sessions() as session:
            row_id = (await session.execute(select(NotificationOutbox.id))).scalar_one()
        stale = await outbox._claim(row_id, h.clock())
        async with h.sessions() as session:
            await session.execute(update(NotificationOutbox).values(attempts=2, claimed_by="other-host:1"))
            await session.commit()
        written = await outbox._finish(stale, status="done")
        return written, await h.row()

    written, row = run(tmp_path, monkeypatch, scenario)
    assert written is False
    assert (row.status, row.claimed_by) == ("processing", "other-host:1")


def test_the_lease_always_outlasts_a_dispatch():
    assert outbox.OutboxSettings(lease_seconds=10, dispatch_timeout_seconds=60).effective_lease_seconds == 120


# ── concurrency ──────────────────────────────────────────────────────────────


def test_two_claims_of_one_row_take_it_once(tmp_path, monkeypatch):
    async def scenario(h):
        await outbox.queue(_event())
        async with h.sessions() as session:
            row_id = (await session.execute(select(NotificationOutbox.id))).scalar_one()
        claims = await asyncio.gather(*(outbox._claim(row_id, h.clock()) for _ in range(4)))
        return claims, await h.row()

    claims, row = run(tmp_path, monkeypatch, scenario)
    assert sum(claim is not None for claim in claims) == 1
    assert (row.status, row.attempts) == ("processing", 1)


def test_two_concurrent_drains_send_each_notification_once(tmp_path, monkeypatch):
    async def scenario(h):
        await h.add_route("Webhook")
        h.channel.delay = 0.05
        async with h.sessions() as session:
            for n in range(5):
                await outbox.enqueue(_event(key=f"alert:{n}:alert_created"), session)
            await session.commit()
        await asyncio.gather(outbox.drain(NO_JITTER), outbox.drain(NO_JITTER), outbox.drain_key("alert:3:alert_created", NO_JITTER))
        return await h.rows(), h.channel.sent

    rows, sent = run(tmp_path, monkeypatch, scenario)
    assert [r.status for r in rows] == ["done"] * 5
    assert sorted(key for _, key in sent) == sorted(f"alert:{n}:alert_created" for n in range(5))


# ── emit() ───────────────────────────────────────────────────────────────────


def test_emit_queues_then_delivers(tmp_path, monkeypatch):
    async def scenario(h):
        await h.add_route("SOC webhook")
        emit_module.emit(_event())
        await asyncio.gather(*list(emit_module._IN_FLIGHT))
        return await h.row(), h.channel.sent

    row, sent = run(tmp_path, monkeypatch, scenario)
    assert row.status == "done"
    assert sent == [("SOC webhook", "alert:14:alert_created")]


def test_emit_never_raises_and_falls_back_when_the_outbox_is_down(monkeypatch, errors):
    direct = []

    class Broken:
        async def __aenter__(self):
            raise ConnectionRefusedError("MySQL is down")

        async def __aexit__(self, *exc):
            return False

    async def direct_dispatch(event):
        direct.append(event.dedupe_key)

    monkeypatch.setattr(outbox, "new_session", Broken)
    monkeypatch.setattr(emit_module, "_run", direct_dispatch)

    async def scenario():
        assert emit_module.emit(_event()) is None
        await asyncio.gather(*list(emit_module._IN_FLIGHT))

    asyncio.run(scenario())
    assert direct == ["alert:14:alert_created"]
    assert any("could not queue" in message for message in errors)
    assert any("dispatching directly, without retries" in message for message in errors)


def test_emit_without_a_running_loop_is_a_no_op():
    assert emit_module.emit(_event()) is None


def test_enqueue_never_raises(errors):
    session = SimpleNamespace(no_autoflush=None)
    assert asyncio.run(outbox.enqueue(_event(), session)) is False
    assert errors


def test_kick_without_a_running_loop_is_a_no_op():
    assert outbox.kick(_event()) is None


# ── retention and visibility ─────────────────────────────────────────────────


def test_prune_keeps_dead_rows_longer_and_pending_ones_always(tmp_path, monkeypatch):
    async def scenario(h):
        async with h.sessions() as session:
            for key, status, age in (
                ("done-new", "done", 6),
                ("done-old", "done", 8),
                ("dead-new", "dead", 29),
                ("dead-old", "dead", 31),
                ("pending-old", "pending", 90),
            ):
                at = T0 - timedelta(days=age)
                session.add(
                    NotificationOutbox(
                        event_json="{}",
                        dedupe_key=key,
                        trigger="alert_created",
                        status=status,
                        next_attempt_at=at,
                        created_at=at,
                        updated_at=at,
                    ),
                )
            await session.commit()
        deleted = await outbox.prune(outbox.OutboxSettings())
        return deleted, sorted(r.dedupe_key for r in await h.rows())

    deleted, left = run(tmp_path, monkeypatch, scenario)
    assert deleted == {"done": 1, "dead": 1}
    assert left == ["dead-new", "done-new", "pending-old"]


def test_summary_counts_one_customers_waiting_and_dead_rows(tmp_path, monkeypatch):
    async def scenario(h):
        async with h.sessions() as session:
            for key, status, customer, age in (
                ("a", "pending", CC, 30),
                ("b", "pending", CC, 600),
                ("c", "processing", CC, 5),
                ("d", "dead", CC, 9000),
                ("e", "done", CC, 1),
                ("f", "pending", "TENANT_B", 99999),
            ):
                at = T0 - timedelta(seconds=age)
                session.add(
                    NotificationOutbox(
                        event_json="{}",
                        dedupe_key=key,
                        customer_code=customer,
                        trigger="alert_created",
                        status=status,
                        next_attempt_at=at,
                        created_at=at,
                        updated_at=at,
                    ),
                )
            await session.commit()
        async with h.sessions() as session:
            return await outbox.summary(CC, session, now=T0), await outbox.summary("TENANT_C", session, now=T0)

    mine, empty = run(tmp_path, monkeypatch, scenario)
    assert mine == {"pending": 2, "processing": 1, "dead": 1, "oldest_pending_age_seconds": 600}
    assert empty == {"pending": 0, "processing": 0, "dead": 0, "oldest_pending_age_seconds": None}


def test_last_error_never_keeps_a_url_or_a_credential():
    text = "Teams returned 400: https://acme.webhook.office.com/webhookb2/abc@def/IncomingWebhook/123/xyz Authorization: Bearer sk_live_1"
    cleaned = outbox.safe_error(text)
    assert "office.com" not in cleaned and "sk_live_1" not in cleaned
    assert cleaned == "Teams returned 400: <url> Authorization: Bearer <redacted>"
    assert outbox.safe_error("api_key=abc123 password: hunter2") == "api_key=<redacted> password: <redacted>"
    assert len(outbox.safe_error("x" * 5000)) == 1000


# ── what counts as transient, against the dispatchers' own texts ─────────────


def _client_with(handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    return factory


def _status(code, body="{}"):
    return lambda request: httpx.Response(code, text=body)


def _raises(exc):
    def handler(request):
        raise exc

    return handler


async def _webhook():
    return await dispatchers.dispatch_webhook(url="https://hooks.invalid/x", method="POST", headers=None, structured_payload={"a": 1})


async def _teams():
    return await dispatchers.dispatch_teams(webhook_url="https://teams.invalid/x", card={})


async def _resend():
    return await dispatchers.dispatch_resend(
        base_url="https://resend.invalid",
        api_key="re_key",
        from_address="soc@example.com",
        to=["a@example.com"],
        subject="s",
        text_body="b",
    )


@pytest.mark.parametrize(
    "send, handler, transient",
    [
        # Nothing can have been delivered: retried.
        (_webhook, _status(503), True),
        (_webhook, _status(429), True),
        (_webhook, _raises(httpx.ConnectError("refused")), True),
        (_webhook, _raises(httpx.ConnectTimeout("timed out")), True),
        (_webhook, _raises(httpx.PoolTimeout("no connection")), True),
        (_teams, _status(429), True),
        (_teams, _status(503), True),
        (_resend, _status(429, '{"message": "Too many requests"}'), True),
        (_resend, _status(503, '{"message": "Unavailable"}'), True),
        # The provider may have accepted it before the failure: final, never re-sent.
        (_webhook, _status(500), False),
        (_webhook, _status(502), False),
        (_webhook, _status(504), False),
        (_webhook, _status(408), False),
        (_webhook, _raises(httpx.ReadTimeout("timed out")), False),
        (_webhook, _raises(httpx.WriteTimeout("timed out")), False),
        (_webhook, _raises(httpx.RemoteProtocolError("peer closed")), False),
        (_webhook, _raises(httpx.ReadError("reset")), False),
        (_teams, _status(502), False),
        (_resend, _status(500, '{"message": "Internal error"}'), False),
        # Won't succeed by retrying.
        (_webhook, _status(404), False),
        (_webhook, _status(400), False),
        (_teams, _status(400), False),
        (_resend, _status(403, '{"message": "The example.com domain is not verified."}'), False),
        (_resend, _status(422, '{"message": "Invalid to field"}'), False),
        # A status quoted in a body never counts: only where dispatchers.py writes it.
        (_webhook, _status(400, "upstream returned 503: busy"), False),
        (_teams, _status(500, "Teams rate-limited this request (429)"), False),
    ],
)
def test_transient_failures_are_told_from_permanent_ones(monkeypatch, send, handler, transient):
    monkeypatch.setattr(dispatchers.httpx, "AsyncClient", _client_with(handler))
    status, message, _latency, _ref = asyncio.run(send())
    assert status == "failed"
    assert outbox.is_transient_failure(message) is transient, message


@pytest.mark.parametrize(
    "message, transient",
    [
        ("Dispatcher exception: KeyError: 'x'", False),
        ("Webhook returned 503: x; Template error: 'foo' is undefined", True),
        ("Shuffle returned 503: unavailable", True),
        ("Shuffle returned 502: bad gateway", False),
        ("gaierror: [Errno 8] nodename nor servname provided", True),
        ("Shuffle authentication failed (401): bad key", False),
        ("Shuffle returned non-JSON response", False),
        ("Shuffle reported failure: app not authenticated", False),
        ("Shuffle connector is not configured in CoPilot.", False),
        ("Assignee 'bob' has no email address on their account.", False),
        ("Unsupported channel: pager", False),
        ("No recipients resolved for this route.", False),
        (None, False),
        ("", False),
    ],
)
def test_classification_of_the_providers_other_texts(message, transient):
    assert outbox.is_transient_failure(message) is transient


def test_one_row_per_queued_key_is_enforced_by_the_database(tmp_path, monkeypatch):
    """The index itself, not just the upsert: a plain second insert of a queued key is refused."""
    from sqlalchemy.exc import IntegrityError

    async def scenario(h):
        await outbox.queue(_event())
        async with h.sessions() as session:
            session.add(NotificationOutbox(event_json="{}", dedupe_key="k", queued_key="alert:14:alert_created", trigger="t"))
            with pytest.raises(IntegrityError):
                await session.commit()
        async with h.sessions() as session:
            return (await session.execute(select(func.count()).select_from(NotificationOutbox))).scalar_one()

    assert run(tmp_path, monkeypatch, scenario) == 1


# ── review findings: internal events, isolation, progress, signatures ─────────


def _task_event():
    from app.notifications.services.event_builders import case_task_assigned_event

    return case_task_assigned_event(task_id=5, case_id=2, title="Contain the host", assignee="bob", actor="al")


def test_an_internal_event_reaches_each_of_two_internal_routes_once(tmp_path, monkeypatch):
    """The review's probe (H1). A case-task assignment carries no customer, the dispatch log's
    customer_code is NOT NULL: the log write failed after the first route's send, its rollback
    broke the second route, and every retry re-sent the first. Now each route gets it once."""

    async def scenario(h):
        first = await h.add_route("first", trigger="case_task_assigned", scope="internal")
        second = await h.add_route("second", trigger="case_task_assigned", scope="internal")
        event = _task_event()
        assert event.customer_code is None
        assert await outbox.queue(event)
        await outbox.drain_key(event.dedupe_key, NO_JITTER)
        for _ in range(12):
            h.clock.advance(hours=9)
            await outbox.drain(NO_JITTER)
        return (first, second), await h.row(), await h.log(), h.channel

    (first, second), row, log, channel = run(tmp_path, monkeypatch, scenario)
    assert (channel.count("first"), channel.count("second")) == (1, 1)
    assert (row.status, row.attempts) == ("done", 1)
    assert json.loads(row.route_outcomes) == {str(first): "sent", str(second): "sent"}
    assert sorted((entry.route_id, entry.status, entry.customer_code) for entry in log) == [(first, "sent", ""), (second, "sent", "")]


def test_dispatch_without_the_outbox_also_reaches_both_internal_routes(tmp_path, monkeypatch):
    async def scenario(h):
        await h.add_route("first", trigger="case_task_assigned", scope="internal")
        await h.add_route("second", trigger="case_task_assigned", scope="internal")
        async with h.sessions() as session:
            response = await svc.dispatch_event(_task_event(), session)
        return response, h.channel

    response, channel = run(tmp_path, monkeypatch, scenario)
    assert response.dispatched == 2
    assert (channel.count("first"), channel.count("second")) == (1, 1)


@pytest.mark.parametrize("expire_on_commit", [False, True])
def test_one_routes_rollback_cannot_break_the_next_route(tmp_path, monkeypatch, expire_on_commit):
    """A log write that rolls back (or a commit on an expire-on-commit session, the old emit()
    path's) used to expire every route still in the session; the next one's first attribute
    read was MissingGreenlet."""

    async def scenario(h):
        await h.add_route("first")
        await h.add_route("second")
        real = svc._record_log
        calls = []

        async def rolls_back_first(session, **kw):
            calls.append(kw["route_id"])
            if len(calls) == 1:
                await session.rollback()
                return True
            return await real(session, **kw)

        monkeypatch.setattr(svc, "_record_log", rolls_back_first)
        async with AsyncSession(h.engine, expire_on_commit=expire_on_commit) as session:
            response = await svc.dispatch_event(_event(), session)
        return response, h.channel

    response, channel = run(tmp_path, monkeypatch, scenario)
    assert (channel.count("first"), channel.count("second")) == (1, 1)
    assert response.dispatched == 2


def test_progress_is_kept_route_by_route_so_a_re_emission_does_not_resend(tmp_path, monkeypatch):
    """A re-emission of a key (A → B → A): the log's `sent` rows are the first emission's, so the
    log can't tell what this one delivered before its attempt timed out. The route outcomes,
    written as each route finished, can."""

    async def scenario(h):
        await h.add_route("A")
        await h.add_route("B")
        hang = {"armed": False}

        class Hanging(FakeChannel):
            async def send(self, *, route, event, message, ctx):
                if route.name == "B" and hang["armed"]:
                    hang["armed"] = False
                    await asyncio.sleep(10)
                return await super().send(route=route, event=event, message=message, ctx=ctx)

        h.channel = Hanging()
        monkeypatch.setattr(svc, "get_channel", lambda channel: h.channel)
        settings = outbox.OutboxSettings(jitter=0.0, dispatch_timeout_seconds=0.5)
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", settings)
        h.clock.advance(hours=1)
        hang["armed"] = True
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", settings)
        second = (await h.rows())[1]
        h.clock.advance(minutes=5)
        await outbox.drain(settings)
        return second, await h.rows(), h.channel

    second, rows, channel = run(tmp_path, monkeypatch, scenario)
    assert second.status == "pending" and "timed out" in second.last_error
    assert list(json.loads(second.route_outcomes).values()) == ["sent"], "A recorded, as sent, the moment it was sent"
    assert [r.status for r in rows] == ["done", "done"]
    assert (channel.count("A"), channel.count("B")) == (2, 2), "one each per emission"


def test_a_retry_skips_what_the_log_shows_sent_since_the_row_was_created(tmp_path, monkeypatch):
    """The attempt sent route A, B failed transiently, and then the database went away: neither
    the progress write nor the outcome reached the row (a crash, in effect). The lease sweep
    brings the row back, and the retry finds A in the dispatch log since the row's creation."""

    async def scenario(h):
        await h.add_route("A")
        await h.add_route("B")
        h.channel.script["B"] = [failed("ConnectError: [Errno 61] Connection refused"), SendResult(status="sent")]
        real_progress, real_finish = outbox._record_progress, outbox._finish

        async def lost(*args, **kwargs):
            raise ConnectionError("database went away")

        monkeypatch.setattr(outbox, "_record_progress", lost)
        monkeypatch.setattr(outbox, "_finish", lost)
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        stuck = await h.row()
        monkeypatch.setattr(outbox, "_record_progress", real_progress)
        monkeypatch.setattr(outbox, "_finish", real_finish)
        h.clock.advance(minutes=10)
        counts = await outbox.drain(NO_JITTER)
        h.clock.advance(minutes=10)
        await outbox.drain(NO_JITTER)
        return stuck, counts, await h.row(), h.channel

    stuck, counts, row, channel = run(tmp_path, monkeypatch, scenario)
    assert (stuck.status, stuck.route_outcomes) == ("processing", None)
    assert counts["recovered"] == 1
    assert (row.status, row.attempts) == ("done", 2)
    assert (channel.count("A"), channel.count("B")) == (1, 1), "A came from the log, B was retried"


def test_a_re_emission_is_delivered_again_even_after_a_failed_first_attempt(tmp_path, monkeypatch):
    """M2's other half: the earlier emission's `sent` row predates the new row, so it never
    stops the new one, on its first attempt or a retry."""

    async def scenario(h):
        await h.add_route("R")
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        h.clock.advance(hours=2)
        real = svc.routes_for_event
        calls = []

        async def fails_once(event, session):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("database went away")
            return await real(event, session)

        monkeypatch.setattr(svc, "routes_for_event", fails_once)
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        h.clock.advance(minutes=5)
        await outbox.drain(NO_JITTER)
        return await h.rows(), h.channel

    rows, channel = run(tmp_path, monkeypatch, scenario)
    assert [r.status for r in rows] == ["done", "done"]
    assert channel.count("R") == 2


def test_the_same_dispatch_error_twice_is_final(tmp_path, monkeypatch, errors):
    async def scenario(h):
        await h.add_route("R")

        async def broken(event, session):
            raise RuntimeError("schema mismatch")

        monkeypatch.setattr(svc, "routes_for_event", broken)
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        first = await h.row()
        h.clock.advance(minutes=5)
        await outbox.drain(NO_JITTER)
        return first, await h.row()

    first, row = run(tmp_path, monkeypatch, scenario)
    assert (first.status, first.attempts) == ("pending", 1)
    assert (row.status, row.attempts) == ("dead", 2)
    assert any("is dead after 2 attempt(s)" in message for message in errors)


def test_a_failure_that_may_have_delivered_is_settled_and_logged(tmp_path, monkeypatch):
    warnings = []
    sink = logger.add(lambda m: warnings.append(m.record["message"]), level="WARNING")
    try:

        async def scenario(h):
            await h.add_route("Webhook")
            h.channel.script["Webhook"] = [failed("ReadTimeout: The read operation timed out")]
            await outbox.queue(_event())
            await outbox.drain_key("alert:14:alert_created", NO_JITTER)
            return await h.row()

        row = run(tmp_path, monkeypatch, scenario)
    finally:
        logger.remove(sink)
    assert (row.status, row.attempts) == ("done", 1)
    assert any("is not retried" in message and "ReadTimeout" in message for message in warnings)


def test_each_delivery_tells_providers_its_outbox_row(tmp_path, monkeypatch):
    async def scenario(h):
        await h.add_route("R")
        await outbox.queue(_event())
        await outbox.drain_key("alert:14:alert_created", NO_JITTER)
        return await h.row(), h.channel.delivery_ids

    row, ids = run(tmp_path, monkeypatch, scenario)
    assert ids == [str(row.id)]


# ── M1: an error that aborted the caller's transaction is raised ─────────────


def _mysql_error(code, message="x"):
    import pymysql
    from sqlalchemy.exc import OperationalError

    return OperationalError("INSERT INTO notification_outbox …", {}, pymysql.err.OperationalError(code, message))


class _FailingSession:
    """Just enough of an AsyncSession for `enqueue`: the upsert raises `error`; a later
    `SELECT @@innodb_rollback_on_timeout` answers `rollback_on_timeout`."""

    def __init__(self, error, rollback_on_timeout=0, dialect="mysql"):
        from contextlib import nullcontext

        self.error = error
        self.rollback_on_timeout = rollback_on_timeout
        self.no_autoflush = nullcontext()
        self.dialect = dialect

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name=self.dialect))

    async def execute(self, statement, *args, **kwargs):
        if "innodb_rollback_on_timeout" in str(statement):
            return SimpleNamespace(scalar=lambda: self.rollback_on_timeout)
        raise self.error


@pytest.mark.parametrize(
    "error, rollback_on_timeout, raises",
    [
        (_mysql_error(1213, "Deadlock found when trying to get lock"), 0, True),
        (_mysql_error(1205, "Lock wait timeout exceeded"), 1, True),
        (_mysql_error(1205, "Lock wait timeout exceeded"), 0, False),
        (_mysql_error(1146, "Table 'copilot.notification_outbox' doesn't exist"), 0, False),
    ],
)
def test_enqueue_raises_only_what_aborted_the_transaction(error, rollback_on_timeout, raises, errors):
    from sqlalchemy.exc import OperationalError

    session = _FailingSession(error, rollback_on_timeout)
    if raises:
        with pytest.raises(OperationalError):
            asyncio.run(outbox.enqueue(_event(), session))
        assert any("aborted the caller's transaction" in message for message in errors)
    else:
        assert asyncio.run(outbox.enqueue(_event(), session)) is False


def test_a_lost_connection_is_raised():
    from sqlalchemy.exc import DBAPIError

    error = DBAPIError("INSERT …", {}, Exception("gone"), connection_invalidated=True)
    with pytest.raises(DBAPIError):
        asyncio.run(outbox.enqueue(_event(), _FailingSession(error)))


def test_a_review_whose_notification_deadlocks_is_not_written_and_not_notified(tmp_path, monkeypatch):
    from sqlalchemy.exc import OperationalError

    from app.ai_analyst.schema.ai_analyst import SubmitReviewRequest
    from app.db.universal_models import AiAnalystReview

    async def scenario(h):
        await _seed_job(h)
        emitted = _patch_ai_path(monkeypatch, h)

        async def username(user_id, session):
            return "asmith"

        async def deadlocks(event, session):
            raise _mysql_error(1213, "Deadlock found when trying to get lock")

        monkeypatch.setattr(ai_svc, "_username_for", username)
        monkeypatch.setattr(ai_svc.outbox, "enqueue", deadlocks)
        async with h.sessions() as session:
            report = AiAnalystReport(job_id=JOB, alert_id=14, customer_code=CC, summary="s", created_at=T0)
            session.add(report)
            await session.commit()
            report_id = report.id
        async with h.sessions() as session:
            with pytest.raises(OperationalError):
                await ai_svc.submit_review(report_id, SubmitReviewRequest(overall_verdict="up"), 3, session)
        async with h.sessions() as session:
            reviews = (await session.execute(select(AiAnalystReview))).scalars().all()
        return reviews, emitted, h.kicked

    reviews, emitted, kicked = run(tmp_path, monkeypatch, scenario)
    assert reviews == [] and emitted == [] and kicked == []


# ── Resend's idempotency key ─────────────────────────────────────────────────


def test_the_resend_idempotency_key_is_safe_bounded_and_per_delivery():
    from app.notifications.channels.resend import IDEMPOTENCY_KEY_MAX
    from app.notifications.channels.resend import idempotency_key

    key = idempotency_key("alert:14:investigation_complete", 3, "41")
    assert key == "alert:14:investigation_complete:3:41"
    assert idempotency_key("alert:14:investigation_complete", 3, "41") == key, "stable across a row's retries"
    assert idempotency_key("alert:14:investigation_complete", 3, "42") != key, "a re-emission is a new key"
    assert idempotency_key("case:1:case_assigned:Zoë Ångström", 3, "1") == "case:1:case_assigned:Zo___ngstr_m:3:1"
    long_a = idempotency_key("x" * 400 + "a", 3, "1")
    long_b = idempotency_key("x" * 400 + "b", 3, "1")
    assert len(long_a) == IDEMPOTENCY_KEY_MAX and long_a != long_b
    assert long_a.endswith(":3:1:" + long_a.rsplit(":", 1)[1])


def test_dispatch_resend_sends_the_key_only_when_given(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request.headers.get("Idempotency-Key"))
        return httpx.Response(200, json={"id": "msg_1"})

    monkeypatch.setattr(dispatchers.httpx, "AsyncClient", _client_with(handler))

    async def both():
        await _resend()
        await dispatchers.dispatch_resend(
            base_url="https://resend.invalid",
            api_key="re_key",
            from_address="soc@example.com",
            to=["a@example.com"],
            subject="s",
            text_body="b",
            idempotency_key="alert:14:x:3:41",
        )

    asyncio.run(both())
    assert seen == [None, "alert:14:x:3:41"]


# ── L1 and L3: the sweep's own robustness, and pruning ───────────────────────


def test_one_rows_failing_claim_does_not_stop_the_sweep(tmp_path, monkeypatch, errors):
    async def scenario(h):
        await h.add_route("R")
        await outbox.queue(_event(key="alert:1:alert_created"))
        await outbox.queue(_event(key="alert:2:alert_created"))
        real = outbox._claim
        calls = []

        async def first_deadlocks(row_id, due_by, **kw):
            calls.append(row_id)
            if len(calls) == 1:
                raise _mysql_error(1213, "Deadlock found")
            return await real(row_id, due_by, **kw)

        monkeypatch.setattr(outbox, "_claim", first_deadlocks)
        counts = await outbox.drain(NO_JITTER)
        return counts, [r.status for r in await h.rows()]

    counts, statuses = run(tmp_path, monkeypatch, scenario)
    assert counts["done"] == 1 and statuses == ["pending", "done"]
    assert any("the claim failed" in message for message in errors)


def test_backoff_never_overflows():
    assert outbox.OutboxSettings().backoff(10_000, rng=lambda low, high: 1.0) == timedelta(hours=8)


def test_prune_works_in_batches(tmp_path, monkeypatch):
    async def scenario(h):
        async with h.sessions() as session:
            for n in range(5):
                at = T0 - timedelta(days=9)
                session.add(
                    NotificationOutbox(
                        event_json="{}",
                        dedupe_key=f"old-{n}",
                        trigger="t",
                        status="done",
                        next_attempt_at=at,
                        created_at=at,
                        updated_at=at,
                    ),
                )
            await session.commit()
        deleted = await outbox.prune(outbox.OutboxSettings(), batch=2)
        return deleted, await h.rows()

    deleted, left = run(tmp_path, monkeypatch, scenario)
    assert deleted["done"] == 5 and left == []


def test_the_sweep_prunes_on_its_first_run_and_then_daily(tmp_path, monkeypatch):
    async def scenario(h):
        monkeypatch.setattr(outbox, "_last_prune", None)

        async def old_done(key):
            at = h.clock() - timedelta(days=9)
            async with h.sessions() as session:
                session.add(
                    NotificationOutbox(
                        event_json="{}",
                        dedupe_key=key,
                        trigger="t",
                        status="done",
                        next_attempt_at=at,
                        created_at=at,
                        updated_at=at,
                    ),
                )
                await session.commit()

        await old_done("a")
        await outbox.drain_notification_outbox()
        after_first = [r.dedupe_key for r in await h.rows()]
        await old_done("b")
        h.clock.advance(hours=1)
        await outbox.drain_notification_outbox()
        within_a_day = [r.dedupe_key for r in await h.rows()]
        h.clock.advance(hours=24)
        await outbox.drain_notification_outbox()
        return after_first, within_a_day, [r.dedupe_key for r in await h.rows()]

    after_first, within_a_day, next_day = run(tmp_path, monkeypatch, scenario)
    assert after_first == []
    assert within_a_day == ["b"]
    assert next_day == []
