"""``POST /api/artifacts/collect/start``: the collection start route for talon-analyst's automatic
investigations, and its second gate for the Talon service account (talon-analyst plan EA-4b; SPEC
D77, INV-ACT-1's stated exception).

The harness is ``test_talon_actions``'s (real routers, a real in-memory database), with
``talon-analyst`` (the service account, an analyst assigned to ACME) and ``svc`` added. Velociraptor
is ``test_talon_endpoint_actions``' recorder of the start function, or, where what reaches
Velociraptor matters, the recording gRPC stub behind the real services.

Pinned here:
- an assigned analyst starts a flow and gets its id; the answer is ``{success, message, flow_id,
  client_id, artifact}``, never rows, and nothing waits, reads results or uploads;
- refused: an unassigned analyst, another customer's host, a host name on two ``agents`` rows, a
  client id that isn't the host's, an artifact outside the host's list (400), and every command,
  script, quarantine or remediation artifact, for every role;
- the Talon service account: only its allowlist's auto-run artifacts with exactly their pins (else
  403, whatever its role), nothing with the allowlist unset, held by its configured name and by
  ``talon-analyst`` either way; other users are unaffected;
- ``ARTIFACT_COLLECT`` once, with the caller as the actor;
- the resource limits reach ``collect_client`` as its arguments, from the settings;
- no parameter value in the logs or a start error's answer;
- the route is behind "Talon v2" (404 while off), and its setting is an admin's, audited.

Run with: cd backend && python -m pytest tests/test_talon_collect_start.py
"""

import importlib.util
import json
import os
from contextlib import ExitStack
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from loguru import logger  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.connectors.velociraptor.services.artifacts as artifacts_service  # noqa: E402
import tests.test_talon_actions as harness  # noqa: E402
from app.audit.models.audit import AuditAction  # noqa: E402
from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonAutomationAlertCap  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonAutomationPolicy  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonAutomationStart  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonInvestigationTrigger  # noqa: E402
from app.connectors.talon.services import talon_automation  # noqa: E402
from app.connectors.talon.services import talon_collections  # noqa: E402
from app.connectors.talon.services import talon_service_account  # noqa: E402
from app.connectors.talon.services import talon_triggers  # noqa: E402
from app.connectors.velociraptor.routes import artifacts as velociraptor_routes  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import ArtifactParameter  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import Artifacts  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import ArtifactsResponse  # noqa: E402
from app.connectors.velociraptor.services import collection_policy  # noqa: E402
from app.connectors.velociraptor.services import talon_catalogue  # noqa: E402
from app.connectors.velociraptor.services.artifacts import FlowLimits  # noqa: E402
from app.connectors.velociraptor.utils import universal  # noqa: E402
from app.incidents.models import AlertContext  # noqa: E402
from app.incidents.models import Asset  # noqa: E402
from tests.test_talon_actions import ACME  # noqa: E402
from tests.test_talon_actions import GLOBEX  # noqa: E402
from tests.test_talon_actions import HOST  # noqa: E402
from tests.test_talon_actions import VID  # noqa: E402
from tests.test_talon_actions import agent_row  # noqa: E402
from tests.test_talon_actions import as_user  # noqa: E402
from tests.test_talon_endpoint_actions import FLOW  # noqa: E402
from tests.test_talon_endpoint_actions import TALON_FLOW_ID  # noqa: E402
from tests.test_talon_endpoint_actions import Velociraptor  # noqa: E402
from tests.test_talon_endpoint_actions import built_in_definitions  # noqa: E402
from tests.test_velociraptor_query_variables import _RecordingStub  # noqa: E402

ROUTE = "/artifacts/collect/start"
SETTINGS = "/talon/v2/settings/collections"
SERVICE = "talon-analyst"
OTHER_VID = "C.fedcba9876543210"
GLOBEX_HOST, GLOBEX_VID = "WIN-GLOBEX-01", "C.00000000000000aa"
SERVICES_PINS = [{"key": "Calculate_hashes", "value": "N"}, {"key": "CertificateInfo", "value": "N"}]
HOST_ARTIFACTS = [
    "Windows.System.Pslist",
    "Windows.Network.Netstat",
    "Windows.System.Services",
    "Windows.System.TaskScheduler",
    "Windows.Sys.StartupItems",
    "Windows.System.DNSCache",
    "Windows.System.PowerShell",
    "Windows.System.CmdShell",
    "Windows.Remediation.Quarantine",
    "Windows.Remediation.Sinkhole",
    "Windows.Execute.RemotePowerShellScript",
]
ALL_AUTO_RUN = sorted(talon_catalogue.TALON_AUTO_RUN)
# A parameter value no log line may hold.
MARKER = "zz-secret-param-7f3a"
# talon-analyst's `talon.endpoint_catalogue.AUTO_RUN` at `690d55f`, flattened: artifact → pins.
TALON_ANALYST_AUTO_RUN = {
    "Windows.System.Pslist": {},
    "Linux.Sys.Pslist": {},
    "Windows.Network.Netstat": {},
    "Linux.Network.Netstat": {},
    "Windows.System.Services": {"Calculate_hashes": "N", "CertificateInfo": "N"},
    "Windows.System.TaskScheduler": {"AlsoUpload": "N", "UploadCommands": "N"},
    "Windows.Sys.StartupItems": {"AlsoUpload": "N"},
}


#: The ACME alert every scenario seeds (the first alert in a fresh database), with HOST as its asset
#: and a pipeline trigger sent just now: the Talon service account's starts name it (AP-2a's binding;
#: ``test_talon_investigation_triggers`` tests the binding itself).
TRIGGERED_ALERT = 1


def body(artifact="Windows.System.Pslist", env=None, hostname=HOST, vid=VID, alert_id=TRIGGERED_ALERT):
    out = {"hostname": hostname, "velociraptor_id": vid, "artifact_name": artifact, "alert_id": alert_id}
    if env is not None:
        out["parameters"] = {"env": env}
    return out


SERVICES = body("Windows.System.Services", SERVICES_PINS)


@contextmanager
def service_users():
    """The harness's users plus the Talon service account (``talon-analyst``) and ``svc``, both
    analysts assigned to ACME."""
    with patch.dict(harness.USERS, {SERVICE: (20, 2, [ACME]), "svc": (21, 2, [ACME])}):
        with patch.dict(harness.SCOPES, {SERVICE: ["analyst"], "svc": ["analyst"]}):
            yield


#: The tables AP-2a and AP-2 add (the trigger record, the per-alert cap, the automation policy and
#: its start records, and the audit log the start's audit row is written to in its transaction).
AUTOMATION_TABLES = [
    TalonInvestigationTrigger.__table__,
    TalonAutomationAlertCap.__table__,
    TalonAutomationPolicy.__table__,
    TalonAutomationStart.__table__,
    AuditLog.__table__,
]


class _Db(harness._Db):
    async def create(self):
        await super().create()
        tables = AUTOMATION_TABLES
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self


_seeded = {}
_harness_seed = harness._seed


async def _seed(db, enabled):
    """The harness's seed, plus the ACME alert's asset and a pipeline trigger for it."""
    ctx = await _harness_seed(db, enabled)
    assert ctx.alert_id == TRIGGERED_ALERT
    async with db.session() as session:
        context = AlertContext(source="wazuh", context={})
        session.add(context)
        await session.commit()
        session.add(
            Asset(
                alert_linked=ctx.alert_id,
                asset_name=HOST,
                alert_context_id=context.id,
                velociraptor_id=VID,
                customer_code=ACME,
                index_name="wazuh-alerts",
                index_id="1",
            ),
        )
        session.add(
            TalonInvestigationTrigger(
                alert_id=ctx.alert_id,
                customer_code=ACME,
                source="pipeline",
                assets=[{"asset_name": HOST, "velociraptor_id": VID}],
                sent_at=talon_triggers.utcnow(),
            ),
        )
        await session.commit()
    _seeded["db"] = db
    return ctx


def call(scenario, users=True, **kwargs):
    """``harness.call`` with this file's tables and seed; ``users=False`` leaves the harness's users
    as the caller patched them (a service account with another role)."""
    with service_users() if users else ExitStack(), patch.object(harness, "_Db", _Db), patch.object(harness, "_seed", _seed):
        with patch.object(talon_triggers, "new_session", lambda: _seeded["db"].session()):
            return harness.call(scenario, **kwargs)


async def pins_for(allowed):
    """What a PUT would store: the hashes of the definitions Velociraptor (the fake patched now)
    gives for each artifact."""
    return {
        a: collection_policy.definition_hashes(await artifacts_service.get_artifact_policy_definitions(a, "root")) for a in allowed or []
    }


async def configure(ctx, allowed=ALL_AUTO_RUN, username=None, hashes=None, level_1="auto", automation=True):
    """EA-4b's allowlist and pins, and (AP-2) the global switch and ACME's automation policy: level 1
    on ``level_1`` (None: no row), as ``lab`` runs once AP-2 is deployed."""
    pins = hashes if hashes is not None else (await pins_for(allowed) if allowed is not None else None)
    async with ctx.db.session() as session:
        await session.execute(
            update(TalonConnectorSettings)
            .where(TalonConnectorSettings.connector_name == "Talon")
            .values(collect_allowed_artifacts=allowed, collect_service_username=username, collect_definition_hashes=pins),
        )
        await session.commit()
    await set_policy(ctx, level_1=level_1, automation=automation)


async def set_policy(ctx, level_1="auto", automation=True, customer=ACME, **modes):
    """The global switch and ``customer``'s automation policy (``level_1`` None: no row)."""
    async with ctx.db.session() as session:
        await session.execute(
            update(TalonConnectorSettings).where(TalonConnectorSettings.connector_name == "Talon").values(automation_enabled=automation),
        )
        await session.execute(delete(TalonAutomationPolicy).where(TalonAutomationPolicy.customer_code == customer))
        if level_1 is not None:
            session.add(TalonAutomationPolicy(customer_code=customer, level_1_mode=level_1, **modes))
        await session.commit()


@pytest.fixture(autouse=True)
def built_in_velociraptor_definitions():
    """By default Velociraptor's definitions are built in, with no dependencies (a scenario's own
    fake replaces this); the service account's definition cache starts empty in every test."""

    async def lookup(artifact_name, org_id):
        return [{"name": artifact_name, "compiled_in": True}]

    collection_policy.clear_auto_run_definitions_cache()
    with patch.object(artifacts_service, "get_artifact_policy_definitions", lookup):
        yield
    collection_policy.clear_auto_run_definitions_cache()


async def add_agents(ctx, *rows):
    async with ctx.db.session() as session:
        session.add_all(rows)
        await session.commit()


def collect_audits(ctx):
    return [c.kwargs for c in ctx.quarantine_audit.await_args_list if c.kwargs["action"] == AuditAction.ARTIFACT_COLLECT]


def start_scenario(name, payload, *, allowed=ALL_AUTO_RUN, username=None, host_artifacts=HOST_ARTIFACTS, setup=None, flow_id=FLOW):
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, flow_id=flow_id, host_artifacts=host_artifacts)
            await configure(ctx, allowed, username)
            if setup is not None:
                await setup(ctx)
            response = await client.post(ROUTE, json=payload, headers=as_user(name))
        return response, vr, ctx

    return scenario


# ── the catalogue ─────────────────────────────────────────────────────────────


def test_the_auto_run_subset_mirrors_talon_analyst_and_is_inside_the_chat_catalogue():
    assert {name: dict(entry.pinned) for name, entry in talon_catalogue.TALON_AUTO_RUN.items()} == TALON_ANALYST_AUTO_RUN
    for name, entry in talon_catalogue.TALON_AUTO_RUN.items():
        chat = talon_catalogue.TALON_CATALOGUE[name]
        assert entry.settable == frozenset()  # the model picks a kind, never a parameter
        assert dict(entry.pinned) == dict(chat.pinned) or (not chat.pinned and set(entry.pinned) <= chat.settable)
        assert not talon_catalogue.is_response_artifact(name)


@pytest.mark.parametrize(
    "name, parameters, why",
    [
        ("Windows.System.Services", [("Calculate_hashes", "N"), ("CertificateInfo", "N")], None),
        ("Windows.System.Services", [("Calculate_hashes", "Y"), ("CertificateInfo", "N")], "must be sent as N"),
        ("Windows.System.Services", [("Calculate_hashes", "N")], "CertificateInfo must be sent as N"),
        ("Windows.System.Pslist", [("ProcessRegex", "x")], "can't be set"),
        ("Windows.System.Pslist", [], None),
        ("Windows.System.DNSCache", [], "allowlist"),  # in the chat catalogue, not auto-run
        ("Windows.System.PowerShell", [], "allowlist"),
    ],
)
def test_auto_run_violation(name, parameters, why):
    reason = talon_catalogue.auto_run_violation(name, parameters, frozenset(ALL_AUTO_RUN) | {"Windows.System.DNSCache"})
    assert (reason is None) if why is None else (why in reason)


def test_an_artifact_off_the_admins_list_is_refused_even_if_auto_run():
    reason = talon_catalogue.auto_run_violation("Windows.System.Pslist", [], frozenset({"Linux.Sys.Pslist"}))
    assert reason == "not an artifact on the Talon service account's allowlist"


# ── an analyst ────────────────────────────────────────────────────────────────


def test_an_assigned_analyst_starts_a_flow_and_gets_its_id_never_rows():
    response, vr, ctx = call(start_scenario("ana", body()))
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Velociraptor flow started",
        "flow_id": FLOW,
        "client_id": VID,
        "artifact": "Windows.System.Pslist",
    }
    assert TALON_FLOW_ID.fullmatch(response.json()["flow_id"])
    ((kind, started, kwargs),) = vr.starts
    assert kind == "collect" and (started["hostname"], started["velociraptor_id"], started["velociraptor_org"]) == (HOST, VID, "root")
    # An analyst keeps /collect's unescaping and policy; the limits apply to every caller.
    assert kwargs == {"literal_values": False, "limits": talon_collections.collect_start_limits()}
    assert vr.finishes == []  # never waited for, read or uploaded
    # The analyst policy read the definition in the host's org; nothing else was looked up.
    # (After configure's reads, one per allowed artifact, as an admin's save makes them.)
    assert vr.definitions.lookups[len(ALL_AUTO_RUN) :] == [("Windows.System.Pslist", "root")]


def test_the_audit_event_names_the_caller_once():
    response, vr, ctx = call(start_scenario("ana", body()))
    assert response.status_code == 200
    (event,) = collect_audits(ctx)
    assert (event["actor_user_id"], event["actor_username"], event["entity_id"]) == (2, "ana", HOST)
    assert event["new_value"] == {"artifact_name": "Windows.System.Pslist", "velociraptor_id": VID}
    assert len(ctx.quarantine_audit.await_args_list) == 1


def test_the_service_accounts_audit_event_names_it_once():
    response, vr, ctx = call(start_scenario(SERVICE, SERVICES))
    assert response.status_code == 200
    (event,) = collect_audits(ctx)
    assert (event["actor_user_id"], event["actor_username"]) == (20, SERVICE)
    assert len(ctx.quarantine_audit.await_args_list) == 1


def test_an_unassigned_analyst_is_refused():
    response, vr, ctx = call(start_scenario("globex_ana", body()))
    assert response.status_code in (403, 404) and vr.starts == [] and collect_audits(ctx) == []


def test_another_customers_host_is_refused():
    async def setup(ctx):
        await add_agents(ctx, agent_row(hostname=GLOBEX_HOST, vid=GLOBEX_VID, customer=GLOBEX, agent_id="031"))

    response, vr, ctx = call(start_scenario("ana", body(hostname=GLOBEX_HOST, vid=GLOBEX_VID), setup=setup))
    assert response.status_code == 403 and vr.starts == [] and collect_audits(ctx) == []
    # Nor the service account, whose allowlist names the artifact.
    response, vr, ctx = call(start_scenario(SERVICE, body(hostname=GLOBEX_HOST, vid=GLOBEX_VID), setup=setup))
    assert response.status_code == 403 and vr.starts == [] and collect_audits(ctx) == []


@pytest.mark.parametrize("name", ["ana", SERVICE])
def test_a_host_name_on_two_agents_rows_is_refused(name):
    async def setup(ctx):
        await add_agents(ctx, agent_row(vid=OTHER_VID, agent_id="022"))

    response, vr, ctx = call(start_scenario(name, body(), setup=setup))
    assert response.status_code == 409 and "exactly one agent" in response.json()["message"]
    assert vr.starts == [] and collect_audits(ctx) == []


@pytest.mark.parametrize("name", ["ana", SERVICE])
def test_a_client_id_that_isnt_the_hosts_is_refused(name):
    response, vr, ctx = call(start_scenario(name, body(vid=OTHER_VID)))
    assert response.status_code == 409 and vr.starts == [] and collect_audits(ctx) == []


@pytest.mark.parametrize("vid", ["C.0123456789abcdef-O1234", "C.0123", "server", ""])
def test_a_client_id_that_isnt_a_root_org_client_is_refused(vid):
    response, vr, ctx = call(start_scenario("ana", body(vid=vid)))
    assert response.status_code in (400, 422) and vr.starts == []


def test_another_client_claiming_the_hosts_client_id_is_refused():
    async def setup(ctx):
        await add_agents(ctx, agent_row(hostname="WIN-ACME-02", vid=VID.upper() + "-O1", agent_id="023"))

    response, vr, ctx = call(start_scenario("ana", body(), setup=setup))
    assert response.status_code == 409 and vr.starts == []


@pytest.mark.parametrize("name, artifact", [("ana", "Windows.System.DNSCache"), (SERVICE, "Windows.System.Services")])
def test_an_artifact_outside_the_hosts_list_is_a_400(name, artifact):
    payload = body(artifact, SERVICES_PINS if artifact == "Windows.System.Services" else None)
    response, vr, ctx = call(start_scenario(name, payload, host_artifacts=["Windows.System.Pslist"]))
    assert response.status_code == 400 and response.json()["message"] == talon_collections.NOT_APPLICABLE
    assert artifact not in response.text and HOST not in response.text  # a fixed text, no echo
    assert vr.starts == [] and collect_audits(ctx) == []


@pytest.mark.parametrize("name", ["ana", "admin", "resp", SERVICE])
@pytest.mark.parametrize(
    "artifact",
    [
        "Windows.System.PowerShell",
        "Windows.System.CmdShell",
        "Windows.Remediation.Quarantine",
        "Windows.Remediation.Sinkhole",
        "Windows.Execute.RemotePowerShellScript",
    ],
)
def test_command_quarantine_and_remediation_artifacts_are_refused_for_every_role(name, artifact):
    response, vr, ctx = call(start_scenario(name, body(artifact, [{"key": "Command", "value": "whoami"}])))
    assert response.status_code == 403 and vr.starts == [] and collect_audits(ctx) == []


@pytest.mark.parametrize(
    "parameters",
    [
        {"env": [{"key": "ProcessRegex", "value": "a"}, {"key": "ProcessRegex", "value": "b"}]},
        {"env": [{"key": "ProcessRegex", "value": "a‮"}]},
        {"env": [{"key": "Process`Regex", "value": "a"}]},
        {"env": [{"key": "ProcessRegex"}]},
        {"ProcessRegex": "a"},
        {"env": [{"key": "ProcessRegex", "value": "x" * 513}]},
    ],
)
def test_malformed_parameters_are_a_400_that_never_echoes_a_value(parameters):
    payload = body()
    payload["parameters"] = parameters
    response, vr, ctx = call(start_scenario("ana", payload))
    assert response.status_code == 400 and vr.starts == []
    assert "‮" not in response.text and "x" * 20 not in response.text


# ── the Talon service account ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "payload",
    [
        SERVICES,
        body("Windows.System.Pslist"),
        body("Windows.System.TaskScheduler", [{"key": "AlsoUpload", "value": "N"}, {"key": "UploadCommands", "value": "N"}]),
        body("Windows.Sys.StartupItems", [{"key": "AlsoUpload", "value": "N"}]),
    ],
)
def test_the_service_account_starts_its_allowlists_artifacts_with_their_pins(payload):
    response, vr, ctx = call(start_scenario(SERVICE, payload))
    assert response.status_code == 200 and response.json()["flow_id"] == FLOW
    ((_, started, kwargs),) = vr.starts
    assert started["artifact_name"] == payload["artifact_name"]
    assert (started["parameters"] or {}).get("env", []) == payload.get("parameters", {}).get("env", [])
    # Its pins as written, the auto-run gate instead of the analyst allowlist (TaskScheduler and
    # StartupItems aren't on it), Velociraptor's built-in definitions required, and the limits.
    assert kwargs == {"literal_values": True, "limits": talon_collections.collect_start_limits()}
    # One read for the pin check and the definition check together (cached), after configure's.
    assert vr.definitions.lookups[len(ALL_AUTO_RUN) :] == [(payload["artifact_name"], "root")]


def test_a_custom_definition_is_refused_for_the_service_account():
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            vr.definitions.custom.add("Windows.System.Services")
            await configure(ctx)
            response = await client.post(ROUTE, json=SERVICES, headers=as_user(SERVICE))
        return response, vr

    response, vr = call(scenario)
    assert response.status_code == 403 and vr.starts == []


@pytest.mark.parametrize(
    "payload, allowed",
    [
        # (A catalogue artifact outside the auto-run subset is level 2 since AP-2:
        # test_talon_automation_policy's level tests.)
        (body("Windows.System.Pslist"), ["Windows.System.Services"]),  # auto-run, but not on the admin's list
        (body("Windows.System.Services", [{"key": "Calculate_hashes", "value": "Y"}, SERVICES_PINS[1]]), ALL_AUTO_RUN),
        (body("Windows.System.Services", [SERVICES_PINS[0]]), ALL_AUTO_RUN),  # a pin left out
        (body("Windows.System.Services"), ALL_AUTO_RUN),  # no pins at all
        (body("Windows.System.Pslist", [{"key": "ProcessRegex", "value": "lsass"}]), ALL_AUTO_RUN),
        (
            body("Windows.System.TaskScheduler", [{"key": "AlsoUpload", "value": "Y"}, {"key": "UploadCommands", "value": "N"}]),
            ALL_AUTO_RUN,
        ),
    ],
)
def test_the_service_account_outside_its_allowlist_or_with_a_changed_pin_is_a_403(payload, allowed):
    response, vr, ctx = call(start_scenario(SERVICE, payload, allowed=allowed))
    assert response.status_code == 403 and response.json()["message"] == talon_collections.SERVICE_REFUSED
    assert vr.starts == [] and collect_audits(ctx) == []


def test_the_service_account_is_held_whatever_its_role():
    with patch.dict(harness.SCOPES, {SERVICE: ["admin"]}):
        with patch.dict(harness.USERS, {SERVICE: (20, 1, [])}):
            response, vr, ctx = call(start_scenario(SERVICE, body("Windows.System.DNSCache")), users=False)
    assert response.status_code == 403 and vr.starts == []
    with patch.dict(harness.SCOPES, {SERVICE: ["admin"]}):
        with patch.dict(harness.USERS, {SERVICE: (20, 1, [])}):
            response, vr, ctx = call(
                start_scenario(SERVICE, body("Windows.System.Pslist"), allowed=["Windows.System.Services"]),
                users=False,
            )
    assert response.status_code == 403 and response.json()["message"] == talon_collections.SERVICE_REFUSED and vr.starts == []


@pytest.mark.parametrize("allowed", [None, []])
def test_the_service_account_with_the_allowlist_unset_or_empty_starts_nothing(allowed):
    response, vr, ctx = call(start_scenario(SERVICE, body("Windows.System.Pslist"), allowed=allowed))
    assert response.status_code == 403 and vr.starts == [] and collect_audits(ctx) == []
    if allowed is None:
        assert response.json()["message"] == talon_collections.UNSET


def test_with_no_setting_row_the_service_account_is_held_and_allowed_nothing():
    # (With no row "Talon v2" is off too, so the route is a 404 anyway.)
    assert talon_collections.allowed_artifacts(None) is None
    assert talon_collections.is_service_account(SimpleNamespace(username=SERVICE), None)
    assert not talon_collections.is_service_account(SimpleNamespace(username="ana"), None)


def test_the_configured_name_and_talon_analyst_are_both_held_and_other_users_are_not():
    # `svc` is named in the setting: held. `talon-analyst` stays held. `ana` is an analyst like any other.
    response, vr, ctx = call(start_scenario("svc", body("Windows.System.DNSCache"), username="svc"))
    assert response.status_code == 403 and vr.starts == []
    response, vr, ctx = call(start_scenario(SERVICE, body("Windows.System.DNSCache"), username="svc"))
    assert response.status_code == 403 and vr.starts == []
    response, vr, ctx = call(start_scenario("ana", body("Windows.System.DNSCache"), username="svc"))
    assert response.status_code == 200 and len(vr.starts) == 1
    response, vr, ctx = call(start_scenario("svc", SERVICES, username="svc"))
    assert response.status_code == 200 and vr.starts[0][2]["literal_values"] is True
    # Matched whatever the letter case (MySQL compares user names that way).
    assert talon_collections.is_service_account(SimpleNamespace(username="Talon-Analyst"), None)


def test_other_users_are_unaffected_by_the_allowlist():
    # An analyst and an admin start a chat-catalogue artifact the service account may not.
    for name in ("ana", "admin"):
        response, vr, ctx = call(start_scenario(name, body("Windows.System.DNSCache"), allowed=[]))
        assert response.status_code == 200 and len(vr.starts) == 1


# ── what the route answers ────────────────────────────────────────────────────


@pytest.mark.parametrize("flow_id", ["F.ABC.H", "", "flow", "F." + "a" * 65])
def test_a_flow_id_not_in_talon_analysts_form_is_a_502(flow_id):
    response, vr, ctx = call(start_scenario(SERVICE, SERVICES, flow_id=flow_id))
    assert response.status_code == 502 and response.json()["message"] == talon_collections.NO_FLOW_ID
    assert "flow_id" not in response.json()


def test_a_server_error_starting_the_flow_is_a_fixed_text():
    async def failing(body, **kwargs):
        raise HTTPException(status_code=500, detail=f"Failed to run artifact collection on {body}: {MARKER}")

    async def scenario(client, ctx):
        with ExitStack() as stack:
            Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            stack.enter_context(patch.object(velociraptor_routes, "start_artifact_collection", failing))
            await configure(ctx)
            return await client.post(ROUTE, json=body(env=[{"key": "ProcessRegex", "value": MARKER}]), headers=as_user("ana"))

    response = call(scenario)
    assert response.status_code == 500 and response.json()["message"] == talon_collections.START_FAILED
    assert MARKER not in response.text


def test_with_talon_v2_off_the_route_is_not_found():
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            response = await client.post(ROUTE, json=SERVICES, headers=as_user(SERVICE))
            anonymous = await client.post(ROUTE, json=SERVICES)
        return response, anonymous, vr

    for enabled in (False, None):
        response, anonymous, vr = call(scenario, enabled=enabled)
        assert response.status_code == 404 and response.json() == {"detail": "Not Found"} and vr.starts == []
        assert anonymous.status_code in (401, 403)  # the scope check comes first


def test_a_portal_user_cannot_reach_the_route():
    response, vr, ctx = call(start_scenario("portal", body()))
    assert response.status_code in (401, 403) and vr.starts == []


# ── what reaches Velociraptor, and the logs ───────────────────────────────────


class EchoingStub(_RecordingStub):
    """Answers ``collect_client`` as Velociraptor does: the new flow, echoing its request."""

    def Query(self, request, timeout=None):  # noqa: N802 - gRPC method name
        vql = request.Query[0].VQL
        if "collect_client(" in vql:
            self.requests.append(request)
            env = [{"key": e.key, "value": e.value} for e in request.env]
            rows = [{"Flow": {"flow_id": FLOW, "request": {"specs": [{"parameters": {"env": env}}]}}}]
            return [SimpleNamespace(Response=json.dumps(rows), log="")]
        return super().Query(request, timeout)


def recording(stack, stub, declared):
    service = universal.UniversalService()
    service.stub = stub

    async def fake_create(cls, connector_name):
        return service

    async def artifact_by_name(artifact_name, org_id="root"):
        return ArtifactsResponse(
            success=True,
            message="ok",
            artifacts=[Artifacts(name=artifact_name, description="", parameters=[ArtifactParameter(name=n) for n in declared])],
        )

    listing = ArtifactsResponse(success=True, message="ok", artifacts=[Artifacts(name=n, description="") for n in HOST_ARTIFACTS])
    stack.enter_context(patch.object(artifacts_service.UniversalService, "create", classmethod(fake_create)))
    stack.enter_context(patch.object(artifacts_service, "get_artifact_by_name", artifact_by_name))
    stack.enter_context(patch.object(velociraptor_routes, "get_all_artifacts_for_hostname", _async(listing)))
    return built_in_definitions(stack)


def _async(value):
    async def answer(*args, **kwargs):
        return value

    return answer


def run_recorded(name, payload, declared):
    stub = EchoingStub(hostname=HOST)
    lines = []

    async def scenario(client, ctx):
        with ExitStack() as stack:
            recording(stack, stub, declared)
            await configure(ctx)
            sink = logger.add(lambda message: lines.append(str(message)), level="DEBUG")
            try:
                return await client.post(ROUTE, json=payload, headers=as_user(name))
            finally:
                logger.remove(sink)

    return call(scenario), stub, lines


def test_the_resource_limits_reach_the_query_as_collect_client_arguments():
    response, stub, lines = run_recorded(SERVICE, SERVICES, ["Calculate_hashes", "CertificateInfo", "NameRegex"])
    assert response.status_code == 200 and response.json()["flow_id"] == FLOW
    (vql, env, org) = stub.call_with("collect_client(")
    assert vql == (
        "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName], "
        "env=dict(`Calculate_hashes`=Param0, `CertificateInfo`=Param1), "
        "timeout=300, cpu_limit=25.0, max_rows=10000, max_bytes=1048576) AS Flow FROM scope()"
    )
    assert env == {
        "OrgId": "root",
        "ClientId": VID,
        "ArtifactName": "Windows.System.Services",
        "Param0": "N",
        "Param1": "N",
    }
    # Started only: never waited for, read or uploaded.
    assert [v for v, _, _ in stub.calls() if "collect_client(" not in v and "artifact_definitions(" not in v] == []


def test_the_limits_come_from_the_settings_and_the_timeout_stays_at_most_300(monkeypatch):
    monkeypatch.setenv("VELOCIRAPTOR_COLLECT_START_TIMEOUT", "120")
    monkeypatch.setenv("VELOCIRAPTOR_COLLECT_START_CPU_LIMIT", "10")
    monkeypatch.setenv("VELOCIRAPTOR_COLLECT_START_MAX_ROWS", "500")
    monkeypatch.setenv("VELOCIRAPTOR_COLLECT_START_MAX_BYTES", "4096")
    assert talon_collections.collect_start_limits() == FlowLimits(timeout=120, cpu_limit=10, max_rows=500, max_bytes=4096)
    response, stub, lines = run_recorded(SERVICE, body("Windows.System.Pslist"), [])
    (vql, env, org) = stub.call_with("collect_client(")
    assert vql.endswith("artifacts=[ArtifactName], timeout=120, cpu_limit=10.0, max_rows=500, max_bytes=4096) AS Flow FROM scope()")
    monkeypatch.setenv("VELOCIRAPTOR_COLLECT_START_TIMEOUT", "900")
    monkeypatch.setenv("VELOCIRAPTOR_COLLECT_START_CPU_LIMIT", "400")
    monkeypatch.setenv("VELOCIRAPTOR_COLLECT_START_MAX_ROWS", "-1")
    monkeypatch.setenv("VELOCIRAPTOR_COLLECT_START_MAX_BYTES", "lots")
    assert talon_collections.collect_start_limits() == FlowLimits(timeout=300, cpu_limit=100, max_rows=10000, max_bytes=1048576)


def test_collect_sets_no_limits():
    assert "timeout=" not in artifacts_service.VQL_COLLECT.format(limits="")
    assert FlowLimits(300, 25, 10000, 1048576).vql() == ", timeout=300, cpu_limit=25.0, max_rows=10000, max_bytes=1048576"


def test_no_parameter_value_appears_in_the_logs():
    payload = body(env=[{"key": "ProcessRegex", "value": MARKER}])
    response, stub, lines = run_recorded("ana", payload, ["ProcessRegex"])
    assert response.status_code == 200 and response.json()["flow_id"] == FLOW
    # It reached Velociraptor (as a query variable), and Velociraptor echoed it back...
    (vql, env, org) = stub.call_with("collect_client(")
    assert env["Param0"] == MARKER and MARKER not in vql
    # ...but no log line holds it, while the start itself is logged.
    assert lines and not [line for line in lines if MARKER in line]
    assert any("Collection start: Windows.System.Pslist" in line for line in lines)


# ── the setting ───────────────────────────────────────────────────────────────


def test_the_setting_is_an_admins_and_audited():
    async def scenario(client, ctx):
        with patch.object(talon_collections, "record_audit_event", ctx.audit):
            before = await client.get(SETTINGS, headers=as_user("admin"))
            refused = [
                await client.put(SETTINGS, json={"service_username": "x", "allowed_artifacts": []}, headers=as_user(name))
                for name in ("ana", "demoted", "resp", SERVICE)
            ]
            read_refused = await client.get(SETTINGS, headers=as_user("ana"))
            put = await client.put(
                SETTINGS,
                json={"service_username": "svc", "allowed_artifacts": ["Windows.System.Pslist", "Linux.Sys.Pslist", "Linux.Sys.Pslist"]},
                headers=as_user("admin"),
            )
            bad = await client.put(
                SETTINGS,
                json={"service_username": None, "allowed_artifacts": ["Windows.System.PowerShell"]},
                headers=as_user("admin"),
            )
            after = await client.get(SETTINGS, headers=as_user("admin"))
        async with ctx.db.session() as session:
            row = await session.get(TalonConnectorSettings, 1)
        return before, refused, read_refused, put, bad, after, row, ctx

    before, refused, read_refused, put, bad, after, row, ctx = call(scenario)
    assert before.status_code == 200 and before.headers["cache-control"] == "no-store"
    assert before.json()["service_username"] == SERVICE and before.json()["allowed_artifacts"] is None
    assert before.json()["auto_run_catalogue"] == TALON_ANALYST_AUTO_RUN
    assert [r.status_code for r in refused] == [403, 403, 403, 403] and read_refused.status_code == 403
    assert put.status_code == 200 and put.json()["allowed_artifacts"] == ["Linux.Sys.Pslist", "Windows.System.Pslist"]
    assert put.json()["service_username"] == "svc" and put.json()["service_username_configured"] == "svc"
    assert bad.status_code == 400
    assert after.json()["allowed_artifacts"] == ["Linux.Sys.Pslist", "Windows.System.Pslist"]
    assert row.collect_allowed_artifacts == ["Linux.Sys.Pslist", "Windows.System.Pslist"] and row.v2_enabled is True
    ((event,),) = [[c.kwargs for c in ctx.audit.await_args_list]]
    assert event["action"] == AuditAction.CONNECTOR_UPDATE and event["actor_username"] == "admin"
    assert event["old_value"] == {
        "collect_service_username": None,
        "collect_service_user_id": None,
        "collect_allowed_artifacts": None,
        "collect_definition_hashes": None,
    }
    pins = {
        a: collection_policy.definition_hashes([{"name": a, "compiled_in": True}]) for a in ["Linux.Sys.Pslist", "Windows.System.Pslist"]
    }
    assert event["new_value"] == {
        "collect_service_username": "svc",
        "collect_service_user_id": 21,
        "collect_allowed_artifacts": ["Linux.Sys.Pslist", "Windows.System.Pslist"],
        "collect_definition_hashes": pins,
    }
    assert after.json()["definition_hashes"] == pins
    assert after.json()["definitions_match"] == {"Linux.Sys.Pslist": True, "Windows.System.Pslist": True}
    assert put.json()["service_user_exists"] is True and put.json()["service_user_id"] == 21
    assert before.json()["service_user_exists"] is True and before.json()["service_user_id"] == 20


def test_setting_the_allowlist_without_a_row_leaves_talon_v2_off():
    async def scenario(client, ctx):
        with patch.object(talon_collections, "record_audit_event", ctx.audit):
            put = await client.put(SETTINGS, json={"service_username": None, "allowed_artifacts": ALL_AUTO_RUN}, headers=as_user("admin"))
        async with ctx.db.session() as session:
            row = await session.get(TalonConnectorSettings, 1)
        start = await client.post(ROUTE, json=body(), headers=as_user(SERVICE))
        return put, row, start

    put, row, start = call(scenario, enabled=None)
    assert put.status_code == 200 and row.v2_enabled is False and row.collect_allowed_artifacts == ALL_AUTO_RUN
    assert start.status_code == 404


@pytest.mark.parametrize("username", ["", " svc", "svc\n", "a‮b"])
def test_a_service_username_that_isnt_a_plain_name_is_refused(username):
    async def scenario(client, ctx):
        with patch.object(talon_collections, "record_audit_event", ctx.audit):
            return await client.put(SETTINGS, json={"service_username": username, "allowed_artifacts": []}, headers=as_user("admin"))

    assert call(scenario).status_code == 400


# ── review of #1287: the service account on every other route that starts something ─────────


_HARNESS_APP = harness._app


def _full_app(db):
    """The harness's app plus the Velociraptor routes."""
    from app.routers import velociraptor

    app = _HARNESS_APP(db)
    app.include_router(velociraptor.router)
    return app


def full_call(scenario, **kwargs):
    with patch.object(harness, "_app", _full_app):
        return call(scenario, **kwargs)


def manual_scenario(name, path, payload, username=None):
    from app.connectors.velociraptor.schema.artifacts import CollectArtifactResponse

    done = CollectArtifactResponse(success=True, message="collected", results=[])

    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            waited = []

            async def finish(*args, **kwargs):
                waited.append(args)
                return done

            stack.enter_context(patch.object(velociraptor_routes, "finish_artifact_collection", finish))
            stack.enter_context(patch.object(velociraptor_routes, "run_file_collection", finish))
            await configure(ctx, username=username)
            response = await client.post(path, json=payload, headers=as_user(name))
        return response, vr, waited, ctx

    return scenario


COLLECT = {"hostname": HOST, "artifact_name": "Windows.System.Pslist"}
FILE = ("/artifacts/collect/file/agent/021", {"file": "C:\\Windows\\Temp\\x.txt"})


@pytest.mark.parametrize("name", [SERVICE, "svc"])
def test_the_service_account_is_refused_on_collect_and_file_collection(name):
    # `svc` is the configured name; `talon-analyst` is held either way.
    for path, payload in [("/artifacts/collect", COLLECT), FILE]:
        response, vr, waited, ctx = full_call(manual_scenario(name, path, payload, username="svc"))
        assert response.status_code == 403 and response.json()["message"] == talon_service_account.REFUSED, path
        assert vr.starts == [] and waited == [] and collect_audits(ctx) == []


def test_the_service_account_is_refused_on_collect_whatever_its_role():
    with patch.dict(harness.SCOPES, {SERVICE: ["admin"]}), patch.dict(harness.USERS, {SERVICE: (20, 1, [])}):
        with patch.object(harness, "_app", _full_app):
            response, vr, waited, ctx = call(manual_scenario(SERVICE, "/artifacts/collect", COLLECT), users=False)
    assert response.status_code == 403 and vr.starts == []


def test_ordinary_analysts_are_unaffected_on_collect_and_file_collection():
    response, vr, waited, ctx = full_call(manual_scenario("ana", "/artifacts/collect", COLLECT))
    assert response.status_code == 200 and len(vr.starts) == 1 and len(waited) == 1
    response, vr, waited, ctx = full_call(manual_scenario("ana", *FILE))
    assert response.status_code == 200 and len(waited) == 1


def test_the_service_account_is_held_by_its_recorded_id_after_a_rename():
    async def scenario(client, ctx):
        with patch.object(talon_collections, "record_audit_event", ctx.audit):
            put = await client.put(SETTINGS, json={"service_username": "svc", "allowed_artifacts": ALL_AUTO_RUN}, headers=as_user("admin"))
        async with ctx.db.session() as session:
            row = await session.get(TalonConnectorSettings, 1)
        renamed = SimpleNamespace(id=21, username="renamed", role_id=2)
        stranger = SimpleNamespace(id=2, username="ana", role_id=2)
        return put, row, renamed, stranger

    put, row, renamed, stranger = call(scenario)
    assert put.status_code == 200 and row.collect_service_user_id == 21
    assert talon_service_account.is_service_account(renamed, row)  # the id still matches
    assert not talon_service_account.is_service_account(stranger, row)


def test_get_reports_a_configured_user_that_does_not_exist():
    async def scenario(client, ctx):
        with patch.object(talon_collections, "record_audit_event", ctx.audit):
            put = await client.put(SETTINGS, json={"service_username": "ghost", "allowed_artifacts": []}, headers=as_user("admin"))
        return put, await client.get(SETTINGS, headers=as_user("admin"))

    put, got = call(scenario)
    assert got.json()["service_user_exists"] is False and got.json()["service_user_id"] is None
    assert got.json()["recorded_service_user_id"] is None and got.json()["service_username"] == "ghost"


@pytest.mark.parametrize("username, warned", [("ghost", True), ("svc", False), (None, False)])
def test_startup_warns_when_no_user_has_the_configured_name(username, warned):
    lines = []

    async def scenario(client, ctx):
        if username is not None:
            await configure(ctx, allowed=[], username=username)
        sink = logger.add(lambda message: lines.append(str(message)), level="WARNING")
        try:
            await talon_service_account.warn_if_service_user_missing(ctx.db.engine)
        finally:
            logger.remove(sink)

    call(scenario)
    assert bool([line for line in lines if "no single CoPilot user is named" in line]) is warned


# Every route but /collect (whose shared start function refuses it) that starts endpoint work and
# that the service account's analyst role, or any role, reaches.
REFUSING_ROUTES = [
    ("app.connectors.velociraptor.routes.artifacts", "velociraptor_artifacts_router", "/collect/file/agent/{agent_id}", "POST"),
    ("app.connectors.velociraptor.routes.artifacts", "velociraptor_artifacts_router", "/command", "POST"),
    ("app.connectors.velociraptor.routes.artifacts", "velociraptor_artifacts_router", "/quarantine", "POST"),
    ("app.file_analysis.routes", "file_analysis_router", "/velociraptor/enumerate", "POST"),
    ("app.file_analysis.routes", "file_analysis_router", "/submit", "POST"),
    ("app.agents.routes.agents", "agents_router", "/{agent_id}/delete", "DELETE"),
    ("app.agents.routes.agents", "agents_router", "/bulk/delete", "POST"),
    ("app.agents.routes.agents", "agents_router", "/bulk/delete/filter", "POST"),
    ("app.integrations.copilot_mcp.routes.copilot_mcp", "copilot_mcp_router", "/query", "POST"),
    ("app.integrations.copilot_action.routes.copilot_action", "copilot_action_router", "/invoke", "POST"),
]


@pytest.mark.parametrize("module, router, path, method", REFUSING_ROUTES)
def test_every_other_route_that_starts_something_refuses_the_service_account(module, router, path, method):
    import importlib

    routes = [r for r in getattr(importlib.import_module(module), router).routes if r.path == path and method in r.methods]
    assert len(routes) == 1
    dependencies = [d.dependency for d in routes[0].dependencies]
    assert talon_service_account.refuse_talon_service_account_dependency in dependencies


def test_the_service_account_never_decides_a_talon_action():
    from app.connectors.talon.services import talon_action_execution as execution

    async def scenario(client, ctx):
        await configure(ctx)
        row = SimpleNamespace(action="comment_on_alert", customer_code=ACME, target={"alert_id": ctx.alert_id})
        async with ctx.db.session() as session:
            with pytest.raises(HTTPException) as refused:
                await execution.check_d47(SimpleNamespace(id=20, username=SERVICE, role_id=2), row, session)
        return refused.value

    refused = call(scenario)
    assert refused.status_code == 403 and refused.detail == talon_service_account.REFUSED


# ── the definition check, the analyst policy, fixed texts and logs ─────────────────────────────


@pytest.mark.parametrize(
    "extra, dependency",
    [
        ({"tools": [{"name": "autorunsc"}]}, False),
        ({"imports": ["X"]}, False),
        ({"required_permissions": ["EXECVE"]}, False),
        ({"tools": [{"name": "t"}]}, True),
    ],
)
def test_a_definition_with_tools_imports_or_elevated_permissions_is_refused_for_the_service_account(extra, dependency):
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)

            async def lookup(artifact_name, org_id):
                own = {"name": artifact_name, "compiled_in": True, **({} if dependency else extra)}
                dep = {"name": "Windows.Forensics.Lnk", "compiled_in": True, **(extra if dependency else {})}
                return [own, dep]

            stack.enter_context(patch.object(artifacts_service, "get_artifact_policy_definitions", lookup))
            await configure(ctx)
            response = await client.post(ROUTE, json=SERVICES, headers=as_user(SERVICE))
        return response, vr

    response, vr = call(scenario)
    assert response.status_code == 403 and vr.starts == []
    assert response.json()["message"] == talon_collections.POLICY_REFUSED


def test_the_service_accounts_definition_check_lets_pinned_uploads_and_eval_through():
    # TaskScheduler's guarded upload() and StartupItems' dependency's eval()/upload(): no tools,
    # imports or elevated permissions, built in. Rule 4's VQL scan is the recorded residual.
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)

            async def lookup(artifact_name, org_id):
                vql = "SELECT if(condition=AlsoUpload, then=upload(file=OSPath)) FROM scope()"
                return [
                    {"name": artifact_name, "compiled_in": True, "sources": [{"query": vql}]},
                    {"name": "Windows.Forensics.Lnk", "compiled_in": True, "sources": [{"query": "SELECT eval(func=x) FROM scope()"}]},
                ]

            stack.enter_context(patch.object(artifacts_service, "get_artifact_policy_definitions", lookup))
            await configure(ctx)
            response = await client.post(
                ROUTE,
                json=body("Windows.Sys.StartupItems", [{"key": "AlsoUpload", "value": "N"}]),
                headers=as_user(SERVICE),
            )
        return response, vr

    response, vr = call(scenario)
    assert response.status_code == 200 and len(vr.starts) == 1


@pytest.mark.parametrize("artifact", ["Windows.System.TaskScheduler", "Windows.Sys.StartupItems"])
def test_an_ordinary_analyst_is_held_to_the_analyst_allowlist_on_the_start_route(artifact):
    pins = talon_catalogue.TALON_AUTO_RUN[artifact].pinned
    response, vr, ctx = call(start_scenario("ana", body(artifact, [{"key": k, "value": v} for k, v in pins.items()])))
    assert response.status_code == 403 and response.json()["message"] == talon_collections.POLICY_REFUSED
    assert artifact not in response.text and vr.starts == []


@pytest.mark.parametrize("hostname", ["WIN'ACME", "WIN`ACME", "a\\b", "x\ny"])
def test_a_host_name_that_could_break_a_query_is_a_fixed_400(hostname):
    response, vr, ctx = call(start_scenario("ana", body(hostname=hostname)))
    assert response.status_code == 400 and response.json()["message"] == talon_collections.BAD_REQUEST and vr.starts == []


@pytest.mark.parametrize("name, payload", [("globex_ana", body()), ("ana", body("Bad Name!")), ("ana", body(hostname="NO-SUCH-HOST"))])
def test_a_refusal_echoes_nothing_and_is_logged_before_any_start_line(name, payload):
    lines = []

    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            await configure(ctx)
            sink = logger.add(lambda message: lines.append(str(message)), level="DEBUG")
            try:
                response = await client.post(ROUTE, json=payload, headers=as_user(name))
            finally:
                logger.remove(sink)
        return response, vr

    response, vr = call(scenario)
    assert response.status_code in (400, 403, 404) and vr.starts == []
    assert payload["hostname"] not in response.text and payload["artifact_name"] not in response.text
    assert not [line for line in lines if "Collection start:" in line]


# ── the migration ─────────────────────────────────────────────────────────────


def test_the_migration_upgrades_and_downgrades():
    import sqlalchemy as sa

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    path = Path(__file__).parent.parent / "alembic" / "versions" / "e4b2c0d1a7f3_add_talon_collect_service_gate.py"
    spec = importlib.util.spec_from_file_location("ea4b_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert (migration.revision, migration.down_revision) == ("e4b2c0d1a7f3", "f1282a0b1c2d")

    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            sa.text("CREATE TABLE talon_connector_settings (id INTEGER PRIMARY KEY, connector_name VARCHAR(256), v2_enabled BOOLEAN)"),
        )
        conn.execute(sa.text("INSERT INTO talon_connector_settings (connector_name, v2_enabled) VALUES ('Talon', 1)"))

        def columns():
            return {c["name"] for c in sa.inspect(conn).get_columns("talon_connector_settings")}

        with patch.object(migration, "op", Operations(MigrationContext.configure(conn))):
            migration.upgrade()
            assert columns() == {
                "id",
                "connector_name",
                "v2_enabled",
                "collect_service_username",
                "collect_service_user_id",
                "collect_allowed_artifacts",
                "collect_definition_hashes",
            }
            row = conn.execute(
                sa.text(
                    "SELECT collect_service_username, collect_service_user_id, collect_allowed_artifacts, collect_definition_hashes "
                    "FROM talon_connector_settings",
                ),
            ).one()
            assert tuple(row) == (None, None, None, None)  # unset: the service account starts nothing
            migration.downgrade()
            assert columns() == {"id", "connector_name", "v2_enabled"}
        assert conn.execute(sa.text("SELECT connector_name, v2_enabled FROM talon_connector_settings")).one() == ("Talon", 1)


# ── re-review of #1287: the definition pin and a stale user id ─────────────────────────────────


def changed_definitions(stack, changed):
    """Velociraptor's definitions as after an upgrade: `changed` artifacts' VQL differs."""
    lookups = []

    async def lookup(artifact_name, org_id):
        lookups.append((artifact_name, org_id))
        definition = {"name": artifact_name, "compiled_in": True}
        if artifact_name in changed:
            definition["sources"] = [{"query": "SELECT * FROM info()"}]
        return [definition]

    stack.enter_context(patch.object(artifacts_service, "get_artifact_policy_definitions", lookup))
    return lookups


def test_a_definition_that_changed_since_the_setting_was_saved_is_refused_until_an_admin_saves_again():
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            await configure(ctx)  # pinned against the definitions as they were
            changed_definitions(stack, {"Windows.System.Services"})  # Velociraptor upgraded
            collection_policy.clear_auto_run_definitions_cache()
            refused = await client.post(ROUTE, json=SERVICES, headers=as_user(SERVICE))
            other = await client.post(ROUTE, json=body("Windows.System.Pslist"), headers=as_user(SERVICE))
            analyst = await client.post(ROUTE, json=body("Windows.System.DNSCache"), headers=as_user("ana"))
            with patch.object(talon_collections, "record_audit_event", ctx.audit):
                seen = await client.get(SETTINGS, headers=as_user("admin"))
                await client.put(SETTINGS, json={"service_username": None, "allowed_artifacts": ALL_AUTO_RUN}, headers=as_user("admin"))
            again = await client.post(ROUTE, json=SERVICES, headers=as_user(SERVICE))
        return refused, other, analyst, seen, again, vr

    refused, other, analyst, seen, again, vr = call(scenario)
    assert refused.status_code == 403 and refused.json()["message"] == talon_collections.DEFINITION_CHANGED
    assert "Windows.System.Services" not in refused.text
    assert other.status_code == 200  # an unchanged artifact still starts
    assert analyst.status_code == 200  # other users are unaffected
    assert seen.json()["definitions_match"]["Windows.System.Services"] is False
    assert seen.json()["definitions_match"]["Windows.System.Pslist"] is True
    assert set(seen.json()["definition_hashes"]["Windows.System.Services"]) == {"Windows.System.Services"}
    assert again.status_code == 200  # reviewed and saved again
    assert [started["artifact_name"] for _, started, _ in vr.starts] == [
        "Windows.System.Pslist",
        "Windows.System.DNSCache",
        "Windows.System.Services",
    ]


def test_a_dependency_that_changed_is_refused_too():
    async def scenario(client, ctx):
        state = {"dep": "v1"}

        async def lookup(artifact_name, org_id):
            return [
                {"name": artifact_name, "compiled_in": True},
                {"name": "Windows.Forensics.Lnk", "compiled_in": True, "export": state["dep"]},
            ]

        with ExitStack() as stack:
            Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            stack.enter_context(patch.object(artifacts_service, "get_artifact_policy_definitions", lookup))
            await configure(ctx)
            state["dep"] = "v2"
            collection_policy.clear_auto_run_definitions_cache()
            return await client.post(
                ROUTE,
                json=body("Windows.Sys.StartupItems", [{"key": "AlsoUpload", "value": "N"}]),
                headers=as_user(SERVICE),
            )

    response = call(scenario)
    assert response.status_code == 403 and response.json()["message"] == talon_collections.DEFINITION_CHANGED


def test_no_stored_pin_is_refused():
    response, vr, ctx = call(_no_pin_scenario())
    assert response.status_code == 403 and response.json()["message"] == talon_collections.DEFINITION_CHANGED and vr.starts == []


def _no_pin_scenario():
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            await configure(ctx, hashes={})
            return await client.post(ROUTE, json=SERVICES, headers=as_user(SERVICE)), vr, ctx

    return scenario


def test_definition_reads_are_cached_between_starts():
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            await configure(ctx)
            before = len(vr.definitions.lookups)
            answers = [await client.post(ROUTE, json=SERVICES, headers=as_user(SERVICE)) for _ in range(3)]
        return answers, vr.definitions.lookups[before:]

    with patch.dict(talon_automation.CAP_DEFAULTS, {"per_alert": 3}):  # three starts on one alert
        answers, lookups = call(scenario)
    assert [a.status_code for a in answers] == [200, 200, 200]
    assert lookups == [("Windows.System.Services", "root")]  # one read for three starts


def test_saving_reads_the_definitions_afresh():
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            await collection_policy.auto_run_definitions("Windows.System.Pslist", "root")  # cached
            before = len(vr.definitions.lookups)
            with patch.object(talon_collections, "record_audit_event", ctx.audit):
                put = await client.put(
                    SETTINGS,
                    json={"service_username": None, "allowed_artifacts": ["Windows.System.Pslist"]},
                    headers=as_user("admin"),
                )
        return put, vr.definitions.lookups[before:]

    put, lookups = call(scenario)
    assert put.status_code == 200 and ("Windows.System.Pslist", "root") in lookups


@pytest.mark.parametrize("failure, status", [("unreadable", 502), ("custom", 400), ("tools", 400)])
def test_a_definition_that_cant_be_pinned_saves_nothing(failure, status):
    async def scenario(client, ctx):
        async def lookup(artifact_name, org_id):
            if failure == "unreadable":
                raise HTTPException(status_code=500, detail="Failed to get artifact")
            return [
                {"name": artifact_name, "compiled_in": failure != "custom", **({"tools": [{"name": "x"}]} if failure == "tools" else {})},
            ]

        with patch.object(artifacts_service, "get_artifact_policy_definitions", lookup):
            with patch.object(talon_collections, "record_audit_event", ctx.audit):
                put = await client.put(
                    SETTINGS,
                    json={"service_username": None, "allowed_artifacts": ["Windows.System.Pslist"]},
                    headers=as_user("admin"),
                )
        async with ctx.db.session() as session:
            row = await session.get(TalonConnectorSettings, 1)
        return put, row, ctx

    put, row, ctx = call(scenario)
    assert put.status_code == status and row.collect_allowed_artifacts is None and row.collect_definition_hashes is None
    assert ctx.audit.await_args_list == []


def test_definition_hashes_cover_every_field_and_ignore_key_order():
    one = collection_policy.definition_hashes([{"name": "A", "sources": [{"query": "SELECT 1"}], "compiled_in": True}])
    same = collection_policy.definition_hashes([{"compiled_in": True, "sources": [{"query": "SELECT 1"}], "name": "A"}])
    other = collection_policy.definition_hashes([{"name": "A", "sources": [{"query": "SELECT 2"}], "compiled_in": True}])
    assert one == same and one != other and len(one["A"]) == 64


async def _record_id(ctx, user_id, username=None):
    async with ctx.db.session() as session:
        await session.execute(
            update(TalonConnectorSettings)
            .where(TalonConnectorSettings.connector_name == "Talon")
            .values(collect_service_user_id=user_id, collect_service_username=username, collect_allowed_artifacts=[]),
        )
        await session.commit()


@pytest.mark.parametrize(
    "recorded, username, cleared, warned",
    [
        (20, None, False, False),  # talon-analyst, still named so
        (21, "svc", False, False),
        (99, None, True, True),  # no user has the id any more: cleared
        (21, None, False, True),  # `svc`, while the setting's name is talon-analyst: kept, with a warning
    ],
)
def test_startup_clears_a_recorded_id_only_when_no_user_has_it(recorded, username, cleared, warned):
    lines = []

    async def scenario(client, ctx):
        await _record_id(ctx, recorded, username)
        sink = logger.add(lambda message: lines.append(str(message)), level="WARNING")
        try:
            await talon_service_account.warn_if_service_user_missing(ctx.db.engine)
        finally:
            logger.remove(sink)
        async with ctx.db.session() as session:
            return await session.get(TalonConnectorSettings, 1)

    row = call(scenario)
    assert (row.collect_service_user_id is None) is cleared and (row.collect_service_user_id == recorded) is not cleared
    assert bool([line for line in lines if "recorded service-account user id" in line]) is warned


def test_a_renamed_service_account_is_still_gated_after_a_restart():
    lines = []

    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=HOST_ARTIFACTS)
            with patch.object(talon_collections, "record_audit_event", ctx.audit):
                await client.put(SETTINGS, json={"service_username": "svc", "allowed_artifacts": ALL_AUTO_RUN}, headers=as_user("admin"))
            await set_policy(ctx)
            async with ctx.db.session() as session:  # the account is renamed outside the setting
                await session.execute(update(User).where(User.id == 21).values(username="renamed"))
                await session.commit()
            sink = logger.add(lambda message: lines.append(str(message)), level="WARNING")
            try:
                await talon_service_account.warn_if_service_user_missing(ctx.db.engine)  # a restart
            finally:
                logger.remove(sink)
            async with ctx.db.session() as session:
                row = await session.get(TalonConnectorSettings, 1)
            with patch.dict(harness.USERS, {"renamed": (21, 2, [ACME])}), patch.dict(harness.SCOPES, {"renamed": ["analyst"]}):
                outside = await client.post(ROUTE, json=body("Windows.System.DNSCache"), headers=as_user("renamed"))
                manual = await client.post(ROUTE, json=SERVICES, headers=as_user("renamed"))
        return row, outside, manual, vr

    row, outside, manual, vr = call(scenario)
    assert row.collect_service_user_id == 21  # kept
    assert outside.status_code == 403 and outside.json()["message"] == talon_automation.LEVEL_OFF  # still held (level 2 is off)
    assert manual.status_code == 200 and vr.starts[0][2]["literal_values"] is True  # its allowlist still works
    assert [line for line in lines if "stays held to the gate" in line]


def test_deleting_the_service_user_clears_its_recorded_id():
    from app.auth.services.universal import delete_user

    async def scenario(client, ctx):
        await _record_id(ctx, 21, "svc")
        async with ctx.db.session() as session:
            await delete_user(21, session)
        async with ctx.db.session() as session:
            row = await session.get(TalonConnectorSettings, 1)
        reused = SimpleNamespace(id=21, username="someone-else", role_id=2)
        return row, reused

    row, reused = call(scenario)
    assert row.collect_service_user_id is None
    assert not talon_service_account.is_service_account(reused, row)  # a reused id gates nobody


def test_deleting_another_user_keeps_the_recorded_id():
    from app.auth.services.universal import delete_user

    async def scenario(client, ctx):
        await _record_id(ctx, 21, "svc")
        async with ctx.db.session() as session:
            await delete_user(2, session)
        async with ctx.db.session() as session:
            return await session.get(TalonConnectorSettings, 1)

    assert call(scenario).collect_service_user_id == 21
