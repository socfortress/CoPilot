"""Per-customer opt-out of the Sysmon noise statistics, its withdraw, and the decommission and deletion hooks
(sharing.py).

Run with: cd backend && python -m pytest tests/test_sysmon_stats_sharing.py
"""
import asyncio
import json
import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.active_response.schema.sysmon_stats import StatsOutcome  # noqa: E402
from app.active_response.schema.sysmon_stats import StatsSharingRequest  # noqa: E402
from app.active_response.services.sysmon_stats import runner  # noqa: E402
from app.active_response.services.sysmon_stats import sharing  # noqa: E402
from app.active_response.services.sysmon_stats.identity import (  # noqa: E402
    customer_pseudonym,
)
from app.active_response.services.sysmon_stats.identity import load_secret  # noqa: E402
from app.audit.models.audit import AuditAction  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import SysmonStatsCustomerSettings  # noqa: E402
from tests.sysmon_stats_support import Sysmonsync  # noqa: E402
from tests.sysmon_stats_support import World  # noqa: E402
from tests.sysmon_stats_support import week_docs  # noqa: E402

NOW = datetime(2026, 11, 25, 0, 30, tzinfo=timezone.utc)
ADMIN = type("U", (), {"id": 7, "username": "alice"})()


def run(coro):
    return asyncio.run(coro)


async def opt(world, code, sharing_on, service, **hints):
    body = StatsSharingRequest(sharing=sharing_on, **hints)
    async with world.db.session() as session:
        return await sharing.set_sharing(session, code, body, actor=ADMIN, transport=service.transport, now=NOW)


async def row(world, code):
    async with world.db.session() as s:
        return (
            (await s.execute(select(SysmonStatsCustomerSettings).where(SysmonStatsCustomerSettings.customer_code == code)))
            .scalars()
            .first()
        )


async def pseudonym(world, code):
    async with world.db.session() as s:
        return customer_pseudonym(await load_secret(s), code)


def test_an_opt_out_is_stored_audited_queued_and_withdrawn(monkeypatch, audit_rows):
    world = World(monkeypatch)
    service = Sysmonsync(withdraws=[httpx.Response(200, json={"result": "withdrawn", "scope": "customer", "reports_deleted": 3})])

    async def scenario():
        await world.setup()
        result = await opt(world, "contoso", False, service)
        return result, await row(world, "contoso"), await pseudonym(world, "contoso")

    result, stored, cust = run(scenario())
    assert result.outcome == "withdrawn" and result.reports_deleted == 3
    assert stored.sharing_enabled is False and stored.updated_by == 7
    assert stored.withdrawn_at == NOW.replace(tzinfo=None)
    (request,) = service.withdraws()
    assert json.loads(request.content) == {"format": "socfortress-sysmon-withdraw/1", "customer": cust}
    assert world.minio.names("stats-withdraw/") == []  # confirmed: dequeued
    sharing_rows = [r for r in audit_rows if r.action == AuditAction.SYSMON_STATS_SHARING.value]
    assert sharing_rows[0].old_value == {"sharing": True, "install_dir_name": None, "own_domains_count": 0}
    assert sharing_rows[0].new_value == {"sharing": False, "install_dir_name": None, "own_domains_count": 0}
    (withdraw_row,) = [r for r in audit_rows if r.action == AuditAction.SYSMON_STATS_WITHDRAW.value]
    assert withdraw_row.new_value == {"customer_pseudonym": cust, "http_status": 200, "outcome": "withdrawn", "reports_deleted": 3}
    assert withdraw_row.customer_code == "contoso" and withdraw_row.result == "success"


def test_a_failed_withdraw_stays_queued_and_the_next_tick_sends_it_first(monkeypatch):
    world = World(monkeypatch, week_docs("contoso") + week_docs("northwind"))
    service = Sysmonsync(withdraws=[httpx.Response(503, json={}), httpx.Response(200, json={"result": "withdrawn", "reports_deleted": 0})])

    async def scenario():
        await world.setup({"contoso": "C", "northwind": "N"})
        first = await opt(world, "contoso", False, service)
        queued = world.minio.names("stats-withdraw/")
        async with world.db.session() as session:
            # The 503 asked to wait 300 s: the tick after that window sends the withdraw first, then northwind's report
            result = await runner.run_tick(session, now=NOW + timedelta(minutes=10), transport=service.transport)
        return first, queued, result

    first, queued, result = run(scenario())
    assert first.outcome == "queued" and len(queued) == 1
    paths = [r.url.path for r in service.requests]
    second_withdraw = [i for i, p in enumerate(paths) if p.endswith("/withdraw")][1]
    assert second_withdraw < paths.index("/v1/sysmon/report")
    assert world.minio.names("stats-withdraw/") == []
    assert [c.customer_code for c in result.customers] == ["northwind"]


def test_with_the_kill_switch_off_the_withdraw_is_queued_not_sent(monkeypatch):
    world = World(monkeypatch)
    monkeypatch.setenv("SYSMON_STATS_SHARING", "off")
    service = Sysmonsync()

    async def scenario():
        await world.setup()
        return await opt(world, "contoso", False, service)

    result = run(scenario())
    assert result.outcome == "queued" and service.requests == [] and len(world.minio.names("stats-withdraw/")) == 1


def test_a_report_that_lands_after_the_opt_out_is_withdrawn_again(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))

    async def opt_out_meanwhile(request):
        async with world.db.session() as s:
            s.add(SysmonStatsCustomerSettings(customer_code="contoso", sharing_enabled=False))
            await s.commit()

    service = Sysmonsync(on_report=opt_out_meanwhile)

    async def scenario():
        await world.setup()
        async with world.db.session() as session:
            return await runner.run_tick(session, now=NOW, transport=service.transport)

    result = run(scenario())
    assert result.customers[0].outcome is StatsOutcome.SENT
    paths = [r.url.path for r in service.requests]
    assert paths[-1] == "/v1/sysmon/report/withdraw" and paths.index("/v1/sysmon/report/withdraw") > paths.index("/v1/sysmon/report")


def test_opting_in_again_waits_180_seconds_after_the_withdraw(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))
    service = Sysmonsync()

    async def scenario():
        await world.setup()
        await opt(world, "contoso", False, service)
        await opt(world, "contoso", True, service)
        async with world.db.session() as session:
            early = await runner.run_tick(session, now=NOW + timedelta(seconds=60), transport=service.transport)
        async with world.db.session() as session:
            late = await runner.run_tick(session, now=NOW + timedelta(seconds=200), transport=service.transport)
        return early, late

    early, late = run(scenario())
    assert early.outcome is StatsOutcome.NOTHING_DUE
    assert late.customers and late.customers[0].outcome is StatsOutcome.SENT


def test_hints_are_validated_and_kept_when_not_given(monkeypatch):
    world = World(monkeypatch)
    service = Sysmonsync()

    async def scenario():
        await world.setup()
        await opt(
            world,
            "contoso",
            True,
            service,
            install_dir_name="edrsvc",
            own_domains=["Contoso.COM.", "contoso.com", "corp.contoso.com"],
        )
        await opt(world, "contoso", True, service)
        kept = await row(world, "contoso")
        errors = []
        for bad in (
            {"install_dir_name": "bad dir"},
            {"install_dir_name": "__INSTALLDIRNAME__"},
            {"own_domains": ["single"]},
            {"own_domains": [f"d{i}.example.com" for i in range(21)]},
        ):
            try:
                await opt(world, "contoso", True, service, **bad)
            except HTTPException as e:
                errors.append(e.status_code)
        try:
            await opt(world, "nobody", True, service)
        except HTTPException as e:
            errors.append(e.status_code)
        await opt(world, "contoso", True, service, install_dir_name=None, own_domains=[])
        cleared = await row(world, "contoso")
        return kept, errors, cleared

    kept, errors, cleared = run(scenario())
    assert kept.install_dir_name == "edrsvc" and kept.own_domains == ["contoso.com", "corp.contoso.com"]
    assert errors == [400, 400, 400, 400, 404]
    assert cleared.install_dir_name is None and cleared.own_domains is None


def test_decommission_and_delete_queue_a_withdraw_by_pseudonym(monkeypatch):
    world = World(monkeypatch)

    async def scenario():
        await world.setup({"contoso": "C", "northwind": "N"})
        await opt(world, "northwind", True, Sysmonsync(), install_dir_name="nwedr")
        cust_c, cust_n = await pseudonym(world, "contoso"), await pseudonym(world, "northwind")
        await sharing.on_customer_deleted("contoso")
        await sharing.on_customer_decommissioned("northwind")
        # The customer row goes; the queued withdraws stay
        async with world.db.session() as s:
            await s.execute(delete(Customers))
            await s.commit()
        return cust_c, cust_n, await row(world, "northwind")

    cust_c, cust_n, gone = run(scenario())
    assert world.minio.names("stats-withdraw/") == sorted([f"stats-withdraw/{cust_c}.json", f"stats-withdraw/{cust_n}.json"])
    assert gone is None
    assert world.minio.json(f"stats-withdraw/{cust_c}.json")["customer_code"] == "contoso"


def test_the_settings_row_cascades_with_the_customer(monkeypatch):
    world = World(monkeypatch)

    async def scenario():
        await world.setup()
        await opt(world, "contoso", True, Sysmonsync(), install_dir_name="edrsvc")
        async with world.db.session() as s:
            # The database's own cascade (SQLite with foreign keys on), as a customer deletion leaves it to MySQL
            await s.execute(delete(Customers).where(Customers.customer_code == "contoso"))
            await s.commit()
        return await row(world, "contoso")

    assert run(scenario()) is None


def test_the_hooks_never_raise(monkeypatch):
    world = World(monkeypatch)

    def broken():
        raise RuntimeError("no database")

    monkeypatch.setattr(sharing, "new_session", broken)
    run(sharing.on_customer_deleted("contoso"))
    run(sharing.on_customer_decommissioned("contoso"))
    assert world.minio.puts == []


@pytest.mark.parametrize("module", ["app.customers.routes.customers", "app.customer_provisioning.services.decommission"])
def test_the_customer_flows_call_the_hooks(module):
    import importlib
    import inspect

    source = inspect.getsource(importlib.import_module(module))
    assert "on_customer_deleted(customer_code)" in source or "on_customer_decommissioned(customer_meta.customer_code)" in source


def test_decommission_keeps_an_opt_out_and_turns_sharing_off(monkeypatch, audit_rows):
    """Review: decommission deleted the settings row while the Customers row stayed, so an admin's opt-out reverted to
    sharing (no row means on), its hints went, and reports started again. Now sharing is off and stays off."""
    from app.active_response.services.sysmon_stats import status as status_mod

    docs = (
        week_docs("contoso")
        + week_docs("contoso", monday="2026-11-23")
        + week_docs("northwind")
        + week_docs("northwind", monday="2026-11-23")
    )
    world = World(monkeypatch, docs)
    service = Sysmonsync()

    async def scenario():
        await world.setup({"contoso": "Contoso Ltd", "northwind": "Northwind"})
        await opt(world, "contoso", False, service, install_dir_name="edrsvc", own_domains=["contoso.com"])
        await sharing.on_customer_decommissioned("contoso", now=NOW)
        # A customer that was sharing (no row) is turned off too
        await sharing.on_customer_decommissioned("northwind", now=NOW)
        async with world.db.session() as s:
            status = await status_mod.get_status(s, now=NOW)
        ticks = []
        for moment in (NOW, datetime(2026, 12, 2, 23, 0, tzinfo=timezone.utc)):
            async with world.db.session() as s:
                ticks.append(await runner.run_tick(s, now=moment, transport=service.transport))
        return status, ticks, await row(world, "contoso"), await row(world, "northwind")

    status, ticks, contoso, northwind = run(scenario())
    assert [c.sharing for c in status.customers] == [False, False]
    assert contoso.sharing_enabled is False and contoso.install_dir_name == "edrsvc" and contoso.own_domains == ["contoso.com"]
    assert northwind.sharing_enabled is False and northwind.withdrawn_at is not None
    assert service.reports() == [] and all(t.outcome is StatsOutcome.NOTHING_DUE for t in ticks)
    decommissioned = [
        r for r in audit_rows if r.action == AuditAction.SYSMON_STATS_SHARING.value and r.details == "Customer decommissioned"
    ]
    assert [(r.customer_code, r.actor_username) for r in decommissioned] == [("contoso", "system"), ("northwind", "system")]
    assert {"sharing": False} == _as_dict(decommissioned[1].new_value) and {"sharing": True} == _as_dict(decommissioned[1].old_value)


def _as_dict(value):
    return json.loads(value) if isinstance(value, str) else value


def test_a_refused_customer_deletion_withdraws_nothing(monkeypatch):
    """Review: the withdraw was queued before the deletion was committed, so a refused deletion (users still assigned)
    withdrew a live, sharing customer's reports. Now it is queued only once the customer is gone."""
    from sqlmodel import SQLModel

    import app.auth.models.users as users
    from app.customers.routes.customers import delete_customer

    world = World(monkeypatch, week_docs("contoso"))

    async def scenario():
        await world.setup({"contoso": "Contoso Ltd", "northwind": "Northwind"})
        tables = [SQLModel.metadata.tables[n] for n in ("role", "user", "user_customer_access", "customersmeta")]
        async with world.db.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        async with world.db.session() as s:
            s.add(users.User(id=7, username="analyst1", password="x", email="a@example.invalid"))
            await s.commit()
            s.add(users.UserCustomerAccess(user_id=7, customer_code="contoso"))
            await s.commit()
        async with world.db.session() as s:
            await load_secret(s, create=True)
        async with world.db.session() as s:
            with pytest.raises(HTTPException) as refused:
                await delete_customer("contoso", s)
        after_refusal = world.minio.names("stats-withdraw/")
        async with world.db.session() as s:
            deleted = await delete_customer("northwind", s)
        return refused.value, after_refusal, deleted, await pseudonym(world, "northwind")

    refused, after_refusal, deleted, cust_n = run(scenario())
    assert refused.status_code == 400 and after_refusal == []
    assert deleted.success and world.minio.names("stats-withdraw/") == [f"stats-withdraw/{cust_n}.json"]
