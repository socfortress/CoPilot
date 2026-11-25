"""A tick of the Sysmon noise statistics (runner.py): the kill switch, the locks, the weekly state, the probe, the pause,
the service-wide answers, the deadlines, and database transactions ended before every network call.

Everything is a fake: SQLite for the tables, MinIO in memory, an indexer that evaluates the aggregations over synthetic
alerts, and sysmon-sync as an httpx.MockTransport. Now is pinned to Wednesday 2026-11-25 00:30 UTC, when every
customer's W47 report is due (send times run from Monday 01:00 to Tuesday 24:00).

Run with: cd backend && python -m pytest tests/test_sysmon_stats_runner.py
"""
import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from loguru import logger  # noqa: E402

from app.active_response.schema.sysmon_stats import StatsOutcome  # noqa: E402
from app.active_response.services.sysmon_stats import identity  # noqa: E402
from app.active_response.services.sysmon_stats import runner  # noqa: E402
from app.audit.models.audit import AuditAction  # noqa: E402
from app.db import named_lock  # noqa: E402
from tests.sysmon_stats_support import LICENSE_KEY  # noqa: E402
from tests.sysmon_stats_support import Sysmonsync  # noqa: E402
from tests.sysmon_stats_support import World  # noqa: E402
from tests.sysmon_stats_support import week_docs  # noqa: E402

NOW = datetime(2026, 11, 25, 0, 30, tzinfo=timezone.utc)


def tick(world, service, now=NOW, **kw):
    async def go():
        async with world.db.session() as session:
            return await runner.run_tick(session, now=now, transport=service.transport, **kw)

    return go()


def run(coro):
    return asyncio.run(coro)


def sends(audit_rows):
    return [r for r in audit_rows if r.action == AuditAction.SYSMON_STATS_SEND.value]


# ── the kill switch ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("env", [{"SYSMON_STATS_SHARING": "off"}, {"SYSMON_STATS_SHARING": "maybe"}, {"SYSMON_DEFAULT_SYNC": "off"}])
def test_the_kill_switch_stops_every_query_and_request(monkeypatch, env):
    world = World(monkeypatch, week_docs("contoso"))
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    service = Sysmonsync()

    async def scenario():
        await world.setup()
        return await tick(world, service)

    result = run(scenario())
    assert result.outcome is StatsOutcome.SHARING_OFF
    assert world.indexer_clients == 0 and world.indexer.searches == [] and service.requests == []
    assert world.minio.puts == []


def test_an_explicit_on_overrides_the_default_sync_being_off(monkeypatch):
    from app.active_response.services.sysmon_stats import settings

    monkeypatch.setenv("SYSMON_DEFAULT_SYNC", "off")
    monkeypatch.setenv("SYSMON_STATS_SHARING", "on")
    assert settings.sharing_mode()[0].value == "on"
    monkeypatch.setenv("SYSMON_STATS_SHARING", "Maybe")
    assert settings.sharing_mode() == (settings.SharingMode.OFF, "Maybe")


# ── locks ───────────────────────────────────────────────────────────────────


def test_another_replica_holding_the_lock_skips_the_tick(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))

    @asynccontextmanager
    async def not_held(prefix, label):
        yield False

    monkeypatch.setattr(named_lock, "mysql_named_lock", not_held)
    service = Sysmonsync()

    async def scenario():
        await world.setup()
        return await tick(world, service)

    assert run(scenario()).outcome is StatsOutcome.LOCKED
    assert service.requests == [] and world.indexer.searches == []


def test_a_run_in_progress_in_this_process_skips_the_tick(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))
    service = Sysmonsync()

    async def scenario():
        await world.setup()
        async with runner._RUN_LOCK:
            return await tick(world, service)

    assert run(scenario()).outcome is StatsOutcome.RUNNING and service.requests == []


# ── a tick ──────────────────────────────────────────────────────────────────


def test_a_tick_sends_each_due_customer_once(monkeypatch, audit_rows):
    world = World(monkeypatch, week_docs("contoso") + week_docs("Northwind"))
    service = Sysmonsync()

    async def scenario():
        await world.setup({"contoso": "Contoso Ltd", "northwind": "Northwind Traders"})
        first = await tick(world, service)
        second = await tick(world, service, now=NOW + timedelta(hours=6))
        return first, second

    first, second = run(scenario())
    assert first.outcome is StatsOutcome.COMPLETED
    assert sorted(c.customer_code for c in first.customers) == ["contoso", "northwind"]
    assert all(c.outcome is StatsOutcome.SENT for c in first.customers)
    assert len(service.probes()) == 1 and len(service.reports()) == 2
    bodies = [json.loads(r.content) for r in service.reports()]
    for body in bodies:
        assert body["week"] == "2026-W47" and body["endpoints"] == 5
        names = {p["fields"].get("QueryName") for p in body["patterns"]}
        assert names == {"telemetry.fabrikam-example.com", None}
        text = json.dumps(body)
        assert "c2.example-bad.net" not in text and "fileserver.corp" not in text and "contoso" not in text.lower()
    week = world.week()
    assert week["contoso"]["status"] == "terminal" and week["contoso"]["outcome"] == "sent"
    assert week["contoso"]["local_drops"] == {"dns-private-suffix": 1}
    # The next tick: nothing due, no probe, no indexer
    assert second.outcome is StatsOutcome.NOTHING_DUE
    assert len(service.probes()) == 1 and len(service.reports()) == 2
    (row1, row2) = sends(audit_rows)
    assert row1.actor_username == "system" and row1.actor_user_id is None and row1.result == "success"
    assert row1.new_value["payload_sha256"] == week[row1.customer_code]["payload_sha256"]
    assert row1.entity_id.startswith("2026-W47/cust_")


def test_nothing_due_means_no_probe_and_no_indexer(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))
    service = Sysmonsync()

    async def scenario():
        await world.setup()
        # Monday 00:30: no send time has come yet
        return await tick(world, service, now=datetime(2026, 11, 23, 0, 30, tzinfo=timezone.utc))

    assert run(scenario()).outcome is StatsOutcome.NOTHING_DUE
    assert service.requests == [] and world.indexer_clients == 0


def test_send_now_ignores_the_jitter_for_one_customer(monkeypatch, audit_rows):
    world = World(monkeypatch, week_docs("contoso") + week_docs("northwind"))
    service = Sysmonsync()
    admin = type("U", (), {"id": 7, "username": "alice"})()

    async def scenario():
        await world.setup({"contoso": "Contoso Ltd", "northwind": "Northwind Traders"})
        return await tick(
            world,
            service,
            now=datetime(2026, 11, 23, 0, 30, tzinfo=timezone.utc),
            customer_code="contoso",
            ignore_jitter=True,
            actor=admin,
        )

    result = run(scenario())
    assert [c.customer_code for c in result.customers] == ["contoso"]
    (row,) = sends(audit_rows)
    assert (row.actor_user_id, row.actor_username, row.details) == (7, "alice", "Send now")


def test_the_send_time_is_deterministic_per_copilot_and_customer():
    secret = bytes(range(32))
    a = identity.due_time(secret, "contoso", "2026-W47", date(2026, 11, 16))
    assert a == identity.due_time(secret, "contoso", "2026-W47", date(2026, 11, 16))
    assert datetime(2026, 11, 23, 1, tzinfo=timezone.utc) <= a < datetime(2026, 11, 25, tzinfo=timezone.utc)
    assert a != identity.due_time(secret, "fabrikam", "2026-W47", date(2026, 11, 16))
    assert identity.customer_pseudonym(secret, "contoso") == identity.customer_pseudonym(secret, "contoso")
    assert identity.customer_pseudonym(secret, "contoso").startswith("cust_") and len(identity.customer_pseudonym(secret, "contoso")) == 37


def test_service_not_accepting_is_quiet(monkeypatch, audit_rows):
    world = World(monkeypatch, week_docs("contoso"))
    service = Sysmonsync(probe=httpx.Response(404, json={"detail": "reports are not enabled"}))
    lines = []
    sink = logger.add(lambda m: lines.append(str(m)), level="INFO")

    async def scenario():
        await world.setup()
        first = await tick(world, service)
        second = await tick(world, service, now=NOW + timedelta(hours=6))
        return first, second

    try:
        first, second = run(scenario())
    finally:
        logger.remove(sink)
    assert first.outcome is second.outcome is StatsOutcome.SERVICE_NOT_ACCEPTING
    assert world.indexer_clients == 0 and service.reports() == [] and sends(audit_rows) == []
    assert sum("not accepting noise reports" in line for line in lines) == 1
    assert world.week() == {} and world.state()["service"]["accepting"] is False


def test_a_pending_report_is_retried_by_the_next_tick(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))
    service = Sysmonsync(reports=[httpx.ConnectError("refused"), Sysmonsync().stored()])

    async def scenario():
        await world.setup()
        first = await tick(world, service)
        status = world.week()["contoso"]["status"]
        second = await tick(world, service, now=NOW + timedelta(hours=6))
        return first, status, second

    first, status, second = run(scenario())
    assert first.outcome is StatsOutcome.NETWORK_ERROR and status == "pending"
    assert second.customers[0].outcome is StatsOutcome.SENT and world.week()["contoso"]["attempts"] == 2


def test_a_408_waits_15_minutes(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))
    service = Sysmonsync(reports=[httpx.Response(408, json={"reason": "body-timeout"}), Sysmonsync().stored()])

    async def scenario():
        await world.setup()
        await tick(world, service)
        early = await tick(world, service, now=NOW + timedelta(minutes=5))
        late = await tick(world, service, now=NOW + timedelta(minutes=20))
        return early, late

    early, late = run(scenario())
    assert early.outcome is StatsOutcome.NOTHING_DUE and late.customers[0].outcome is StatsOutcome.SENT


def test_a_rate_limit_holds_every_request(monkeypatch):
    world = World(monkeypatch, week_docs("contoso") + week_docs("northwind"))
    service = Sysmonsync(reports=[httpx.Response(429, json={"reason": "rate-limit"}, headers={"Retry-After": "3600"})])

    async def scenario():
        await world.setup({"contoso": "C", "northwind": "N"})
        first = await tick(world, service)
        count = len(service.requests)
        held = await tick(world, service, now=NOW + timedelta(minutes=30))
        return first, count, held

    first, count, held = run(scenario())
    assert first.outcome is StatsOutcome.RATE_LIMITED and len(service.reports()) == 1
    assert held.outcome is StatsOutcome.RATE_LIMITED and len(service.requests) == count


def test_a_week_wide_refusal_marks_the_rest_of_the_week(monkeypatch):
    world = World(monkeypatch, week_docs("contoso") + week_docs("northwind"))
    service = Sysmonsync(reports=[httpx.Response(422, json={"detail": "x", "reason": "customer-limit"})])

    async def scenario():
        await world.setup({"contoso": "C", "northwind": "N"})
        return await tick(world, service)

    result = run(scenario())
    assert result.outcome is StatsOutcome.CUSTOMER_LIMIT and len(service.reports()) == 1
    week = world.week()
    assert {week[c]["outcome"] for c in ("contoso", "northwind")} == {"customer_limit"}
    assert all(week[c]["status"] == "terminal" for c in ("contoso", "northwind"))


def test_a_content_refusal_pauses_reports_until_an_update_or_a_resume(monkeypatch, audit_rows):
    world = World(monkeypatch, week_docs("contoso") + week_docs("northwind"))
    refused = httpx.Response(
        422,
        json={"detail": "x", "reason": "identity-leak", "patterns": [{"index": 0, "reason": "identity-leak", "field": "TargetFilename"}]},
    )
    service = Sysmonsync(reports=[refused, Sysmonsync().stored()])
    admin = type("U", (), {"id": 7, "username": "alice"})()

    async def scenario():
        await world.setup({"contoso": "C", "northwind": "N"})
        first = await tick(world, service)
        after_first = len(service.reports())
        paused = await tick(world, service, now=NOW + timedelta(hours=6))
        after_paused = len(service.reports())
        resumed = await tick(world, service, now=NOW + timedelta(hours=7), resume=True, actor=admin)
        return first, after_first, paused, after_paused, resumed

    first, after_first, paused, after_paused, resumed = run(scenario())
    assert first.outcome is StatsOutcome.REFUSED and after_first == 1
    assert paused.outcome is StatsOutcome.LATCHED and after_paused == 1
    assert resumed.customers and resumed.customers[0].outcome is StatsOutcome.SENT
    assert world.state()["latch"] is None
    assert any(r.action == AuditAction.SYSMON_STATS_RESUME.value and r.old_value == {"latch_reason": "identity-leak"} for r in audit_rows)


def test_a_new_copilot_version_lifts_the_pause(monkeypatch):
    world = World(monkeypatch, week_docs("contoso") + week_docs("northwind"))
    refused = httpx.Response(422, json={"detail": "x", "reason": "command-line", "patterns": [{"index": 0, "reason": "command-line"}]})
    service = Sysmonsync(reports=[refused, Sysmonsync().stored()])

    async def scenario():
        await world.setup({"contoso": "C", "northwind": "N"})
        await tick(world, service)
        monkeypatch.setattr(runner, "CURRENT_VERSION", "99.0.0")
        return await tick(world, service, now=NOW + timedelta(hours=6))

    result = run(scenario())
    assert result.customers and result.customers[0].outcome is StatsOutcome.SENT


def test_database_transactions_end_before_every_network_call(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))
    open_during_requests = []
    holder = {}

    async def on_report(request):
        open_during_requests.append(holder["session"].in_transaction())

    service = Sysmonsync(on_report=on_report)
    real_handle = service.handle

    async def handle(request):
        open_during_requests.append(holder["session"].in_transaction())
        return await real_handle(request)

    service.handle = handle

    async def scenario():
        await world.setup({"contoso": "C"}, hostnames={"contoso": ["WS-0142"]})
        async with world.db.session() as session:
            holder["session"] = session
            real_search = world.indexer.search

            async def search(index, body, **kwargs):
                open_during_requests.append(session.in_transaction())
                return await real_search(index, body, **kwargs)

            world.indexer.search = search
            return await runner.run_tick(session, now=NOW, transport=httpx.MockTransport(handle))

    result = run(scenario())
    assert result.customers[0].outcome is StatsOutcome.SENT
    assert open_during_requests and not any(open_during_requests)


def test_the_tick_deadline_stops_before_the_next_customer(monkeypatch):
    world = World(monkeypatch, week_docs("contoso") + week_docs("northwind"))
    service = Sysmonsync()
    clock = iter([0.0, 0.0] + [10_000.0] * 100)
    monkeypatch.setattr(runner, "_monotonic", lambda: next(clock))

    async def scenario():
        await world.setup({"contoso": "C", "northwind": "N"})
        return await tick(world, service)

    result = run(scenario())
    assert len(result.customers) == 1 and len(service.reports()) == 1


def test_a_customer_over_its_deadline_stays_pending(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))
    world.indexer.delay = 0.2
    monkeypatch.setattr(runner.settings, "CUSTOMER_DEADLINE", 0.1)
    service = Sysmonsync()

    async def scenario():
        await world.setup()
        return await tick(world, service)

    result = run(scenario())
    assert result.customers[0].outcome is StatsOutcome.INDEXER_TIMEOUT
    assert world.week()["contoso"]["status"] == "pending" and service.reports() == []


def test_customers_without_events_and_ambiguous_codes_are_terminal(monkeypatch):
    world = World(monkeypatch, week_docs("acme"))
    service = Sysmonsync()

    async def scenario():
        await world.setup({"acme": "A1", "ACME": "A2", "northwind": "N"})
        return await tick(world, service)

    run(scenario())
    week = world.week()
    assert week["acme"]["outcome"] == week["ACME"]["outcome"] == "ambiguous_label"
    assert week["northwind"]["outcome"] == "no_sysmon_events" and week["northwind"]["status"] == "terminal"
    assert service.reports() == []


def test_an_opted_out_customer_is_never_collected(monkeypatch):
    from app.db.universal_models import SysmonStatsCustomerSettings

    world = World(monkeypatch, week_docs("contoso"))
    service = Sysmonsync()

    async def scenario():
        await world.setup()
        async with world.db.session() as s:
            s.add(SysmonStatsCustomerSettings(customer_code="contoso", sharing_enabled=False))
            await s.commit()
        return await tick(world, service)

    assert run(scenario()).outcome is StatsOutcome.NOTHING_DUE
    assert world.indexer_clients == 0 and service.requests == []


def test_no_license_sends_nothing(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))
    service = Sysmonsync()

    async def scenario():
        await world.setup(license_key=None)
        return await tick(world, service)

    assert run(scenario()).outcome is StatsOutcome.NO_LICENSE and service.requests == []


def test_no_usable_fields_is_reported(monkeypatch):
    world = World(monkeypatch, [{"timestamp": 1, "agent.id": "x"}])
    service = Sysmonsync()

    async def scenario():
        await world.setup()
        return await tick(world, service)

    assert run(scenario()).outcome is StatsOutcome.INDEXER_FIELDS_UNAVAILABLE and service.reports() == []


def test_the_license_key_never_reaches_a_log_the_state_or_an_audit_row(monkeypatch, audit_rows):
    world = World(monkeypatch, week_docs("contoso"))
    service = Sysmonsync(reports=[httpx.ConnectError(f"bad header {LICENSE_KEY}"), Sysmonsync().stored()])
    lines = []
    sink = logger.add(lambda m: lines.append(str(m)), level="DEBUG")

    async def scenario():
        await world.setup()
        await tick(world, service)
        await tick(world, service, now=NOW + timedelta(hours=6))

    try:
        run(scenario())
    finally:
        logger.remove(sink)
    assert LICENSE_KEY not in "\n".join(lines)
    for content in world.minio.objects.values():
        assert LICENSE_KEY.encode() not in content
    for row in audit_rows:
        assert LICENSE_KEY not in json.dumps(row.model_dump(), default=str)
    secret_row = run(_secret(world))
    for content in world.minio.objects.values():
        assert secret_row.encode() not in content
    assert secret_row not in "\n".join(lines)


async def _secret(world):
    from sqlalchemy import select

    from app.db.universal_models import SysmonStatsIdentity

    async with world.db.session() as s:
        return (await s.execute(select(SysmonStatsIdentity.report_secret))).scalar_one()


def test_the_job_is_registered_every_6_hours_and_admin_only():
    import ast
    from pathlib import Path

    from app.schedulers import scheduler
    from app.schedulers.routes.scheduler import ADMIN_ONLY_JOBS
    from app.schedulers.services.send_sysmon_stats import send_sysmon_stats

    assert scheduler.get_function_by_name("send_sysmon_stats") is send_sysmon_stats
    intervals = {}
    for node in ast.walk(ast.parse(Path(scheduler.__file__).read_text())):
        if isinstance(node, ast.Dict):
            entries = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
            if isinstance(entries.get("job_id"), ast.Constant):
                intervals[entries["job_id"].value] = entries["time_interval"].value
    assert intervals["send_sysmon_stats"] == 360
    assert "send_sysmon_stats" in ADMIN_ONLY_JOBS


def test_the_job_never_raises(monkeypatch):
    from unittest.mock import AsyncMock

    from app.schedulers.services import send_sysmon_stats as job

    tick_fn = AsyncMock()
    monkeypatch.setattr(job, "run_tick", tick_fn)
    asyncio.run(job.send_sysmon_stats())
    tick_fn.assert_awaited_once()
    monkeypatch.setattr(job, "run_tick", AsyncMock(side_effect=RuntimeError("boom")))
    asyncio.run(job.send_sysmon_stats())


def test_a_run_never_raises(monkeypatch):
    from unittest.mock import AsyncMock

    world = World(monkeypatch, week_docs("contoso"))
    monkeypatch.setattr(runner, "_locked_run", AsyncMock(side_effect=RuntimeError("bug")))

    async def scenario():
        await world.setup()
        return await tick(world, Sysmonsync())

    assert run(scenario()).outcome is StatsOutcome.ERROR
