"""An analyst can only collect allowlisted, read-only artifacts through ``POST /api/artifacts/collect``.

``/collect`` admits admin and analyst and used to accept any artifact in the host's OS list,
which includes the command artifacts (``Windows.System.PowerShell``, ``CmdShell``,
``Linux.Sys.BashShell``) and the ``*.Remediation.*`` ones. An analyst could therefore run an
arbitrary command, or quarantine a host, around the admin/responder-only ``/command`` and
``/quarantine``. ``collection_policy`` now applies an allowlist to anyone but an admin or
responder: the artifact and every artifact it depends on, as the host's own Velociraptor org
resolves them (``artifact_definitions(names=[X], deps=true)``), must be on ``ANALYST_ARTIFACTS``
and be Velociraptor's compiled-in definition; every parameter set must be on its safe list (or
left at its default); and each definition must still look read-only to a text scan that sees
through backticks and comments.

The routes also resolve the target host once: every agent row with the hostname is
access-checked, rows that disagree on client, org or customer are a 409, and the single row
supplies the client id and org.

The route functions are called directly with their collaborators patched. No DB, no Velociraptor.

Run with: cd backend && python -m pytest tests/test_velociraptor_collect_policy.py
"""

import asyncio
import os
import re
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")
os.environ.setdefault("MYSQL_PASSWORD", "test-only-password-not-the-default")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "test-only-password-not-the-default")

import app.connectors.velociraptor.routes.artifacts as routes  # noqa: E402
import app.connectors.velociraptor.services.artifacts as artifacts_service  # noqa: E402
from app.auth.models.users import RoleEnum  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import Artifacts  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import ArtifactsResponse  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    CollectArtifactBody,
)
from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    CollectArtifactResponse,
)
from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    CommandArtifactsEnum,
)
from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    QuarantineArtifactsEnum,
)
from app.connectors.velociraptor.schema.artifacts import QuarantineBody  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    QuarantineResponse,
)
from app.connectors.velociraptor.schema.artifacts import RunCommandBody  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    RunCommandResponse,
)
from app.connectors.velociraptor.services import collection_policy  # noqa: E402
from app.middleware import customer_access  # noqa: E402

ANALYST = SimpleNamespace(id=2, username="analyst", role_id=RoleEnum.analyst.value)
RESPONDER = SimpleNamespace(id=5, username="responder", role_id=RoleEnum.responder.value)
ADMIN = SimpleNamespace(id=1, username="admin", role_id=RoleEnum.admin.value)
HOST_ORG = "O1234ABCD"
HOST_CLIENT = "C.475df76785008b04"
HOST_CUSTOMER = "00001"


def _definition(query="SELECT * FROM pslist()", parameters=(), **fields):
    """A definition as artifact_definitions() reports it; built in (``compiled_in``) unless overridden."""
    fields.setdefault("compiled_in", True)
    return {"parameters": [dict(p) for p in parameters], "sources": [{"query": query}], **fields}


def _agent(customer_code=HOST_CUSTOMER, velociraptor_id=HOST_CLIENT, velociraptor_org=HOST_ORG):
    return SimpleNamespace(
        hostname="HOST-1",
        customer_code=customer_code,
        velociraptor_id=velociraptor_id,
        velociraptor_org=velociraptor_org,
    )


class _AgentRows:
    """An AsyncSession stand-in: every agent query by hostname returns `rows`."""

    def __init__(self, rows):
        self.rows = rows

    async def execute(self, statement):
        rows = list(self.rows)
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: rows, first=lambda: rows[0] if rows else None))

    async def commit(self):
        pass


# Definitions as Velociraptor's artifact_definitions() reports them in the host's org (abridged).
DEFINITIONS = {
    "Windows.System.PowerShell": _definition(
        "SELECT * FROM execve(argv=[PowerShellExe, '-c', Command])",
        [{"name": "Command"}, {"name": "PowerShellExe", "default": "C:\\Windows\\powershell.exe"}],
        required_permissions=["EXECVE"],
    ),
    "Windows.System.CmdShell": _definition(
        "SELECT * FROM execve(argv=['cmd', '/c', Command])",
        [{"name": "Command"}],
        required_permissions=["EXECVE"],
    ),
    "Linux.Sys.BashShell": _definition(
        "SELECT * FROM execve(argv=['bash', '-c', Command])",
        [{"name": "Command"}],
        required_permissions=["EXECVE"],
    ),
    "Windows.Remediation.Quarantine": _definition("SELECT * FROM execve(argv=['netsh'])", required_permissions=["EXECVE", "NETWORK"]),
    "Linux.Remediation.Quarantine": _definition("SELECT * FROM execve(argv=['nft'])", required_permissions=["EXECVE", "NETWORK"]),
    "Custom.Linux.Remediation.Quarantine": _definition("SELECT * FROM execve(argv=['nft'])"),
    "Windows.System.WMIQuery": _definition("SELECT * FROM wmi(query=Query)", [{"name": "Query"}], required_permissions=["EXECVE"]),
    "Windows.Sigma.EventLogs": _definition("SELECT * FROM execve(argv=['x'])", required_permissions=["EXECVE", "FILESYSTEM_WRITE"]),
    "Windows.KapeFiles.Targets": _definition("SELECT upload(file=OSPath) FROM glob(globs=Glob)", [{"name": "Device"}]),
    "Custom.Windows.Anything": _definition(),
    # Triage, as on the allowlist.
    "Windows.Sys.Programs": _definition(
        "SELECT * FROM read_reg_key(globs=programKeys)",
        [{"name": "programKeys", "default": "HKLM\\Software\\*"}],
    ),
    "Windows.System.Pslist": _definition(
        "SELECT * FROM pslist() WHERE Name =~ ProcessRegex",
        [{"name": "ProcessRegex", "default": "."}, {"name": "PidRegex", "default": "."}],
    ),
    "Windows.Network.Netstat": _definition("SELECT * FROM netstat()"),
    "Windows.Forensics.Prefetch": _definition(
        "SELECT * FROM glob(globs=prefetchGlobs)",
        [{"name": "dateAfter"}, {"name": "prefetchGlobs"}],
    ),
    "Linux.Sys.Pslist": _definition("SELECT * FROM pslist() WHERE Name =~ processRegex", [{"name": "processRegex", "default": "."}]),
    "MacOS.System.QuarantineEvents": _definition("SELECT * FROM sqlite(file=QuarantineGlob)", [{"name": "QuarantineGlob"}]),
}


@pytest.fixture
def collect(monkeypatch):
    """Call the /collect route as `user`; return its response. `run.calls` records what happened.

    `run.agents` are the agent rows for the hostname, `run.accessible` the customer codes the
    caller may see, `run.definitions` what the host's org resolves each artifact name to and
    `run.dependencies` the artifacts each one depends on (returned by the deps=true lookup).
    """
    calls = {"collections": [], "targets": [], "definition_lookups": [], "commands": [], "quarantines": []}
    definitions = dict(DEFINITIONS)
    dependencies = {}
    accessible = ["*"]
    session = _AgentRows([_agent()])

    async def allow_host(user, hostname, session):
        return None

    async def accessible_customers(user, session):
        return list(accessible)

    async def host_artifacts(hostname, session):
        return ArtifactsResponse(success=True, message="ok", artifacts=[Artifacts(name=name, description="") for name in definitions])

    async def no_parameter_check(name, parameters, org_id="root"):
        return None

    async def audit(**kwargs):
        return None

    # The routes start the flow (start_collection_as / start_command_as), then wait for it.
    async def start_collection(body, literal_values=False, limits=None):
        calls["collections"].append(body.artifact_name)
        calls["targets"].append((body.velociraptor_id, body.velociraptor_org))
        return "F.COLLECTED"

    async def finish_collection(body, flow_id, session):
        return CollectArtifactResponse(success=True, message="collected", results=[])

    async def start_command(body, literal=False):
        calls["commands"].append((body.velociraptor_id, body.velociraptor_org))
        return "F.RAN"

    async def finish_command(body, flow_id):
        return RunCommandResponse(success=True, message="ran", results=[])

    async def quarantine_host(body):
        calls["quarantines"].append((body.velociraptor_id, body.velociraptor_org))
        return QuarantineResponse(success=True, message="quarantined", results=[])

    async def quarantine_status(session, body, response):
        return None

    async def policy_definitions(name, org_id):
        calls["definition_lookups"].append((name, org_id))
        found = definitions.get(name)
        if found is None:
            return []
        return [{"name": name, **found}] + [{"name": dep, **definitions[dep]} for dep in dependencies.get(name, ())]

    # The coarse hostname check is the pre-existing one; the per-row checks under test go
    # through the real enforce_owned_object_access with the caller's accessible customers.
    monkeypatch.setattr(routes, "enforce_hostname_access", allow_host)
    monkeypatch.setattr(customer_access.customer_access_handler, "get_user_accessible_customers", accessible_customers)
    monkeypatch.setattr(routes, "get_all_artifacts_for_hostname", host_artifacts)
    monkeypatch.setattr(routes, "validate_artifact_parameters", no_parameter_check)
    monkeypatch.setattr(routes, "record_audit_event", audit)
    monkeypatch.setattr(routes, "start_artifact_collection", start_collection)
    monkeypatch.setattr(routes, "finish_artifact_collection", finish_collection)
    monkeypatch.setattr(routes, "start_remote_command", start_command)
    monkeypatch.setattr(routes, "finish_remote_command", finish_command)
    monkeypatch.setattr(routes, "quarantine_host", quarantine_host)
    monkeypatch.setattr(routes, "update_agent_quarantine_status", quarantine_status)
    monkeypatch.setattr(artifacts_service, "get_artifact_policy_definitions", policy_definitions)

    def run(user, artifact_name, parameters=None):
        body = CollectArtifactBody(hostname="HOST-1", artifact_name=artifact_name, parameters=parameters)
        return asyncio.run(routes.collect_artifact(body, request=None, current_user=user, session=session))

    def command(user):
        body = RunCommandBody(hostname="HOST-1", command="id", artifact_name=CommandArtifactsEnum.windows_powershell)
        return asyncio.run(routes.run_command(body, request=None, current_user=user, session=session))

    def quarantine(user):
        body = QuarantineBody(hostname="HOST-1", action="quarantine", artifact_name=QuarantineArtifactsEnum.windows_quarantine)
        return asyncio.run(routes.quarantine(body, request=None, current_user=user, session=session))

    run.calls = calls
    run.definitions = definitions
    run.dependencies = dependencies
    run.accessible = accessible
    run.agents = session.rows
    run.command = command
    run.quarantine = quarantine
    return run


def _refused(collect, user, artifact, parameters=None):
    with pytest.raises(HTTPException) as exc:
        collect(user, artifact, parameters=parameters)
    assert exc.value.status_code == 403
    assert collect.calls["collections"] == []
    return exc.value.detail


# --- what an analyst cannot do ---------------------------------------------------------


@pytest.mark.parametrize(
    "artifact",
    [
        "Windows.System.PowerShell",
        "Windows.System.CmdShell",
        "Linux.Sys.BashShell",
        "Windows.Remediation.Quarantine",
        "Linux.Remediation.Quarantine",
        "Custom.Linux.Remediation.Quarantine",
    ],
)
def test_analyst_cannot_collect_command_or_remediation_artifacts(collect, artifact):
    _refused(collect, ANALYST, artifact, parameters={"env": [{"key": "Command", "value": "id"}]})


@pytest.mark.parametrize(
    "artifact",
    ["Windows.System.WMIQuery", "Windows.Sigma.EventLogs", "Windows.KapeFiles.Targets", "Custom.Windows.Anything"],
)
def test_analyst_cannot_collect_artifacts_off_the_allowlist(collect, artifact):
    assert "allowlist" in _refused(collect, ANALYST, artifact)


@pytest.mark.parametrize(
    "query, fields",
    [
        ("SELECT * FROM execve(argv=['powershell', '-c', 'whoami'])", {}),  # runs a command, declares nothing
        ("SELECT upload(file='C:/Windows/System32/config/SAM') FROM scope()", {}),
        ("SELECT rm(filename='C:/evidence.log') FROM scope()", {}),
        ("SELECT pskill(pid=4242) FROM scope()", {}),
        ("SELECT * FROM http_client(url='https://example.invalid/x')", {}),
        ("SELECT * FROM query(query=SomeVQL)", {}),
        ("SELECT * FROM Artifact.Generic.Utils.FetchBinary(ToolName='x')", {}),
        ("SELECT * FROM pslist()", {"required_permissions": ["EXECVE"]}),
        ("SELECT * FROM pslist()", {"implied_permissions": ["FILESYSTEM_WRITE"]}),
        ("SELECT * FROM pslist()", {"imports": ["Custom.Helpers"]}),
        ("SELECT * FROM pslist()", {"tools": [{"name": "Autoruns", "url": "https://example.invalid/a.zip"}]}),
    ],
    ids=[
        "undeclared-execve",
        "upload",
        "rm",
        "pskill",
        "http_client",
        "dynamic-vql",
        "tool-fetch",
        "required-perm",
        "implied-perm",
        "imports",
        "tools",
    ],
)
def test_an_allowlisted_name_with_a_capable_definition_is_refused(collect, query, fields):
    """Rule 4: the definition in the host's org is what runs, so it is scanned every time."""
    collect.definitions["Windows.System.Pslist"] = _definition(query, **fields)

    _refused(collect, ANALYST, "Windows.System.Pslist")


def test_a_command_artifact_with_no_declared_permissions_is_refused_even_if_allowlisted(collect, monkeypatch):
    monkeypatch.setitem(collection_policy.ANALYST_ARTIFACTS, "Custom.Windows.Undeclared", frozenset({"Command"}))
    collect.definitions["Custom.Windows.Undeclared"] = _definition(
        "SELECT * FROM execve(argv=['cmd.exe', '/c', Command])",
        [{"name": "Command"}],
    )

    assert "execve" in _refused(collect, ANALYST, "Custom.Windows.Undeclared", {"env": [{"key": "Command", "value": "whoami"}]})


def test_a_really_do_it_toggle_cannot_be_flipped(collect, monkeypatch):
    monkeypatch.setitem(collection_policy.ANALYST_ARTIFACTS, "Custom.Windows.Lister", frozenset({"NameRegex"}))
    collect.definitions["Custom.Windows.Lister"] = _definition(
        "SELECT * FROM pslist() WHERE Name =~ NameRegex",
        [{"name": "NameRegex", "default": "."}, {"name": "ReallyDoIt", "default": "N", "type": "bool"}],
    )

    assert "ReallyDoIt" in _refused(collect, ANALYST, "Custom.Windows.Lister", {"env": [{"key": "ReallyDoIt", "value": "Y"}]})
    # Sent back unchanged, as the frontend sends every default, it is not a choice.
    assert collect(
        ANALYST,
        "Custom.Windows.Lister",
        {"env": [{"key": "ReallyDoIt", "value": "N"}, {"key": "NameRegex", "value": "svchost"}]},
    )


def test_a_tool_path_parameter_cannot_be_changed(collect, monkeypatch):
    monkeypatch.setitem(collection_policy.ANALYST_ARTIFACTS, "Custom.Windows.Lister", frozenset())
    collect.definitions["Custom.Windows.Lister"] = _definition(
        "SELECT * FROM pslist()",
        [{"name": "ToolPath", "default": "C:\\Tools\\lister.exe"}],
    )

    assert "ToolPath" in _refused(collect, ANALYST, "Custom.Windows.Lister", {"env": [{"key": "ToolPath", "value": "C:\\\\evil.exe"}]})
    # The frontend doubles the default's backslashes for the old VQL literal; that is still the default.
    assert collect(ANALYST, "Custom.Windows.Lister", {"env": [{"key": "ToolPath", "value": "C:\\\\Tools\\\\lister.exe"}]})


def test_unlisted_parameters_are_refused_for_allowlisted_artifacts(collect):
    assert "Unknown" in _refused(collect, ANALYST, "Windows.System.Pslist", {"Unknown": "x"})


def test_the_definition_is_read_in_the_hosts_org_and_refused_when_missing_there(collect):
    collect(ANALYST, "Windows.System.Pslist")
    assert collect.calls["definition_lookups"] == [("Windows.System.Pslist", HOST_ORG)]

    collect.calls["collections"].clear()
    collect.definitions["Windows.System.Pslist"] = None  # on the host's list, but not defined in its org
    assert "not found" in _refused(collect, ANALYST, "Windows.System.Pslist")


# --- only Velociraptor's built-in definitions, artifact and dependencies ----------------


def test_a_child_org_definition_of_a_built_in_name_is_refused(collect):
    """A child org can shadow a built-in name with its own YAML; that definition is not compiled in."""
    collect.definitions["Windows.System.Pslist"] = _definition("SELECT * FROM pslist()", compiled_in=False)

    assert "built-in definition" in _refused(collect, ANALYST, "Windows.System.Pslist")
    assert collect.calls["definition_lookups"] == [("Windows.System.Pslist", HOST_ORG)]


@pytest.mark.parametrize("flag", [None, "true", 1], ids=["missing", "string", "int"])
def test_only_a_literal_true_compiled_in_counts_as_built_in(collect, flag):
    definition = _definition()
    definition.pop("compiled_in")
    if flag is not None:
        definition["compiled_in"] = flag
    collect.definitions["Windows.System.Pslist"] = definition

    assert "built-in definition" in _refused(collect, ANALYST, "Windows.System.Pslist")


def test_a_dependency_that_resolves_to_a_non_built_in_definition_is_refused(collect):
    """The allowlisted artifact is built in, but the artifact it calls is the org's own copy."""
    collect.definitions["Windows.System.Pslist"] = _definition("SELECT * FROM Artifact.Windows.Sys.Programs()")
    collect.definitions["Windows.Sys.Programs"] = _definition("SELECT * FROM pslist()", compiled_in=False)
    collect.dependencies["Windows.System.Pslist"] = ["Windows.Sys.Programs"]

    detail = _refused(collect, ANALYST, "Windows.System.Pslist")
    assert "dependency Windows.Sys.Programs" in detail and "built-in definition" in detail


def test_a_dependency_off_the_allowlist_is_refused(collect):
    collect.definitions["Windows.System.Pslist"] = _definition("SELECT * FROM pslist()")
    collect.dependencies["Windows.System.Pslist"] = ["Windows.KapeFiles.Targets"]
    collect.definitions["Windows.KapeFiles.Targets"] = _definition("SELECT * FROM glob(globs='*')")

    detail = _refused(collect, ANALYST, "Windows.System.Pslist")
    assert "dependency Windows.KapeFiles.Targets" in detail and "allowlist" in detail


def test_a_dependency_is_scanned_like_the_artifact(collect):
    collect.definitions["Windows.System.Pslist"] = _definition("SELECT * FROM Artifact.Windows.Sys.Programs()")
    collect.definitions["Windows.Sys.Programs"] = _definition('SELECT * FROM execve(argv=["true"])')
    collect.dependencies["Windows.System.Pslist"] = ["Windows.Sys.Programs"]

    detail = _refused(collect, ANALYST, "Windows.System.Pslist")
    assert "dependency Windows.Sys.Programs" in detail and "execve" in detail


def test_built_in_allowlisted_dependencies_are_collected(collect):
    collect.definitions["Windows.System.Pslist"] = _definition("SELECT * FROM Artifact.Windows.Sys.Programs()")
    collect.dependencies["Windows.System.Pslist"] = ["Windows.Sys.Programs"]

    assert collect(ANALYST, "Windows.System.Pslist").success is True
    assert collect.calls["collections"] == ["Windows.System.Pslist"]


# Inert VQL strings fed to the filter: obfuscated spellings vfilter would still parse as a call.
@pytest.mark.parametrize(
    "query, reported",
    [
        ('SELECT * FROM `execve`(argv=["true"])', "execve"),
        ('SELECT * FROM execve/* */(argv=["true"])', "execve"),
        ('SELECT * FROM execve /* note */ (argv=["true"])', "execve"),
        ("SELECT * FROM `Artifact.Custom.Example-Helper`()", "Artifact.Custom.Example-Helper"),
        ("SELECT * FROM `Artifact.Windows.KapeFiles.Targets`()", "Artifact.Windows.KapeFiles.Targets"),
    ],
    ids=["backtick-name", "comment-before-paren", "spaced-comment", "backtick-hyphenated-artifact", "backtick-artifact"],
)
def test_obfuscated_forbidden_calls_are_seen_by_the_normalised_scan(collect, query, reported):
    """The definition claims to be built in, so only the text scan (defence in depth) stands in the way."""
    collect.definitions["Windows.System.Pslist"] = _definition(query)

    assert reported in _refused(collect, ANALYST, "Windows.System.Pslist")


def test_the_normalised_scan_does_not_flag_names_inside_comments_alone():
    """A forbidden name in a comment, with no call, is not a call; a real call still is."""
    assert collection_policy.read_only_violation(_definition("-- execve is not used here\nSELECT * FROM pslist()")) is None
    assert collection_policy.read_only_violation(_definition("/* see `execve` */ SELECT * FROM pslist()")) is None
    assert "execve" in collection_policy.read_only_violation(_definition("/* x */ SELECT * FROM execve(argv=['true'])"))


def test_a_configured_custom_quarantine_artifact_is_refused(collect, monkeypatch):
    monkeypatch.setenv("VELOCIRAPTOR_WINDOWS_QUARANTINE_ARTIFACT", "Custom.Windows.Isolate")
    monkeypatch.setitem(collection_policy.ANALYST_ARTIFACTS, "Custom.Windows.Isolate", frozenset())
    collect.definitions["Custom.Windows.Isolate"] = _definition()

    assert "remediation" in _refused(collect, ANALYST, "Custom.Windows.Isolate")


# --- what still works ------------------------------------------------------------------


@pytest.mark.parametrize(
    "artifact, parameters",
    [
        ("Windows.Sys.Programs", None),
        ("Windows.System.Pslist", {"env": [{"key": "ProcessRegex", "value": "svchost"}, {"key": "PidRegex", "value": "."}]}),
        ("Windows.Network.Netstat", None),
        ("Windows.Forensics.Prefetch", {"env": [{"key": "dateAfter", "value": "2026-10-01"}]}),
        ("Linux.Sys.Pslist", {"processRegex": "sshd"}),
        ("MacOS.System.QuarantineEvents", None),  # "Quarantine" in a triage name is not remediation
    ],
)
def test_analyst_can_still_collect_triage_artifacts(collect, artifact, parameters):
    response = collect(ANALYST, artifact, parameters=parameters)

    assert response.success is True
    assert collect.calls["collections"] == [artifact]


@pytest.mark.parametrize("user", [ADMIN, RESPONDER], ids=["admin", "responder"])
@pytest.mark.parametrize(
    "artifact",
    [
        "Windows.System.PowerShell",
        "Linux.Sys.BashShell",
        "Windows.Remediation.Quarantine",
        "Windows.KapeFiles.Targets",
        "Windows.Sys.Programs",
    ],
)
def test_admin_and_responder_keep_todays_behaviour(collect, user, artifact):
    response = collect(user, artifact, parameters={"env": [{"key": "Command", "value": "id"}]})

    assert response.success is True
    assert collect.calls["collections"] == [artifact]
    assert collect.calls["definition_lookups"] == []


@pytest.mark.parametrize("user", [ADMIN, RESPONDER], ids=["admin", "responder"])
def test_admin_and_responder_are_not_held_to_built_in_definitions(collect, user):
    """Custom, child-org and capable definitions, with any dependency, still run for them."""
    collect.definitions["Windows.System.Pslist"] = _definition('SELECT * FROM `execve`(argv=["true"])', compiled_in=False)
    collect.dependencies["Windows.System.Pslist"] = ["Windows.KapeFiles.Targets"]

    assert collect(user, "Windows.System.Pslist", parameters={"env": [{"key": "Anything", "value": "x"}]}).success is True
    assert collect.calls["collections"] == ["Windows.System.Pslist"]
    assert collect.calls["definition_lookups"] == []


# --- one host record per request -------------------------------------------------------


def _shared(collect, other_customer="00002"):
    """HOST-1 is enrolled for two customers, each with its own Velociraptor client and org."""
    collect.agents[:] = [_agent(), _agent(customer_code=other_customer, velociraptor_id="C.1111111111111111", velociraptor_org="O9999ZZZZ")]


ROUTES = {
    "collect": lambda collect, user: collect(user, "Windows.System.Pslist"),
    "command": lambda collect, user: collect.command(user),
    "quarantine": lambda collect, user: collect.quarantine(user),
}


def _nothing_ran(collect):
    assert collect.calls["collections"] == [] and collect.calls["commands"] == [] and collect.calls["quarantines"] == []
    assert collect.calls["definition_lookups"] == []


@pytest.mark.parametrize("route", ROUTES)
def test_a_hostname_shared_by_two_customers_is_a_409(collect, route):
    _shared(collect)
    with pytest.raises(HTTPException) as exc:
        ROUTES[route](collect, ADMIN)
    assert exc.value.status_code == 409
    _nothing_ran(collect)


@pytest.mark.parametrize("route", ROUTES)
def test_a_shared_hostname_is_a_403_when_the_caller_lacks_one_of_its_customers(collect, route):
    _shared(collect)
    collect.accessible[:] = [HOST_CUSTOMER]
    user = ANALYST if route == "collect" else RESPONDER
    with pytest.raises(HTTPException) as exc:
        ROUTES[route](collect, user)
    assert exc.value.status_code == 403
    _nothing_ran(collect)


def test_two_rows_that_agree_on_client_org_and_customer_are_one_host(collect):
    collect.agents[:] = [_agent(), _agent()]

    assert collect(ANALYST, "Windows.System.Pslist").success is True
    assert collect.calls["targets"] == [(HOST_CLIENT, HOST_ORG)]


def test_rows_that_differ_only_in_org_are_a_409(collect):
    collect.agents[:] = [_agent(), _agent(velociraptor_org="O9999ZZZZ")]
    with pytest.raises(HTTPException) as exc:
        collect(ADMIN, "Windows.System.Pslist")
    assert exc.value.status_code == 409


@pytest.mark.parametrize("route, recorded", [("collect", "targets"), ("command", "commands"), ("quarantine", "quarantines")])
def test_a_single_row_supplies_the_client_id_and_org(collect, route, recorded):
    collect.agents[:] = [_agent(velociraptor_id="C.2222222222222222", velociraptor_org="O5555EEEE")]
    collect.definitions["Windows.System.Pslist"] = _definition()
    collect.accessible[:] = [HOST_CUSTOMER]
    user = ANALYST if route == "collect" else RESPONDER

    assert ROUTES[route](collect, user).success is True
    assert collect.calls[recorded] == [("C.2222222222222222", "O5555EEEE")]
    if route == "collect":
        # The policy reads the definition in that row's org.
        assert collect.calls["definition_lookups"] == [("Windows.System.Pslist", "O5555EEEE")]


def test_a_single_row_of_another_customer_is_a_403(collect):
    collect.accessible[:] = ["00002"]
    with pytest.raises(HTTPException) as exc:
        collect(ANALYST, "Windows.System.Pslist")
    assert exc.value.status_code == 403
    _nothing_ran(collect)


def test_an_unknown_hostname_is_a_404(collect):
    collect.agents[:] = []
    with pytest.raises(HTTPException) as exc:
        collect(ADMIN, "Windows.System.Pslist")
    assert exc.value.status_code == 404


@pytest.mark.parametrize("velociraptor_id, velociraptor_org", [(None, HOST_ORG), ("n/a", HOST_ORG), (HOST_CLIENT, None)])
def test_a_row_without_a_velociraptor_client_or_org_is_a_404(collect, velociraptor_id, velociraptor_org):
    collect.agents[:] = [_agent(velociraptor_id=velociraptor_id, velociraptor_org=velociraptor_org)]
    with pytest.raises(HTTPException) as exc:
        collect(ADMIN, "Windows.System.Pslist")
    assert exc.value.status_code == 404


# --- the lists themselves --------------------------------------------------------------


@pytest.mark.parametrize("member", list(CommandArtifactsEnum) + list(QuarantineArtifactsEnum), ids=lambda m: m.value)
def test_command_and_quarantine_artifacts_are_never_analyst_collectable(member):
    assert member.value not in collection_policy.ANALYST_ARTIFACTS
    assert member.value in collection_policy.response_artifacts()


def test_the_allowlist_holds_no_response_artifact():
    allowlisted = set(collection_policy.ANALYST_ARTIFACTS)
    assert not allowlisted & collection_policy.RESPONSE_ARTIFACTS
    # (PowerShell *history* readers such as Windows.System.Powershell.PSReadline are triage.)
    response_names = re.compile(r"(?i)(^|\.)(remediation|execute|response)(\.|$)|kill|uninstall|cmdshell|bashshell|vbscript")
    assert [name for name in allowlisted if response_names.search(name)] == []


@pytest.mark.parametrize(
    "artifact",
    [
        "Windows.System.WMIQuery",
        "Windows.System.LocalAdmins",
        "Windows.Sigma.EventLogs",
        "Windows.OSQuery.Generic",
        "Linux.OSQuery.Generic",
        "MacOS.OSQuery.Generic",
        "Windows.Network.NetstatEnriched",
        "Windows.Carving.Evtx",
        "Windows.Network.PacketCapture",
        "Linux.Network.PacketCapture",
        "Generic.Client.VQL",
    ],
)
def test_artifacts_kept_to_admins_and_responders_are_off_the_allowlist(artifact):
    assert artifact not in collection_policy.ANALYST_ARTIFACTS


def test_no_safe_parameter_looks_like_a_command_tool_or_toggle():
    unsafe = re.compile(
        r"(?i)(exe|path|binary|url|tool|command|cmd|script|reallydoit|delete|kill|upload|dump|remove|install|accessor|vql|query|output)",
    )
    offenders = {name: sorted(p for p in params if unsafe.search(p)) for name, params in collection_policy.ANALYST_ARTIFACTS.items()}
    assert {name: params for name, params in offenders.items() if params} == {}


def test_unknown_roles_are_not_response_roles():
    assert collection_policy.is_response_role(SimpleNamespace(role_id=RoleEnum.analyst.value)) is False
    assert collection_policy.is_response_role(SimpleNamespace(role_id=RoleEnum.customer_user.value)) is False
    assert collection_policy.is_response_role(SimpleNamespace(role_id=999)) is False
    assert collection_policy.is_response_role(SimpleNamespace()) is False
