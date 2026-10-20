"""Talon v2 endpoint actions in CoPilot: an approved ``collect_artifact`` or ``endpoint_command``
starts a Velociraptor flow and reports its id (talon-analyst plan EA-4; SPEC §9.5, D74-D79, D84,
INV-ACT-1).

The harness is ``test_talon_actions``'s: real routers, a real in-memory database, talon-analyst as
``FakeTalon``. Velociraptor is either a recorder of the start functions or, where what reaches
Velociraptor matters, ``test_velociraptor_query_variables``' recording gRPC stub behind the real
services.

Pinned here:
- both actions are ``endpoint-action``s on a host: an analyst (or a demoted admin) can't approve
  either, a responder can't approve for a customer they lack, and nothing starts with the setting
  off;
- the shapes CoPilot runs (``plan_for``): the record's host and client, a command artifact and at
  most 2,000 characters for a command, no command/script/quarantine/remediation artifact for a
  collection, an ``env`` list of parameters; anything else is refused before the claim;
- the re-check under the ``agents`` lock: a changed client or a shared host name starts nothing;
- two concurrent approvals start one flow;
- the run is the routes' shared start function: the host's artifact list, the parameter names and
  the route's audit event once, as the approver; it starts the flow and never waits, reads results
  or uploads; the result carries ``flow_id``, ``client_id`` and ``artifact`` in the form
  talon-analyst's resume reads; no usable flow id is ``failed``; a start error never reports the
  command;
- the command and parameter values reach Velociraptor as written (no VQL unescaping);
- ``TALON_ACTION_EXECUTE``'s audit holds the command's SHA-256 and length, never its text, while the
  mirror keeps it verbatim, and the mirror's command comes from the GET, not the stream;
- the manual ``/collect`` and ``/command`` routes still wait and return the results.

Run with: cd backend && python -m pytest tests/test_talon_endpoint_actions.py
"""

import asyncio
import hashlib
import inspect
import json
import os
import re
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy import update  # noqa: E402

import app.connectors.velociraptor.services.artifacts as artifacts_service  # noqa: E402
from app.audit.models.audit import AuditAction  # noqa: E402
from app.connectors.talon.services import talon_action_execution as execution  # noqa: E402
from app.connectors.talon.services import talon_action_sync as sync  # noqa: E402
from app.connectors.velociraptor.routes import artifacts as velociraptor_routes  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import ArtifactParameter  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import Artifacts  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import ArtifactsResponse  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    CollectArtifactBody,
)
from app.connectors.velociraptor.schema.artifacts import RunCommandBody  # noqa: E402
from app.connectors.velociraptor.services import talon_catalogue  # noqa: E402
from app.connectors.velociraptor.utils import universal  # noqa: E402
from app.connectors.velociraptor.utils.validation import (  # noqa: E402
    vql_string_literal_value,
)
from app.db.universal_models import Agents  # noqa: E402
from tests.test_talon_actions import ACME  # noqa: E402
from tests.test_talon_actions import HOST  # noqa: E402
from tests.test_talon_actions import THREAD  # noqa: E402
from tests.test_talon_actions import VID  # noqa: E402
from tests.test_talon_actions import agent_row  # noqa: E402
from tests.test_talon_actions import approve  # noqa: E402
from tests.test_talon_actions import as_user  # noqa: E402
from tests.test_talon_actions import audit_actions  # noqa: E402
from tests.test_talon_actions import call  # noqa: E402
from tests.test_talon_actions import claims  # noqa: E402
from tests.test_talon_actions import results  # noqa: E402
from tests.test_talon_actions import row_of  # noqa: E402
from tests.test_velociraptor_query_variables import _RecordingStub  # noqa: E402

FLOW = "F.CQMNTHE1CSPKC"
# talon-analyst's `talon.actions.FLOW_ID`: what its resume accepts as a started flow's id.
TALON_FLOW_ID = re.compile(r"F\.[A-Za-z0-9]{1,64}")
TARGET = {"customer_code": ACME, "agent_id": "021", "velociraptor_id": VID, "hostname": HOST, "os": "windows"}
# A regex with a backslash, and a pinned switch, as talon-analyst sends them (`_env`).
PARAMETERS = {"env": [{"key": "ProcessRegex", "value": "powershell\\.exe"}, {"key": "UsernameRegex", "value": "SYSTEM"}]}
COLLECT_ARGS = {"hostname": HOST, "velociraptor_id": VID, "artifact_name": "Windows.System.Pslist", "parameters": PARAMETERS}
# Backslashes and a quote: the manual route's VQL unescaping would change this command.
COMMAND = "Get-ChildItem 'C:\\Users\\Public' | Select-Object -First 50"
COMMAND_ARGS = {"hostname": HOST, "velociraptor_id": VID, "artifact_name": "Windows.System.PowerShell", "command": COMMAND}
PROVENANCE = {
    "untrusted_seen": False,
    "injection_detected": False,
    "web_used": False,
    "risk_labels": [],
    "shape": "read-only",
    "copied_from_output": False,
}
ARGS = {"collect_artifact": COLLECT_ARGS, "endpoint_command": COMMAND_ARGS}
HOST_ARTIFACTS = ["Windows.System.Pslist", "Windows.System.PowerShell", "Windows.System.CmdShell", "Windows.Remediation.Quarantine"]
BOTH = ["collect_artifact", "endpoint_command"]


def add(ctx, action, *, user="5", args=None, target=None, **over):
    return ctx.talon.add(
        action,
        user=user,
        target=dict(target or TARGET),
        args=json.loads(json.dumps(args if args is not None else ARGS[action])),
        provenance=dict(PROVENANCE),
        **over,
    )


class Velociraptor:
    """The routes' Velociraptor calls, recorded: the host's artifact list, the parameter check, the
    two starts (each answers ``flow_id``) and the waits, which must never be called for Talon."""

    def __init__(self, stack, flow_id=FLOW, host_artifacts=HOST_ARTIFACTS):
        self.flow_id = flow_id
        self.starts = []
        self.parameter_checks = []
        self.finishes = []
        listing = ArtifactsResponse(success=True, message="ok", artifacts=[Artifacts(name=n, description="") for n in host_artifacts])
        stack.enter_context(patch.object(velociraptor_routes, "get_all_artifacts_for_hostname", AsyncMock(return_value=listing)))
        stack.enter_context(patch.object(velociraptor_routes, "validate_artifact_parameters", self._check))
        stack.enter_context(patch.object(velociraptor_routes, "start_artifact_collection", self._start_collection))
        stack.enter_context(patch.object(velociraptor_routes, "start_remote_command", self._start_command))
        stack.enter_context(patch.object(velociraptor_routes, "finish_artifact_collection", self._finish))
        stack.enter_context(patch.object(velociraptor_routes, "finish_remote_command", self._finish))
        self.definitions = built_in_definitions(stack)

    async def _check(self, artifact_name, parameters, org_id="root"):
        plain = json.loads(json.dumps(parameters, default=lambda model: model.model_dump()))
        self.parameter_checks.append((artifact_name, plain, org_id))

    async def _start_collection(self, body, **kwargs):
        self.starts.append(("collect", body.model_dump(), kwargs))
        return self.flow_id

    async def _start_command(self, body, **kwargs):
        self.starts.append(("command", body.model_dump(), kwargs))
        return self.flow_id

    async def _finish(self, *args, **kwargs):
        self.finishes.append(args)
        raise AssertionError("a Talon action never waits for its flow")


def recording_velociraptor(stack, stub):
    """The real services against ``stub``; the artifact declares the collection's parameters."""
    service = universal.UniversalService()
    service.stub = stub

    async def fake_create(cls, connector_name):
        return service

    async def artifact_by_name(artifact_name, org_id="root"):
        parameters = [ArtifactParameter(name=n) for n in ("ProcessRegex", "PidRegex", "UsernameRegex")]
        return ArtifactsResponse(
            success=True,
            message="ok",
            artifacts=[Artifacts(name=artifact_name, description="", parameters=parameters)],
        )

    listing = ArtifactsResponse(success=True, message="ok", artifacts=[Artifacts(name=n, description="") for n in HOST_ARTIFACTS])
    stack.enter_context(patch.object(artifacts_service.UniversalService, "create", classmethod(fake_create)))
    stack.enter_context(patch.object(artifacts_service, "get_artifact_by_name", artifact_by_name))
    stack.enter_context(patch.object(velociraptor_routes, "get_all_artifacts_for_hostname", AsyncMock(return_value=listing)))
    return built_in_definitions(stack)


def built_in_definitions(stack):
    """``artifact_definitions(deps=true)`` in the host's org: built in (``compiled_in``) unless a test
    changes ``definitions.custom`` or adds ``definitions.dependencies``; lookups are recorded."""
    definitions = SimpleNamespace(custom=set(), dependencies=[], lookups=[])

    async def lookup(artifact_name, org_id):
        definitions.lookups.append((artifact_name, org_id))
        names = [artifact_name] + list(definitions.dependencies)
        return [{"name": n, "compiled_in": n not in definitions.custom} for n in names]

    stack.enter_context(patch.object(artifacts_service, "get_artifact_policy_definitions", lookup))
    return definitions


def audits(ctx):
    """Every audit event, CoPilot's Talon events and the Velociraptor routes' own, as text."""
    calls = list(ctx.audit.await_args_list) + list(ctx.quarantine_audit.await_args_list)
    return json.dumps([{k: v for k, v in c.kwargs.items() if k != "request"} for c in calls], default=str)


# ── the registry and D47 ──────────────────────────────────────────────────────


def test_both_actions_are_endpoint_actions_on_a_host():
    for action in BOTH:
        assert sync.ACTION_CLASSES[action] == "endpoint-action"
        assert action in sync.HOST_ACTIONS and action in sync.FLOW_ACTIONS and action not in sync.QUARANTINE_ACTIONS
        decides = {
            name
            for name, role in [("admin", 1), ("analyst", 2), ("customer_user", 4), ("responder", 5)]
            if execution.role_may_decide(action, SimpleNamespace(role_id=role))
        }
        assert decides == {"admin", "responder"}


@pytest.mark.parametrize("action", BOTH)
@pytest.mark.parametrize("name", ["ana", "demoted"])
def test_an_analyst_or_a_demoted_admin_cannot_approve_either(action, name):
    async def scenario(client, ctx):
        ctx.talon.lenient = True  # even if talon-analyst answered them, CoPilot refuses
        with ExitStack() as stack:
            vr = Velociraptor(stack)
            rid = add(ctx, action)
            response = await approve(client, name, rid)
        return response, claims(ctx.talon), vr.starts, await row_of(ctx, rid)

    response, claimed, starts, row = call(scenario)
    assert response.status_code == 403 and response.json()["message"] == "this role may not decide this action"
    assert claimed == [] and starts == [] and row.state == "pending"


@pytest.mark.parametrize("action", BOTH)
@pytest.mark.parametrize("lenient", [False, True], ids=["talon refuses", "copilot refuses"])
def test_a_responder_cannot_approve_for_a_customer_they_lack(action, lenient):
    async def scenario(client, ctx):
        ctx.talon.lenient = lenient
        with ExitStack() as stack:
            vr = Velociraptor(stack)
            rid = add(ctx, action)
            response = await approve(client, "globex_resp", rid)
        return response.status_code, claims(ctx.talon), vr.starts

    status, claimed, starts = call(scenario)
    assert status == (403 if lenient else 404) and claimed == [] and starts == []


@pytest.mark.parametrize("action", BOTH)
def test_with_the_setting_off_nothing_starts(action):
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack)
            rid = add(ctx, action)
            response = await approve(client, "resp", rid)
        return response, ctx.talon.requests, vr.starts

    response, requests, starts = call(scenario, enabled=False)
    assert response.status_code == 404 and response.json() == {"detail": "Not Found"}
    assert requests == [] and starts == []


# ── the shapes CoPilot runs ───────────────────────────────────────────────────


def _row(action, args=None, target=None, customer=ACME):
    return SimpleNamespace(
        action=action,
        customer_code=customer,
        target=dict(target or TARGET),
        args=args if args is not None else ARGS[action],
    )


def test_plan_for_takes_a_collection_and_a_command():
    collect = execution.plan_for(_row("collect_artifact"))
    assert (collect.hostname, collect.velociraptor_id, collect.artifact_name) == (HOST, VID, "Windows.System.Pslist")
    assert collect.parameters == (("ProcessRegex", "powershell\\.exe"), ("UsernameRegex", "SYSTEM"))
    command = execution.plan_for(_row("endpoint_command"))
    assert (command.artifact_name, command.command) == ("Windows.System.PowerShell", COMMAND)
    longest = execution.plan_for(_row("endpoint_command", {**COMMAND_ARGS, "command": "x" * 2000}))
    assert len(longest.command) == 2000
    bash = execution.plan_for(
        _row("endpoint_command", {**COMMAND_ARGS, "artifact_name": "Linux.Sys.BashShell", "command": "ps aux | head -200"}),
    )
    assert bash.artifact_name == "Linux.Sys.BashShell"


def _with(args, **changes):
    out = json.loads(json.dumps(args))
    out.update(changes)
    return out


NETSTAT_PINS = {"env": [{"key": "DumpProcess", "value": "N"}, {"key": "KillProcess", "value": "N"}]}
NETSTAT_ARGS = _with(COLLECT_ARGS, artifact_name="Windows.Network.NetstatEnriched", parameters=NETSTAT_PINS)


CATALOGUE_ONLY = "not an artifact in Talon's collection catalogue"
REFUSED = [
    ("endpoint_command", _with(COMMAND_ARGS, artifact_name="Windows.System.CmdShell"), "not a command artifact"),
    ("endpoint_command", _with(COMMAND_ARGS, command="whoami\x1b[2J"), "the command holds control or invisible characters"),
    ("endpoint_command", _with(COMMAND_ARGS, command="Get-Item x\u202e"), "the command holds control or invisible characters"),
    ("endpoint_command", _with(COMMAND_ARGS, command="Get-\u200bProcess"), "the command holds control or invisible characters"),
    ("endpoint_command", _with(COMMAND_ARGS, command="whoami\x00"), "the command holds control or invisible characters"),
    ("endpoint_command", _with(COMMAND_ARGS, command="whoami\u2028id"), "the command holds control or invisible characters"),
    ("endpoint_command", _with(COMMAND_ARGS, command="whoami\rid"), "the command holds control or invisible characters"),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Custom.Windows.System.Pslist"), CATALOGUE_ONLY),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Windows.AttackSimulation.AtomicRedTeam"), CATALOGUE_ONLY),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Windows.Sysinternals.Autoruns"), CATALOGUE_ONLY),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Linux.Utils.InstallDeb"), CATALOGUE_ONLY),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="windows.system.pslist"), CATALOGUE_ONLY),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Windows.KapeFiles.Targets"), CATALOGUE_ONLY),
    (
        "collect_artifact",
        _with(NETSTAT_ARGS, parameters={"env": [{"key": "DumpProcess", "value": "N"}, {"key": "KillProcess", "value": "Y"}]}),
        "parameter KillProcess must be sent as N for Windows.Network.NetstatEnriched",
    ),
    (
        "collect_artifact",
        _with(NETSTAT_ARGS, parameters={"env": [{"key": "DumpProcess", "value": "N"}]}),
        "parameter KillProcess must be sent as N for Windows.Network.NetstatEnriched",
    ),
    (
        "collect_artifact",
        _with(COLLECT_ARGS, parameters={"env": [{"key": "DISABLE_DANGEROUS_API_CALLS", "value": "N"}]}),
        "parameter DISABLE_DANGEROUS_API_CALLS can't be set for Windows.System.Pslist",
    ),
    (
        "collect_artifact",
        _with(COLLECT_ARGS, parameters={"env": [{"key": "ProcessRegex", "value": "a\u202eb"}]}),
        "a parameter holds control or invisible characters",
    ),
    ("endpoint_command", _with(COMMAND_ARGS, command="x" * 2001), "not a command of at most 2000 characters"),
    ("endpoint_command", _with(COMMAND_ARGS, command=""), "not a command of at most 2000 characters"),
    ("endpoint_command", _with(COMMAND_ARGS, command=["whoami"]), "not a command of at most 2000 characters"),
    ("endpoint_command", _with(COMMAND_ARGS, artifact_name="Windows.System.Pslist"), "not a command artifact"),
    ("endpoint_command", _with(COMMAND_ARGS, artifact_name="Windows.Execute.RemotePowerShellScript"), "not a command artifact"),
    ("endpoint_command", {**COMMAND_ARGS, "parameters": {"env": []}}, "the arguments are not this action's"),
    ("endpoint_command", {k: v for k, v in COMMAND_ARGS.items() if k != "command"}, "the arguments are not this action's"),
    ("endpoint_command", _with(COMMAND_ARGS, hostname="WIN-OTHER-01"), "the arguments don't name the target host"),
    ("endpoint_command", _with(COMMAND_ARGS, velociraptor_id="C.1111111111111111"), "the arguments don't name the target host"),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Windows.System.PowerShell"), CATALOGUE_ONLY),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Linux.Sys.BashShell"), CATALOGUE_ONLY),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Windows.Remediation.Quarantine"), CATALOGUE_ONLY),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Windows.Remediation.Sinkhole"), CATALOGUE_ONLY),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Generic.Client.VQL"), CATALOGUE_ONLY),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name="Windows.System.Pslist' OR 1"), "not an artifact CoPilot collects for Talon"),
    ("collect_artifact", _with(COLLECT_ARGS, artifact_name=None), "not an artifact CoPilot collects for Talon"),
    ("collect_artifact", {**COLLECT_ARGS, "command": "whoami"}, "the arguments are not this action's"),
    ("collect_artifact", _with(COLLECT_ARGS, parameters={"ProcessRegex": "x"}), "the parameters are not an env list"),
    ("collect_artifact", _with(COLLECT_ARGS, parameters=None), "the parameters are not an env list"),
    ("collect_artifact", _with(COLLECT_ARGS, parameters={"env": [{"key": "ProcessRegex"}]}), "a parameter is not a key and a value"),
    (
        "collect_artifact",
        _with(COLLECT_ARGS, parameters={"env": [{"key": "ProcessRegex", "value": 1}]}),
        "a parameter is not a short string",
    ),
    (
        "collect_artifact",
        _with(COLLECT_ARGS, parameters={"env": [{"key": "ProcessRegex", "value": "x" * 513}]}),
        "a parameter is not a short string",
    ),
    ("collect_artifact", _with(COLLECT_ARGS, parameters={"env": [{"key": "Proc`ess", "value": "x"}]}), "not a parameter name"),
    (
        "collect_artifact",
        _with(COLLECT_ARGS, parameters={"env": [{"key": "ProcessRegex", "value": "a"}, {"key": "ProcessRegex", "value": "b"}]}),
        "a parameter is given twice",
    ),
    (
        "collect_artifact",
        _with(COLLECT_ARGS, parameters={"env": [{"key": f"P{i}", "value": "x"} for i in range(17)]}),
        "too many parameters",
    ),
]


@pytest.mark.parametrize("action, args, why", REFUSED, ids=[f"{a}: {w} #{i}" for i, (a, _, w) in enumerate(REFUSED)])
def test_plan_for_refuses_what_copilot_does_not_run(action, args, why):
    with pytest.raises(execution.ProposalShape) as exc:
        execution.plan_for(_row(action, args))
    assert str(exc.value) == why


@pytest.mark.parametrize("action", BOTH)
def test_plan_for_refuses_a_target_that_is_not_the_records_host(action):
    for target in (
        {**TARGET, "customer_code": "GLOBEX"},
        {**TARGET, "velociraptor_id": VID + "-O123"},
        {**TARGET, "velociraptor_id": VID.upper()},
        {**TARGET, "hostname": ""},
    ):
        with pytest.raises(execution.ProposalShape):
            execution.plan_for(_row(action, target=target))


def test_the_response_denylist_holds_whatever_the_catalogue_says(monkeypatch):
    assert not talon_catalogue.is_response_artifact("Custom.Linux.Quarantine.NoTest")
    monkeypatch.setenv("VELOCIRAPTOR_LINUX_QUARANTINE_ARTIFACT", "Custom.Linux.Quarantine.NoTest")
    assert talon_catalogue.is_response_artifact("Custom.Linux.Quarantine.NoTest")
    for name in ("Windows.REMEDIATION.Sinkhole", "linux.remediation.x", "Windows.System.CmdShell", "Generic.Client.VQL"):
        assert talon_catalogue.is_response_artifact(name), name
    # Even if one were added to the catalogue by mistake, it is refused.
    with patch.object(
        talon_catalogue,
        "TALON_CATALOGUE",
        {**talon_catalogue.TALON_CATALOGUE, "Windows.System.PowerShell": talon_catalogue.TalonArtifact()},
    ):
        assert talon_catalogue.catalogue_violation("Windows.System.PowerShell", ()) == CATALOGUE_ONLY


# The chat catalogue of talon-analyst `main` (`talon.endpoint_catalogue`, fb6991e): the names, the
# parameters the model may set and the pins. A change there must change `talon_catalogue` too.
TALON_ANALYST_CATALOGUE = {
    "Windows.System.Pslist": (
        {"ProcessRegex", "PidRegex", "ExePathRegex", "CommandLineRegex", "UsernameRegex", "UntrustedAuthenticode"},
        {},
    ),
    "Windows.Network.Netstat": (set(), {}),
    "Windows.Network.NetstatEnriched": (
        {"IPRegex", "PortRegex", "ProcessNameRegex", "ProcessPathRegex", "CommandLineRegex", "UsernameRegex"},
        {"DumpProcess": "N", "KillProcess": "N"},
    ),
    "Windows.System.Services": ({"NameRegex", "DisplayNameRegex", "PathNameRegex", "Calculate_hashes", "CertificateInfo"}, {}),
    "Windows.System.TaskScheduler": ({"Username"}, {"AlsoUpload": "N", "UploadCommands": "N"}),
    "Windows.Sys.StartupItems": (set(), {"AlsoUpload": "N"}),
    "Windows.Persistence.PermanentWMIEvents": ({"AllRootNamespaces"}, {}),
    "Windows.System.DNSCache": (set(), {}),
    "Windows.Sys.Users": (set(), {}),
    "Windows.Forensics.Prefetch": ({"binaryRegex", "hashRegex", "IncludeFilesAccessed"}, {}),
    "Windows.EventLogs.EvtxHunter": ({"IocRegex", "WhitelistRegex", "PathRegex", "ChannelRegex", "ProviderRegex", "IdRegex"}, {}),
    "Linux.Sys.Pslist": ({"processRegex"}, {}),
    "Linux.Network.Netstat": ({"StateRegex"}, {}),
    "Linux.Sys.Users": (set(), {}),
    "Linux.Sys.LastUserLogin": ({"recent_x_days", "MaxCount", "excluded_users"}, {}),
    "Linux.Ssh.AuthorizedKeys": (set(), {"AlsoUpload": "N"}),
    "Linux.Syslog.SSHLogin": (set(), {}),
}


def test_the_allowlist_is_talon_analysts_catalogue():
    mirrored = {name: (set(entry.settable), dict(entry.pinned)) for name, entry in talon_catalogue.TALON_CATALOGUE.items()}
    assert mirrored == TALON_ANALYST_CATALOGUE


@pytest.mark.parametrize("artifact", sorted(TALON_ANALYST_CATALOGUE))
def test_each_catalogue_artifact_with_valid_parameters_is_accepted(artifact):
    settable, pinned = TALON_ANALYST_CATALOGUE[artifact]
    env = [{"key": name, "value": "x"} for name in sorted(settable)] + [{"key": k, "value": v} for k, v in sorted(pinned.items())]
    for chosen in (env, [e for e in env if e["key"] in pinned]):  # every parameter, or only the pins
        plan = execution.plan_for(_row("collect_artifact", _with(COLLECT_ARGS, artifact_name=artifact, parameters={"env": chosen})))
        assert plan.artifact_name == artifact and dict(plan.parameters) == {e["key"]: e["value"] for e in chosen}


@pytest.mark.parametrize("action", BOTH)
def test_a_proposal_copilot_cannot_run_is_refused_before_the_claim(action):
    bad = (
        _with(COMMAND_ARGS, command="x" * 2001)
        if action == "endpoint_command"
        else _with(COLLECT_ARGS, artifact_name="Windows.System.PowerShell")
    )

    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack)
            rid = add(ctx, action, args=bad)
            response = await approve(client, "resp", rid)
        return response, claims(ctx.talon), vr.starts, await row_of(ctx, rid)

    response, claimed, starts, row = call(scenario)
    assert response.status_code == 409 and response.json()["message"] == "CoPilot can't run this proposal"
    assert claimed == [] and starts == [] and row.state == "pending"


# ── the re-check under the agents lock ────────────────────────────────────────


async def _shared_name(session):
    session.add(agent_row(hostname=HOST.lower(), vid="C.1111111111111111", agent_id="022"))


async def _changed_client(session):
    await session.execute(update(Agents).where(Agents.agent_id == "021").values(velociraptor_id="C.2222222222222222"))


@pytest.mark.parametrize("action", BOTH)
@pytest.mark.parametrize(
    "change, why",
    [(_shared_name, "the host name is not on exactly one agent"), (_changed_client, "the host's Velociraptor client changed")],
    ids=["shared host name", "changed client id"],
)
def test_a_changed_client_or_a_shared_name_starts_nothing(action, change, why):
    async def scenario(client, ctx):
        async with ctx.db.session() as session:
            await change(session)
            await session.commit()
        with ExitStack() as stack:
            vr = Velociraptor(stack)
            # D47's enforce_hostname_access passes; the re-check under the lock catches the change.
            stack.enter_context(patch.object(execution, "enforce_hostname_access", AsyncMock()))
            rid = add(ctx, action)
            response = await approve(client, "resp", rid)
        return response, vr.starts, await row_of(ctx, rid), results(ctx.talon, rid), ctx.quarantine_audit.await_count

    response, starts, row, posted, route_audits = call(scenario)
    assert response.status_code == 200 and response.json()["action"]["state"] == "failed"
    assert starts == [] and route_audits == 0 and row.state == "failed"
    assert row.execution_result == {"success": False, "message": f"not run: {why}", "status_code": None}
    assert [p["outcome"] for p in posted] == ["failed"]


# ── the run ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("action", BOTH)
def test_two_concurrent_approvals_start_one_flow(action):
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack)
            rid = add(ctx, action)
            ctx.talon.claim_gate = asyncio.Event()
            first = asyncio.create_task(approve(client, "resp", rid))
            while not claims(ctx.talon):  # the first is holding its claim at talon-analyst
                await asyncio.sleep(0.01)
            second = await approve(client, "admin", rid)
            ctx.talon.claim_gate.set()
            first = await first
        return first, second, claims(ctx.talon), vr.starts, await row_of(ctx, rid)

    first, second, claimed, starts, row = call(scenario)
    assert first.status_code == 200 and first.json()["action"]["state"] == "executed"
    assert second.status_code == 409 and len(claimed) == 1 and len(starts) == 1 and row.state == "executed"


@pytest.mark.parametrize("action", BOTH)
def test_an_approved_proposal_starts_through_the_routes_checks_and_reports_the_flow(action):
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack)
            rid = add(ctx, action, user="2")  # an analyst proposed it; a responder approves
            response = await approve(client, "resp", rid)
        return response, vr, results(ctx.talon, rid), ctx.talon.records[rid], await row_of(ctx, rid), ctx

    response, vr, posted, rec, row, ctx = call(scenario)
    assert response.status_code == 200 and response.json()["action"]["state"] == "executed"
    artifact = ARGS[action]["artifact_name"]
    expected = {
        "success": True,
        "message": "Velociraptor flow started",
        "status_code": 200,
        "flow_id": FLOW,
        "client_id": VID,
        "artifact": artifact,
    }
    assert [p["outcome"] for p in posted] == ["executed"] and posted[0]["result"] == expected
    assert rec["status"] == "executed" and row.execution_result == expected and row.outcome_posted_at is not None
    # What talon-analyst's resume (`started_result`) reads: only `result.flow_id`, in its F. form.
    assert TALON_FLOW_ID.fullmatch(posted[0]["result"]["flow_id"])
    # Started once, through the route's checks, with the values as written; never waited for.
    ((kind, body, kwargs),) = vr.starts
    assert kwargs == ({"literal_values": True} if kind == "collect" else {"literal": True}) and vr.finishes == []
    assert (body["hostname"], body["velociraptor_id"], body["velociraptor_org"]) == (HOST, VID, "root")
    if action == "collect_artifact":
        assert kind == "collect" and body["artifact_name"] == artifact and body["parameters"] == PARAMETERS
        assert vr.parameter_checks == [(artifact, body["parameters"], "root")]
        assert body["data_store_only"] is False  # no wait and no upload either way: finish isn't called
    else:
        assert kind == "command" and body["command"] == COMMAND and body["artifact_name"] == artifact
    # The route's own audit event, once, as the approver; Talon's approve and execute.
    (route_audit,) = ctx.quarantine_audit.await_args_list
    route_action = AuditAction.ARTIFACT_COLLECT if action == "collect_artifact" else AuditAction.RESPONSE_COMMAND_EXECUTE
    assert route_audit.kwargs["action"] == route_action and route_audit.kwargs["actor_username"] == "resp"
    assert route_audit.kwargs["new_value"] == {"artifact_name": artifact, "velociraptor_id": VID}
    assert audit_actions(ctx) == [(AuditAction.TALON_ACTION_APPROVE, "success"), (AuditAction.TALON_ACTION_EXECUTE, "success")]


@pytest.mark.parametrize("action", BOTH)
def test_an_artifact_outside_the_hosts_list_starts_nothing(action):
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack, host_artifacts=["Windows.Network.Netstat"])
            rid = add(ctx, action)
            response = await approve(client, "resp", rid)
        return response, vr.starts, results(ctx.talon, rid), ctx.quarantine_audit.await_count

    response, starts, posted, route_audits = call(scenario)
    assert response.json()["action"]["state"] == "failed" and starts == [] and route_audits == 0
    (result,) = [p["result"] for p in posted]
    artifact = ARGS[action]["artifact_name"]
    assert result == {
        "success": False,
        "message": f"Artifact name {artifact} does not apply for hostname {HOST} or does not exist",
        "status_code": 400,
    }


def test_a_parameter_the_artifact_does_not_declare_starts_nothing():
    stub = _RecordingStub(hostname=HOST)
    args = _with(COLLECT_ARGS, parameters={"env": [{"key": "ExePathRegex", "value": "x"}]})  # this server's Pslist lacks it

    async def scenario(client, ctx):
        with ExitStack() as stack:
            recording_velociraptor(stack, stub)
            rid = add(ctx, "collect_artifact", args=args)
            response = await approve(client, "resp", rid)
        return response, results(ctx.talon, rid)

    response, posted = call(scenario)
    assert response.json()["action"]["state"] == "failed"
    (result,) = [p["result"] for p in posted]
    assert result["status_code"] == 400 and result["message"].startswith("Parameter 'ExePathRegex' is not valid")
    assert not any("collect_client(" in vql for vql, _, _ in stub.calls())


class _FlowStub(_RecordingStub):
    """Velociraptor answering a collect_client with ``rows``."""

    def __init__(self, rows):
        super().__init__(hostname=HOST)
        self.rows = rows

    def Query(self, request, timeout=None):  # noqa: N802 - gRPC method name
        if "collect_client(" in request.Query[0].VQL:
            self.requests.append(request)
            return [SimpleNamespace(Response=json.dumps(self.rows), log="")]
        return super().Query(request, timeout)


@pytest.mark.parametrize("action", BOTH)
@pytest.mark.parametrize(
    "rows, message",
    [
        ([], "CoPilot could not start the collection"),
        ([{"Flow": {}}], "CoPilot could not start the collection"),
        ([{"Flow": {"flow_id": "F.CQMNTHE1CSPKC.H"}}], "CoPilot could not start the collection"),
        ([{"Flow": {"flow_id": "F." + "A" * 65}}], "Velociraptor gave no usable flow id"),
    ],
    ids=["no row", "no flow id", "a hunt id", "too long for talon-analyst"],
)
def test_a_start_without_a_usable_flow_id_reports_failed(action, rows, message):
    stub = _FlowStub(rows)

    async def scenario(client, ctx):
        with ExitStack() as stack:
            recording_velociraptor(stack, stub)
            rid = add(ctx, action)
            response = await approve(client, "resp", rid)
        return response, results(ctx.talon, rid), ctx.talon.records[rid], await row_of(ctx, rid), stub, audits(ctx)

    response, posted, rec, row, stub, audited = call(scenario)
    assert response.json()["action"]["state"] == "failed" and row.state == "failed" and rec["status"] == "failed"
    (result,) = [p["result"] for p in posted]
    assert result == {"success": False, "message": message, "status_code": 500} and "flow_id" not in result
    assert [vql for vql, _, _ in stub.calls() if "collect_client(" in vql]  # it may have started; never waited for
    assert not any("watch_monitoring(" in vql or "source(" in vql for vql, _, _ in stub.calls())
    assert "Get-ChildItem" not in json.dumps(result) and "Get-ChildItem" not in audited


@pytest.mark.parametrize("action", BOTH)
def test_a_start_error_never_reports_the_request(action):
    class Broken(_RecordingStub):
        def Query(self, request, timeout=None):  # noqa: N802 - gRPC method name
            raise RuntimeError("the gRPC channel broke")

    async def scenario(client, ctx):
        with ExitStack() as stack:
            recording_velociraptor(stack, Broken(hostname=HOST))
            stack.enter_context(patch.object(velociraptor_routes, "validate_artifact_parameters", AsyncMock()))
            rid = add(ctx, action)
            response = await approve(client, "resp", rid)
        return response, results(ctx.talon, rid), audits(ctx)

    response, posted, audited = call(scenario)
    action = response.json()["action"]
    assert action["state"] == "failed" and action["state_reason"] == "CoPilot could not start the collection"
    assert [p["result"] for p in posted] == [{"success": False, "message": "CoPilot could not start the collection", "status_code": 500}]
    assert action["execution_result"] == posted[0]["result"] and "Get-ChildItem" not in audited


# ── what reaches Velociraptor ─────────────────────────────────────────────────


@pytest.mark.parametrize("action", BOTH)
def test_the_command_and_parameters_reach_velociraptor_as_written(action):
    stub = _RecordingStub(hostname=HOST)

    async def scenario(client, ctx):
        with ExitStack() as stack:
            recording_velociraptor(stack, stub)
            rid = add(ctx, action)
            response = await approve(client, "resp", rid)
        return response, results(ctx.talon, rid)

    response, posted = call(scenario)
    assert response.json()["action"]["state"] == "executed" and posted[0]["result"]["flow_id"] == FLOW
    vql, env, org = stub.call_with("collect_client(")
    assert org == "root"
    if action == "endpoint_command":
        assert vql == artifacts_service.VQL_RUN_COMMAND
        assert env == {"OrgId": "root", "ClientId": VID, "ArtifactName": "Windows.System.PowerShell", "Command": COMMAND}
        assert vql_string_literal_value(COMMAND) != COMMAND  # what the manual route's unescaping would have run
    else:
        assert vql == artifacts_service.VQL_COLLECT_WITH_ENV.format(env="`ProcessRegex`=Param0, `UsernameRegex`=Param1")
        assert env == {
            "OrgId": "root",
            "ClientId": VID,
            "ArtifactName": "Windows.System.Pslist",
            "Param0": "powershell\\.exe",
            "Param1": "SYSTEM",
        }
        assert "powershell" not in vql
    # Started, never waited for, read or uploaded.
    assert [v for v, _, _ in stub.calls() if "collect_client(" not in v and "artifact_definitions(" not in v] == []


# ── the audit and the mirror ──────────────────────────────────────────────────


def test_the_audit_log_holds_the_commands_hash_not_its_text():
    async def scenario(client, ctx):
        with ExitStack() as stack:
            Velociraptor(stack)
            rid = add(ctx, "endpoint_command")
            response = await approve(client, "resp", rid)
            card = await client.get(f"/talon/actions/{rid}", headers=as_user("resp"))
        return response, ctx, await row_of(ctx, rid), card.json()["action"]

    response, ctx, row, card = call(scenario)
    assert response.json()["action"]["state"] == "executed"
    (execute,) = [c for c in ctx.audit.await_args_list if c.kwargs["action"] == AuditAction.TALON_ACTION_EXECUTE]
    args = execute.kwargs["new_value"]["args"]
    assert args == {
        "hostname": HOST,
        "velociraptor_id": VID,
        "artifact_name": "Windows.System.PowerShell",
        "command_sha256": hashlib.sha256(COMMAND.encode("utf-8")).hexdigest(),
        "command_length": len(COMMAND),
    }
    assert "Get-ChildItem" not in audits(ctx) and "Public" not in audits(ctx)
    # The mirror and the card keep it verbatim, for the person deciding.
    assert row.args["command"] == COMMAND and card["args"]["command"] == COMMAND


def test_audited_args_replaces_only_a_command():
    assert execution.audited_args("collect_artifact", COLLECT_ARGS) == COLLECT_ARGS
    assert execution.audited_args("quarantine_host", {"hostname": HOST}) == {"hostname": HOST}
    lone = "a\ud800b"  # never valid UTF-8, still hashed rather than failing the audit
    out = execution.audited_args("endpoint_command", {"command": lone})
    assert out["command_length"] == 3 and len(out["command_sha256"]) == 64 and "command" not in out
    out = execution.audited_args("endpoint_command", {"command": ["rm", "-rf"]})
    assert "command" not in out and out["command_length"] == len(repr(["rm", "-rf"]))


def test_the_mirrors_command_comes_from_the_get_not_the_stream():
    async def scenario(client, ctx):
        rid = add(ctx, "endpoint_command", tool_call_id="call_cmd")
        claimed = {"type": "tool-input-available", "toolCallId": "call_cmd", "toolName": "endpoint_command"}
        claimed["input"] = {"agent_id": "021", "shell": "powershell", "command": "Remove-Item -Recurse -Force C:\\"}
        card = {"type": "tool-approval-request", "approvalId": rid, "toolCallId": "call_cmd"}
        wire = f"data: {json.dumps(claimed)}\n\ndata: {json.dumps(card)}\n\ndata: [DONE]\n\n".encode()
        ctx.talon.chat_pieces = [wire[i : i + 7] for i in range(0, len(wire), 7)]
        response = await client.post(f"/talon/v2/chat/{THREAD}", json={"message": "list the users folder"}, headers=as_user("resp"))
        await sync.wait_for_background()
        return response, wire, await row_of(ctx, rid)

    response, wire, row = call(scenario)
    assert response.status_code == 200 and response.content == wire  # forwarded byte for byte
    assert row is not None and row.args == COMMAND_ARGS and row.provenance == PROVENANCE


# ── the shared start functions and the manual routes ──────────────────────────


def test_the_start_functions_signatures_are_pinned():
    for function in (velociraptor_routes.start_collection_as, velociraptor_routes.start_command_as):
        assert list(inspect.signature(function).parameters) == [
            "current_user",
            "collect_artifact_body" if function is velociraptor_routes.start_collection_as else "run_command_body",
            "request",
            "session",
            "literal_values",
        ] + (["require_built_in"] if function is velociraptor_routes.start_collection_as else [])
        assert inspect.signature(function).parameters["literal_values"].default is False
    assert inspect.signature(velociraptor_routes.start_collection_as).parameters["require_built_in"].default is False


class _HostRows:
    """An AsyncSession stand-in for the manual routes: every agent query returns the one host."""

    def __init__(self):
        self.agent = agent_row()

    async def execute(self, statement):
        rows = [self.agent]
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: rows, first=lambda: rows[0]))

    def add(self, obj):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


@pytest.mark.parametrize("route", ["collect", "command"])
def test_the_manual_routes_still_wait_and_return_results(route):
    stub = _RecordingStub(hostname=HOST)
    audit = AsyncMock()
    user = SimpleNamespace(id=1, username="admin", role_id=1)
    command = "Get-ChildItem C:\\\\Users"  # the frontend doubles a path's backslashes

    async def run():
        with ExitStack() as stack:
            recording_velociraptor(stack, stub)
            stack.enter_context(patch.object(velociraptor_routes, "enforce_hostname_access", AsyncMock()))
            stack.enter_context(patch.object(velociraptor_routes, "record_audit_event", audit))
            stack.enter_context(patch.object(artifacts_service, "fetch_file_from_filestore", AsyncMock(return_value={"success": False})))
            if route == "collect":
                body = CollectArtifactBody(
                    hostname=HOST,
                    artifact_name="Windows.System.Pslist",
                    parameters={"env": [{"key": "ProcessRegex", "value": "C:\\\\x"}]},
                )
                return await velociraptor_routes.collect_artifact(body, request=None, current_user=user, session=_HostRows())
            body = RunCommandBody(hostname=HOST, artifact_name="Windows.System.PowerShell", command=command)
            return await velociraptor_routes.run_command(body, request=None, current_user=user, session=_HostRows())

    response = asyncio.run(run())
    assert response.success is True and response.results == [{"Stdout": "ok", "client_id": "C.475df76785008b04"}]
    queries = [vql for vql, _, _ in stub.calls() if "artifact_definitions(" not in vql]
    assert [q.split(" FROM ")[0] if "collect_client(" not in q else "collect" for q in queries] == [
        "collect",
        "SELECT *",  # watch_monitoring: the route waits for the flow, as before
        "SELECT *",  # source(): and reads its results
    ]
    assert "watch_monitoring(" in queries[1] and "source(" in queries[2]
    _, env, _ = stub.call_with("collect_client(")
    if route == "command":
        assert env["Command"] == "Get-ChildItem C:\\Users"  # still VQL-unescaped for the manual route
    else:
        assert env["Param0"] == "C:\\x"
    (event,) = audit.await_args_list
    assert event.kwargs["action"] == (AuditAction.ARTIFACT_COLLECT if route == "collect" else AuditAction.RESPONSE_COMMAND_EXECUTE)
    assert "Get-ChildItem" not in json.dumps(event.kwargs["new_value"])


def test_a_manual_route_refusal_happens_before_anything_starts():
    async def run():
        with ExitStack() as stack:
            start = AsyncMock()
            stack.enter_context(patch.object(velociraptor_routes, "start_remote_command", start))
            stack.enter_context(
                patch.object(
                    velociraptor_routes,
                    "enforce_hostname_access",
                    AsyncMock(side_effect=HTTPException(status_code=403, detail="no")),
                ),
            )
            body = RunCommandBody(hostname=HOST, artifact_name="Windows.System.PowerShell", command="whoami")
            with pytest.raises(HTTPException) as exc:
                await velociraptor_routes.run_command(
                    body,
                    request=None,
                    current_user=SimpleNamespace(id=5, username="r", role_id=5),
                    session=_HostRows(),
                )
            return exc.value.status_code, start.await_count

    assert asyncio.run(run()) == (403, 0)


# ── review of #1286: the extra layers ─────────────────────────────────────────


@pytest.mark.parametrize("custom", ["artifact", "dependency"])
def test_a_collection_whose_definition_is_not_built_in_starts_nothing(custom):
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack)
            if custom == "artifact":
                vr.definitions.custom.add("Windows.System.Pslist")
            else:
                vr.definitions.dependencies.append("Custom.Shadow.Lnk")
                vr.definitions.custom.add("Custom.Shadow.Lnk")
            rid = add(ctx, "collect_artifact")
            response = await approve(client, "resp", rid)
        return response, vr, results(ctx.talon, rid), ctx.quarantine_audit.await_count

    response, vr, posted, route_audits = call(scenario)
    assert response.json()["action"]["state"] == "failed" and vr.starts == [] and route_audits == 0
    assert vr.definitions.lookups == [("Windows.System.Pslist", "root")]  # in the host's org
    (result,) = [p["result"] for p in posted]
    assert result["status_code"] == 403 and "built-in definition" in result["message"]


def test_a_built_in_collection_reads_its_definitions_in_the_hosts_org():
    async def scenario(client, ctx):
        with ExitStack() as stack:
            vr = Velociraptor(stack)
            rid = add(ctx, "collect_artifact")
            response = await approve(client, "resp", rid)
        return response, vr

    response, vr = call(scenario)
    assert response.json()["action"]["state"] == "executed" and vr.definitions.lookups == [("Windows.System.Pslist", "root")]


@pytest.mark.parametrize("action", BOTH + ["quarantine_host"])
def test_a_host_outside_the_root_org_runs_nothing(action):
    async def scenario(client, ctx):
        async with ctx.db.session() as session:
            await session.execute(update(Agents).where(Agents.agent_id == "021").values(velociraptor_org="O123"))
            await session.commit()
        with ExitStack() as stack:
            vr = Velociraptor(stack)
            if action == "quarantine_host":
                rid = ctx.talon.add(action, user="5")
            else:
                rid = add(ctx, action)
            response = await approve(client, "resp", rid)
        return response, vr.starts, await row_of(ctx, rid), ctx.velociraptor.await_count

    response, starts, row, quarantined = call(scenario)
    assert response.json()["action"]["state"] == "failed" and starts == [] and quarantined == 0
    assert row.execution_result["message"] == "not run: the host is not in Velociraptor's root org"


def test_a_flow_started_on_another_client_is_failed():
    plan = execution.plan_for(_row("collect_artifact"))
    other = SimpleNamespace(flow_id=FLOW, client_id="C.1111111111111111", artifact="Windows.System.Pslist")
    assert execution.started_result(other, plan) == {
        "success": False,
        "message": "the flow started on another Velociraptor client than the proposal's",
        "status_code": 500,
    }
    same = SimpleNamespace(flow_id=FLOW, client_id=VID.upper().replace("C.", "C."), artifact="Windows.System.Pslist")
    assert execution.started_result(same, plan)["client_id"] == VID  # the same client, as stored in another case


def test_a_flow_on_another_client_is_reported_failed_end_to_end():
    async def scenario(client, ctx):
        with ExitStack() as stack:
            Velociraptor(stack)
            real = velociraptor_routes.start_command_as

            async def elsewhere(*args, **kwargs):
                started = await real(*args, **kwargs)
                return velociraptor_routes.StartedFlow(started.flow_id, "C.1111111111111111", started.org_id, started.artifact)

            stack.enter_context(patch.object(velociraptor_routes, "start_command_as", elsewhere))
            rid = add(ctx, "endpoint_command")
            response = await approve(client, "resp", rid)
        return response, results(ctx.talon, rid)

    response, posted = call(scenario)
    assert response.json()["action"]["state"] == "failed"
    assert [p["result"]["message"] for p in posted] == ["the flow started on another Velociraptor client than the proposal's"]


# A newline, a backtick (PowerShell's continuation and escape), both quotes and backslashes.
TRICKY = "Get-ChildItem \"C:\\Users\\Public\" |`\n  Where-Object { $_.Name -like '*.ps1' } | Select-Object -First 50 # \\x41 \\n"


def test_a_tricky_command_runs_verbatim_through_the_parameterized_path():
    stub = _RecordingStub(hostname=HOST)
    assert "\n" in TRICKY and "`" in TRICKY and '"' in TRICKY and "'" in TRICKY and "\\" in TRICKY

    async def scenario(client, ctx):
        with ExitStack() as stack:
            recording_velociraptor(stack, stub)
            rid = add(ctx, "endpoint_command", args=_with(COMMAND_ARGS, command=TRICKY))
            response = await approve(client, "resp", rid)
        return response

    response = call(scenario)
    assert response.json()["action"]["state"] == "executed"
    vql, env, _ = stub.call_with("collect_client(")
    assert vql == artifacts_service.VQL_RUN_COMMAND and env["Command"] == TRICKY
    assert "Where-Object" not in vql and vql_string_literal_value(TRICKY) != TRICKY


class _EchoingStub(_RecordingStub):
    """Velociraptor echoing the collection's request, the command with it, as collect_client and the
    flow completion event do."""

    def Query(self, request, timeout=None):  # noqa: N802 - gRPC method name
        vql = request.Query[0].VQL
        env = {e.key: e.value for e in request.env}
        if "collect_client(" in vql:
            self.requests.append(request)
            echo = {"flow_id": FLOW, "request": {"specs": [{"parameters": {"env": [{"key": "Command", "value": env.get("Command")}]}}]}}
            return [SimpleNamespace(Response=json.dumps([{"Flow": echo}]), log="")]
        if "watch_monitoring(" in vql:
            self.requests.append(request)
            return [SimpleNamespace(Response=json.dumps([{"FlowId": FLOW, "Flow": {"request": {"env": SECRET}}}]), log="")]
        return super().Query(request, timeout)


SECRET = "Get-Secret-Marker-7c1e"


@pytest.mark.parametrize("path", ["talon", "manual", "manual failure"])
def test_the_command_never_appears_in_the_logs(path):
    from loguru import logger

    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="DEBUG")
    stub = _EchoingStub(hostname=HOST)
    command = f"{SECRET} -Path 'C:\\Users'"
    try:
        if path == "talon":

            async def scenario(client, ctx):
                with ExitStack() as stack:
                    recording_velociraptor(stack, stub)
                    rid = add(ctx, "endpoint_command", args=_with(COMMAND_ARGS, command=command))
                    return await approve(client, "resp", rid)

            assert call(scenario).json()["action"]["state"] == "executed"
        else:
            if path == "manual failure":
                stub.Query = lambda request, timeout=None: (_ for _ in ()).throw(RuntimeError("the channel broke"))

            async def run():
                with ExitStack() as stack:
                    recording_velociraptor(stack, stub)
                    stack.enter_context(patch.object(velociraptor_routes, "enforce_hostname_access", AsyncMock()))
                    stack.enter_context(patch.object(velociraptor_routes, "record_audit_event", AsyncMock()))
                    body = RunCommandBody(hostname=HOST, artifact_name="Windows.System.PowerShell", command=command)
                    user = SimpleNamespace(id=1, username="admin", role_id=1)
                    try:
                        return await velociraptor_routes.run_command(body, request=None, current_user=user, session=_HostRows())
                    except HTTPException as exc:
                        return exc

            outcome = asyncio.run(run())
            if path == "manual failure":
                # CoPilot's HTTPException handler writes the detail to its error log too.
                assert isinstance(outcome, HTTPException) and outcome.status_code == 500 and SECRET not in str(outcome.detail)
                assert "artifact Windows.System.PowerShell" in outcome.detail
            else:
                assert outcome.success is True
    finally:
        logger.remove(sink)
    text = "\n".join(lines)
    assert lines and SECRET not in text
    assert "Windows.System.PowerShell" in text
