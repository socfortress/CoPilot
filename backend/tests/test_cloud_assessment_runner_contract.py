"""CoPilot and copilot-prowler agree (#1328): what the backend sends, the runner accepts; what the
runner answers and writes, the backend reads.

The runner's own code is imported from ``prowler-runner/`` (its request models, error texts, job and
connection-test answers, and its OCSF normalizer run over the fixture Prowler's writer produced), so a
change on either side that breaks the other fails here, without a container or a network.
"""

import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.cloud_assessment.models.cloud_assessment import CloudAssessmentAccount
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentScan
from app.cloud_assessment.schema import cloud_assessment as schema
from app.cloud_assessment.services import accounts
from app.cloud_assessment.services import ingest
from app.cloud_assessment.services import runner_client
from app.cloud_assessment.services.errors import RUNNER_MESSAGES
from tests.cloud_assessment_support import AWS_KEYS
from tests.cloud_assessment_support import CLIENT_SECRET
from tests.cloud_assessment_support import ROLE_ARN
from tests.cloud_assessment_support import gcp_key

RUNNER_DIR = Path(__file__).resolve().parents[2] / "prowler-runner"
pytestmark = pytest.mark.skipif(not (RUNNER_DIR / "runner" / "models.py").exists(), reason="prowler-runner/ isn't in this checkout")


@pytest.fixture(scope="module")
def runner_modules():
    sys.path.insert(0, str(RUNNER_DIR))
    try:
        import runner.connection as connection
        import runner.errors as errors
        import runner.jobs as jobs
        import runner.models as models
        import runner.ocsf as ocsf

        yield {"models": models, "errors": errors, "jobs": jobs, "ocsf": ocsf, "connection": connection}
    finally:
        sys.path.remove(str(RUNNER_DIR))
        for name in [name for name in sys.modules if name == "runner" or name.startswith("runner.")]:
            del sys.modules[name]


def _account(provider, auth_method, config):
    return CloudAssessmentAccount(id=1, customer_code="ACME", name="x", provider=provider, auth_method=auth_method, config=config)


PAYLOADS = {
    "aws role with keys": (
        _account("aws", "role", {"role_arn": ROLE_ARN, "external_id": accounts.new_external_id(), "regions": ["eu-west-1"]}),
        AWS_KEYS,
    ),
    "aws role, host identity": (_account("aws", "role", {"role_arn": ROLE_ARN, "external_id": accounts.new_external_id()}), None),
    "aws keys": (_account("aws", "access_keys", {"excluded_checks": ["iam_root_mfa_enabled"], "timeout_seconds": 900}), AWS_KEYS),
    "azure": (
        _account(
            "azure",
            "client_secret",
            {
                "tenant_id": "72f988bf-86f1-41af-91ab-2d7cd011db47",
                "client_id": "72f988bf-86f1-41af-91ab-2d7cd011db47",
                "subscription_ids": ["72f988bf-86f1-41af-91ab-2d7cd011db47"],
            },
        ),
        {"client_secret": CLIENT_SECRET},
    ),
    "m365": (
        _account(
            "m365",
            "client_secret",
            {
                "tenant_id": "72f988bf-86f1-41af-91ab-2d7cd011db47",
                "client_id": "72f988bf-86f1-41af-91ab-2d7cd011db47",
                "tenant_domain": "acme.onmicrosoft.com",
            },
        ),
        {"client_secret": CLIENT_SECRET},
    ),
    "gcp": (
        _account("gcp", "service_account_key", {"project_ids": ["acme-prod-1"], "organization_id": "123"}),
        {"service_account_key": gcp_key()},
    ),
}


@pytest.mark.parametrize("name", list(PAYLOADS))
def test_the_runner_accepts_what_copilot_sends(name, runner_modules):
    account, secret = PAYLOADS[name]
    if secret and account.provider == "gcp":
        secret = accounts.checked_secret("service_account_key", schema.SecretIn(service_account_key=secret["service_account_key"]))
    payload = accounts.runner_payload(account, secret)
    parsed = runner_modules["models"].ScanPayload.model_validate(payload).root
    assert parsed.provider == account.provider


def test_copilot_s_copy_of_the_runner_s_texts_is_word_for_word(runner_modules):
    messages = runner_modules["errors"].MESSAGES
    assert {code: messages[code] for code in RUNNER_MESSAGES} == RUNNER_MESSAGES


def test_the_patterns_are_the_runner_s(runner_modules):
    models = runner_modules["models"]
    assert schema.ROLE_ARN_PATTERN == models.ROLE_ARN_PATTERN
    assert schema.UUID_PATTERN == models.UUID_PATTERN


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("regions", ["eu-west-1"]),
        ("regions", ["us-gov-west-1"]),
        ("regions", ["EU-WEST-1"]),
        ("regions", ["eu-west-1; rm -rf"]),
        ("excluded_checks", ["iam_root_mfa_enabled"]),
        ("excluded_checks", ["-x"]),
        ("excluded_services", ["s3"]),
        ("excluded_services", ["S3"]),
        ("project_ids", ["acme-prod-1"]),
        ("project_ids", ["Acme"]),
        ("tenant_domain", "acme.onmicrosoft.com"),
        ("tenant_domain", "-acme.com"),
        ("organization_id", "123456"),
        ("organization_id", "12a"),
    ],
)
def test_copilot_refuses_what_the_runner_would(field, value, runner_modules):
    models = runner_modules["models"]
    scope_models = {
        "regions": models.AwsScope,
        "project_ids": models.GcpScope,
        "organization_id": models.GcpScope,
        "tenant_domain": models.M365Scope,
        "excluded_checks": models.ScanOptions,
        "excluded_services": models.ScanOptions,
    }

    def accepts(model) -> bool:
        try:
            model(**{field: value})
        except ValidationError:
            return False
        return True

    assert accepts(schema.AccountConfigIn) == accepts(scope_models[field])


def test_copilot_reads_the_runner_s_job_answer(runner_modules):
    jobs = runner_modules["jobs"]
    job = jobs.Job(id="a" * 32, provider="aws", dir=Path("/nowhere"), timeout=3600, prowler_version="5.52.0")
    job.status = jobs.JobStatus.FAILED
    job.error_code = "permission_denied"
    job.prowler_errors = ["AccessDeniedException"]
    job.logs = {"error_lines": 7, "critical_lines": 0, "error_classes": []}
    parsed = runner_client.parse_job(job.public())
    assert (parsed.job_id, parsed.status, parsed.error_code, parsed.prowler_errors, parsed.error_lines) == (
        "a" * 32,
        "failed",
        "permission_denied",
        ["AccessDeniedException"],
        7,
    )
    for status in jobs.JobStatus:
        assert status.value in runner_client.JOB_STATUSES


def test_copilot_reads_the_runner_s_connection_test_answer(runner_modules):
    outcome = runner_modules["connection"]._outcome(False, "auth_failed", "ClientAuthenticationError")
    assert set(outcome) >= {"ok", "code", "prowler_error"} and outcome["code"] in RUNNER_MESSAGES


def test_copilot_stores_everything_the_runner_normalizes(runner_modules):
    """The runner's normalizer over the OCSF Prowler's own writer produced, then CoPilot's rows."""
    findings = []
    with open(RUNNER_DIR / "tests" / "fixtures" / "aws_sample.ocsf.json", encoding="utf-8") as stream:
        summary = runner_modules["ocsf"].normalize_stream(stream, findings.append, "aws")
    assert summary["checks"] and findings
    checks = [ingest.check_row(entry, 1) for entry in summary["checks"]]
    assert all(checks)
    assert {row["check_id"] for row in checks} == {entry["check_id"] for entry in summary["checks"]}
    assert any(row["compliance"] for row in checks)
    scan = CloudAssessmentScan(
        id=1,
        account_id=1,
        customer_code="ACME",
        status="ingesting",
        trigger_type="manual",
        queued_at=datetime.now(timezone.utc),
    )
    rows = [ingest.finding_row(item, scan) for item in findings]
    assert all(rows)
    assert all(row["finding_uid_hash"] == item["finding_uid_sha256"] for row, item in zip(rows, findings))
    assert any(row["detected_at"] for row in rows)
    totals = summary["totals"]
    assert all(key in totals for key in ("total", "pass", "fail", "manual", "muted"))
    assert set(summary["fail_by_severity"]) == set(schema.SEVERITIES)
