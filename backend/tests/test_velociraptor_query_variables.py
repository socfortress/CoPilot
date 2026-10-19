"""Values reach Velociraptor as query variables, never as VQL text.

`/artifacts/command`, `/artifacts/collect`, `/artifacts/collect/file`, quarantine, flows,
agent lookups and the file-analysis fetcher all used to paste request (or endpoint-reported)
values into VQL between quotes. A quote, a trailing backslash or a backtick in one of them
closed the literal and the rest ran as server-side VQL. Every value now travels in
`VQLCollectorArgs.env` and the query text is a constant template that references it by name;
artifact parameter *names* (literal `dict()` keys) are only accepted when the artifact
declares them.

These tests drive the real services and the real `UniversalService` against a recording gRPC
stub, so they see exactly the `VQLCollectorArgs` that would go to the server: the VQL text and
the env entries. No DB or Velociraptor server.

Run with: cd backend && python -m pytest tests/test_velociraptor_query_variables.py
"""

import asyncio
import base64
import json
import os
import tempfile
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")
os.environ.setdefault("MYSQL_PASSWORD", "test-only-password-not-the-default")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "test-only-password-not-the-default")

import app.agents.velociraptor.services.agents as agents_service  # noqa: E402
import app.connectors.velociraptor.services.artifacts as artifacts  # noqa: E402
import app.connectors.velociraptor.services.flows as flows_service  # noqa: E402
import app.connectors.velociraptor.utils.universal as universal  # noqa: E402
import app.file_analysis.services.velociraptor_fetch as velociraptor_fetch  # noqa: E402
from app.connectors.velociraptor.routes.artifacts import (  # noqa: E402
    format_file_path_for_os,
)
from app.connectors.velociraptor.schema.artifacts import ArtifactParameter  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import Artifacts  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import ArtifactsResponse  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    CollectArtifactBody,
)
from app.connectors.velociraptor.schema.artifacts import CollectFileBody  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import QuarantineBody  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import RunCommandBody  # noqa: E402
from app.connectors.velociraptor.schema.flows import RetrieveFlowRequest  # noqa: E402
from app.connectors.velociraptor.utils.validation import (  # noqa: E402
    validate_artifact_parameter_name,
)
from app.connectors.velociraptor.utils.validation import (  # noqa: E402
    vql_string_literal_value,
)

ORG = "O1234ABCD"
CLIENT = "C.475df76785008b04"
FLOW = "F.CQMNTHE1CSPKC"

# Values that broke out of the old string literals, or would break any naive escaping.
PAYLOADS = [
    "'",
    "\\",
    "trailing backslash \\",
    "')) FROM scope() UNION SELECT collect_client(org_id='root', client_id='C.1111111111111111', artifacts=['Linux.Sys.BashShell'], env=dict(Command='id')) FROM scope() --",
    "x\\', env=dict()) AS Flow, execve(argv=['id']) AS Pwn FROM scope() //",
    "line one\nSELECT * FROM info()\n",
    "`whoami`",
    "\"double\" and 'single'",
    "{ SELECT * FROM info() }",
    "''' multiline '''",
    "\\x27 hex quote",
]


class _RecordingStub:
    """A pyvelociraptor `APIStub` stand-in: records each request, answers by query shape."""

    def __init__(self, hostname="WIN-HOST"):
        self.requests = []
        self.hostname = hostname
        self.file_bytes = b""

    def Query(self, request, timeout=None):  # noqa: N802 - gRPC method name
        self.requests.append(request)
        vql = request.Query[0].VQL
        if "collect_client(" in vql or "create_flow_download(" in vql:
            rows = [{"Flow": {"flow_id": FLOW}}]
        elif "watch_monitoring(" in vql:
            rows = [{"FlowId": FLOW}]
        elif "artifact_definitions(" in vql:
            rows = []
        elif "os_info.hostname" in vql:
            rows = [{"Hostname": self.hostname}]
        elif "last_seen_at" in vql:
            rows = [{"last_seen_at": 1, "client_id": CLIENT}]
        elif "read_file(" in vql:
            rows = [{"Data": base64.b64encode(self.file_bytes).decode()}] if self.file_bytes and "offset=0," in vql else []
        else:
            rows = [{"Stdout": "ok", "client_id": CLIENT}]
        return [SimpleNamespace(Response=json.dumps(rows), log="")]

    def calls(self):
        """(vql, env, org_id) for every request, in order."""
        return [(r.Query[0].VQL, {e.key: e.value for e in r.env}, r.org_id) for r in self.requests]

    def call_with(self, fragment):
        matches = [call for call in self.calls() if fragment in call[0]]
        assert len(matches) == 1, f"expected one query containing {fragment!r}, got {self.calls()}"
        return matches[0]


@pytest.fixture
def stub(monkeypatch):
    stub = _RecordingStub()
    service = universal.UniversalService()
    service.stub = stub

    async def fake_create(cls, connector_name):
        return service

    # Patch the class each service module holds: another test reloads `universal`, after
    # which its UniversalService is a different class object from the services' one.
    for module in (universal, artifacts, flows_service, agents_service, velociraptor_fetch):
        monkeypatch.setattr(module.UniversalService, "create", classmethod(fake_create))
    return stub


def _assert_not_in_query(vql, value):
    """No distinctive piece of the value may appear in the query text."""
    for piece in ("execve", "UNION", "whoami", "info()", "multiline", "hex quote", "trailing", "double"):
        if piece in value:
            assert piece not in vql, f"{piece!r} leaked into the query: {vql}"


# --- the client: env becomes VQLEnv entries ------------------------------------------


def test_create_vql_request_carries_env_entries():
    request = universal.UniversalService().create_vql_request("SELECT X FROM scope()", "root", {"X": "it's \\ `raw`"})

    assert request.Query[0].VQL == "SELECT X FROM scope()"
    assert [(e.key, e.value) for e in request.env] == [("X", "it's \\ `raw`")]
    assert request.org_id == "root"


def test_create_vql_request_without_env_is_unchanged():
    request = universal.UniversalService().create_vql_request("SELECT * FROM info()")

    assert list(request.env) == []
    assert request.max_wait == 1


@pytest.mark.parametrize("name", ["", "1Abc", "Has Space", "back`tick", "Dot.Name", "SELECT", "from", "As", "x'"])
def test_env_names_must_be_plain_non_keyword_identifiers(name):
    with pytest.raises(ValueError):
        universal.build_vql_env({name: "v"})


def test_env_values_must_be_strings():
    with pytest.raises(TypeError):
        universal.build_vql_env({"Count": 3})


def test_execute_query_async_forwards_env(stub):
    service = universal.UniversalService()
    service.stub = stub

    asyncio.run(service.execute_query_async("SELECT Foo FROM scope()", org_id=ORG, env={"Foo": "bar"}))

    assert stub.calls() == [("SELECT Foo FROM scope()", {"Foo": "bar"}, ORG)]


# --- POST /artifacts/command ----------------------------------------------------------


def _run_command(command):
    body = RunCommandBody(
        hostname="WIN-HOST",
        velociraptor_id=CLIENT,
        velociraptor_org=ORG,
        artifact_name="Windows.System.PowerShell",
        command=command,
    )
    return asyncio.run(artifacts.run_remote_command(body))


@pytest.mark.parametrize("command", PAYLOADS)
def test_command_never_enters_the_query(stub, command):
    _run_command(command)

    vql, env, org_id = stub.call_with("collect_client(")
    assert vql == artifacts.VQL_RUN_COMMAND
    assert env == {
        "OrgId": ORG,
        "ClientId": CLIENT,
        "ArtifactName": "Windows.System.PowerShell",
        "Command": vql_string_literal_value(command),
    }
    assert org_id == ORG
    _assert_not_in_query(vql, command)


def test_command_query_is_identical_for_every_payload(stub):
    for command in PAYLOADS + ["Get-Process"]:
        _run_command(command)

    collect_queries = {vql for vql, _, _ in stub.calls() if "collect_client(" in vql}
    assert collect_queries == {artifacts.VQL_RUN_COMMAND}


def test_normal_command_keeps_the_call_shape(stub):
    response = _run_command("Get-ChildItem C:\\\\Users | Select-Object Name")

    assert response.success is True
    assert response.results == [{"Stdout": "ok", "client_id": CLIENT}]
    calls = stub.calls()
    assert [vql for vql, _, _ in calls] == [
        "SELECT collect_client(org_id=OrgId, client_id=ClientId, urgent=true, artifacts=[ArtifactName], "
        "env=dict(Command=Command)) AS Flow FROM scope()",
        "SELECT * FROM watch_monitoring(artifact='System.Flow.Completion') WHERE FlowId = TargetFlowId LIMIT 1",
        "SELECT * FROM source(client_id=ClientId, flow_id=FlowId, artifact=ArtifactName)",
    ]
    # The command means what it did as a VQL literal: the doubled backslash is one backslash.
    assert calls[0][1]["Command"] == "Get-ChildItem C:\\Users | Select-Object Name"
    assert calls[1][1] == {"TargetFlowId": FLOW}
    assert calls[2][1] == {"ClientId": CLIENT, "FlowId": FLOW, "ArtifactName": "Windows.System.PowerShell"}
    assert {org for _, _, org in calls} == {ORG}


def test_command_identifiers_are_still_validated(stub):
    body = RunCommandBody(
        hostname="WIN-HOST",
        velociraptor_id="C.475df76785008b04'",
        velociraptor_org=ORG,
        artifact_name="Windows.System.PowerShell",
        command="whoami",
    )
    with pytest.raises(HTTPException):
        asyncio.run(artifacts.run_remote_command(body))
    assert stub.requests == []


# --- POST /artifacts/collect ----------------------------------------------------------

ATOMIC = "Windows.AttackSimulation.AtomicRedTeam"
ATOMIC_PARAMETERS = ["InstallART", "T1552.001 - 3", "Sidebar gadgets (Vista and higher)"]


class _FakeSession:
    def __init__(self):
        self.agent = SimpleNamespace(agent_id="001")

    async def execute(self, statement):
        agent = self.agent
        return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: agent))

    def add(self, obj):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


@pytest.fixture
def collect(stub, monkeypatch):
    """Run run_artifact_collection with a fixed artifact definition; return the stub."""
    declared = {"names": ATOMIC_PARAMETERS, "orgs": []}

    async def fake_get_artifact_by_name(artifact_name, org_id="root"):
        declared["orgs"].append(org_id)
        parameters = [ArtifactParameter(name=name) for name in declared["names"]]
        artifact = Artifacts(name=artifact_name, description="", parameters=parameters)
        return ArtifactsResponse(success=True, message="ok", artifacts=[artifact])

    async def fake_fetch_file_from_filestore(**kwargs):
        return {"success": False}

    monkeypatch.setattr(artifacts, "get_artifact_by_name", fake_get_artifact_by_name)
    monkeypatch.setattr(artifacts, "fetch_file_from_filestore", fake_fetch_file_from_filestore)

    def run(parameters, artifact_name=ATOMIC):
        body = CollectArtifactBody(
            hostname="WIN-HOST",
            velociraptor_id=CLIENT,
            velociraptor_org=ORG,
            artifact_name=artifact_name,
            parameters=parameters,
        )
        return asyncio.run(artifacts.run_artifact_collection(body, _FakeSession()))

    run.stub = stub
    run.declared = declared
    return run


@pytest.mark.parametrize("value", PAYLOADS)
def test_collect_parameter_values_never_enter_the_query(collect, value):
    collect({"env": [{"key": "InstallART", "value": value}, {"key": "T1552.001 - 3", "value": "Y"}]})

    vql, env, org_id = collect.stub.call_with("collect_client(")
    assert vql == (
        "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName], "
        "env=dict(`InstallART`=Param0, `T1552.001 - 3`=Param1)) AS Flow FROM scope()"
    )
    assert env == {
        "OrgId": ORG,
        "ClientId": CLIENT,
        "ArtifactName": ATOMIC,
        "Param0": vql_string_literal_value(value),
        "Param1": "Y",
    }
    assert org_id == ORG
    _assert_not_in_query(vql, value)


def test_collect_query_is_identical_for_every_value(collect):
    for value in PAYLOADS + ["N"]:
        collect({"env": [{"key": "InstallART", "value": value}]})

    collect_queries = {vql for vql, _, _ in collect.stub.calls() if "collect_client(" in vql}
    assert collect_queries == {
        "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName], env=dict(`InstallART`=Param0)) AS Flow FROM scope()",
    }


@pytest.mark.parametrize("value", PAYLOADS)
def test_collect_plain_dict_values_never_enter_the_query(collect, value):
    collect({"InstallART": value})

    vql, env, _ = collect.stub.call_with("collect_client(")
    assert (
        vql
        == "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName], env=dict(`InstallART`=Param0)) AS Flow FROM scope()"
    )
    assert env["Param0"] == vql_string_literal_value(value)
    _assert_not_in_query(vql, value)


@pytest.mark.parametrize(
    "name",
    [
        "NotAParameter",
        "InstallART`=Param0) AS Flow, execve(argv=['id']) AS Pwn FROM scope() --",
        "InstallART`",
        "installart",  # names are matched exactly, as Velociraptor matches them
        "org_id",
        "urgent",
    ],
)
def test_collect_unknown_or_malicious_parameter_name_is_refused(collect, name):
    with pytest.raises(HTTPException) as exc:
        collect({"env": [{"key": name, "value": "Y"}]})

    assert exc.value.status_code == 400
    assert not any("collect_client(" in vql for vql, _, _ in collect.stub.calls())


@pytest.mark.parametrize(
    "name",
    ["Bad`Name", "Bad'Name", 'Bad"Name', "Bad\\Name", "Bad\nName", "Bad\rName", "Bad\x00Name", "", " Leading", "x" * 300],
)
def test_collect_declared_but_unsafe_parameter_name_is_refused(collect, name):
    """Second line of defence: even a name the artifact declares must pass the format check."""
    collect.declared["names"] = [name]

    with pytest.raises(HTTPException) as exc:
        collect({"env": [{"key": name, "value": "Y"}]})

    assert exc.value.status_code == 400
    assert not any("collect_client(" in vql for vql, _, _ in collect.stub.calls())


def test_collect_without_parameters_keeps_the_call_shape(collect):
    response = collect(None)

    assert response.success is True
    vql, env, _ = collect.stub.call_with("collect_client(")
    assert vql == "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName]) AS Flow FROM scope()"
    assert env == {"OrgId": ORG, "ClientId": CLIENT, "ArtifactName": ATOMIC}
    # No parameters asked for, so the artifact definition is not needed.
    assert not any("artifact_definitions()" in vql for vql, _, _ in collect.stub.calls())


def test_collect_with_an_empty_env_list_still_passes_env(collect):
    collect({"env": []})

    vql, env, _ = collect.stub.call_with("collect_client(")
    assert vql == "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName], env=dict()) AS Flow FROM scope()"
    assert env == {"OrgId": ORG, "ClientId": CLIENT, "ArtifactName": ATOMIC}


def test_collect_frontend_windows_path_reaches_the_artifact_unchanged(collect):
    """The frontend doubles a Windows path's backslashes for the old literal; the artifact
    must still receive single backslashes."""
    collect({"env": [{"key": "InstallART", "value": "C:\\\\Users\\\\Public\\\\*.exe"}]})

    _, env, _ = collect.stub.call_with("collect_client(")
    assert env["Param0"] == "C:\\Users\\Public\\*.exe"


def test_collect_identifiers_are_still_validated(collect):
    with pytest.raises(HTTPException) as exc:
        collect(None, artifact_name="Windows.Foo'])")
    assert exc.value.status_code == 400
    assert collect.stub.requests == []


# --- POST /artifacts/collect/file ------------------------------------------------------


@pytest.fixture
def collect_file(stub, monkeypatch):
    async def fake_fetch_file_from_filestore(**kwargs):
        return {"success": False}

    monkeypatch.setattr(artifacts, "fetch_file_from_filestore", fake_fetch_file_from_filestore)

    def run(file, root_disk="C:"):
        body = CollectFileBody(
            hostname="WIN-HOST",
            velociraptor_id=CLIENT,
            velociraptor_org=ORG,
            artifact_name="Generic.Collectors.File",
            file=file,
            root_disk=root_disk,
        )
        return asyncio.run(artifacts.run_file_collection(body, _FakeSession()))

    run.stub = stub
    return run


@pytest.mark.parametrize("value", PAYLOADS)
def test_file_glob_and_root_never_enter_the_query(collect_file, value):
    collect_file(value, root_disk=value)

    vql, env, org_id = collect_file.stub.call_with("collect_client(")
    assert vql == artifacts.VQL_COLLECT_FILE
    assert env == {
        "OrgId": ORG,
        "ClientId": CLIENT,
        "ArtifactName": "Generic.Collectors.File",
        "CollectionSpec": vql_string_literal_value(value),
        "Root": vql_string_literal_value(value),
    }
    assert org_id == ORG
    _assert_not_in_query(vql, value)


def test_file_collection_path_from_the_agent_route_is_unchanged(collect_file):
    """format_file_path_for_os escapes Windows backslashes for the old literal."""
    collect_file(format_file_path_for_os("Users\\Administrator\\Downloads\\LICENSE.txt", "Windows"))

    _, env, _ = collect_file.stub.call_with("collect_client(")
    assert env["CollectionSpec"] == "Glob\nUsers\\Administrator\\Downloads\\LICENSE.txt\n"
    assert env["Root"] == "C:"


# --- quarantine -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "action, expected",
    [("quarantine", artifacts.VQL_QUARANTINE), ("remove_quarantine", artifacts.VQL_REMOVE_QUARANTINE)],
)
def test_quarantine_queries_are_constant(stub, action, expected):
    body = QuarantineBody(
        hostname="WIN-HOST",
        velociraptor_id=CLIENT,
        velociraptor_org=ORG,
        artifact_name="Windows.Remediation.Quarantine",
        action=action,
    )
    response = asyncio.run(artifacts.quarantine_host(body))

    assert response.success is True
    vql, env, org_id = stub.call_with("collect_client(")
    assert vql == expected
    assert env == {"OrgId": ORG, "ClientId": CLIENT, "ArtifactName": "Windows.Remediation.Quarantine"}
    assert org_id == ORG
    assert CLIENT not in vql and ORG not in vql


# --- the other VQL sites --------------------------------------------------------------


def test_artifact_lookup_by_name_uses_a_variable(stub):
    asyncio.run(artifacts.get_artifact_by_name(ATOMIC))

    vql, env, _ = stub.call_with("artifact_definitions()")
    assert vql == "SELECT name,description,parameters FROM artifact_definitions() WHERE name = ArtifactName"
    assert env == {"ArtifactName": ATOMIC}


def test_flow_listing_and_results_use_variables(stub):
    asyncio.run(flows_service.get_flows(CLIENT, ORG))
    asyncio.run(flows_service.get_flow(RetrieveFlowRequest(client_id=CLIENT, session_id=FLOW), ORG))

    assert stub.calls() == [
        ("SELECT * FROM flows(client_id=ClientId)", {"ClientId": CLIENT}, ORG),
        ("SELECT * FROM flow_results(client_id=ClientId, flow_id=FlowId)", {"ClientId": CLIENT, "FlowId": FLOW}, ORG),
    ]


def test_client_lookups_use_variables(stub):
    service = universal.UniversalService()
    service.stub = stub
    asyncio.run(service.get_client_id("WIN-HOST"))
    asyncio.run(service.get_client_id_via_client_id("C.1' OR 1=1"))

    for vql, env, _ in stub.calls():
        assert vql in (universal.VQL_CLIENT_ID_BY_SEARCH, universal.VQL_CLIENT_LAST_SEEN_BY_SEARCH)
        assert env["Search"] in ("host:WIN-HOST", "client_id:C.1' OR 1=1")


def test_agent_name_is_a_variable_even_when_lookup_rejects_it(stub):
    """collect_velociraptor_agent falls through to its own queries when get_client_id refuses
    the name; those used to interpolate it unvalidated."""
    name = "host') FROM scope() SELECT execve(argv=['id']) FROM scope() --"
    try:
        asyncio.run(agents_service.collect_velociraptor_agent(name))
    except ValueError:
        # Building the VelociraptorAgent at the end fails on its own (it omits the required
        # client_org); only the queries sent before that matter here.
        pass

    assert stub.requests, "the fall-through queries should still run"
    for vql, env, _ in stub.calls():
        assert "execve" not in vql
        assert env == {"Search": f"host:{name}"}


def test_org_client_listing_and_client_deletion_use_variables(stub):
    asyncio.run(agents_service.collect_velociraptor_clients(ORG))
    asyncio.run(agents_service.delete_client(CLIENT))

    assert stub.calls() == [
        ("SELECT * FROM query(org_id=OrgId, query='SELECT * FROM clients()')", {"OrgId": ORG}, "root"),
        (
            "SELECT collect_client(client_id='server', artifacts=['Server.Utils.DeleteClient'], "
            "env=dict(ClientIdList=ClientIdList, ReallyDoIt='Y')) FROM scope()",
            {"ClientIdList": CLIENT},
            "root",
        ),
    ]


def test_filestore_download_uses_variables_for_the_endpoint_reported_hostname(stub, monkeypatch, tmp_path):
    """The hostname comes from the endpoint itself, so it is attacker-controlled too."""
    monkeypatch.chdir(tmp_path)
    stub.hostname = "evil'), x=execve(argv=['id'])) FROM scope() --"

    result = asyncio.run(artifacts.fetch_file_from_filestore(client_id=CLIENT, flow_id=FLOW, org_id=ORG, agent_id="001"))

    assert result["success"] is False  # the stub serves no file bytes
    for vql, _, _ in stub.calls():
        assert "execve" not in vql and CLIENT not in vql and FLOW not in vql
    vql, env, _ = stub.call_with("create_flow_download(")
    assert vql == (
        "SELECT create_flow_download(client_id=ClientId, flow_id=FlowId, wait=true, format=Format, "
        "expand_sparse=false, name=DownloadName) FROM scope()"
    )
    safe_host = artifacts.safe_file_component(stub.hostname)
    assert env == {"ClientId": CLIENT, "FlowId": FLOW, "Format": "json", "DownloadName": f"{safe_host}-{CLIENT}-{FLOW}"}
    _, read_env, _ = stub.call_with("read_file(")
    assert read_env == {"VfsPath": f"/downloads/{CLIENT}/{FLOW}/{safe_host}-{CLIENT}-{FLOW}.zip"}
    assert list(tmp_path.iterdir()) == []  # nothing written to the working directory


@pytest.mark.parametrize(
    "hostname",
    ["../../../../etc/cron.d/evil", "..", "/abs/path", "a/../../b", "..\\..\\windows", "host\x00name", "....", ".hidden"],
)
def test_filestore_download_keeps_a_hostile_hostname_inside_its_temp_dir(stub, monkeypatch, tmp_path, hostname):
    """A hostname reported by the endpoint must not move the download outside its temp dir."""
    import app.data_store.data_store_operations as data_store

    scratch = tmp_path / "scratch"
    scratch.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    stub.hostname = hostname
    stub.file_bytes = b"PK zip bytes"
    uploaded = {}

    async def fake_upload(agent_id, flow_id, file_path, file_name):
        uploaded.update(path=file_path, name=file_name, data=open(file_path, "rb").read())
        return {"bucket_name": "b", "object_key": f"{agent_id}/{flow_id}/{file_name}", "file_name": file_name}

    monkeypatch.setattr(data_store, "upload_agent_artifact_file", fake_upload)

    result = asyncio.run(artifacts.fetch_file_from_filestore(client_id=CLIENT, flow_id=FLOW, org_id=ORG, agent_id="001"))

    assert result["success"] is True
    assert uploaded["data"] == b"PK zip bytes"
    name = uploaded["name"]
    assert "/" not in name and "\\" not in name and ".." not in name and not name.startswith(".")
    assert os.path.dirname(os.path.realpath(uploaded["path"])).startswith(os.path.realpath(scratch))
    _, read_env, _ = stub.call_with("read_file(")
    assert read_env["VfsPath"] == f"/downloads/{CLIENT}/{FLOW}/{name}"
    # The temp dir is gone afterwards, and nothing landed in the working directory.
    assert list(scratch.iterdir()) == [] and list(work.iterdir()) == []


@pytest.mark.parametrize(
    "value, expected",
    [("WIN-HOST01", "WIN-HOST01"), ("host.example.com", "host.example.com"), ("../../etc", "____etc"), ("", "host"), ("a b/c", "a_b_c")],
)
def test_safe_file_component(value, expected):
    assert artifacts.safe_file_component(value) == expected


def test_contained_path_refuses_escapes(tmp_path):
    assert artifacts.contained_path(str(tmp_path), "x.zip") == os.path.join(os.path.realpath(tmp_path), "x.zip")
    for name in ("../x.zip", "/etc/passwd", "a/b.zip"):
        with pytest.raises(HTTPException):
            artifacts.contained_path(str(tmp_path), name)


@pytest.mark.parametrize("os_name", ["windows", "linux"])
@pytest.mark.parametrize("path", PAYLOADS)
def test_file_analysis_finder_query_is_constant(os_name, path):
    vql, env = velociraptor_fetch._finder_vql(CLIENT, os_name, path, upload=True, org_id=ORG)
    other_vql, _ = velociraptor_fetch._finder_vql(CLIENT, os_name, "C:\\Users\\x.exe", upload=False, org_id="root")

    assert vql == other_vql
    _assert_not_in_query(vql, path)
    if os_name == "windows":
        assert env["SearchFilesGlobTable"] == f"Glob\n{path}\n"
    else:
        assert env["SearchFilesGlob"] == path
    assert env["ClientId"] == CLIENT and env["UploadFile"] == "Y"
    # The collection runs in the client's own org.
    assert vql.startswith("SELECT collect_client(org_id=OrgId, client_id=ClientId,") and env["OrgId"] == ORG


def test_file_analysis_rejects_a_malformed_client_id():
    with pytest.raises(HTTPException):
        velociraptor_fetch._finder_vql("C.1', artifacts=[]) AS Flow FROM scope() --", "linux", "/tmp/x", upload=True)


# --- CoPilot Actions: undeclared script parameters are dropped, not refused ------------

SCRIPT_ARTIFACT_PARAMETERS = ["ScriptURL", "Arg1", "Arg2", "Arg3", "Arg4", "Arg5", "Arg6"]


def test_copilot_action_drops_parameters_the_script_artifact_does_not_declare(collect):
    """Velociraptor ignored them before; the Actions path (admin/responder) must keep working."""
    from app.integrations.copilot_action.routes import copilot_action

    collect.declared["names"] = SCRIPT_ARTIFACT_PARAMETERS
    agent = SimpleNamespace(hostname="WIN-HOST", velociraptor_id=CLIENT, velociraptor_org=ORG, os="Windows 10", agent_id="001")
    script_parameters = [
        SimpleNamespace(name="Target", arg_position=1),
        SimpleNamespace(name="Mode", arg_position=8),  # past the artifact's Arg1-Arg6
        SimpleNamespace(name="Verbose", arg_position=None),  # unpositioned
    ]
    details = SimpleNamespace(copilot_action=SimpleNamespace(script_parameters=script_parameters))
    parameters = {
        "ScriptURL": "https://scripts.example.invalid/a.ps1",
        "Target": "C:\\Temp",
        "Mode": "x`) AS Pwn",
        "Verbose": "dropped-value",
    }

    from loguru import logger

    warnings = []
    sink = logger.add(lambda message: warnings.append(message.record["message"]), level="WARNING")
    try:
        response = asyncio.run(copilot_action.invoke_action_on_agent(agent, "Example", details, parameters, _FakeSession()))
    finally:
        logger.remove(sink)

    assert response.success is True
    # The dropped names are logged -- the names only, never their values.
    dropped = [message for message in warnings if "Dropping parameters" in message]
    assert len(dropped) == 1
    assert "Arg8" in dropped[0] and "Verbose" in dropped[0]
    assert "dropped-value" not in dropped[0] and "Pwn" not in dropped[0]
    vql, env, org_id = collect.stub.call_with("collect_client(")
    assert vql == (
        "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName], "
        "env=dict(`ScriptURL`=Param0, `Arg1`=Param1)) AS Flow FROM scope()"
    )
    # The values go through the VQL-literal unescape (pre-existing behaviour: the old query
    # pasted them inside '...'), where the unknown escape "\\T" keeps only the "T".
    assert env["Param0"] == "https://scripts.example.invalid/a.ps1" and env["Param1"] == "C:Temp"
    # Nothing of the dropped parameters reaches Velociraptor, in the query or its variables.
    assert set(env) == {"OrgId", "ClientId", "ArtifactName", "Param0", "Param1"}
    for vql_sent, env_sent, _ in collect.stub.calls():
        assert "Arg8" not in vql_sent and "Verbose" not in vql_sent and "Mode" not in vql_sent
        assert not any("dropped-value" in value or "Pwn" in value for value in env_sent.values())
    assert org_id == ORG


def test_collect_still_refuses_parameters_the_artifact_does_not_declare(collect):
    collect.declared["names"] = SCRIPT_ARTIFACT_PARAMETERS
    with pytest.raises(HTTPException) as exc:
        collect({"env": [{"key": "Verbose", "value": "1"}]})
    assert exc.value.status_code == 400


# --- helpers --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body, value",
    [
        # Python's int(_, 16) accepts a sign or surrounding space; vfilter's decode_hex does not.
        ("\\x+f", "\\x+f"),
        ("\\x f", "\\x f"),
        ("\\x-0", "\\x-0"),
        ("\\x0x", "\\x0x"),
        ("\\xg1", "\\xg1"),
        ("\\x1G", "\\x1G"),
        # The invalid escape copies in[j] (the output index), not in[i]: after an earlier
        # escape has shortened the output, that is a different byte.
        ("\\n\\x+f", "\nnx+f"),
    ],
)
def test_vql_hex_escapes_are_decoded_as_strictly_as_vfilter(body, value):
    """vfilter's decode_hex takes [0-9A-Fa-f] only; anything else is not decoded (utils/unquote.go)."""
    assert vql_string_literal_value(body) == value


def test_vql_hex_escapes_decode_valid_digits():
    assert vql_string_literal_value("\\x41\\x6a\\x4A") == "AjJ"


@pytest.mark.parametrize("value", ["\ud800", "abc\udfff", "\udc80x"])
def test_unencodable_strings_are_a_400_not_a_500(value):
    with pytest.raises(HTTPException) as exc:
        vql_string_literal_value(value)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        universal.build_vql_env({"Value": value})
    assert exc.value.status_code == 400


def test_an_unencodable_command_is_a_400(stub):
    with pytest.raises(HTTPException) as exc:
        _run_command("whoami \ud800")
    # run_remote_command wraps every failure in a 500; the value must not reach Velociraptor.
    assert exc.value.status_code in (400, 500)
    assert "collect_client(" not in " ".join(vql for vql, _, _ in stub.calls())


@pytest.mark.parametrize(
    "body, value",
    [
        ("plain", "plain"),
        ("C:\\\\Users\\\\x", "C:\\Users\\x"),
        ("a\\nb\\tc\\rd", "a\nb\tc\rd"),
        ("it\\'s", "it's"),
        ('say \\"hi\\"', 'say "hi"'),
        ("\\x41\\x42", "AB"),
        ("C:\\Users", "C:Users"),  # an unknown escape keeps only the character, as VQL did
        ("ends with \\", "ends with "),
        ("bare ' quote", "bare ' quote"),
        ("", ""),
        ("unicode \u00e9\u4e2d", "unicode \u00e9\u4e2d"),
    ],
)
def test_vql_string_literal_value_matches_vql_unescaping(body, value):
    assert vql_string_literal_value(body) == value


@pytest.mark.parametrize("name", ["Glob", "Upload_File", "T1552.001 - 3", "Sidebar gadgets (Vista and higher)", "$Boot", "_SANS_Triage"])
def test_real_artifact_parameter_names_are_accepted(name):
    assert validate_artifact_parameter_name(name) == name


def test_collect_policy_definition_lookup_uses_a_variable_in_the_hosts_org(stub):
    asyncio.run(artifacts.get_artifact_policy_definitions(ATOMIC, ORG))

    vql, env, org_id = stub.call_with("artifact_definitions(")
    assert vql == (
        "SELECT name, compiled_in, built_in, parameters, required_permissions, implied_permissions, imports, tools, "
        "export, precondition, sources FROM artifact_definitions(names=[ArtifactName], deps=true)"
    )
    assert env == {"ArtifactName": ATOMIC}
    assert org_id == ORG


def test_collect_parameter_names_are_checked_against_the_hosts_org(collect):
    collect({"env": [{"key": "InstallART", "value": "N"}]})

    assert collect.declared["orgs"] == [ORG]


def test_file_analysis_fetch_runs_every_query_in_the_clients_org(stub):
    service = universal.UniversalService()
    service.stub = stub
    velociraptor_fetch._client_os(service, CLIENT, ORG)
    velociraptor_fetch._read_uploads(service, CLIENT, FLOW, ORG)
    velociraptor_fetch._download_one(service, {"file_store": "/clients/x"}, FLOW, ORG)

    assert {org for _, _, org in stub.calls()} == {ORG}
