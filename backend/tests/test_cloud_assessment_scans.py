"""Scans (#1328): starting, following, storing, cancelling, deleting, schedules, retention, and
reading the results back (checks, findings, compliance, reports).

Real router and services on an in-memory database; copilot-prowler and MinIO are fakes
(``cloud_assessment_support``). The job is ``run_tick``, called directly.

Pinned here:
- a scan goes queued → running → completed with one runner job, and only one scan per account is
  under way; a busy or unreachable runner leaves it queued, a refusal fails it with the runner's code;
- a completed scan's counts, checks, findings and reports are stored once (a second attempt replaces
  the first), the runner's copy is deleted, and the next scan marks what's new and what was resolved;
- a job the runner lost, a dead backend's half-done step, a failed or cancelled job all end right;
- schedules queue one scan a slot, never at once when set, never for a disabled account;
- retention prunes findings and reports past the kept scans and keeps their counts;
- text from the customer's cloud is cleaned before it is stored;
- a report is a download (attachment, sandboxed), audited.
"""

import hashlib
from datetime import timedelta

import pytest

from app.cloud_assessment.models.cloud_assessment import CloudAssessmentCheckResult
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentFinding
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentScan
from app.cloud_assessment.services import ingest
from app.cloud_assessment.services import scans as scan_service
from app.cloud_assessment.utils import utc_now
from tests.cloud_assessment_support import AWS_KEYS
from tests.cloud_assessment_support import AWS_ROLE
from tests.cloud_assessment_support import CATALOG
from tests.cloud_assessment_support import FakeMinio
from tests.cloud_assessment_support import FakeRunner
from tests.cloud_assessment_support import as_user
from tests.cloud_assessment_support import check
from tests.cloud_assessment_support import finding
from tests.cloud_assessment_support import run
from tests.cloud_assessment_support import summary

ACCOUNTS = "/cloud_assessment/ACME/accounts"
SCANS = "/cloud_assessment/ACME/scans"


async def add_account(world, **overrides) -> dict:
    answer = await world.add({**AWS_ROLE, **overrides})
    assert answer.status_code == 200, answer.text
    return answer.json()["account"]


async def start(world, account_id: int, who: str = "ana"):
    return await world.client.post(f"{ACCOUNTS}/{account_id}/scans", headers=as_user(who))


async def completed_scan(world, runner: FakeRunner) -> dict:
    account = await add_account(world)
    scan = (await start(world, account["id"])).json()["scan"]
    runner.finish(next(iter(runner.jobs)))
    await world.tick()
    return {"account": account, "scan": (await world.client.get(f"{SCANS}/{scan['id']}", headers=as_user("ana"))).json()["scan"]}


# --- starting -------------------------------------------------------------------------------------


def test_a_scan_starts_at_once_with_the_decrypted_credential(monkeypatch, audit_rows):
    runner = FakeRunner()

    async def scenario(world):
        account = await add_account(world)
        answer = await start(world, account["id"])
        again = await start(world, account["id"])
        return account, answer, again

    account, answer, again = run(scenario, monkeypatch, runner=runner)
    assert answer.status_code == 200 and answer.json()["scan"]["status"] == "running"
    sent = next(body for body in runner.bodies if body and body.get("auth"))
    assert sent["auth"]["base_credentials"] == AWS_KEYS and sent["auth"]["external_id"] == account["external_id"]
    assert sent["scope"] == {"regions": ["eu-west-1"]}
    assert again.status_code == 409  # one scan of an account at a time
    assert [row.action for row in audit_rows if row.action.startswith("cloud_assessment.scan")] == ["cloud_assessment.scan_start"]


def test_a_busy_runner_leaves_the_scan_queued_until_the_job_starts_it(monkeypatch):
    runner = FakeRunner()
    runner.start_error = (429, "busy")

    async def scenario(world):
        account = await add_account(world)
        queued = (await start(world, account["id"])).json()["scan"]
        runner.start_error = None
        await world.tick()
        return queued, await world.db.scan(queued["id"])

    queued, after = run(scenario, monkeypatch, runner=runner)
    assert queued["status"] == "queued" and queued["started_at"] is None
    assert after.status == "running" and after.runner_job_id


def test_a_refused_scan_fails_with_the_runner_s_code(monkeypatch):
    runner = FakeRunner()
    runner.start_error = (422, "invalid_request")

    async def scenario(world):
        account = await add_account(world)
        return (await start(world, account["id"])).json()["scan"]

    scan = run(scenario, monkeypatch, runner=runner)
    assert scan["status"] == "failed" and scan["error_code"] == "invalid_request" and scan["error_message"] == "The request is not valid."


def test_a_disabled_account_isn_t_scanned(monkeypatch):
    async def scenario(world):
        account = await add_account(world, enabled=False)
        return await start(world, account["id"])

    assert run(scenario, monkeypatch).status_code == 409


def test_a_scan_needs_the_runner_set_up(monkeypatch):
    async def scenario(world):
        account = await add_account(world)
        monkeypatch.setenv("PROWLER_RUNNER_TOKEN", "")
        answer = await start(world, account["id"])
        return answer, await world.db.rows(CloudAssessmentScan)

    answer, stored = run(scenario, monkeypatch)
    assert answer.status_code == 503 and "PROWLER_RUNNER_TOKEN" in answer.json()["detail"] and stored == []


# --- following and storing ------------------------------------------------------------------------


def test_a_completed_scan_is_stored_and_the_runner_s_copy_deleted(monkeypatch):
    runner = FakeRunner()
    minio = FakeMinio()

    async def scenario(world):
        done = await completed_scan(world, runner)
        checks = await world.db.rows(CloudAssessmentCheckResult)
        findings = await world.db.rows(CloudAssessmentFinding)
        return done["scan"], checks, findings, await world.db.scan(done["scan"]["id"])

    scan, checks, findings, row = run(scenario, monkeypatch, runner=runner, minio=minio)
    assert scan["status"] == "completed" and scan["prowler_version"] == "5.52.0"
    assert scan["counts"]["total"] == 10 and scan["counts"]["failed"] == 3 and scan["counts"]["failed_critical"] == 1
    assert scan["counts"]["new_failed"] == 0 and scan["counts"]["resolved_failed"] == 0  # a first scan marks nothing new
    assert sorted(c.check_id for c in checks) == ["iam_root_mfa_enabled", "s3_bucket_public"]
    assert checks[0].remediation_urls == ["https://hub.prowler.com/check/" + checks[0].check_id]  # javascript: dropped
    assert len(findings) == 3 and not any(f.is_new for f in findings)
    assert scan["reports"] == ["html", "csv"]
    html = minio.objects[("cloud-assessment", row.html_object_key)]
    assert html == runner.artifacts["html"] and row.html_file_hash == hashlib.sha256(html).hexdigest() and row.html_file_size == len(html)
    assert runner.jobs == {} and len(runner.deleted) == 1


def test_the_next_scan_marks_new_carried_and_resolved_findings(monkeypatch):
    runner = FakeRunner()

    async def scenario(world):
        done = await completed_scan(world, runner)
        first = {f.finding_uid_hash: f for f in await world.db.rows(CloudAssessmentFinding)}
        # finding 1 still fails, 2 is fixed, 3 is now muted, 4 is new
        runner.findings = [finding(1), finding(3, check_id="s3_bucket_public", severity="critical", muted=True), finding(4)]
        second = (await start(world, done["account"]["id"])).json()["scan"]
        runner.finish(next(iter(runner.jobs)))
        await world.tick(now=utc_now() + timedelta(seconds=5))
        rows = await world.db.rows(CloudAssessmentFinding, CloudAssessmentFinding.scan_id == second["id"])
        return first, {f.resource_name: f for f in rows}, await world.db.scan(second["id"])

    first, second, scan = run(scenario, monkeypatch, runner=runner)
    carried = second["resource1"]
    assert carried.is_new is False and carried.first_seen_at == first[carried.finding_uid_hash].first_seen_at
    assert second["resource4"].is_new is True
    assert scan.new_fail_count == 1  # resource4 (a muted failure isn't news)
    assert scan.resolved_fail_count == 1  # resource2; resource3 is muted, not fixed


def test_new_and_resolved_count_distinct_ids(monkeypatch):
    """Prowler repeats a finding's id within one scan for some checks (live: API Gateway's per-stage
    checks, 237 findings and 229 ids): both rows are stored, and each id counts once."""
    runner = FakeRunner()

    async def scenario(world):
        done = await completed_scan(world, runner)
        twice = finding(7, uid="prowler-aws-apigateway_restapi_logging_enabled-123456789012-us-east-1-api")
        runner.findings = [finding(1), twice, dict(twice, resource_name="api-stage-2")]
        second = (await start(world, done["account"]["id"])).json()["scan"]
        runner.finish(next(iter(runner.jobs)))
        await world.tick()
        rows = await world.db.rows(CloudAssessmentFinding, CloudAssessmentFinding.scan_id == second["id"])
        return rows, await world.db.scan(second["id"])

    rows, scan = run(scenario, monkeypatch, runner=runner)
    assert len(rows) == 3 and sum(row.is_new for row in rows) == 2
    assert scan.new_fail_count == 1 and scan.resolved_fail_count == 2


def test_a_second_attempt_replaces_the_first(monkeypatch):
    runner = FakeRunner()

    async def scenario(world):
        account = await add_account(world)
        scan = (await start(world, account["id"])).json()["scan"]
        job_id = next(iter(runner.jobs))
        runner.finish(job_id)
        async with world.db.factory() as session:
            # As if an earlier attempt had stored part of it and died.
            await session.execute(
                CloudAssessmentScan.__table__.update().where(CloudAssessmentScan.id == scan["id"]).values(status="running"),
            )
            session.add(CloudAssessmentCheckResult(scan_id=scan["id"], check_id="stale_check", severity="low"))
            await session.commit()
        await world.tick()
        return await world.db.rows(CloudAssessmentCheckResult)

    checks = run(scenario, monkeypatch, runner=runner)
    assert sorted(c.check_id for c in checks) == ["iam_root_mfa_enabled", "s3_bucket_public"]


@pytest.mark.parametrize(("status", "code", "expected"), [("failed", "auth_failed", "failed"), ("cancelled", "cancelled", "cancelled")])
def test_a_job_that_ended_badly_ends_the_scan(status, code, expected, monkeypatch):
    runner = FakeRunner()

    async def scenario(world):
        account = await add_account(world)
        scan = (await start(world, account["id"])).json()["scan"]
        runner.finish(next(iter(runner.jobs)), status=status, error=code, prowler_errors=["AWSAssumeRoleError"])
        await world.tick()
        return (await world.client.get(f"{SCANS}/{scan['id']}", headers=as_user("ana"))).json()["scan"]

    scan = run(scenario, monkeypatch, runner=runner)
    assert scan["status"] == expected
    if expected == "failed":
        assert scan["error_code"] == "auth_failed" and scan["prowler_errors"] == ["AWSAssumeRoleError"]


def test_a_job_the_runner_lost_fails_the_scan(monkeypatch):
    runner = FakeRunner()

    async def scenario(world):
        account = await add_account(world)
        scan = (await start(world, account["id"])).json()["scan"]
        runner.jobs.clear()  # copilot-prowler restarted
        await world.tick()
        return await world.db.scan(scan["id"])

    scan = run(scenario, monkeypatch, runner=runner)
    assert scan.status == "failed" and scan.error_code == "results_lost"


def test_an_unreachable_runner_is_waited_for_then_given_up_on(monkeypatch):
    runner = FakeRunner()

    async def scenario(world):
        account = await add_account(world)
        scan = (await start(world, account["id"])).json()["scan"]
        runner.unreachable = True
        await world.tick()
        waiting = (await world.db.scan(scan["id"])).status
        await world.tick(now=utc_now() + scan_service.RUNNER_SILENCE_LIMIT + timedelta(minutes=1))
        return waiting, await world.db.scan(scan["id"])

    waiting, scan = run(scenario, monkeypatch, runner=runner)
    assert waiting == "running" and scan.status == "failed" and scan.error_code == "runner_unreachable"


def test_results_that_can_t_be_stored_fail_the_scan_rather_than_loop(monkeypatch):
    runner = FakeRunner()

    async def broken(self):
        raise RuntimeError("boom")

    async def scenario(world):
        account = await add_account(world)
        scan = (await start(world, account["id"])).json()["scan"]
        runner.finish(next(iter(runner.jobs)))
        monkeypatch.setattr(ingest.Ingestion, "_store_reports", broken)
        await world.tick()
        return await world.db.scan(scan["id"]), await world.db.rows(CloudAssessmentFinding)

    scan, findings = run(scenario, monkeypatch, runner=runner)
    assert scan.status == "failed" and scan.error_code == "ingest_failed" and findings == []


def test_a_failure_is_logged_by_its_class_never_its_text(monkeypatch):
    """A database error's text carries the statement's values: findings from a customer's cloud."""
    from loguru import logger

    from app.schedulers.services import invoke_cloud_assessment as job

    runner = FakeRunner()
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="DEBUG")

    async def leaky(self):
        raise RuntimeError("INSERT … ('arn:aws:iam::123456789012:user/payroll-admin')")

    async def failing_tick():
        raise RuntimeError("token=hunter2")

    try:

        async def scenario(world):
            account = await add_account(world)
            await start(world, account["id"])
            runner.finish(next(iter(runner.jobs)))
            monkeypatch.setattr(ingest.Ingestion, "_store_reports", leaky)
            await world.tick()
            monkeypatch.setattr(job, "run_tick", failing_tick)
            await job.invoke_cloud_assessment()

        run(scenario, monkeypatch, runner=runner)
    finally:
        logger.remove(sink)
    logged = "\n".join(lines)
    assert "storing scan 1's results failed: RuntimeError" in logged and "the tick failed: RuntimeError" in logged
    assert "payroll-admin" not in logged and "hunter2" not in logged


def test_a_dead_backend_s_half_done_steps_are_recovered(monkeypatch):
    async def scenario(world):
        account = await add_account(world)
        long_ago = utc_now() - timedelta(hours=2)
        async with world.db.factory() as session:
            session.add_all(
                [
                    CloudAssessmentScan(
                        account_id=account["id"],
                        customer_code="ACME",
                        status="starting",
                        trigger_type="manual",
                        queued_at=long_ago,
                        started_at=long_ago,
                    ),
                    CloudAssessmentScan(
                        account_id=account["id"],
                        customer_code="ACME",
                        status="ingesting",
                        trigger_type="manual",
                        queued_at=long_ago,
                        started_at=long_ago,
                        completed_at=long_ago,
                        runner_job_id="0" * 32,
                    ),
                ],
            )
            await session.commit()
        async with world.db.factory() as session:
            await scan_service.recover_stale(session, utc_now())
        return await world.db.rows(CloudAssessmentScan)

    starting, ingesting = run(scenario, monkeypatch)
    assert (starting.status, starting.error_code) == ("failed", "dispatch_lost")
    assert (ingesting.status, ingesting.completed_at) == ("running", None)


def test_ingestion_cleans_what_the_cloud_said(monkeypatch):
    runner = FakeRunner()
    runner.findings = [
        finding(1, resource_name="evil\x07name\ud800", status_extended="line\x1b[31m"),
        finding(2, check_id="NOT A CHECK"),
        finding(3, status="PASS"),
        {"finding_uid": "x", "finding_uid_sha256": "nothex", "check_id": "iam_x", "status": "FAIL"},
        "not json",
        finding(4, severity="catastrophic", resource_uid="r" * 5000),
    ]

    async def scenario(world):
        await completed_scan(world, runner)
        return {f.resource_name: f for f in await world.db.rows(CloudAssessmentFinding)}

    stored = run(scenario, monkeypatch, runner=runner)
    assert sorted(stored) == ["evilname�", "resource4"]
    assert stored["evilname�"].status_extended == "line[31m"
    assert stored["resource4"].severity == "unknown" and len(stored["resource4"].resource_uid) == 1024


def test_findings_none_of_which_can_be_read_fail_the_scan(monkeypatch):
    """A copilot-prowler older than CoPilot (found live: an image from before ``finding_uid_sha256``)
    sends findings CoPilot can't match across scans. A scan that completed with 238 failures counted
    and none listed would mislead: it fails, and nothing of it is kept."""
    runner = FakeRunner()
    minio = FakeMinio()
    runner.findings = [{key: value for key, value in finding(index).items() if key != "finding_uid_sha256"} for index in range(1, 4)]

    async def scenario(world):
        account = await add_account(world)
        scan = (await start(world, account["id"])).json()["scan"]
        runner.finish(next(iter(runner.jobs)))
        await world.tick()
        answer = (await world.client.get(f"{SCANS}/{scan['id']}", headers=as_user("ana"))).json()["scan"]
        return answer, await world.db.rows(CloudAssessmentFinding), await world.db.rows(CloudAssessmentCheckResult)

    scan, findings, checks = run(scenario, monkeypatch, runner=runner, minio=minio)
    assert scan["status"] == "failed" and scan["error_code"] == "findings_unreadable"
    assert "same CoPilot version" in scan["error_message"]
    assert findings == [] and checks == [] and minio.objects == {} and runner.jobs == {}


def test_a_report_that_can_t_be_kept_doesn_t_fail_the_scan(monkeypatch):
    runner = FakeRunner()
    minio = FakeMinio()
    minio.fail_put = True

    async def scenario(world):
        return (await completed_scan(world, runner))["scan"]

    scan = run(scenario, monkeypatch, runner=runner, minio=minio)
    assert scan["status"] == "completed" and scan["reports"] == []


def test_findings_past_the_cap_are_counted_not_stored(monkeypatch):
    runner = FakeRunner()
    runner.findings = [finding(index) for index in range(1, 1206)]
    monkeypatch.setenv("CLOUD_ASSESSMENT_MAX_FINDINGS", "1000")

    async def scenario(world):
        done = await completed_scan(world, runner)
        return done["scan"], await world.db.rows(CloudAssessmentFinding)

    scan, findings = run(scenario, monkeypatch, runner=runner)
    assert scan["status"] == "completed" and len(findings) == 1000


# --- cancelling and deleting ----------------------------------------------------------------------


def test_cancelling_a_running_scan_stops_the_runner_s_job(monkeypatch, audit_rows):
    runner = FakeRunner()

    async def scenario(world):
        account = await add_account(world)
        scan = (await start(world, account["id"])).json()["scan"]
        cancelled = await world.client.post(f"{SCANS}/{scan['id']}/cancel", headers=as_user("ana"))
        again = await world.client.post(f"{SCANS}/{scan['id']}/cancel", headers=as_user("ana"))
        return cancelled, again

    cancelled, again = run(scenario, monkeypatch, runner=runner)
    assert cancelled.status_code == 200 and cancelled.json()["scan"]["status"] == "cancelled"
    assert runner.deleted and again.status_code == 409
    assert audit_rows[-1].action == "cloud_assessment.scan_cancel" and audit_rows[-1].old_value == {"status": "running"}


def test_cancelling_a_queued_scan_needs_no_runner(monkeypatch):
    runner = FakeRunner()
    runner.start_error = (429, "busy")

    async def scenario(world):
        account = await add_account(world)
        scan = (await start(world, account["id"])).json()["scan"]
        runner.unreachable = True
        return await world.client.post(f"{SCANS}/{scan['id']}/cancel", headers=as_user("ana"))

    assert run(scenario, monkeypatch, runner=runner).json()["scan"]["status"] == "cancelled"


def test_a_scan_is_deleted_by_an_admin_once_it_has_ended(monkeypatch, audit_rows):
    runner = FakeRunner()
    minio = FakeMinio()

    async def scenario(world):
        account = await add_account(world)
        scan = (await start(world, account["id"])).json()["scan"]
        while_running = await world.client.delete(f"{SCANS}/{scan['id']}", headers=as_user("admin"))
        runner.finish(next(iter(runner.jobs)))
        await world.tick()
        by_analyst = await world.client.delete(f"{SCANS}/{scan['id']}", headers=as_user("ana"))
        deleted = await world.client.delete(f"{SCANS}/{scan['id']}", headers=as_user("admin"))
        return while_running, by_analyst, deleted, await world.db.rows(CloudAssessmentScan), await world.db.rows(CloudAssessmentFinding)

    while_running, by_analyst, deleted, scans_left, findings_left = run(scenario, monkeypatch, runner=runner, minio=minio)
    assert while_running.status_code == 409 and by_analyst.status_code == 403 and deleted.status_code == 200
    assert scans_left == [] and findings_left == [] and minio.objects == {}
    assert audit_rows[-1].action == "cloud_assessment.scan_delete"


# --- schedules ------------------------------------------------------------------------------------


def test_a_schedule_queues_one_scan_a_slot_and_never_at_once(monkeypatch):
    runner = FakeRunner()

    async def scenario(world):
        account = await add_account(world, schedule="daily", schedule_hour=2)
        set_at = (await world.db.account(account["id"])).updated_at
        next_slot = set_at.replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=1)
        before = await world.tick(now=set_at + timedelta(minutes=1))
        at_slot = await world.tick(now=next_slot + timedelta(minutes=1))
        again = await world.tick(now=next_slot + timedelta(minutes=2))
        return before, at_slot, again, await world.db.rows(CloudAssessmentScan)

    before, at_slot, again, stored = run(scenario, monkeypatch, runner=runner)
    assert before["scheduled"] == 0 and at_slot["scheduled"] == 1 and again["scheduled"] == 0
    assert [(scan.trigger_type, scan.status) for scan in stored] == [("schedule", "running")]


def test_a_disabled_account_s_schedule_waits(monkeypatch):
    async def scenario(world):
        account = await add_account(world, schedule="daily", schedule_hour=2, enabled=False)
        set_at = (await world.db.account(account["id"])).updated_at
        return await world.tick(now=set_at + timedelta(days=2))

    assert run(scenario, monkeypatch)["scheduled"] == 0


# --- retention ------------------------------------------------------------------------------------


def test_retention_prunes_findings_past_the_kept_scans_and_keeps_their_counts(monkeypatch):
    runner = FakeRunner()
    minio = FakeMinio()
    monkeypatch.setenv("CLOUD_ASSESSMENT_KEEP_FINDINGS_SCANS", "1")

    async def scenario(world):
        done = await completed_scan(world, runner)
        first = done["scan"]
        second = (await start(world, done["account"]["id"])).json()["scan"]
        runner.finish(next(iter(runner.jobs)))
        monkeypatch.setattr(scan_service, "_last_retention", None)
        await world.tick()
        pruned = (await world.client.get(f"{SCANS}/{first['id']}", headers=as_user("ana"))).json()["scan"]
        gone = await world.client.get(f"{SCANS}/{first['id']}/findings", headers=as_user("ana"))
        checks = await world.client.get(f"{SCANS}/{first['id']}/checks", headers=as_user("ana"))
        kept = await world.client.get(f"{SCANS}/{second['id']}/findings", headers=as_user("ana"))
        return pruned, gone, checks, kept

    pruned, gone, checks, kept = run(scenario, monkeypatch, runner=runner, minio=minio)
    assert pruned["findings_pruned"] is True and pruned["counts"]["failed"] == 3 and pruned["reports"] == []
    assert gone.status_code == 410 and checks.json()["total"] == 2
    assert kept.json()["total"] == 3
    assert len(minio.objects) == 2  # only the newest scan's reports


def test_retention_deletes_scans_past_the_retention_period(monkeypatch):
    async def scenario(world):
        account = await add_account(world)
        old = utc_now() - timedelta(days=500)
        async with world.db.factory() as session:
            session.add(
                CloudAssessmentScan(account_id=account["id"], customer_code="ACME", status="failed", trigger_type="manual", queued_at=old),
            )
            await session.commit()
        async with world.db.factory() as session:
            removed = await scan_service.apply_retention(session, utc_now())
        return removed, await world.db.rows(CloudAssessmentScan)

    removed, left = run(scenario, monkeypatch)
    assert removed == 1 and left == []


# --- reading the results --------------------------------------------------------------------------


def test_findings_filter_and_page(monkeypatch):
    runner = FakeRunner()
    runner.findings = [finding(index, severity="high" if index % 2 else "low") for index in range(1, 8)] + [
        finding(9, check_id="s3_bucket_public", severity="critical"),
    ]

    async def scenario(world):
        scan = (await completed_scan(world, runner))["scan"]
        url = f"{SCANS}/{scan['id']}/findings"
        everything = (await world.client.get(url, params={"page_size": 3}, headers=as_user("ana"))).json()
        critical = (await world.client.get(url, params={"severity": ["critical"]}, headers=as_user("ana"))).json()
        searched = (await world.client.get(url, params={"q": "resource7"}, headers=as_user("ana"))).json()
        wildcard = (await world.client.get(url, params={"q": "%"}, headers=as_user("ana"))).json()
        bad = await world.client.get(url, params={"severity": ["sev1"]}, headers=as_user("ana"))
        return everything, critical, searched, wildcard, bad

    everything, critical, searched, wildcard, bad = run(scenario, monkeypatch, runner=runner)
    assert everything["total"] == 8 and len(everything["findings"]) == 3
    assert everything["findings"][0]["severity"] == "critical"  # worst first
    assert everything["findings"][0]["check_title"] == "Title of s3_bucket_public"
    assert critical["total"] == 1 and searched["total"] == 1 and wildcard["total"] == 0
    assert bad.status_code == 422


def test_checks_filter_by_status_and_list_their_services(monkeypatch):
    runner = FakeRunner()
    runner.summary = summary([check("iam_a", fail=1), check("iam_b", fail=0, passed=3), check("s3_c", fail=0, manual=2)])

    async def scenario(world):
        scan = (await completed_scan(world, runner))["scan"]
        url = f"{SCANS}/{scan['id']}/checks"
        return [
            (await world.client.get(url, params=params, headers=as_user("ana"))).json()
            for params in ({}, {"status": "fail"}, {"status": "pass"}, {"status": "manual"})
        ]

    every, failing, passing, manual = run(scenario, monkeypatch, runner=runner)
    assert every["total"] == 3 and every["services"] == ["iam", "s3"]
    assert [c["check_id"] for c in failing["checks"]] == ["iam_a"] and failing["checks"][0]["status"] == "fail"
    assert [c["check_id"] for c in passing["checks"]] == ["iam_b"] and [c["check_id"] for c in manual["checks"]] == ["s3_c"]


def test_compliance_uses_the_runner_s_catalog_and_works_without_it(monkeypatch):
    runner = FakeRunner()
    runner.summary = summary(
        [
            check("iam_root_mfa_enabled", fail=0, passed=1, compliance={"CIS-5.0": ["1.1"], "MITRE-ATTACK": ["T1078"]}),
            check("s3_bucket_public", fail=2, compliance={"CIS-5.0": ["2.1"]}),
        ],
    )

    async def scenario(world):
        scan = (await completed_scan(world, runner))["scan"]
        url = f"{SCANS}/{scan['id']}/compliance"
        overview = (await world.client.get(url, headers=as_user("ana"))).json()
        detail = (await world.client.get(f"{url}/CIS-5.0", headers=as_user("ana"))).json()
        missing = await world.client.get(f"{url}/HIPAA", headers=as_user("ana"))
        runner.unreachable = True
        from app.cloud_assessment.services import runner_client

        runner_client.clear_catalog_cache()
        without = (await world.client.get(url, headers=as_user("ana"))).json()
        return overview, detail, missing, without

    overview, detail, missing, without = run(scenario, monkeypatch, runner=runner)
    cis = next(f for f in overview["frameworks"] if f["key"] == "CIS-5.0")
    assert overview["catalog_available"] is True and cis["name"] == CATALOG["frameworks"][0]["name"]
    # 1.1 passes, 2.1 (not in the catalog) fails, 1.2's check didn't run and 1.3 has none: not assessed
    assert (cis["requirements_total"], cis["passed"], cis["failed"], cis["not_assessed"]) == (4, 1, 1, 2)
    statuses = {r["id"]: r["status"] for r in detail["requirements"]}
    assert statuses == {"1.1": "pass", "1.2": "not_assessed", "1.3": "not_assessed", "2.1": "fail"}
    assert next(r for r in detail["requirements"] if r["id"] == "1.2")["checks"][0]["ran"] is False
    assert missing.status_code == 404
    assert without["catalog_available"] is False
    assert next(f for f in without["frameworks"] if f["key"] == "CIS-5.0")["requirements_total"] == 2


def test_a_report_is_a_sandboxed_download_and_audited(monkeypatch, audit_rows):
    runner = FakeRunner()

    async def scenario(world):
        scan = (await completed_scan(world, runner))["scan"]
        html = await world.client.get(f"{SCANS}/{scan['id']}/reports/html", headers=as_user("ana"))
        other = await world.client.get(f"/cloud_assessment/GLOBEX/scans/{scan['id']}/reports/html", headers=as_user("admin"))
        return html, other

    html, other = run(scenario, monkeypatch, runner=runner)
    assert html.status_code == 200 and html.content == runner.artifacts["html"]
    assert html.headers["content-disposition"].startswith("attachment;")
    assert html.headers["content-security-policy"] == "sandbox" and html.headers["x-content-type-options"] == "nosniff"
    assert other.status_code == 404  # another customer's scan
    assert audit_rows[-1].action == "cloud_assessment.report_download" and audit_rows[-1].new_value == {"scan_id": 1, "kind": "html"}


def test_results_of_a_scan_under_way_are_a_409(monkeypatch):
    async def scenario(world):
        account = await add_account(world)
        scan = (await start(world, account["id"])).json()["scan"]
        return await world.client.get(f"{SCANS}/{scan['id']}/findings", headers=as_user("ana"))

    assert run(scenario, monkeypatch).status_code == 409


def test_the_scan_list_pages_newest_first(monkeypatch):
    runner = FakeRunner()

    async def scenario(world):
        account = await add_account(world)
        for _ in range(3):
            await start(world, account["id"])
            runner.finish(next(iter(runner.jobs)))
            await world.tick()
        listed = (await world.client.get(SCANS, params={"page_size": 2}, headers=as_user("ana"))).json()
        accounts = (await world.client.get(ACCOUNTS, headers=as_user("ana"))).json()["accounts"]
        return listed, accounts

    listed, accounts = run(scenario, monkeypatch, runner=runner)
    assert listed["total"] == 3 and [scan["id"] for scan in listed["scans"]] == [3, 2]
    assert listed["scans"][0]["account_name"] == "Production" and listed["scans"][0]["provider"] == "aws"
    assert accounts[0]["last_scan"]["id"] == 3 and accounts[0]["last_completed_scan"]["counts"]["failed"] == 3
