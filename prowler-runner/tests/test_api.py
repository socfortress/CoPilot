"""The HTTP API end to end, with a fake ``prowler`` that writes real Prowler output."""

import json
import os
import time
from pathlib import Path

import pytest

from tests.support import AWS_SECRET
from tests.support import SECRET
from tests.support import TOKEN
from tests.support import aws_role_scan
from tests.support import azure_scan
from tests.support import gcp_scan
from tests.support import wait_for
from tests.support import with_settings

RAW_SECRET = "FIXTURE-SECRET-VALUE"


def start(client, payload):
    response = client.post("/v1/scans", json=payload)
    assert response.status_code == 202, response.text
    return response.json()


def invocation(settings, job_id):
    return json.loads((settings.work_dir / job_id / "invocation.json").read_text())


def process_gone(pid: int, timeout: float = 10) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def wait_for_file(path: Path, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists():
        assert time.monotonic() < deadline, f"{path} never appeared"
        time.sleep(0.05)


# --- Authentication -------------------------------------------------------------


def test_healthz_needs_no_token(make_client, settings):
    client = make_client(settings, authorized=False)
    assert client.get("/healthz").json() == {"status": "ok"}


@pytest.mark.parametrize("header", [None, "Bearer wrong-token-" + "x" * 30, f"Basic {TOKEN}", TOKEN])
def test_v1_needs_the_token(make_client, settings, header):
    client = make_client(settings, authorized=False)
    headers = {"Authorization": header} if header else {}
    response = client.get("/v1/health", headers=headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing or wrong bearer token.", "code": "unauthorized"}


@pytest.mark.parametrize("token", [None, "short-token"])
def test_without_a_usable_token_every_request_is_refused(make_client, settings, token):
    client = make_client(with_settings(settings, token=token))
    response = client.get("/v1/health")
    assert response.status_code == 503
    assert response.json()["code"] == "not_configured"


def test_health(client):
    body = client.get("/v1/health").json()
    assert body["status"] == "ok"
    assert body["providers"] == ["aws", "azure", "gcp", "m365"]
    assert body["max_concurrent"] == 2
    assert body["running"] == 0


def test_answers_are_not_cached(client):
    assert client.get("/v1/health").headers["cache-control"] == "no-store"
    assert client.get("/v1/scans/" + "0" * 32).headers["cache-control"] == "no-store"


def test_unknown_routes_answer_a_plain_404(client):
    response = client.get("/v1/nothing-here")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert client.get("/docs").status_code == 404


def test_a_refused_request_never_echoes_a_secret(client):
    payload = azure_scan()
    payload["auth"]["client_secret"] = "VisibleSecret\u0001Value"
    payload["auth"]["tenant_id"] = "not-a-uuid"
    response = client.post("/v1/scans", json=payload)
    assert response.status_code == 422
    assert "VisibleSecret" not in response.text
    assert "not-a-uuid" not in response.text
    body = response.json()
    assert body["code"] == "invalid_request"
    assert {item["field"] for item in body["fields"]} >= {"body.azure.auth.client_secret", "body.azure.auth.tenant_id"}


# --- A scan from start to finish ---------------------------------------------------


def test_a_completed_scan(client, settings):
    job = start(client, aws_role_scan())
    assert job["status"] == "running"
    assert job["provider"] == "aws"
    done = wait_for(client, job["job_id"])
    assert done["status"] == "completed", done
    assert done["error"] is None
    assert done["exit_code"] == 0
    assert done["totals"]["total"] == 7
    assert done["totals"]["fail_by_severity"]["critical"] == 1
    # The scan finished but a check logged an error: reported by count and class only.
    assert done["logs"]["error_lines"] == 1
    assert done["logs"]["error_classes"] == [{"name": "ClientError", "count": 1}]

    summary = client.get(f"/v1/scans/{job['job_id']}/summary")
    assert summary.status_code == 200
    assert summary.json()["totals"] == {"total": 7, "pass": 2, "fail": 3, "manual": 1, "muted": 1}

    findings = client.get(f"/v1/scans/{job['job_id']}/findings")
    assert findings.headers["content-type"].startswith("application/x-ndjson")
    lines = findings.text.splitlines()
    assert len(lines) == 5
    assert RAW_SECRET not in findings.text + summary.text

    html = client.get(f"/v1/scans/{job['job_id']}/artifacts/html")
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")
    assert "attachment" in html.headers["content-disposition"]
    assert client.get(f"/v1/scans/{job['job_id']}/artifacts/csv").text.startswith("PROVIDER;")

    job_dir = settings.work_dir / job["job_id"]
    assert not (job_dir / "out" / "scan.ocsf.json").exists()  # the raw output is gone
    assert not (job_dir / "out" / "compliance").exists()
    assert not (job_dir / "secrets").exists()
    assert oct(job_dir.stat().st_mode & 0o777) == "0o700"


def test_what_prowler_was_given(client, settings):
    job = start(client, aws_role_scan())
    wait_for(client, job["job_id"])
    seen = invocation(settings, job["job_id"])
    assert seen["argv"][0] == "aws"
    assert "--role=arn:aws:iam::123456789012:role/ProwlerScan" in seen["argv"]
    assert AWS_SECRET not in " ".join(seen["argv"])
    assert seen["env"]["AWS_SECRET_ACCESS_KEY"] == AWS_SECRET
    assert "PROWLER_RUNNER_TOKEN" not in seen["env"]
    assert TOKEN not in json.dumps(seen["env"])
    assert seen["cwd"] == str((settings.work_dir / job["job_id"]).resolve()) or seen["cwd"] == str(settings.work_dir / job["job_id"])


def test_the_gcp_key_file_lives_only_while_prowler_runs(client, settings):
    job = start(client, gcp_scan())
    assert wait_for(client, job["job_id"])["status"] == "completed"
    key_file = invocation(settings, job["job_id"])["credentials_file"]
    assert key_file["exists"] is True
    assert key_file["mode"] == 0o600
    assert key_file["content"]["token_uri"] == "https://oauth2.googleapis.com/token"
    assert not (settings.work_dir / job["job_id"] / "secrets").exists()


def test_exit_code_3_still_completes(client):
    job = start(client, azure_scan(excluded_checks=["fake_mode_exit3"]))
    done = wait_for(client, job["job_id"])
    assert done["status"] == "completed"
    assert done["exit_code"] == 3


def test_a_refused_credential(client):
    job = start(client, aws_role_scan(excluded_checks=["fake_mode_auth"]))
    done = wait_for(client, job["job_id"])
    assert done["status"] == "failed"
    assert done["error"] == {
        "code": "auth_failed",
        "message": "The cloud provider refused the credentials.",
        "prowler_errors": ["AWSAssumeRoleError"],
    }
    # Prowler's message named the role: it never leaves the runner.
    assert "SensitiveRoleName" not in json.dumps(done)
    assert client.get(f"/v1/scans/{job['job_id']}/summary").status_code == 409


def test_a_command_line_prowler_refused(client):
    done = wait_for(client, start(client, azure_scan(excluded_checks=["fake_mode_argparse"]))["job_id"])
    assert done["status"] == "failed"
    assert done["exit_code"] == 2
    assert done["error"]["code"] == "invalid_request"


def test_output_that_cannot_be_read(client, settings):
    job = start(client, azure_scan(excluded_checks=["fake_mode_bad_output"]))
    done = wait_for(client, job["job_id"])
    assert done["status"] == "failed"
    assert done["error"]["code"] == "output_invalid"
    assert not (settings.work_dir / job["job_id"] / "out" / "scan.ocsf.json").exists()


def test_a_scan_without_findings(client):
    job = start(client, azure_scan(excluded_checks=["fake_mode_no_output"]))
    done = wait_for(client, job["job_id"])
    assert done["status"] == "completed"
    assert done["totals"]["total"] == 0
    assert client.get(f"/v1/scans/{job['job_id']}/findings").text == ""
    assert client.get(f"/v1/scans/{job['job_id']}/artifacts/html").json()["code"] == "no_artifact"


def test_a_very_long_log_line_is_skipped(client):
    done = wait_for(client, start(client, azure_scan(excluded_checks=["fake_mode_long_line"]))["job_id"])
    assert done["status"] == "completed"
    assert done["logs"]["error_lines"] == 1


# --- Stopping scans ----------------------------------------------------------------


def test_cancelling_kills_prowler_and_what_it_started(client, settings):
    job = start(client, azure_scan(excluded_checks=["fake_mode_sleep"]))
    child_pid_file = settings.work_dir / job["job_id"] / "child.pid"
    wait_for_file(child_pid_file)
    child_pid = int(child_pid_file.read_text())
    response = client.delete(f"/v1/scans/{job['job_id']}")
    assert response.status_code == 204
    assert process_gone(child_pid)
    assert not (settings.work_dir / job["job_id"]).exists()
    assert client.get(f"/v1/scans/{job['job_id']}").status_code == 404


def test_a_scan_past_its_time_limit_is_stopped(make_client, settings):
    client = make_client(with_settings(settings, scan_timeout=2))
    job = start(client, azure_scan(excluded_checks=["fake_mode_sleep"]))
    child_pid_file = settings.work_dir / job["job_id"] / "child.pid"
    wait_for_file(child_pid_file)
    child_pid = int(child_pid_file.read_text())
    done = wait_for(client, job["job_id"], timeout=30)
    assert done["status"] == "failed"
    assert done["error"]["code"] == "timeout"
    assert process_gone(child_pid)


def test_the_runner_refuses_more_scans_than_it_may_run(make_client, settings):
    client = make_client(with_settings(settings, max_concurrent=1))
    first = start(client, azure_scan(excluded_checks=["fake_mode_sleep"]))
    second = client.post("/v1/scans", json=azure_scan())
    assert second.status_code == 429
    assert second.json()["code"] == "busy"
    assert client.delete(f"/v1/scans/{first['job_id']}").status_code == 204
    assert client.post("/v1/scans", json=azure_scan()).status_code == 202


def test_finished_scans_are_kept_up_to_a_limit(make_client, settings):
    client = make_client(with_settings(settings, max_jobs=1))
    job = start(client, azure_scan())
    wait_for(client, job["job_id"])
    refused = client.post("/v1/scans", json=azure_scan())
    assert refused.status_code == 429
    assert refused.json()["code"] == "too_many_jobs"


def test_old_finished_scans_are_forgotten(client, settings):
    job = start(client, azure_scan())
    wait_for(client, job["job_id"])
    manager = client.app.state.jobs
    assert client.portal.call(manager.reap, time.monotonic()) == 0
    assert client.portal.call(manager.reap, time.monotonic() + settings.job_ttl + 1) == 1
    assert client.get(f"/v1/scans/{job['job_id']}").status_code == 404
    assert not (settings.work_dir / job["job_id"]).exists()


@pytest.mark.parametrize("job_id", ["0" * 32, "not-a-job", "../" * 5, "A" * 32])
def test_unknown_scans(client, job_id):
    for path in ("", "/summary", "/findings", "/artifacts/html"):
        response = client.get(f"/v1/scans/{job_id}{path}")
        assert response.status_code == 404, path
    assert client.delete(f"/v1/scans/{job_id}").status_code == 404


def test_an_unknown_artifact_kind(client):
    job = start(client, azure_scan())
    wait_for(client, job["job_id"])
    assert client.get(f"/v1/scans/{job['job_id']}/artifacts/ocsf").status_code == 404


def test_startup_empties_the_work_directory_but_nothing_else(make_client, settings):
    settings.work_dir.mkdir(parents=True)
    leftover = settings.work_dir / ("a" * 32)
    (leftover / "secrets").mkdir(parents=True)
    (leftover / "secrets" / "gcp-service-account.json").write_text("{}")
    connection_dir = settings.work_dir / ("conn-" + "b" * 32)
    connection_dir.mkdir()
    unrelated = settings.work_dir / "not-ours.txt"
    unrelated.write_text("keep")
    make_client(settings)
    assert not leftover.exists()
    assert not connection_dir.exists()
    assert unrelated.read_text() == "keep"


def test_azure_secret_reaches_only_the_environment(client, settings):
    job = start(client, azure_scan())
    wait_for(client, job["job_id"])
    seen = invocation(settings, job["job_id"])
    assert seen["env"]["AZURE_CLIENT_SECRET"] == SECRET
    assert SECRET not in " ".join(seen["argv"])
