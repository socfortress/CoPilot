"""Connection tests: the route with a fake helper, and the real helper with a fake Prowler SDK."""

import importlib.util
import io
import json
import sys
import types
from pathlib import Path

import pytest

from runner.connection import HELPER
from runner.connection import parse_result
from runner.errors import classify
from tests.support import AWS_SECRET
from tests.support import SECRET
from tests.support import aws_role_scan
from tests.support import azure_scan
from tests.support import gcp_scan
from tests.support import m365_scan

# --- The route ---------------------------------------------------------------------


def test_working_credentials(client, tmp_path):
    response = client.post("/v1/connection-test", json=azure_scan())
    assert response.status_code == 200
    assert response.json() == {"ok": True, "code": None, "message": None, "prowler_error": None}
    seen = json.loads((tmp_path / "connection.json").read_text())
    # The secret travels on stdin, never in the arguments or the environment.
    assert seen["payload"]["auth"]["client_secret"] == SECRET
    assert SECRET not in " ".join(seen["argv"])
    assert SECRET not in json.dumps(seen["env"])
    assert seen["isolated"] == 1  # python -I: no user site, no PYTHON* variables, no script directory on the path


def test_refused_credentials(client):
    body = client.post("/v1/connection-test", json=azure_scan("bad-secret")).json()
    assert body == {
        "ok": False,
        "code": "auth_failed",
        "message": "The cloud provider refused the credentials.",
        "prowler_error": "AzureClientAuthenticationError",
    }


def test_the_wrong_tenant(client):
    body = client.post("/v1/connection-test", json=m365_scan("wrongtenant-secret")).json()
    assert body["code"] == "wrong_account"


def test_whatever_else_the_helper_prints_never_leaves(client):
    response = client.post("/v1/connection-test", json=azure_scan("noisy-secret-value"))
    assert "noisy-secret-value" not in response.text
    assert response.json()["code"] == "auth_failed"


def test_a_helper_that_crashes(client):
    assert client.post("/v1/connection-test", json=azure_scan("crash-now")).json()["code"] == "internal"


def test_a_helper_that_hangs(make_client, settings):
    client = make_client(settings.__class__(**{**settings.__dict__, "connection_test_timeout": 1}))
    body = client.post("/v1/connection-test", json=azure_scan("sleep-forever")).json()
    assert body["ok"] is False
    assert body["prowler_error"] == "TimeoutError"


def test_m365_needs_a_domain(client):
    response = client.post("/v1/connection-test", json=m365_scan(tenant_domain=None))
    assert response.status_code == 400
    assert response.json()["code"] == "tenant_domain_required"


def test_the_helper_leaves_nothing_behind(client, settings):
    client.post("/v1/connection-test", json=azure_scan())
    assert not [entry for entry in settings.work_dir.iterdir() if entry.name.startswith("conn-")]


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (b'PROWLER_RUNNER_RESULT {"ok": true, "error_class": null}\n', (True, None, None)),
        (
            b'noise\nPROWLER_RUNNER_RESULT {"ok": false, "error_class": "AWSAssumeRoleError"}\n',
            (False, "auth_failed", "AWSAssumeRoleError"),
        ),
        (b'PROWLER_RUNNER_RESULT {"ok": false, "error_class": "Weird Name; rm"}\n', (False, "connection_failed", None)),
        (b'PROWLER_RUNNER_RESULT {"ok": false, "error_class": "ModuleNotFoundError"}\n', (False, "internal", "ModuleNotFoundError")),
        (b"PROWLER_RUNNER_RESULT not json\n", (False, "internal", None)),
        (b"", (False, "internal", None)),
    ],
)
def test_parse_result(output, expected):
    result = parse_result(output)
    assert (result["ok"], result["code"], result["prowler_error"]) == expected


@pytest.mark.parametrize(
    ("names", "code"),
    [
        (["AWSAssumeRoleError"], "auth_failed"),
        (["NoCredentialsError"], "auth_failed"),
        (["AzureClientIdAndClientSecretNotBelongingToTenantIdError"], "auth_failed"),
        (["GCPInvalidProviderIdError"], "wrong_account"),
        (["AzureNoSubscriptionsError"], "permission_denied"),
        (["M365ExchangeConnectionError"], "m365_powershell_failed"),
        (["AWSIAMRoleARNInvalidAccountIDError"], "invalid_request"),
        (["SomethingUnexpected"], "scan_failed"),
        ([], "scan_failed"),
    ],
)
def test_classify(names, code):
    assert classify(names) == code


# --- The real helper, with a fake Prowler SDK ----------------------------------------


class Connection:
    def __init__(self, is_connected=True, error=None):
        self.is_connected = is_connected
        self.error = error


class AWSAssumeRoleError(Exception):
    pass


@pytest.fixture
def helper(monkeypatch):
    calls = {}

    def provider(name):
        class Provider:
            @staticmethod
            def test_connection(**kwargs):
                calls[name] = kwargs
                if kwargs.get("external_id") == "fails-0000":
                    return Connection(False, AWSAssumeRoleError("role arn:aws:iam::123456789012:role/Hidden refused"))
                return Connection()

        return Provider

    for package, module, cls in (
        ("aws", "aws_provider", "AwsProvider"),
        ("azure", "azure_provider", "AzureProvider"),
        ("gcp", "gcp_provider", "GcpProvider"),
        ("m365", "m365_provider", "M365Provider"),
    ):
        fake = types.ModuleType(f"prowler.providers.{package}.{module}")
        setattr(fake, cls, provider(cls))
        monkeypatch.setitem(sys.modules, f"prowler.providers.{package}.{module}", fake)
    for name in (
        "prowler",
        "prowler.providers",
        "prowler.providers.aws",
        "prowler.providers.azure",
        "prowler.providers.gcp",
        "prowler.providers.m365",
    ):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))

    spec = importlib.util.spec_from_file_location("runner_test_connection_helper", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.calls = calls
    return module


def run_helper(helper, monkeypatch, payload):
    from runner.commands import connection_test_input
    from runner.models import ScanPayload

    data = connection_test_input(ScanPayload.model_validate(payload).root)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(data)))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    helper.main()
    return out.getvalue()


def test_helper_aws_role(helper, monkeypatch):
    output = run_helper(helper, monkeypatch, aws_role_scan())
    assert output == 'PROWLER_RUNNER_RESULT {"ok": true, "error_class": null}\n'
    assert helper.calls["AwsProvider"] == {
        "raise_on_exception": False,
        "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
        "aws_secret_access_key": AWS_SECRET,
        "role_arn": "arn:aws:iam::123456789012:role/ProwlerScan",
        "external_id": "copilot-0123456789abcdef",
        "session_duration": 3600,
    }


def test_helper_reports_a_failure_by_class_only(helper, monkeypatch):
    payload = aws_role_scan()
    payload["auth"]["external_id"] = "fails-0000"
    output = run_helper(helper, monkeypatch, payload)
    assert output == 'PROWLER_RUNNER_RESULT {"ok": false, "error_class": "AWSAssumeRoleError"}\n'
    assert "Hidden" not in output


def test_helper_azure_checks_the_first_subscription(helper, monkeypatch):
    run_helper(helper, monkeypatch, azure_scan())
    assert helper.calls["AzureProvider"]["provider_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert helper.calls["AzureProvider"]["client_secret"] == SECRET


def test_helper_gcp_defaults_to_the_first_project(helper, monkeypatch):
    run_helper(helper, monkeypatch, gcp_scan())
    call = helper.calls["GcpProvider"]
    assert call["provider_id"] == "acme-prod-123"
    assert call["service_account_key"]["client_email"] == "prowler@acme-prod-123.iam.gserviceaccount.com"


def test_helper_m365_checks_the_domain(helper, monkeypatch):
    run_helper(helper, monkeypatch, m365_scan())
    call = helper.calls["M365Provider"]
    assert call["provider_id"] == "contoso.onmicrosoft.com"
    assert "certificate_content" not in call


def test_helper_is_a_standalone_script():
    # It runs under Prowler's interpreter, which doesn't have the runner package.
    source = Path(HELPER).read_text()
    assert "import runner" not in source
    assert "from runner" not in source
