"""The per-customer automation policy, the global automation switch, the dry-run route, and the
policy checks on the Talon service account's collection start (talon-analyst plan AP-2; SPEC D85,
D86, INV-ACT-1; ``services/talon_automation.py``, ``services/talon_collections.py``).

The harness is ``test_talon_collect_start``'s (real routers, a real in-memory database, the ACME
alert sent by the pipeline with HOST as its asset), with ACME's policy at level 1 ``auto`` and the
switch on unless a test says otherwise.

Pinned here:
- the service account's start is refused, with its fixed text and nothing started, for: the switch
  off, no policy row (fail closed), the level off, ``shadow``, ``propose``, an artifact of another
  level (a catalogue artifact is level 2, which isn't startable yet even on ``auto``), a missing,
  portal or replay trigger, a host that isn't the alert's asset, and over each cap (per alert, per
  host, per customer), in the plan's order;
- an accepted start writes its ``talon_automation_start`` row and its ``talon_automation.start``
  audit row before the flow, then the flow id; a cap refusal keeps nothing (the alert's slot
  included); the policy is read again in the reservation (a change after the first check stops the
  start); no committed record, no start;
- the dry run starts nothing (no flow, no slot, no ``ARTIFACT_COLLECT``) and records its verdict,
  ``would_start`` or the refusal's code, counting its own rows for the caps, never the ``auto`` ones;
- the policy routes: any mode set directly (no gate); the service account refused (whatever its
  role), an analyst and a demoted admin refused; level 3 or 4 raised only with ``acknowledge_risk``;
  no level raised for a customer the service user isn't assigned to (lowering still allowed); the
  audit's old and new values; the switch's routes likewise;
- other users' starts are unchanged and recorded nowhere here;
- the migration: a single head on AP-2a's, its tables the models'.

Run with: cd backend && python -m pytest tests/test_talon_automation_policy.py
"""

import importlib.util
import os
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import pytest  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import update  # noqa: E402

import tests.test_talon_actions as harness  # noqa: E402
from app.audit.models.audit import AuditAction  # noqa: E402
from app.audit.models.audit import AuditLog  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonAutomationAlertCap  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonAutomationPolicy  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonAutomationStart  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonInvestigationTrigger  # noqa: E402
from app.connectors.talon.services import talon_automation as automation  # noqa: E402
from app.connectors.talon.services import talon_collections  # noqa: E402
from app.connectors.talon.services import talon_triggers  # noqa: E402
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
from tests.test_talon_collect_start import TRIGGERED_ALERT  # noqa: E402
from tests.test_talon_collect_start import add_agents  # noqa: E402
from tests.test_talon_collect_start import body  # noqa: E402
from tests.test_talon_collect_start import (  # noqa: E402,F401 - autouse
    built_in_velociraptor_definitions,
)
from tests.test_talon_collect_start import call  # noqa: E402
from tests.test_talon_collect_start import collect_audits  # noqa: E402
from tests.test_talon_collect_start import configure  # noqa: E402
from tests.test_talon_collect_start import set_policy  # noqa: E402
from tests.test_talon_endpoint_actions import FLOW  # noqa: E402
from tests.test_talon_endpoint_actions import Velociraptor  # noqa: E402
from tests.test_talon_investigation_triggers import add_trigger  # noqa: E402

DRY_RUN = "/talon/v2/automation/dry-run"
SWITCH = "/talon/v2/settings/automation"
JOB = "copilot-inv-1-1761048000000"
HOST_2, VID_2 = "WIN-ACME-02", "C.00000000000000b2"


def policy_url(code=ACME):
    return f"/talon/v2/automation/{code}"


def put_body(level_1="off", level_2="off", level_3="off", level_4="off", v=1, **extra):
    """A policy PUT; ``v`` is ``expected_version`` (ACME's seeded row is at 1; no row is 0)."""
    modes = {"level_1_mode": level_1, "level_2_mode": level_2, "level_3_mode": level_3, "level_4_mode": level_4}
    return {**modes, "expected_version": v, **extra}


def policy_audits(ctx):
    """The policy and switch changes' audit rows, written in the changes' own transactions."""
    return [a for a in ctx.audit_rows if a.action == AuditAction.TALON_AUTOMATION_POLICY_UPDATE.value]


def refusal_audits(ctx):
    """Refused changes, audited as failures through ``record_audit_event``."""
    return [c.kwargs for c in ctx.audit.await_args_list]


SERVICES_BOUND = {**SERVICES, "job_id": JOB}


# ── helpers ───────────────────────────────────────────────────────────────────


async def starts_of(ctx):
    async with ctx.db.session() as session:
        return (await session.execute(select(TalonAutomationStart).order_by(TalonAutomationStart.id))).scalars().all()


async def audit_rows(ctx):
    async with ctx.db.session() as session:
        return (await session.execute(select(AuditLog).order_by(AuditLog.id))).scalars().all()


async def cap_of(ctx, alert_id=TRIGGERED_ALERT):
    async with ctx.db.session() as session:
        return await session.get(TalonAutomationAlertCap, alert_id)


def run(posts, *, setup=None, allowed=None, policy_audit=None):
    """Configure the allowlist and ACME's level 1 on ``auto``, seed with ``setup(ctx)``, then send
    each ``(name, route, payload)``. Answers the responses, the Velociraptor recorder, and ctx."""

    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            stack.enter_context(patch.object(automation, "record_audit_event", ctx.audit))
            if allowed is None:
                await configure(ctx)
            else:
                await configure(ctx, allowed)
            if setup is not None:
                await setup(ctx)
            responses = []
            for name, method, route, payload in posts:
                responses.append(await client.request(method, route, json=payload, headers=as_user(name)))
            ctx.starts_after = await starts_of(ctx)
            ctx.audit_rows = await audit_rows(ctx)
            ctx.cap = await cap_of(ctx)
        return responses, vr, ctx

    return call(scenario)


def starts(*payloads, name=SERVICE, setup=None):
    return run([(name, "POST", ROUTE, p) for p in payloads], setup=setup)


def policy(**kwargs):
    async def setup(ctx):
        await set_policy(ctx, **kwargs)

    return setup


def message(response):
    return response.json().get("message")


# ── the start: refused in the plan's order ────────────────────────────────────


@pytest.mark.parametrize(
    "kwargs, text",
    [
        ({"automation": False}, automation.AUTOMATION_OFF),
        ({"level_1": None}, automation.NO_POLICY),  # no row: every level off
        ({"level_1": "off"}, automation.LEVEL_OFF),
        ({"level_1": "shadow"}, automation.LEVEL_SHADOW),
        ({"level_1": "propose"}, automation.LEVEL_PROPOSE),
        ({"automation": False, "level_1": None}, automation.AUTOMATION_OFF),  # the switch first
    ],
)
def test_the_service_accounts_start_needs_the_switch_the_row_and_level_1_on_auto(kwargs, text):
    (response,), vr, ctx = starts(SERVICES_BOUND, setup=policy(**kwargs))
    assert response.status_code == 403 and message(response) == text
    assert vr.starts == [] and collect_audits(ctx) == [] and ctx.starts_after == [] and ctx.cap is None


@pytest.mark.parametrize(
    "payload, modes, text",
    [
        # A catalogue artifact outside the auto-run subset is level 2 (CoPilot's own classification).
        (body("Windows.System.DNSCache"), {}, automation.LEVEL_OFF),
        (body("Windows.Forensics.Prefetch"), {}, automation.LEVEL_OFF),
        # Level 2 on auto: CoPilot can't start level 2 yet (AP-6), so still nothing.
        (body("Windows.System.DNSCache"), {"level_2_mode": "auto"}, automation.LEVEL_NOT_AVAILABLE),
        # No level at all: never startable by the service account.
        (body("Windows.System.CmdShell"), {"level_2_mode": "auto"}, talon_collections.SERVICE_REFUSED),
        (body("Generic.Collectors.File"), {"level_2_mode": "auto"}, talon_collections.SERVICE_REFUSED),
    ],
)
def test_an_artifact_of_another_level_is_refused(payload, modes, text):
    (response,), vr, ctx = starts(payload, setup=policy(**modes))
    assert response.status_code == 403 and message(response) == text
    assert vr.starts == [] and ctx.starts_after == []


def test_the_level_1_mode_of_another_customer_doesnt_count():
    async def setup(ctx):
        await set_policy(ctx, level_1=None)
        await set_policy(ctx, customer=GLOBEX)

    (response,), vr, ctx = starts(SERVICES_BOUND, setup=setup)
    assert response.status_code == 403 and message(response) == automation.NO_POLICY and vr.starts == []


def test_the_policy_comes_before_the_allowlist_and_the_trigger():
    async def setup(ctx):
        await set_policy(ctx, level_1="off")
        async with ctx.db.session() as session:
            await session.execute(delete(TalonInvestigationTrigger))
            await session.commit()

    (response,), vr, ctx = starts(SERVICES_BOUND, setup=setup)
    assert message(response) == automation.LEVEL_OFF
    (response,), vr, ctx = run([(SERVICE, "POST", ROUTE, SERVICES_BOUND)], allowed=[], setup=policy(level_1="off"))
    assert message(response) == automation.LEVEL_OFF  # before EA-4b's allowlist


def test_the_alert_requirement_stays_first():
    payload = {k: v for k, v in SERVICES.items() if k != "alert_id"}
    (response,), vr, ctx = starts(payload, setup=policy(automation=False, level_1=None))
    assert response.status_code == 403 and message(response) == talon_triggers.ALERT_REQUIRED


async def _no_triggers(ctx):
    async with ctx.db.session() as session:
        await session.execute(delete(TalonInvestigationTrigger))
        await session.commit()


async def _portal(ctx):
    await add_trigger(ctx, TRIGGERED_ALERT, "portal", user=harness.user_ns("portal"))


async def _replay(ctx):
    await add_trigger(ctx, TRIGGERED_ALERT, "replay", user=harness.user_ns("ana"))


async def _second_host(ctx):
    await add_agents(ctx, agent_row(HOST_2, VID_2, agent_id="022"))


@pytest.mark.parametrize(
    "setup, payload, text",
    [
        (_no_triggers, SERVICES_BOUND, talon_triggers.NO_TRIGGER),
        (_portal, SERVICES_BOUND, talon_triggers.PORTAL_TRIGGER),
        (_replay, SERVICES_BOUND, talon_triggers.REPLAY_TRIGGER),
        (_second_host, body("Windows.System.Pslist", hostname=HOST_2, vid=VID_2), talon_triggers.NOT_ALERT_HOST),
    ],
)
def test_the_trigger_checks_still_hold_on_auto(setup, payload, text):
    (response,), vr, ctx = starts(payload, setup=setup)
    assert response.status_code == 403 and message(response) == text
    assert vr.starts == [] and ctx.starts_after == [] and ctx.cap is None


# ── the start: accepted, recorded before the flow ─────────────────────────────


def test_an_accepted_start_is_recorded_and_audited_before_the_flow_then_gets_its_flow_id():
    seen = {}
    real_start = talon_collections.velociraptor_routes.start_collection_as

    async def start_collection_as(*args, **kwargs):
        # What was committed when the flow was about to start.
        async with seen["ctx"].db.session() as session:
            seen["rows"] = (await session.execute(select(TalonAutomationStart))).scalars().all()
            seen["audits"] = (await session.execute(select(AuditLog))).scalars().all()
        return await real_start(*args, **kwargs)

    async def setup(ctx):
        seen["ctx"] = ctx

    with patch.object(talon_collections.velociraptor_routes, "start_collection_as", start_collection_as):
        (response,), vr, ctx = starts(SERVICES_BOUND, setup=setup)
    assert response.status_code == 200 and response.json()["flow_id"] == FLOW and len(vr.starts) == 1
    (before,) = seen["rows"]
    assert (before.verdict, before.flow_id, before.mode, before.level) == ("reserved", None, "auto", 1)
    (audit,) = seen["audits"]
    assert audit.action == AuditAction.TALON_AUTOMATION_START.value == "talon_automation.start"
    assert (audit.actor_username, audit.customer_code, audit.entity_id) == (SERVICE, ACME, str(before.id))
    assert audit.new_value == {
        "automation_start_id": before.id,
        "level": 1,
        "mode": "auto",
        "artifact": "Windows.System.Services",
        "hostname": HOST,
        "velociraptor_id": VID,
        "policy_version": 1,
        "alert_id": TRIGGERED_ALERT,
        "job_id": JOB,
        "trigger_id": 1,
        "trigger_source": "pipeline",
        "trigger_user_id": None,
        "trigger_username": None,
    }
    (row,) = ctx.starts_after
    assert (row.verdict, row.flow_id, row.customer_code, row.alert_id, row.job_id) == ("started", FLOW, ACME, TRIGGERED_ALERT, JOB)
    assert (row.hostname, row.velociraptor_id, row.artifact) == (HOST, VID, "Windows.System.Services")
    assert row.parameters == [["Calculate_hashes", "N"], ["CertificateInfo", "N"]] and row.finished_at is not None
    (collect,) = collect_audits(ctx)
    assert collect["new_value"]["automation_start_id"] == row.id
    assert ctx.cap.starts == 1


def test_a_start_velociraptor_refuses_is_failed_on_its_record():
    async def refuse(*args, **kwargs):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="not on this host")

    with patch.object(talon_collections.velociraptor_routes, "start_collection_as", refuse):
        (response,), vr, ctx = starts(SERVICES_BOUND)
    assert response.status_code == 400
    (row,) = ctx.starts_after
    assert (row.verdict, row.code, row.flow_id) == ("failed", "HTTP_400", None)


def test_no_committed_record_means_no_start():
    def broken(**kwargs):
        raise RuntimeError("database gone")

    with patch.object(automation, "_start_row", broken):
        (response,), vr, ctx = starts(SERVICES_BOUND)
    assert response.status_code == 500 and message(response) == talon_triggers.CAP_UNRECORDED
    assert vr.starts == [] and collect_audits(ctx) == [] and ctx.starts_after == [] and ctx.audit_rows == []
    assert ctx.cap.starts == 0  # the slot was rolled back with the record


def test_the_reservation_reads_the_policy_again():
    """A level turned off between the first check and the reservation stops the start (CoPilot
    enforces its current policy)."""
    real_check = talon_triggers.check
    seen = {}

    async def check(*args, **kwargs):
        binding = await real_check(*args, **kwargs)
        async with seen["ctx"].db.session() as session:
            await session.execute(
                update(TalonAutomationPolicy).where(TalonAutomationPolicy.customer_code == ACME).values(level_1_mode="off"),
            )
            await session.commit()
        return binding

    async def setup(ctx):
        seen["ctx"] = ctx

    with patch.object(talon_triggers, "check", check):
        (response,), vr, ctx = starts(SERVICES_BOUND, setup=setup)
    assert response.status_code == 403 and message(response) == automation.LEVEL_OFF
    assert vr.starts == [] and ctx.starts_after == [] and ctx.cap.starts == 0


# ── the caps ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "caps, text",
    [
        ({"per_alert": 1}, talon_triggers.ALERT_CAP),
        ({"per_host_hour": 1}, automation.HOST_CAP),
        ({"per_customer_hour": 1}, automation.CUSTOMER_CAP),
    ],
)
def test_each_cap_refuses_the_next_start_and_keeps_nothing_of_it(caps, text):
    (first, second), vr, ctx = starts(SERVICES_BOUND, SERVICES_BOUND, setup=policy(caps=caps))
    assert first.status_code == 200 and second.status_code == 429 and message(second) == text
    assert len(vr.starts) == 1 and [r.verdict for r in ctx.starts_after] == ["started"]
    assert ctx.cap.starts == 1  # a host or customer refusal gives the alert's slot back
    assert [a.action for a in ctx.audit_rows] == [AuditAction.TALON_AUTOMATION_START.value]


def test_the_default_caps():
    assert automation.CAP_DEFAULTS["per_alert"] == talon_triggers.PER_ALERT_CAP == 2
    assert (automation.CAP_DEFAULTS["per_host_hour"], automation.CAP_DEFAULTS["per_customer_hour"]) == (6, 10)
    (first, second, third), vr, ctx = starts(SERVICES_BOUND, SERVICES_BOUND, SERVICES_BOUND)
    assert [r.status_code for r in (first, second, third)] == [200, 200, 429] and message(third) == talon_triggers.ALERT_CAP


def _earlier_starts(caps, clients):
    """``caps`` on ACME's policy, and earlier ``auto`` starts this hour for other alerts on ``clients``."""

    async def setup(ctx):
        await set_policy(ctx, caps=caps)
        async with ctx.db.session() as session:
            for alert_id, client in enumerate(clients, start=50):
                session.add(
                    TalonAutomationStart(
                        customer_code=ACME,
                        alert_id=alert_id,
                        hostname=HOST,
                        velociraptor_id=client,
                        level=1,
                        mode="auto",
                        verdict="started",
                        created_at=talon_triggers.utcnow(),
                    ),
                )
            await session.commit()

    return setup


def test_the_host_cap_counts_every_alert_on_the_host():
    (first, second), vr, ctx = starts(SERVICES_BOUND, SERVICES_BOUND, setup=_earlier_starts({"per_host_hour": 3}, [VID, VID]))
    assert first.status_code == 200 and message(second) == automation.HOST_CAP


def test_the_customer_cap_counts_every_host_of_the_customer():
    setup = _earlier_starts({"per_host_hour": 3, "per_customer_hour": 4}, [VID, VID_2, VID_2])
    (first, second), vr, ctx = starts(SERVICES_BOUND, SERVICES_BOUND, setup=setup)
    assert first.status_code == 200 and message(second) == automation.CUSTOMER_CAP


def test_an_old_start_no_longer_counts():
    async def setup(ctx):
        await set_policy(ctx, caps={"per_host_hour": 1})
        async with ctx.db.session() as session:
            session.add(
                TalonAutomationStart(
                    customer_code=ACME,
                    alert_id=50,
                    hostname=HOST,
                    velociraptor_id=VID,
                    level=1,
                    mode="auto",
                    verdict="started",
                    created_at=talon_triggers.utcnow() - automation.HOUR - automation.HOUR / 60,
                ),
            )
            await session.commit()

    (response,), vr, ctx = starts(SERVICES_BOUND, setup=setup)
    assert response.status_code == 200


# ── the dry run ───────────────────────────────────────────────────────────────


def dry_runs(*payloads, name=SERVICE, setup=None):
    return run([(name, "POST", DRY_RUN, p) for p in payloads], setup=setup)


@pytest.mark.parametrize("mode", ["shadow", "auto"])
def test_a_dry_run_starts_nothing_and_records_would_start(mode):
    (response,), vr, ctx = dry_runs(SERVICES_BOUND, setup=policy(level_1=mode))
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    out = response.json()
    assert out["verdict"] == "would_start" and out["code"] is None and out["status_code"] is None
    assert (out["level"], out["mode"]) == (1, mode) and out["message"] == talon_collections.WOULD_START_TEXT
    assert vr.starts == [] and collect_audits(ctx) == [] and ctx.cap is None and ctx.audit_rows == []
    (row,) = ctx.starts_after
    assert row.id == out["record_id"] and (row.mode, row.verdict, row.level) == ("shadow", "would_start", 1)
    assert (row.alert_id, row.job_id, row.trigger_source, row.policy_version) == (TRIGGERED_ALERT, JOB, "pipeline", 1)
    assert row.parameters == [["Calculate_hashes", "N"], ["CertificateInfo", "N"]] and row.flow_id is None


@pytest.mark.parametrize(
    "setup, payload, status, code",
    [
        (policy(automation=False), SERVICES_BOUND, 403, "AUTOMATION_OFF"),
        (policy(level_1=None), SERVICES_BOUND, 403, "NO_POLICY"),
        (policy(level_1="off"), SERVICES_BOUND, 403, "LEVEL_OFF"),
        (policy(level_1="propose"), SERVICES_BOUND, 403, "LEVEL_PROPOSE"),
        (policy(level_1="shadow"), body("Windows.System.DNSCache"), 403, "LEVEL_OFF"),
        (_portal, SERVICES_BOUND, 403, "PORTAL_TRIGGER"),
        (_replay, SERVICES_BOUND, 403, "REPLAY_TRIGGER"),
        (_no_triggers, SERVICES_BOUND, 403, "NO_TRIGGER"),
        (_second_host, body("Windows.System.Pslist", hostname=HOST_2, vid=VID_2), 403, "NOT_ALERT_HOST"),
    ],
)
def test_a_refused_dry_run_records_its_code(setup, payload, status, code):
    (response,), vr, ctx = dry_runs(payload, setup=setup)
    out = response.json()
    assert response.status_code == 200 and out["verdict"] == "refused"
    assert (out["code"], out["status_code"]) == (code, status) and out["message"].startswith("not started:")
    (row,) = ctx.starts_after
    assert (row.mode, row.verdict, row.code) == ("shadow", "refused", code) and vr.starts == []


def test_a_dry_run_with_a_changed_definition_is_refused():
    async def setup(ctx):
        await configure(ctx, hashes={})

    (response,), vr, ctx = dry_runs(SERVICES_BOUND, setup=setup)
    assert response.json()["code"] == "DEFINITION_CHANGED" and vr.starts == []


def test_dry_runs_are_capped_by_their_own_rows_never_the_auto_ones():
    (a, b, c), vr, ctx = dry_runs(SERVICES_BOUND, SERVICES_BOUND, SERVICES_BOUND, setup=policy(level_1="auto"))
    assert [r.json()["verdict"] for r in (a, b, c)] == ["would_start", "would_start", "refused"]
    assert c.json()["code"] == "ALERT_CAP" and ctx.cap is None
    # Two dry runs then two starts: the dry runs took no slot.
    responses, vr, ctx = run([(SERVICE, "POST", r, SERVICES_BOUND) for r in (DRY_RUN, DRY_RUN, ROUTE, ROUTE)])
    assert [r.status_code for r in responses] == [200] * 4 and len(vr.starts) == 2
    assert [(r.mode, r.verdict) for r in ctx.starts_after] == [("shadow", "would_start")] * 2 + [("auto", "started")] * 2


def test_dry_runs_are_bounded_per_customer_per_hour():
    with patch.object(automation, "DRY_RUNS_PER_CUSTOMER_HOUR", 3):
        responses, vr, ctx = dry_runs(SERVICES_BOUND, SERVICES_BOUND, SERVICES_BOUND, SERVICES_BOUND, setup=policy(level_1="shadow"))
    assert [r.status_code for r in responses] == [200, 200, 200, 429]  # refused verdicts count too (the third is ALERT_CAP)
    assert message(responses[3]) == automation.DRY_RUN_CAP and len(ctx.starts_after) == 3 and vr.starts == []
    assert automation.DRY_RUNS_PER_CUSTOMER_HOUR == 60


def test_a_dry_run_is_the_service_accounts_and_behind_talon_v2():
    (response,), vr, ctx = dry_runs(SERVICES_BOUND, name="ana")
    assert response.status_code == 403 and message(response) == talon_collections.DRY_RUN_SERVICE_ONLY and ctx.starts_after == []
    payload = {k: v for k, v in SERVICES.items() if k != "alert_id"}
    (response,), vr, ctx = dry_runs(payload)
    assert response.status_code == 403 and message(response) == talon_triggers.ALERT_REQUIRED and ctx.starts_after == []

    async def scenario(client, ctx):
        return await client.post(DRY_RUN, json=SERVICES_BOUND, headers=as_user(SERVICE))

    assert call(scenario, enabled=False).status_code == 404
    assert call(lambda client, ctx: client.post(DRY_RUN, json=SERVICES_BOUND, headers=as_user("portal"))).status_code == 403


def test_a_dry_run_that_cant_be_recorded_is_a_500():
    def broken(**kwargs):
        raise RuntimeError("database gone")

    with patch.object(automation, "_start_row", broken):
        (response,), vr, ctx = dry_runs(SERVICES_BOUND)
    assert response.status_code == 500 and message(response) == automation.DRY_RUN_UNRECORDED and vr.starts == []


# ── other users are unchanged ─────────────────────────────────────────────────


def test_an_analysts_start_needs_no_policy_and_is_recorded_nowhere_here():
    (response,), vr, ctx = run([("ana", "POST", ROUTE, body("Windows.System.DNSCache"))], setup=policy(automation=False, level_1=None))
    assert response.status_code == 200 and len(vr.starts) == 1 and ctx.starts_after == [] and ctx.audit_rows == []


# ── the policy routes ─────────────────────────────────────────────────────────


def test_no_row_reads_as_every_level_off():
    (response,), vr, ctx = run([("admin", "GET", policy_url(), None)], setup=policy(level_1=None, automation=False))
    out = response.json()
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert out["exists"] is False and out["version"] == 0 and out["automation_enabled"] is False
    assert [out[f"level_{n}_mode"] for n in (1, 2, 3, 4)] == ["off"] * 4
    assert out["effective_caps"] == dict(automation.CAP_DEFAULTS) and out["startable_levels"] == [1]
    assert out["service_user_assigned"] is True and out["risk_acknowledgement_text"] == automation.RISK_TEXT


@pytest.mark.parametrize("mode", ["shadow", "propose", "auto"])
def test_any_mode_can_be_set_directly(mode):
    responses, vr, ctx = run(
        [("admin", "PUT", policy_url(), put_body(level_1=mode, level_2=mode, v=0)), ("admin", "GET", policy_url(), None)],
        setup=policy(level_1=None),
    )
    put, get = responses
    assert put.status_code == 200 and put.json()["level_1_mode"] == put.json()["level_2_mode"] == mode
    assert get.json()["version"] == 1 and get.json()["updated_by_username"] == "admin" and get.json()["exists"] is True


def test_a_put_is_audited_with_the_old_and_new_values_in_its_transaction():
    responses, vr, ctx = run(
        [
            ("admin", "PUT", policy_url(), put_body(level_1="shadow", v=0)),
            ("admin", "PUT", policy_url(), put_body(level_1="auto", caps={"per_host_hour": 3}, v=1)),
        ],
        setup=policy(level_1=None),
    )
    assert [r.status_code for r in responses] == [200, 200] and responses[1].json()["version"] == 2
    assert responses[1].json()["effective_caps"]["per_host_hour"] == 3
    first, second = policy_audits(ctx)
    assert (first.customer_code, first.entity_type, first.entity_id, first.result) == (ACME, "talon_automation_policy", ACME, "success")
    assert first.old_value == {
        "exists": False,
        "level_1_mode": "off",
        "level_2_mode": "off",
        "level_3_mode": "off",
        "level_4_mode": "off",
        "version": 0,
    }
    assert first.new_value["level_1_mode"] == "shadow" and first.new_value["version"] == 1
    assert second.old_value["level_1_mode"] == "shadow" and second.old_value["caps"] is None
    assert second.new_value["level_1_mode"] == "auto" and second.new_value["caps"] == {"per_host_hour": 3}
    assert second.new_value["acknowledge_risk"] is False and second.actor_username == "admin"
    assert refusal_audits(ctx) == []


def test_a_change_whose_audit_row_cant_be_written_isnt_made():
    def broken(**kwargs):
        raise RuntimeError("audit table gone")

    async def scenario(client, ctx):
        await set_policy(ctx)
        with patch.object(automation, "_audit_row", broken):
            with pytest.raises(RuntimeError):  # the test client raises the app's exception
                await client.put(policy_url(), json=put_body(level_1="shadow"), headers=as_user("admin"))
        async with ctx.db.session() as session:
            return await session.get(TalonAutomationPolicy, ACME)

    row = call(scenario)
    assert (row.level_1_mode, row.version) == ("auto", 1)  # unchanged


def test_expected_version_is_required_and_checked():
    responses, vr, ctx = run(
        [
            ("admin", "PUT", policy_url(), {k: v for k, v in put_body(level_1="off").items() if k != "expected_version"}),
            ("admin", "PUT", policy_url(), put_body(level_1="off", v=0)),  # ACME's row is at 1
        ],
    )
    missing, stale = responses
    assert missing.status_code == 422
    assert stale.status_code == 409 and message(stale) == automation.VERSION_CHANGED
    assert policy_audits(ctx) == []
    (refused,) = refusal_audits(ctx)
    assert refused["action"] == AuditAction.TALON_AUTOMATION_POLICY_UPDATE and refused["result"].value == "failure"
    assert refused["customer_code"] == ACME and "409" in refused["details"] and refused["new_value"]["expected_version"] == 0


@pytest.mark.parametrize("level", ["level_3", "level_4"])
def test_raising_level_3_or_4_needs_the_acknowledgement(level):
    responses, vr, ctx = run(
        [
            ("admin", "PUT", policy_url(), put_body(level_1="auto", **{level: "shadow"}, v=1)),
            ("admin", "PUT", policy_url(), put_body(level_1="auto", **{level: "shadow"}, acknowledge_risk=True, v=1)),
            ("admin", "PUT", policy_url(), put_body(level_1="auto", **{level: "auto"}, v=2)),  # shadow → auto is a raise too
            ("admin", "PUT", policy_url(), put_body(level_1="auto", **{level: "shadow"}, v=2)),  # lowering needs nothing
            ("admin", "PUT", policy_url(), put_body(level_1="auto", v=3)),
        ],
    )
    refused, acknowledged, again, lowered, off = responses
    assert refused.status_code == 400 and message(refused) == automation.RISK_NOT_ACKNOWLEDGED
    assert acknowledged.status_code == 200 and acknowledged.json()["risk_acknowledged_by_username"] == "admin"
    assert acknowledged.json()["risk_acknowledged_at"] is not None
    assert again.status_code == 400 and lowered.status_code == 200 and off.status_code == 200
    assert off.json()["risk_acknowledged_by_username"] is None  # both off: the next raise asks again
    audits = policy_audits(ctx)
    assert len(audits) == 3 and audits[0].new_value["acknowledge_risk"] is True
    assert audits[0].new_value["risk_acknowledged_by_username"] == "admin"
    assert [a["details"] for a in refusal_audits(ctx)] == [f"Refused (HTTP 400): {automation.RISK_NOT_ACKNOWLEDGED}"] * 2


def test_an_unassigned_customer_cant_be_raised_but_can_be_lowered():
    async def setup(ctx):
        await set_policy(ctx, customer=GLOBEX)  # left at level 1 from before the service user lost GLOBEX

    responses, vr, ctx = run(
        [
            ("admin", "GET", policy_url(GLOBEX), None),
            ("admin", "PUT", policy_url(GLOBEX), put_body(level_1="auto", level_2="shadow")),
            ("admin", "PUT", policy_url(GLOBEX), put_body(level_1="auto")),  # nothing raised
            ("admin", "PUT", policy_url(GLOBEX), put_body(level_1="off", v=2)),
        ],
        setup=setup,
    )
    get, raised, kept, lowered = responses
    assert get.json()["service_user_assigned"] is False
    assert raised.status_code == 409 and message(raised) == automation.SERVICE_USER_UNASSIGNED
    assert kept.status_code == 200 and lowered.status_code == 200 and lowered.json()["level_1_mode"] == "off"
    assert [a["customer_code"] for a in refusal_audits(ctx)] == [GLOBEX]


def test_the_service_account_as_an_admin_is_refused_on_every_policy_route():
    async def scenario(client, ctx):
        with patch.object(automation, "record_audit_event", ctx.audit):
            responses = [
                await client.request(method, route, json=payload, headers=as_user(SERVICE))
                for method, route, payload in [
                    ("GET", policy_url(), None),
                    ("PUT", policy_url(), put_body(level_1="auto")),
                    ("GET", SWITCH, None),
                    ("PUT", SWITCH, {"automation_enabled": True}),
                ]
            ]
        return responses, ctx

    with patch.dict(harness.SCOPES, {SERVICE: ["admin"]}), patch.dict(harness.USERS, {SERVICE: (20, 1, [])}):
        responses, ctx = call(scenario, users=False)
    assert [r.status_code for r in responses] == [403] * 4
    assert {message(r) for r in responses} == {automation.SERVICE_REFUSED}
    # The two PUTs are audited as refused, with the service account as the actor.
    assert [(a["actor_username"], a["result"].value, a["entity_type"]) for a in refusal_audits(ctx)] == [
        (SERVICE, "failure", "talon_automation_policy"),
        (SERVICE, "failure", "connector"),
    ]


@pytest.mark.parametrize("name, audited", [("ana", False), ("demoted", True), ("resp", False), (SERVICE, False)])
def test_only_an_admin_reads_or_changes_the_policy(name, audited):
    responses, vr, ctx = run([(name, "GET", policy_url(), None), (name, "PUT", policy_url(), put_body(level_1="off"))])
    assert [r.status_code for r in responses] == [403, 403] and policy_audits(ctx) == []
    # A token without the admin scope is refused before the service; a demoted admin's reaches it.
    assert [a["details"] for a in refusal_audits(ctx)] == ([f"Refused (HTTP 403): {automation.ADMIN_ONLY}"] if audited else [])


@pytest.mark.parametrize(
    "code, status",
    [("NOPE", 404), ("acme", 404), ("ACME ", 404), ("x" * 65, 422)],
)
def test_the_customer_must_exist_exactly(code, status):
    (response,), vr, ctx = run([("admin", "GET", policy_url(code), None)])
    assert response.status_code == status


@pytest.mark.parametrize(
    "extra, text",
    [
        ({"caps": {"per_host_hour": 7}}, automation.BAD_CAPS),  # above its default
        ({"caps": {"per_alert": -1}}, automation.BAD_CAPS),
        ({"caps": {"bananas": 1}}, automation.BAD_CAPS),
        ({"level_2_artifacts": ["Windows.System.CmdShell"]}, automation.BAD_ARTIFACTS),
        ({"level_2_artifacts": ["Not.An.Artifact"]}, automation.BAD_ARTIFACTS),
        ({"file_allow_globs": {"windows": [" C:\\x"]}}, automation.BAD_GLOBS),
    ],
)
def test_a_bad_policy_is_a_400_audited_as_refused(extra, text):
    (response,), vr, ctx = run([("admin", "PUT", policy_url(), put_body(level_1="auto", **extra))])
    assert response.status_code == 400 and message(response) == text
    assert [a["details"] for a in refusal_audits(ctx)] == [f"Refused (HTTP 400): {text}"] and policy_audits(ctx) == []


@pytest.mark.parametrize(
    "payload",
    [
        put_body(level_1="on"),
        {"level_1_mode": "auto", "expected_version": 1},  # every mode, every time
        put_body(caps={"per_alert": True}),
        put_body(acknowledge_risk="yes"),
        put_body(v=-1),
        {**put_body(), "extra": 1},
    ],
)
def test_a_malformed_policy_is_a_422(payload):
    (response,), vr, ctx = run([("admin", "PUT", policy_url(), payload)])
    assert response.status_code == 422


def test_level_2_lists_and_globs_are_stored_for_later():
    extra = {
        "level_2_artifacts": ["Windows.System.DNSCache", "Windows.Forensics.Prefetch", "Windows.System.DNSCache"],
        "file_allow_globs": {"windows": ["C:\\Users\\*\\Downloads\\*"], "linux": ["/tmp/*"]},
    }
    (response,), vr, ctx = run([("admin", "PUT", policy_url(), put_body(level_1="auto", level_2="shadow", **extra))])
    out = response.json()
    assert out["level_2_artifacts"] == ["Windows.Forensics.Prefetch", "Windows.System.DNSCache"]
    assert out["file_allow_globs"] == {"windows": ["C:\\Users\\*\\Downloads\\*"], "linux": ["/tmp/*"]}


# ── the global switch ─────────────────────────────────────────────────────────


def test_the_switch_is_an_admins_and_audited_in_its_transaction():
    responses, vr, ctx = run(
        [
            ("admin", "GET", SWITCH, None),
            ("admin", "PUT", SWITCH, {"automation_enabled": True}),
            ("ana", "PUT", SWITCH, {"automation_enabled": False}),
            ("demoted", "PUT", SWITCH, {"automation_enabled": False}),
            ("admin", "PUT", SWITCH, {"automation_enabled": "yes"}),
            ("admin", "GET", SWITCH, None),
        ],
        setup=policy(automation=False),
    )
    before, put, analyst, demoted, malformed, after = responses
    assert before.status_code == 200 and before.json()["automation_enabled"] is False
    assert put.status_code == 200 and put.json()["automation_enabled"] is True
    assert (analyst.status_code, demoted.status_code, malformed.status_code) == (403, 403, 422)
    assert after.json()["automation_enabled"] is True and after.headers["cache-control"] == "no-store"
    (audit,) = policy_audits(ctx)
    assert (audit.entity_type, audit.entity_id, audit.actor_username) == ("connector", "Talon", "admin")
    assert (audit.old_value, audit.new_value) == ({"automation_enabled": False}, {"automation_enabled": True})
    (refused,) = refusal_audits(ctx)  # the demoted admin's
    assert refused["actor_username"] == "demoted" and refused["new_value"] == {"automation_enabled": False}


def test_a_switch_change_whose_audit_row_cant_be_written_isnt_made():
    def broken(**kwargs):
        raise RuntimeError("audit table gone")

    async def scenario(client, ctx):
        await set_policy(ctx, automation=False)
        with patch.object(automation, "_audit_row", broken):
            with pytest.raises(RuntimeError):
                await client.put(SWITCH, json={"automation_enabled": True}, headers=as_user("admin"))
        async with ctx.db.session() as session:
            return (await session.execute(select(TalonConnectorSettings))).scalars().one().automation_enabled

    assert call(scenario) is False


def test_turning_the_switch_off_stops_the_next_start():
    responses, vr, ctx = run(
        [
            (SERVICE, "POST", ROUTE, SERVICES_BOUND),
            ("admin", "PUT", SWITCH, {"automation_enabled": False}),
            (SERVICE, "POST", ROUTE, SERVICES_BOUND),
        ],
    )
    assert [r.status_code for r in responses] == [200, 200, 403] and message(responses[2]) == automation.AUTOMATION_OFF
    assert len(vr.starts) == 1


def test_the_switch_turned_off_during_a_start_stops_it_in_the_reservation():
    """The switch is read again under the policy row's lock: turned off between the first check and
    the reservation, nothing starts."""
    real_check = talon_triggers.check
    seen = {}

    async def check(*args, **kwargs):
        binding = await real_check(*args, **kwargs)
        async with seen["ctx"].db.session() as session:
            await session.execute(update(TalonConnectorSettings).values(automation_enabled=False))
            await session.commit()
        return binding

    async def setup(ctx):
        seen["ctx"] = ctx

    with patch.object(talon_triggers, "check", check):
        (response,), vr, ctx = starts(SERVICES_BOUND, setup=setup)
    assert response.status_code == 403 and message(response) == automation.AUTOMATION_OFF
    assert vr.starts == [] and ctx.starts_after == [] and ctx.cap.starts == 0


def test_the_switch_and_policy_routes_answer_whatever_talon_v2_says():
    async def scenario(client, ctx):
        with patch.object(automation, "record_audit_event", AsyncMock()):
            return [
                await client.get(SWITCH, headers=as_user("admin")),
                await client.get(policy_url(), headers=as_user("admin")),
                await client.put(policy_url(), json=put_body(level_1="auto", v=0), headers=as_user("admin")),
            ]

    assert [r.status_code for r in call(scenario, enabled=False)] == [200, 200, 200]


def test_the_rollout_calls():
    """AP-10 step 2 (the PR body): the customer's row first (``expected_version`` 0), then the switch;
    each can be run again (the row with the version the GET reads) without changing the levels."""
    calls = [
        ("admin", "PUT", policy_url(), put_body(level_1="auto", v=0)),
        ("admin", "PUT", SWITCH, {"automation_enabled": True}),
        ("admin", "PUT", policy_url(), put_body(level_1="auto", v=1)),
        ("admin", "PUT", SWITCH, {"automation_enabled": True}),
        (SERVICE, "POST", ROUTE, SERVICES_BOUND),
    ]
    responses, vr, ctx = run(calls, setup=policy(level_1=None, automation=False))
    assert [r.status_code for r in responses] == [200] * 5
    assert responses[2].json()["level_1_mode"] == "auto" and responses[2].json()["version"] == 2


def test_deployed_with_the_switch_off_and_no_row_nothing_starts():
    (response,), vr, ctx = starts(SERVICES_BOUND, setup=policy(level_1=None, automation=False))
    assert response.status_code == 403 and message(response) == automation.AUTOMATION_OFF and vr.starts == []


# ── the migration ─────────────────────────────────────────────────────────────

MIGRATION = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "a7d2e9c4b5f1_add_talon_automation_policy.py"


def _migration(name):
    spec = importlib.util.spec_from_file_location(name, MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_migration_is_on_ap_2as_head_and_matches_the_models():
    migration = _migration("ap2_migration")
    assert migration.down_revision == "c2a2a0b1d3e4"
    assert (migration.POLICY, migration.STARTS) == (TalonAutomationPolicy.__tablename__, TalonAutomationStart.__tablename__)
    assert set(migration.INDEXES) == {i.name for i in TalonAutomationStart.__table__.indexes}


def test_the_migration_upgrades_and_downgrades():
    import sqlalchemy as sa

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration = _migration("ap2_migration_ops")
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE talon_connector_settings (id INTEGER PRIMARY KEY, connector_name VARCHAR(256))"))
        conn.execute(sa.text("INSERT INTO talon_connector_settings (connector_name) VALUES ('Talon')"))
        with patch.object(migration, "op", Operations(MigrationContext.configure(conn))):
            migration.upgrade()
            inspector = sa.inspect(conn)
            assert {migration.POLICY, migration.STARTS} <= set(inspector.get_table_names())
            for model in (TalonAutomationPolicy, TalonAutomationStart):
                assert {c["name"] for c in inspector.get_columns(model.__tablename__)} == set(model.__table__.columns.keys())
            assert {i["name"] for i in inspector.get_indexes(migration.STARTS)} == set(migration.INDEXES)
            # The existing row reads as off.
            assert conn.execute(sa.text("SELECT automation_enabled FROM talon_connector_settings")).scalar_one() in (0, False)
            migration.downgrade()
            inspector = sa.inspect(conn)
            assert not {migration.POLICY, migration.STARTS} & set(inspector.get_table_names())
            assert "automation_enabled" not in {c["name"] for c in inspector.get_columns("talon_connector_settings")}
    assert "automation_enabled" in TalonConnectorSettings.__table__.columns
