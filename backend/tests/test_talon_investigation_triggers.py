"""CoPilot's record of every alert it sends to Talon, and the binding of the Talon service account's
automated collections to it (talon-analyst plan AP-2a; ``services/talon_triggers.py``).

The harness is ``test_talon_collect_start``'s (real routers, a real in-memory database), with the
trigger and cap tables added.

Pinned here:
- every sender writes a record before the call, with its kind and user: the alert pipeline, an
  analyst's "Investigate with AI Analyst", a customer portal request and a replay; the alert's
  assets are kept as they were sent; a refusing sender (portal, replay) whose record can't be
  written sends nothing, an allowing one sends anyway;
- the service account's start with ``alert_id`` is refused with no record, a portal or replay
  record (also when newer than a pipeline one), an expired window, another host (an asset added
  after the send included), an asset's other client, another customer's host, and over the
  per-alert cap (a new job doesn't reset it; the audit write failing doesn't loosen it; two
  concurrent starts at the cap minus one start one flow; a slot that can't be recorded is no
  start); each refusal a fixed text, starting nothing;
- it is accepted with a pipeline or an analyst record (a re-trigger reopens the window), and its
  audit event names the alert, the job and the trigger;
- ``alert_id`` and ``job_id`` are no longer a 422; other users, and the service account without
  ``alert_id``, are unchanged;
- the migration has a single head (``test_alembic_single_head``), its tables are the models'.

Run with: cd backend && python -m pytest tests/test_talon_investigation_triggers.py
"""

import asyncio
import importlib.util
import os
from contextlib import ExitStack
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.connectors.talon.services.talon as talon_service  # noqa: E402
import app.customer_portal.services.ai_requests as portal_requests  # noqa: E402
import app.incidents.services.incident_alert as ingest  # noqa: E402
import tests.test_talon_actions as harness  # noqa: E402
from app.ai_analyst.routes import ai_analyst as ai_analyst_routes  # noqa: E402
from app.ai_analyst.schema.ai_analyst import ReplayRequest  # noqa: E402
from app.audit.models.audit import AuditAction  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonAutomationAlertCap  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonInvestigationTrigger  # noqa: E402
from app.connectors.talon.services import talon_collections  # noqa: E402
from app.connectors.talon.services import talon_triggers  # noqa: E402
from app.db.universal_models import CustomerPortalAiRequest  # noqa: E402
from app.incidents.models import AlertContext  # noqa: E402
from app.incidents.models import Asset  # noqa: E402
from tests.test_talon_actions import ACME  # noqa: E402
from tests.test_talon_actions import GLOBEX  # noqa: E402
from tests.test_talon_actions import HOST  # noqa: E402
from tests.test_talon_actions import VID  # noqa: E402
from tests.test_talon_actions import agent_row  # noqa: E402
from tests.test_talon_actions import as_user  # noqa: E402
from tests.test_talon_collect_start import HOST_ARTIFACTS  # noqa: E402
from tests.test_talon_collect_start import ROUTE  # noqa: E402
from tests.test_talon_collect_start import SERVICE  # noqa: E402
from tests.test_talon_collect_start import SERVICES  # noqa: E402
from tests.test_talon_collect_start import add_agents  # noqa: E402
from tests.test_talon_collect_start import body  # noqa: E402
from tests.test_talon_collect_start import (  # noqa: E402,F401 - autouse
    built_in_velociraptor_definitions,
)
from tests.test_talon_collect_start import configure  # noqa: E402
from tests.test_talon_collect_start import service_users  # noqa: E402
from tests.test_talon_endpoint_actions import FLOW  # noqa: E402
from tests.test_talon_endpoint_actions import Velociraptor  # noqa: E402

HOST_2, VID_2 = "WIN-ACME-02", "C.00000000000000b2"
JOB = "copilot-inv-1-1761048000000"


class _Db(harness._Db):
    async def create(self):
        await super().create()
        tables = [TalonInvestigationTrigger.__table__, TalonAutomationAlertCap.__table__, CustomerPortalAiRequest.__table__]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self


def call(scenario, **kwargs):
    with service_users(), patch.object(harness, "_Db", _Db):
        return harness.call(scenario, **kwargs)


def bound(payload, alert_id, job_id=JOB):
    return {**payload, "alert_id": alert_id, "job_id": job_id}


# ── helpers on the test database ──────────────────────────────────────────────


async def add_asset(ctx, alert_id, name=HOST, vid=VID, customer=ACME):
    async with ctx.db.session() as session:
        context = AlertContext(source="wazuh", context={})
        session.add(context)
        await session.commit()
        session.add(
            Asset(
                alert_linked=alert_id,
                asset_name=name,
                alert_context_id=context.id,
                velociraptor_id=vid,
                customer_code=customer,
                index_name="wazuh-alerts",
                index_id="1",
            ),
        )
        await session.commit()


async def add_trigger(ctx, alert_id, source, *, ago=timedelta(minutes=5), user=None, customer=ACME):
    """A record as a sender writes it (``talon_triggers.record``, its assets read now), sent ``ago``."""
    with patch.object(talon_triggers, "new_session", ctx.db.session):
        row = await talon_triggers.record(alert_id, customer, source, user)
    async with ctx.db.session() as session:
        stored = await session.get(TalonInvestigationTrigger, row.id)
        stored.sent_at = talon_triggers.utcnow() - ago
        await session.commit()
    return row


async def triggers(ctx):
    async with ctx.db.session() as session:
        return (await session.execute(select(TalonInvestigationTrigger).order_by(TalonInvestigationTrigger.id))).scalars().all()


def collect_audits(ctx):
    return [c.kwargs for c in ctx.quarantine_audit.await_args_list if c.kwargs["action"] == AuditAction.ARTIFACT_COLLECT]


def scenario_for(name, payloads, setup=None, concurrent=False):
    """Configure the allowlist, seed with ``setup(ctx)`` (which may return the payloads, given the
    seeded alert ids), then post each payload as ``name``."""

    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            stack.enter_context(patch.object(talon_triggers, "new_session", ctx.db.session))
            await configure(ctx)
            await add_asset(ctx, ctx.alert_id)
            sent = (await setup(ctx) if setup is not None else None) or payloads(ctx)
            if concurrent:
                responses = list(await asyncio.gather(*(client.post(ROUTE, json=p, headers=as_user(name)) for p in sent)))
            else:
                responses = [await client.post(ROUTE, json=p, headers=as_user(name)) for p in sent]
        return responses, vr, ctx

    return scenario


def with_triggers(*specs):
    async def setup(ctx):
        for source, ago in specs:
            await add_trigger(ctx, ctx.alert_id, source, ago=ago)

    return setup


def start(name, payloads, setup=None, concurrent=False):
    return call(scenario_for(name, payloads, setup, concurrent))


# ── every sender writes a record ──────────────────────────────────────────────


def _sending(ctx, seen):
    """Talon's ``/investigate``, which notes the records that existed when it was called."""

    async def send(endpoint, data, **kwargs):
        seen.append((endpoint, data, [(t.source, t.user_id) for t in await triggers(ctx)]))
        return {"success": True, "data": {"job_id": "x"}}

    return send


def test_the_alert_pipeline_records_its_send_before_the_call_with_the_alerts_assets():
    async def scenario(client, ctx):
        seen = []
        await add_asset(ctx, ctx.alert_id)
        with patch.object(talon_triggers, "new_session", ctx.db.session), patch.object(
            talon_service,
            "send_post_request",
            _sending(ctx, seen),
        ):
            await ingest._investigate_in_background(ctx.alert_id, ACME)
        return seen, await triggers(ctx)

    seen, rows = call(scenario)
    ((endpoint, data, before),) = seen
    assert endpoint == "/investigate" and data["sender"] == "copilot"
    assert before == [("pipeline", None)]  # written before the call
    (row,) = rows
    assert (row.customer_code, row.source, row.user_id, row.username) == (ACME, "pipeline", None, None)
    assert row.assets == [{"asset_name": HOST, "velociraptor_id": VID}]


def test_an_analysts_investigate_records_the_analyst():
    async def scenario(client, ctx):
        seen = []
        with patch.object(talon_triggers, "new_session", ctx.db.session), patch.object(
            talon_service,
            "send_post_request",
            _sending(ctx, seen),
        ):
            response = await client.post(
                "/talon/investigate",
                json={"alert_id": ctx.alert_id, "customer_code": ACME},
                headers=as_user("ana"),
            )
        return response, seen, await triggers(ctx)

    response, seen, rows = call(scenario)
    assert response.status_code == 200
    assert seen[0][1]["sender"] == "copilot-analyst" and seen[0][2] == [("analyst", 2)]
    (row,) = rows
    assert (row.source, row.user_id, row.username) == ("analyst", 2, "ana")


def test_a_refused_analyst_request_records_nothing():
    async def scenario(client, ctx):
        seen = []
        with patch.object(talon_triggers, "new_session", ctx.db.session), patch.object(
            talon_service,
            "send_post_request",
            _sending(ctx, seen),
        ):
            response = await client.post(
                "/talon/investigate",
                json={"alert_id": ctx.globex_alert_id, "customer_code": GLOBEX},
                headers=as_user("ana"),
            )
        return response, seen, await triggers(ctx)

    response, seen, rows = call(scenario)
    assert response.status_code in (403, 404) and seen == [] and rows == []


def test_a_customer_portal_request_records_the_portal_and_its_user():
    async def scenario(client, ctx):
        seen = []
        alert = SimpleNamespace(id=ctx.alert_id, customer_code=ACME)
        settings = SimpleNamespace(enabled=True, allow_customer_requests=True, daily_request_limit=None)
        with ExitStack() as stack:
            stack.enter_context(patch.object(talon_triggers, "new_session", ctx.db.session))
            stack.enter_context(patch.object(talon_service, "send_post_request", _sending(ctx, seen)))
            stack.enter_context(patch.object(portal_requests, "ensure_alert_visible", AsyncMock(return_value=alert)))
            stack.enter_context(patch.object(portal_requests, "_locked_settings", AsyncMock(return_value=settings)))
            stack.enter_context(patch.object(portal_requests, "_latest_job", AsyncMock(return_value=None)))
            stack.enter_context(patch.object(portal_requests, "_latest_request", AsyncMock(return_value=None)))
            stack.enter_context(patch.object(portal_requests, "record_audit_event", AsyncMock()))
            stack.enter_context(patch.object(portal_requests, "create_comment", AsyncMock()))
            async with ctx.db.session() as session:
                await portal_requests.request_alert_analysis(ctx.alert_id, harness.user_ns("portal"), session)
        return seen, await triggers(ctx)

    seen, rows = call(scenario)
    assert seen[0][1]["sender"] == "customer-portal" and seen[0][2] == [("portal", 10)]
    (row,) = rows
    assert (row.source, row.user_id, row.username) == ("portal", 10, "portal")


def test_a_replay_records_a_replay_and_who_replayed_it():
    async def scenario(client, ctx):
        seen = []
        report = SimpleNamespace(alert_id=ctx.alert_id, customer_code=ACME)
        session = SimpleNamespace(get=AsyncMock(return_value=report))
        with patch.object(talon_triggers, "new_session", ctx.db.session), patch.object(
            talon_service,
            "send_post_request",
            _sending(ctx, seen),
        ):
            await ai_analyst_routes.replay_report_route(
                report_id=7,
                request=ReplayRequest(customer_code=ACME, template_override="sysmon_event_1.txt"),
                session=session,
                current_user=harness.user_ns("ana"),
            )
        return seen, await triggers(ctx)

    seen, rows = call(scenario)
    assert seen[0][1]["template_override"] == "sysmon_event_1.txt" and seen[0][2] == [("replay", 2)]
    (row,) = rows
    assert (row.source, row.user_id) == ("replay", 2)


@pytest.mark.parametrize("source, sent", [("pipeline", True), ("analyst", True), ("portal", False), ("replay", False)])
def test_when_the_record_cant_be_written_only_an_allowing_sender_still_sends(source, sent):
    seen = []

    async def send(endpoint, data, **kwargs):
        seen.append(endpoint)
        return {"success": True, "data": {}}

    async def broken(*args, **kwargs):
        raise RuntimeError("database down")

    async def run():
        with patch.object(talon_triggers, "record", broken), patch.object(talon_service, "send_post_request", send):
            if source == "replay":
                return await talon_service.replay_investigation(5, ACME, "x.txt")
            return await talon_service.investigate_alert(
                talon_service.TalonInvestigateRequest(alert_id=5, customer_code=ACME),
                source=source,
            )

    try:
        asyncio.run(run())
    except HTTPException as e:
        assert e.status_code == 500 and e.detail == talon_triggers.NOT_RECORDED
    assert seen == (["/investigate"] if sent else [])


def test_an_unknown_source_is_a_programming_error():
    with pytest.raises(ValueError):
        asyncio.run(talon_triggers.record(5, ACME, "copilot-analyst"))


# ── the binding: accepted ─────────────────────────────────────────────────────


@pytest.mark.parametrize("source", ["pipeline", "analyst"])
def test_the_service_account_starts_on_the_alerts_host_with_a_pipeline_or_analyst_record(source):
    async def setup(ctx):
        await add_trigger(ctx, ctx.alert_id, source, user=harness.user_ns("ana") if source == "analyst" else None)

    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id)], setup)
    assert response.status_code == 200 and response.json()["flow_id"] == FLOW and len(vr.starts) == 1
    (event,) = collect_audits(ctx)
    assert event["actor_username"] == SERVICE
    assert event["new_value"] == {
        "artifact_name": "Windows.System.Services",
        "velociraptor_id": VID,
        "alert_id": ctx.alert_id,
        "job_id": JOB,
        "trigger_id": 1,
        "trigger_source": source,
        "trigger_user_id": 2 if source == "analyst" else None,
        "trigger_username": "ana" if source == "analyst" else None,
    }


def test_job_id_may_be_left_out():
    setup = with_triggers(("pipeline", timedelta(minutes=5)))
    (response,), vr, ctx = start(SERVICE, lambda ctx: [{**SERVICES, "alert_id": ctx.alert_id}], setup)
    assert response.status_code == 200 and collect_audits(ctx)[0]["new_value"]["job_id"] is None


def test_the_asset_name_matches_the_host_as_agents_does_whatever_its_letter_case():
    assert talon_triggers._host_is_an_asset([{"asset_name": HOST.lower(), "velociraptor_id": VID.upper()}], HOST, VID)
    assert talon_triggers._host_is_an_asset([{"asset_name": HOST, "velociraptor_id": None}], HOST, VID)
    assert not talon_triggers._host_is_an_asset([{"asset_name": HOST, "velociraptor_id": VID_2}], HOST, VID)
    assert not talon_triggers._host_is_an_asset([{"asset_name": HOST_2, "velociraptor_id": VID}], HOST, VID)
    assert not talon_triggers._host_is_an_asset(None, HOST, VID)


def test_an_analysts_re_trigger_reopens_the_window_and_the_audit_names_that_analyst():
    async def setup(ctx):
        await add_trigger(ctx, ctx.alert_id, "pipeline", ago=timedelta(hours=5))
        await add_trigger(ctx, ctx.alert_id, "analyst", ago=timedelta(minutes=1), user=harness.user_ns("ana"))

    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id)], setup)
    assert response.status_code == 200
    value = collect_audits(ctx)[0]["new_value"]
    assert (value["trigger_source"], value["trigger_user_id"], value["trigger_username"]) == ("analyst", 2, "ana")


# ── the binding: refused ──────────────────────────────────────────────────────


def refused(response, vr, ctx, status, text):
    assert response.status_code == status and response.json()["message"] == text
    assert vr.starts == [] and collect_audits(ctx) == []
    assert HOST not in response.text and JOB not in response.text  # a fixed text, no echo


def test_refused_with_no_record():
    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id)])
    refused(response, vr, ctx, 403, talon_triggers.NO_TRIGGER)


def test_refused_for_an_alert_that_doesnt_exist():
    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, 999999)])
    refused(response, vr, ctx, 403, talon_triggers.NO_TRIGGER)


def test_refused_with_a_portal_record():
    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id)], with_triggers(("portal", timedelta(minutes=1))))
    refused(response, vr, ctx, 403, talon_triggers.PORTAL_TRIGGER)


@pytest.mark.parametrize("newest", ["portal", "replay"])
def test_refused_when_the_newest_record_is_a_portal_request_or_a_replay_after_a_pipeline_one(newest):
    setup = with_triggers(("pipeline", timedelta(minutes=30)), (newest, timedelta(minutes=1)))
    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id)], setup)
    text = talon_triggers.PORTAL_TRIGGER if newest == "portal" else talon_triggers.REPLAY_TRIGGER
    refused(response, vr, ctx, 403, text)


def test_refused_with_a_replay_record():
    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id)], with_triggers(("replay", timedelta(minutes=1))))
    refused(response, vr, ctx, 403, talon_triggers.REPLAY_TRIGGER)


def test_refused_with_an_expired_window():
    setup = with_triggers(("pipeline", talon_triggers.WINDOW + timedelta(minutes=1)))
    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id)], setup)
    refused(response, vr, ctx, 403, talon_triggers.NO_TRIGGER)


def test_refused_for_another_host_of_the_customer():
    async def setup(ctx):
        await add_agents(ctx, agent_row(hostname=HOST_2, vid=VID_2, agent_id="032"))
        await add_trigger(ctx, ctx.alert_id, "pipeline")

    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(body(hostname=HOST_2, vid=VID_2), ctx.alert_id)], setup)
    refused(response, vr, ctx, 403, talon_triggers.NOT_ALERT_HOST)


def test_refused_for_an_asset_added_after_the_alert_was_sent():
    async def setup(ctx):
        await add_agents(ctx, agent_row(hostname=HOST_2, vid=VID_2, agent_id="032"))
        await add_trigger(ctx, ctx.alert_id, "pipeline")
        await add_asset(ctx, ctx.alert_id, name=HOST_2, vid=VID_2)  # e.g. through POST /incidents/…/alert/asset

    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(body(hostname=HOST_2, vid=VID_2), ctx.alert_id)], setup)
    refused(response, vr, ctx, 403, talon_triggers.NOT_ALERT_HOST)


def test_refused_when_the_asset_names_another_client():
    async def setup(ctx):
        async with ctx.db.session() as session:
            for asset in (await session.execute(select(Asset))).scalars().all():
                asset.velociraptor_id = VID_2
            await session.commit()
        await add_trigger(ctx, ctx.alert_id, "pipeline")

    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id)], setup)
    refused(response, vr, ctx, 403, talon_triggers.NOT_ALERT_HOST)


def test_refused_for_a_host_of_another_customer_named_as_the_alerts_asset():
    # A GLOBEX alert whose asset bears the ACME host's name: the service account may reach ACME's
    # host, but not for GLOBEX's alert.
    async def setup(ctx):
        await add_asset(ctx, ctx.globex_alert_id, customer=GLOBEX)
        await add_trigger(ctx, ctx.globex_alert_id, "pipeline", customer=GLOBEX)

    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.globex_alert_id)], setup)
    refused(response, vr, ctx, 403, talon_triggers.NOT_ALERT_HOST)


def test_the_per_alert_cap_counts_every_job_together():
    setup = with_triggers(("pipeline", timedelta(minutes=5)))
    jobs = ["copilot-inv-1-1", "copilot-inv-1-2", "copilot-inv-1-3"]  # a new job each time
    responses, vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id, job) for job in jobs], setup)
    assert [r.status_code for r in responses] == [200] * talon_triggers.PER_ALERT_CAP + [429]
    assert responses[-1].json()["message"] == talon_triggers.ALERT_CAP
    assert len(vr.starts) == talon_triggers.PER_ALERT_CAP == len(collect_audits(ctx))


async def set_cap(ctx, alert_id, starts, ago=timedelta(minutes=10)):
    async with ctx.db.session() as session:
        session.add(
            TalonAutomationAlertCap(alert_id=alert_id, customer_code=ACME, starts=starts, window_started_at=talon_triggers.utcnow() - ago),
        )
        await session.commit()


async def cap_of(ctx, alert_id):
    async with ctx.db.session() as session:
        return await session.get(TalonAutomationAlertCap, alert_id)


def test_the_cap_holds_when_the_audit_write_fails():
    """The audit write is best-effort (``record_audit_event`` logs and swallows its failures): the
    cap never reads it."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.audit.services import audit as audit_service

    async def setup(ctx):
        await add_trigger(ctx, ctx.alert_id, "pipeline")
        ctx.quarantine_audit.side_effect = audit_service.record_audit_event  # the real one

    broken = create_async_engine("sqlite+aiosqlite:////nonexistent-dir/audit.db")
    jobs = ["copilot-inv-1-1", "copilot-inv-1-2", "copilot-inv-1-3"]
    with patch.object(audit_service, "async_engine", broken):
        responses, vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id, job) for job in jobs], setup)
    assert [r.status_code for r in responses] == [200, 200, 429] and len(vr.starts) == talon_triggers.PER_ALERT_CAP


def test_two_concurrent_starts_at_the_cap_minus_one_start_at_most_one_flow():
    async def setup(ctx):
        await add_trigger(ctx, ctx.alert_id, "pipeline")
        await set_cap(ctx, ctx.alert_id, talon_triggers.PER_ALERT_CAP - 1)

    responses, vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id, f"copilot-inv-1-{n}") for n in (1, 2)], setup, True)
    assert sorted(r.status_code for r in responses) == [200, 429] and len(vr.starts) == 1


def test_concurrent_reservations_on_separate_connections_take_exactly_the_cap(tmp_path):
    """``reserve`` alone, many at once, each in its own connection to one database file: exactly
    ``PER_ALERT_CAP`` slots are taken, the rest refused (the row created once, by whichever wins)."""
    from sqlalchemy.ext.asyncio import AsyncSession as Session
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy.ext.asyncio import create_async_engine

    async def run():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'cap.db'}", connect_args={"timeout": 30})
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=[TalonAutomationAlertCap.__table__]))
        factory = async_sessionmaker(engine, class_=Session, expire_on_commit=False)
        binding = talon_triggers.Binding(alert_id=7, customer_code=ACME, trigger_id=1, source="pipeline", user_id=None, username=None)

        async def one():
            try:
                await talon_triggers.reserve(binding)
                return 200
            except HTTPException as e:
                return e.status_code

        try:
            with patch.object(talon_triggers, "new_session", factory):
                outcomes = await asyncio.gather(*(one() for _ in range(6)))
                async with factory() as session:
                    row = await session.get(TalonAutomationAlertCap, 7)
            return outcomes, row
        finally:
            await engine.dispose()

    outcomes, row = asyncio.run(run())
    assert sorted(outcomes) == [200] * talon_triggers.PER_ALERT_CAP + [429] * (6 - talon_triggers.PER_ALERT_CAP)
    assert row.starts == talon_triggers.PER_ALERT_CAP


def test_a_passed_window_starts_a_new_one():
    async def setup(ctx):
        await add_trigger(ctx, ctx.alert_id, "pipeline")
        await set_cap(ctx, ctx.alert_id, talon_triggers.PER_ALERT_CAP, ago=talon_triggers.WINDOW + timedelta(minutes=1))

    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id)], setup)
    assert response.status_code == 200


def test_the_cap_is_per_alert():
    async def setup(ctx):
        await add_trigger(ctx, ctx.alert_id, "pipeline")
        await set_cap(ctx, ctx.alert_id + 100, talon_triggers.PER_ALERT_CAP)

    (response,), vr, ctx = start(SERVICE, lambda ctx: [bound(SERVICES, ctx.alert_id)], setup)
    assert response.status_code == 200


def test_a_slot_that_cant_be_recorded_is_no_start():
    async def broken(*args, **kwargs):
        raise RuntimeError("database down")

    with patch.object(talon_triggers, "_take_slot", broken):
        (response,), vr, ctx = start(
            SERVICE,
            lambda ctx: [bound(SERVICES, ctx.alert_id)],
            with_triggers(("pipeline", timedelta(minutes=5))),
        )
    refused(response, vr, ctx, 500, talon_triggers.CAP_UNRECORDED)


def test_a_refused_binding_takes_no_slot():
    async def check(ctx):
        return await cap_of(ctx, ctx.alert_id)

    async def scenario(client, ctx):
        responses, vr, _ = await scenario_for(
            SERVICE,
            lambda ctx: [bound(SERVICES, ctx.alert_id)],
            with_triggers(("portal", timedelta(minutes=1))),
        )(client, ctx)
        return responses, await check(ctx)

    (response,), row = call(scenario)
    assert response.status_code == 403 and row is None


# ── the body, and everyone else ───────────────────────────────────────────────


def test_alert_id_and_job_id_are_no_longer_a_422_and_other_users_are_unchanged():
    # An analyst naming an alert CoPilot never sent: the binding is the service account's alone.
    (response,), vr, ctx = start("ana", lambda ctx: [bound(body(), ctx.alert_id)])
    assert response.status_code == 200 and len(vr.starts) == 1
    (event,) = collect_audits(ctx)
    assert event["new_value"] == {"artifact_name": "Windows.System.Pslist", "velociraptor_id": VID}


def test_the_service_account_without_alert_id_starts_as_before():
    (response,), vr, ctx = start(SERVICE, lambda ctx: [SERVICES])
    assert response.status_code == 200 and len(vr.starts) == 1
    assert set(collect_audits(ctx)[0]["new_value"]) == {"artifact_name", "velociraptor_id"}


@pytest.mark.parametrize(
    "extra",
    [
        {"alert_id": 0},
        {"alert_id": "1; DROP"},
        {"job_id": ""},
        {"job_id": "a" * 65},
        {"job_id": "job id"},
        {"job_id": "x‮"},
        {"jobid": "x"},
    ],
)
def test_a_malformed_alert_id_or_job_id_is_a_422_that_starts_nothing(extra):
    (response,), vr, ctx = start(SERVICE, lambda ctx: [{**SERVICES, **extra}])
    assert response.status_code == 422 and vr.starts == []


# ── the migration ─────────────────────────────────────────────────────────────


def test_the_migration_creates_the_models_table_on_the_single_head():
    path = next((Path(__file__).resolve().parents[1] / "alembic" / "versions").glob("c2a2a0b1d3e4_*.py"))
    spec = importlib.util.spec_from_file_location("ap2a_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "f1289a0b1c2d" and migration.TABLE == TalonInvestigationTrigger.__tablename__
    assert migration.CAP_TABLE == TalonAutomationAlertCap.__tablename__
    assert [c.name for c in TalonAutomationAlertCap.__table__.columns] == ["alert_id", "customer_code", "starts", "window_started_at"]
    table = TalonInvestigationTrigger.__table__
    assert {c.name for c in table.columns} == {"id", "alert_id", "customer_code", "source", "user_id", "username", "assets", "sent_at"}
    assert {i.name for i in table.indexes} == {migration.INDEX}
    assert talon_collections.talon_triggers is talon_triggers  # the start route uses this module
