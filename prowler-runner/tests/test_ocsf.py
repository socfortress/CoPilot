"""Reading Prowler's OCSF output: the file the tests use was written by Prowler 5.52.0's own writer."""

import io
import json

import pytest

from runner.normalize_cli import main as normalize_main
from runner.ocsf import OcsfError
from runner.ocsf import iter_json_array
from runner.ocsf import normalize_finding
from runner.ocsf import normalize_stream
from tests.support import FIXTURES

SAMPLE = FIXTURES / "aws_sample.ocsf.json"
RAW_SECRET = "FIXTURE-SECRET-VALUE"


def sample_items():
    return json.loads(SAMPLE.read_text())


@pytest.mark.parametrize("chunk_size", [1, 7, 64, 4096, 1 << 20])
def test_streaming_reads_the_same_findings_as_json_load(chunk_size):
    with open(SAMPLE, encoding="utf-8") as stream:
        items = list(iter_json_array(stream, chunk_size=chunk_size))
    assert items == sample_items()
    assert len(items) == 7


@pytest.mark.parametrize("text", ["", "   \n", "[]", " [ ] \n", "[\n]"])
def test_an_empty_file_or_array_has_no_findings(text):
    assert list(iter_json_array(io.StringIO(text), chunk_size=2)) == []


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1}',  # not an array
        '[{"a": 1}',  # ends early
        '[{"a": 1} {"b": 2}]',  # no comma
        '[{"a": 1}] trailing',  # data after the array
        '[{"a": ',  # cut inside a finding
    ],
)
def test_malformed_output_is_refused(text):
    with pytest.raises(OcsfError):
        list(iter_json_array(io.StringIO(text), chunk_size=3))


def test_a_finding_larger_than_the_limit_is_refused():
    text = '[{"a": "' + "x" * 5000
    with pytest.raises(OcsfError):
        list(iter_json_array(io.StringIO(text), chunk_size=100, max_item_chars=1000))


def summarize(items):
    written = []
    summary = normalize_stream(io.StringIO(json.dumps(items)), written.append, "aws")
    return summary, written


def test_summary_counts_unmuted_statuses_and_muted_apart():
    summary, written = summarize(sample_items())
    assert summary["totals"] == {"total": 7, "pass": 2, "fail": 3, "manual": 1, "muted": 1}
    assert summary["fail_by_severity"] == {"critical": 1, "high": 1, "medium": 1, "low": 0, "informational": 0, "unknown": 0}
    assert summary["cloud_accounts"] == ["123456789012"]
    assert summary["prowler_version"] == "5.52.0"
    assert summary["skipped"] == 0
    # FAIL and MANUAL findings are written, the muted FAIL included; PASS ones only counted.
    assert sorted((finding["check_id"], finding["status"], finding["muted"]) for finding in written) == [
        ("account_maintain_current_contact_details", "MANUAL", False),
        ("ec2_instance_public_ip", "FAIL", False),
        ("ecs_task_definitions_no_environment_secrets", "FAIL", False),
        ("iam_root_mfa_enabled", "FAIL", False),
        ("s3_bucket_public_access", "FAIL", True),
    ]


def test_check_entries_carry_metadata_and_counts():
    summary, _ = summarize(sample_items())
    checks = {check["check_id"]: check for check in summary["checks"]}
    assert list(checks) == sorted(checks)
    ecs = checks["ecs_task_definitions_no_environment_secrets"]
    assert (ecs["pass"], ecs["fail"], ecs["manual"], ecs["muted"]) == (1, 1, 0, 0)
    assert ecs["severity"] == "critical"
    assert ecs["service"] == "ecs"
    assert ecs["title"] == "ECS task definitions have no secrets in environment variables"
    assert ecs["compliance"] == {"MITRE-ATTACK": ["T1552"], "CIS-5.0": ["5.1"]}
    assert ecs["references"] == ["https://hub.prowler.com/check/ecs_task_definitions_no_environment_secrets"]
    assert ecs["categories"] == ["secrets"]
    assert checks["s3_bucket_public_access"]["muted"] == 1
    assert checks["s3_bucket_public_access"]["fail"] == 0


def test_raw_resource_configuration_never_leaves():
    items = sample_items()
    assert RAW_SECRET in json.dumps(items)  # the fixture does carry it, under resources[].data
    summary, written = summarize(items)
    assert RAW_SECRET not in json.dumps(summary)
    assert RAW_SECRET not in json.dumps(written)
    assert all("data" not in finding for finding in written)


def test_a_finding_keeps_its_resource_fields():
    finding = normalize_finding(sample_items()[0])
    assert finding == {
        "finding_uid": "prowler-aws-ecs_task_definitions_no_environment_secrets-123456789012-eu-west-1-api:7",
        "check_id": "ecs_task_definitions_no_environment_secrets",
        "status": "FAIL",
        "severity": "critical",
        "muted": False,
        "status_extended": "Potential secrets found in ECS task definition api with revision 7: Secret Keyword on the environment variable DB_PASSWORD.",
        "service": "ecs",
        "region": "eu-west-1",
        "cloud_account_uid": "123456789012",
        "cloud_account_name": "production",
        "resource_uid": "arn:aws:ecs:eu-west-1:123456789012:task-definition/api:7",
        "resource_name": "api:7",
        "resource_type": "AwsEcsTaskDefinition",
        "resource_tags": ["env:prod", "owner:team-a"],
        "time": "2026-11-23T12:00:00Z",
    }


def test_control_characters_go_and_other_invisible_characters_stay():
    root = normalize_finding(sample_items()[4])
    assert root["status_extended"] == "MFA is not enabled for root account."  # the BEL is gone
    # A right-to-left override is kept: hiding it would hide a spoofed name. The UI shows it.
    assert root["resource_name"] == "root‮"


def test_long_text_is_cut_with_an_ellipsis():
    finding = normalize_finding(sample_items()[6])
    assert len(finding["status_extended"]) == 2000
    assert finding["status_extended"].endswith("…")


def test_only_http_references_are_kept():
    item = sample_items()[0]
    item["remediation"]["references"] = ["javascript:alert(1)", "https://example.com/fix", "http://example.com/a b", 7]
    item["unmapped"]["additional_urls"] = ["data:text/html,x", "https://example.com/more"]
    summary, _ = summarize([item])
    check = summary["checks"][0]
    assert check["references"] == ["https://example.com/fix"]
    assert check["additional_urls"] == ["https://example.com/more"]


@pytest.mark.parametrize(
    "change",
    [
        lambda item: item["metadata"].pop("event_code"),
        lambda item: item["metadata"].update(event_code="Bad Check; rm -rf"),
        lambda item: item.update(status_code="ERROR"),
        lambda item: item["finding_info"].pop("uid"),
    ],
)
def test_records_that_are_not_prowler_findings_are_skipped(change):
    item = sample_items()[0]
    change(item)
    summary, written = summarize([item, sample_items()[1]])
    assert summary["skipped"] == 1
    assert summary["totals"]["total"] == 1
    assert written == []


def test_unknown_severity_is_reported_as_unknown():
    item = sample_items()[0]
    item["severity"] = "Catastrophic"
    summary, written = summarize([item])
    assert written[0]["severity"] == "unknown"
    assert summary["fail_by_severity"]["unknown"] == 1


def job_dir(tmp_path, ocsf_text=None):
    """A job directory as the runner lays it out, with Prowler's output in out/."""
    directory = tmp_path / ("c" * 32)
    (directory / "out").mkdir(parents=True)
    if ocsf_text is not None:
        (directory / "out" / "scan.ocsf.json").write_text(ocsf_text)
    return directory


def test_the_normalizer_writes_both_files(tmp_path):
    directory = job_dir(tmp_path, SAMPLE.read_text())
    assert normalize_main([str(directory), "aws"]) == 0
    summary = json.loads((directory / "summary.json").read_text())
    lines = (directory / "findings.ndjson").read_text().splitlines()
    assert summary["totals"]["total"] == 7
    assert len(lines) == 5
    assert all(line.isascii() for line in lines)
    assert [json.loads(line)["check_id"] for line in lines][0] == "ecs_task_definitions_no_environment_secrets"
    assert (directory / "summary.json").stat().st_mode & 0o777 == 0o600
    assert not list(directory.glob("*.tmp"))


def test_the_normalizer_reads_a_missing_file_as_no_findings(tmp_path):
    directory = job_dir(tmp_path)
    assert normalize_main([str(directory), "gcp"]) == 0
    summary = json.loads((directory / "summary.json").read_text())
    assert summary["totals"]["total"] == 0
    assert summary["provider"] == "gcp"
    assert (directory / "findings.ndjson").read_text() == ""


def test_the_normalizer_exits_3_on_output_it_cannot_read(tmp_path):
    directory = job_dir(tmp_path, '[{"x": ')
    assert normalize_main([str(directory), "aws"]) == 3
    assert not (directory / "summary.json").exists()


@pytest.mark.parametrize(
    "arguments",
    [
        lambda directory: [str(directory)],
        lambda directory: [str(directory), "kubernetes"],
        lambda directory: [str(directory.parent), "aws"],  # not a job directory
        lambda directory: ["relative/" + "c" * 32, "aws"],
        lambda directory: [str(directory / "missing" / ("d" * 32)), "aws"],
    ],
)
def test_the_normalizer_only_works_in_a_job_directory(tmp_path, arguments):
    directory = job_dir(tmp_path, SAMPLE.read_text())
    assert normalize_main(arguments(directory)) == 2
    assert not (directory / "summary.json").exists()
