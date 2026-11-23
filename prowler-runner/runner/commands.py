"""How a request becomes a Prowler command line, environment and credential files.

Pure functions, no I/O. The rules that matter:

- A secret never goes on the command line (``ps`` shows it to anything in the
  container). Keys and client secrets go in the scan process's environment; a GCP
  key, which Prowler reads from a file, goes in a file in the job's private directory.
- The scan's environment is built from scratch. Nothing of the runner's own
  environment (its token above all) reaches Prowler, except proxy settings.
- Every value placed on the command line has passed a pattern that rules out a
  leading "-", and single values are written as ``--option=value``, so no value can
  be read as an option.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

from runner.layout import OUTPUT_NAME
from runner.models import AwsAccessKeysAuth
from runner.models import AwsKeys
from runner.models import AwsRoleAuth
from runner.models import AwsScanRequest
from runner.models import AzureScanRequest
from runner.models import ClientSecretAuth
from runner.models import GcpScanRequest
from runner.models import M365ScanRequest
from runner.models import ScanRequest
from runner.settings import Settings

OUTPUT_FORMATS = ("json-ocsf", "html", "csv")
GCP_KEY_FILE = "gcp-service-account.json"


@dataclass(frozen=True)
class ScanCommand:
    argv: list[str]
    env: dict[str, str]
    # File name in the job's secrets directory -> content, written with mode 0600.
    secret_files: dict[str, bytes] = field(default_factory=dict)


def scan_environment(settings: Settings) -> dict[str, str]:
    """The environment every Prowler process starts from."""
    env = {
        "PATH": settings.scan_path,
        "HOME": settings.scan_home,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "POWERSHELL_TELEMETRY_OPTOUT": "1",
        "POWERSHELL_UPDATECHECK": "Off",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
    }
    env.update(settings.passthrough_env)
    return env


def _unique(values) -> list[str]:
    return list(dict.fromkeys(values))


def aws_environment(keys: AwsKeys) -> dict[str, str]:
    env = {
        "AWS_ACCESS_KEY_ID": keys.access_key_id,
        "AWS_SECRET_ACCESS_KEY": keys.secret_access_key.get_secret_value(),
    }
    if keys.session_token is not None:
        env["AWS_SESSION_TOKEN"] = keys.session_token.get_secret_value()
    return env


def client_secret_environment(auth: ClientSecretAuth) -> dict[str, str]:
    """What Prowler's ``--sp-env-auth`` reads, for Azure and Microsoft 365 alike."""
    return {
        "AZURE_TENANT_ID": auth.tenant_id,
        "AZURE_CLIENT_ID": auth.client_id,
        "AZURE_CLIENT_SECRET": auth.client_secret.get_secret_value(),
    }


def build_scan_command(request: ScanRequest, settings: Settings, out_dir: Path, secrets_dir: Path) -> ScanCommand:
    argv = [*settings.prowler_cmd, request.provider]
    env = scan_environment(settings)
    secret_files: dict[str, bytes] = {}

    if isinstance(request, AwsScanRequest):
        auth = request.auth
        if isinstance(auth, AwsRoleAuth):
            argv += [
                f"--role={auth.role_arn}",
                f"--external-id={auth.external_id}",
                f"--session-duration={auth.session_duration_seconds}",
            ]
            if auth.base_credentials is not None:
                env.update(aws_environment(auth.base_credentials))
            # Without base credentials boto3 falls back to the host's instance or task role.
        elif isinstance(auth, AwsAccessKeysAuth):
            env.update(aws_environment(auth))
            env["AWS_EC2_METADATA_DISABLED"] = "true"
        if request.scope.regions:
            argv += ["--filter-region", *_unique(request.scope.regions)]
    elif isinstance(request, AzureScanRequest):
        argv.append("--sp-env-auth")
        env.update(client_secret_environment(request.auth))
        if request.scope.subscription_ids:
            argv += ["--subscription-ids", *_unique(request.scope.subscription_ids)]
    elif isinstance(request, GcpScanRequest):
        key = json.dumps(request.auth.service_account_key.key_file()).encode()
        secret_files[GCP_KEY_FILE] = key
        argv.append(f"--credentials-file={secrets_dir / GCP_KEY_FILE}")
        if request.scope.project_ids:
            argv += ["--project-ids", *_unique(request.scope.project_ids)]
        if request.scope.excluded_project_ids:
            argv += ["--excluded-project-ids", *_unique(request.scope.excluded_project_ids)]
        if request.scope.organization_id:
            argv.append(f"--organization-id={request.scope.organization_id}")
    elif isinstance(request, M365ScanRequest):
        argv.append("--sp-env-auth")
        env.update(client_secret_environment(request.auth))
    else:  # pragma: no cover - the request models allow nothing else
        raise ValueError("unknown provider")

    argv += [
        "--output-formats",
        *OUTPUT_FORMATS,
        f"--output-directory={out_dir}",
        f"--output-filename={OUTPUT_NAME}",
        # Failed checks are the point of a scan, not an error: exit 0 instead of 3.
        "--ignore-exit-code-3",
        # One JSON log line per message, errors only, no progress bars or colour.
        "--only-logs",
        "--log-level=ERROR",
        "--no-color",
    ]
    if request.options.excluded_checks:
        argv += ["--excluded-checks", *_unique(request.options.excluded_checks)]
    if request.options.excluded_services:
        argv += ["--excluded-services", *_unique(request.options.excluded_services)]
    return ScanCommand(argv=argv, env=env, secret_files=secret_files)


def connection_test_input(request: ScanRequest) -> dict:
    """What the connection-test helper reads on its stdin (secrets included: stdin is private to it)."""
    if isinstance(request, AwsScanRequest):
        auth = request.auth
        data: dict = {"method": auth.method}
        if isinstance(auth, AwsRoleAuth):
            data.update(role_arn=auth.role_arn, external_id=auth.external_id, session_duration=auth.session_duration_seconds)
            keys = auth.base_credentials
        else:
            keys = auth
        if keys is not None:
            data.update(_aws_keys(keys))
        return {"provider": "aws", "auth": data}
    if isinstance(request, (AzureScanRequest, M365ScanRequest)):
        auth = request.auth
        scope = request.scope.model_dump(exclude_none=True)
        return {
            "provider": request.provider,
            "auth": {"tenant_id": auth.tenant_id, "client_id": auth.client_id, "client_secret": auth.client_secret.get_secret_value()},
            "scope": scope,
        }
    if isinstance(request, GcpScanRequest):
        return {
            "provider": "gcp",
            "auth": {"service_account_key": request.auth.service_account_key.key_file()},
            "scope": request.scope.model_dump(exclude_none=True),
        }
    raise ValueError("unknown provider")  # pragma: no cover


def _aws_keys(keys: AwsKeys) -> dict:
    data = {"aws_access_key_id": keys.access_key_id, "aws_secret_access_key": keys.secret_access_key.get_secret_value()}
    if keys.session_token is not None:
        data["aws_session_token"] = keys.session_token.get_secret_value()
    return data
