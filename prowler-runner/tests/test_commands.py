"""Command lines and environments: secrets in the environment or a private file, never on the command line."""

import json
from pathlib import Path

from runner.commands import GCP_KEY_FILE
from runner.commands import build_scan_command
from runner.commands import connection_test_input
from runner.models import ScanPayload
from tests.support import AWS_SECRET
from tests.support import KEY_ID
from tests.support import SECRET
from tests.support import TOKEN
from tests.support import aws_role_scan
from tests.support import azure_scan
from tests.support import gcp_scan
from tests.support import m365_scan

OUT = Path("/work/job/out")
SECRETS = Path("/work/job/secrets")


def command(payload, settings):
    return build_scan_command(ScanPayload.model_validate(payload).root, settings, OUT, SECRETS)


def assert_common_options(argv):
    assert argv[argv.index("--output-formats") + 1 : argv.index("--output-formats") + 4] == ["json-ocsf", "html", "csv"]
    for option in (
        f"--output-directory={OUT}",
        "--output-filename=scan",
        "--ignore-exit-code-3",
        "--only-logs",
        "--log-level=ERROR",
        "--no-color",
    ):
        assert option in argv
    assert "--scan-secrets-validate" not in argv


def test_aws_role_scan(settings):
    built = command(aws_role_scan(excluded_checks=["iam_root_mfa_enabled", "iam_root_mfa_enabled"]), settings)
    argv = built.argv
    assert argv[: len(settings.prowler_cmd) + 1] == [*settings.prowler_cmd, "aws"]
    assert "--role=arn:aws:iam::123456789012:role/ProwlerScan" in argv
    assert "--external-id=copilot-0123456789abcdef" in argv
    assert "--session-duration=3600" in argv
    assert argv[argv.index("--filter-region") + 1 : argv.index("--filter-region") + 3] == ["eu-west-1", "us-east-1"]
    assert argv.count("iam_root_mfa_enabled") == 1
    assert_common_options(argv)
    assert built.env["AWS_ACCESS_KEY_ID"] == KEY_ID
    assert built.env["AWS_SECRET_ACCESS_KEY"] == AWS_SECRET
    assert "AWS_EC2_METADATA_DISABLED" not in built.env
    assert AWS_SECRET not in " ".join(argv)


def test_aws_role_without_base_credentials_uses_the_hosts_identity(settings):
    payload = aws_role_scan()
    del payload["auth"]["base_credentials"]
    built = command(payload, settings)
    assert not any(name.startswith("AWS_") for name in built.env)


def test_aws_access_keys(settings):
    payload = {
        "provider": "aws",
        "auth": {"method": "access_keys", "access_key_id": KEY_ID, "secret_access_key": AWS_SECRET, "session_token": "FwoGZXIvYXdzEJr" * 4},
    }
    built = command(payload, settings)
    assert not any(option.startswith("--role") for option in built.argv)
    assert built.env["AWS_SESSION_TOKEN"] == "FwoGZXIvYXdzEJr" * 4
    assert built.env["AWS_EC2_METADATA_DISABLED"] == "true"
    assert "--filter-region" not in built.argv


def test_azure(settings):
    built = command(azure_scan(), settings)
    assert built.argv[len(settings.prowler_cmd) : len(settings.prowler_cmd) + 2] == ["azure", "--sp-env-auth"]
    assert built.argv[built.argv.index("--subscription-ids") + 1] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert built.env["AZURE_CLIENT_SECRET"] == SECRET
    assert built.env["AZURE_TENANT_ID"] == "11111111-2222-3333-4444-555555555555"
    assert SECRET not in " ".join(built.argv)
    assert_common_options(built.argv)


def test_m365_uses_the_client_secret(settings):
    built = command(m365_scan(), settings)
    assert built.argv[len(settings.prowler_cmd) : len(settings.prowler_cmd) + 2] == ["m365", "--sp-env-auth"]
    assert built.env["AZURE_CLIENT_SECRET"] == SECRET
    assert "--certificate-auth" not in built.argv
    assert "contoso.onmicrosoft.com" not in built.argv  # only the connection test uses the domain


def test_gcp_key_goes_to_a_private_file_rebuilt_from_the_checked_fields(settings):
    payload = gcp_scan(unexpected_field="dropped")
    built = command(payload, settings)
    assert f"--credentials-file={SECRETS / GCP_KEY_FILE}" in built.argv
    assert built.argv[built.argv.index("--project-ids") + 1 : built.argv.index("--project-ids") + 3] == ["acme-prod-123", "acme-dev-456"]
    key = json.loads(built.secret_files[GCP_KEY_FILE])
    assert key["token_uri"] == "https://oauth2.googleapis.com/token"
    assert "unexpected_field" not in key
    assert key["private_key"].startswith("-----BEGIN PRIVATE KEY-----")
    assert "BEGIN PRIVATE KEY" not in " ".join(built.argv)


def test_the_runners_environment_never_reaches_a_scan(settings, monkeypatch):
    monkeypatch.setenv("PROWLER_RUNNER_TOKEN", TOKEN)
    built = command(azure_scan(), settings)
    assert "PROWLER_RUNNER_TOKEN" not in built.env
    assert TOKEN not in built.env.values()
    assert set(built.env) >= {"PATH", "HOME", "LANG", "POWERSHELL_TELEMETRY_OPTOUT"}
    assert built.env["PATH"] == settings.scan_path


def test_connection_test_input_carries_the_credentials():
    role = ScanPayload.model_validate(aws_role_scan()).root
    assert connection_test_input(role)["auth"] == {
        "method": "role",
        "role_arn": "arn:aws:iam::123456789012:role/ProwlerScan",
        "external_id": "copilot-0123456789abcdef",
        "session_duration": 3600,
        "aws_access_key_id": KEY_ID,
        "aws_secret_access_key": AWS_SECRET,
    }
    m365 = connection_test_input(ScanPayload.model_validate(m365_scan()).root)
    assert m365["auth"]["client_secret"] == SECRET
    assert m365["scope"] == {"tenant_domain": "contoso.onmicrosoft.com"}
    gcp = connection_test_input(ScanPayload.model_validate(gcp_scan()).root)
    assert gcp["auth"]["service_account_key"]["project_id"] == "acme-prod-123"
