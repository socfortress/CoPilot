"""Cloud accounts (#1328): ``/api/cloud_assessment/{code}/accounts``.

Real router, real in-memory database, real request parsing; token decoding and user lookup are
replaced, copilot-prowler is a fake that keeps jobs by its rules (``cloud_assessment_support``).

Pinned here:
- the rules, pure: settings per provider (what applies, what's required), the credential each
  sign-in takes, the hint, the runner's request;
- admins add, change and delete accounts, by the token *and* the database role; analysts read and
  test; a portal user never; another customer's account is a 404, another customer a 403;
- the credential is write-only: encrypted at rest, in no response, no audit row, no log line; an
  update without one keeps it; without the key nothing is saved; a changed key is a 409;
- an AWS role's External ID is generated, unique, and no request sets or changes it;
- a connection test stores its verdict; a runner that can't be asked changes nothing, and a
  runner's 401 is never a CoPilot 401.
"""

import re
from pathlib import Path

import pytest
from loguru import logger

from app.cloud_assessment.models.cloud_assessment import CloudAssessmentAccount
from app.cloud_assessment.schema.cloud_assessment import AccountConfigIn
from app.cloud_assessment.schema.cloud_assessment import SecretIn
from app.cloud_assessment.services import accounts as svc
from app.cloud_assessment.services import crypto
from app.cloud_assessment.services import runner_client
from tests.cloud_assessment_support import AWS_KEYS
from tests.cloud_assessment_support import AWS_KEYS_ACCOUNT
from tests.cloud_assessment_support import AWS_ROLE
from tests.cloud_assessment_support import AZURE
from tests.cloud_assessment_support import CLIENT_SECRET
from tests.cloud_assessment_support import GCP
from tests.cloud_assessment_support import M365
from tests.cloud_assessment_support import ROLE_ARN
from tests.cloud_assessment_support import FakeRunner
from tests.cloud_assessment_support import as_user
from tests.cloud_assessment_support import gcp_key
from tests.cloud_assessment_support import run

BASE = "/cloud_assessment/{code}/accounts"
SECRETS = (AWS_KEYS["secret_access_key"], CLIENT_SECRET, "MIIBMIIB")


def no_secret_in(text: str) -> bool:
    return not any(secret in text for secret in SECRETS)


# --- the rules ------------------------------------------------------------------------------------


def test_a_role_needs_its_arn():
    with pytest.raises(svc.AccountProblem) as problem:
        svc.checked_config("aws", "role", AccountConfigIn())
    assert problem.value.detail == "role_arn is required for AWS accounts"


@pytest.mark.parametrize(
    ("provider", "auth", "config", "field"),
    [
        ("aws", "access_keys", {"role_arn": ROLE_ARN}, "role_arn"),
        ("aws", "role", {"role_arn": ROLE_ARN, "tenant_id": "72f988bf-86f1-41af-91ab-2d7cd011db47"}, "tenant_id"),
        (
            "azure",
            "client_secret",
            {
                "tenant_id": "72f988bf-86f1-41af-91ab-2d7cd011db47",
                "client_id": "72f988bf-86f1-41af-91ab-2d7cd011db47",
                "regions": ["eu-west-1"],
            },
            "regions",
        ),
        ("gcp", "service_account_key", {"tenant_domain": "acme.com"}, "tenant_domain"),
    ],
)
def test_a_setting_that_doesn_t_apply_is_refused(provider, auth, config, field):
    with pytest.raises(svc.AccountProblem) as problem:
        svc.checked_config(provider, auth, AccountConfigIn(**config))
    assert problem.value.detail.startswith(field)


def test_m365_needs_a_tenant_domain():
    config = AccountConfigIn(tenant_id=M365["config"]["tenant_id"], client_id=M365["config"]["client_id"])
    with pytest.raises(svc.AccountProblem) as problem:
        svc.checked_config("m365", "client_secret", config)
    assert "tenant_domain" in problem.value.detail


def test_a_sign_in_the_provider_doesn_t_take_is_refused():
    with pytest.raises(svc.AccountProblem):
        svc.checked_config("azure", "role", AccountConfigIn())


def test_lists_are_kept_once_each_and_empty_ones_dropped():
    config = svc.checked_config(
        "aws",
        "role",
        AccountConfigIn(role_arn=ROLE_ARN, regions=["eu-west-1", "eu-west-1", "us-east-1"], excluded_checks=[]),
    )
    assert config == {"role_arn": ROLE_ARN, "regions": ["eu-west-1", "us-east-1"]}


def test_an_update_keeps_what_copilot_filled_in():
    config = svc.checked_config("aws", "role", AccountConfigIn(role_arn=ROLE_ARN), keep={"external_id": "copilot-x", "role_arn": "old"})
    assert config == {"role_arn": ROLE_ARN, "external_id": "copilot-x"}


def test_aws_keys_come_in_pairs():
    with pytest.raises(svc.AccountProblem):
        svc.checked_secret("access_keys", SecretIn(access_key_id=AWS_KEYS["access_key_id"]))


def test_the_wrong_credential_for_the_sign_in_is_refused():
    with pytest.raises(svc.AccountProblem):
        svc.checked_secret("client_secret", SecretIn(**AWS_KEYS))


def test_a_session_key_is_refused():
    with pytest.raises(ValueError):
        SecretIn(access_key_id="ASIAABCDEFGHIJKLMNOP", secret_access_key=AWS_KEYS["secret_access_key"])


def test_a_gcp_key_keeps_only_the_checked_fields():
    secret = svc.checked_secret("service_account_key", SecretIn(service_account_key={**gcp_key(), "extra": "dropped"}))
    assert "extra" not in secret["service_account_key"]
    assert secret["service_account_key"]["token_uri"] == "https://oauth2.googleapis.com/token"


def test_a_gcp_key_sending_its_assertion_elsewhere_is_refused():
    with pytest.raises(ValueError):
        SecretIn(service_account_key=gcp_key(token_uri="https://evil.example/token"))


def test_hints_tell_credentials_apart_without_giving_them_away():
    assert svc.secret_hint("role", AWS_KEYS) == "…MNOP"
    assert svc.secret_hint("client_secret", {"client_secret": CLIENT_SECRET}) == "Abc…"
    assert svc.secret_hint("service_account_key", {"service_account_key": gcp_key()}) == "aaaaaaaa…"


def test_external_ids_are_unique_and_shaped_for_aws():
    ids = {svc.new_external_id() for _ in range(100)}
    assert len(ids) == 100
    assert all(re.fullmatch(r"copilot-[0-9a-f]{32}", value) for value in ids)


def test_a_schedule_needs_its_hour_and_weekday():
    assert svc.checked_schedule("off", 3, 2) == ("off", None, None)
    assert svc.checked_schedule("daily", 3, 2) == ("daily", 3, None)
    with pytest.raises(svc.AccountProblem):
        svc.checked_schedule("weekly", 3, None)
    with pytest.raises(svc.AccountProblem):
        svc.checked_schedule("daily", None, None)


def _account(**overrides) -> CloudAssessmentAccount:
    values = dict(
        id=1,
        customer_code="ACME",
        name="x",
        provider="aws",
        auth_method="role",
        config={"role_arn": ROLE_ARN, "external_id": "copilot-e"},
    )
    values.update(overrides)
    return CloudAssessmentAccount(**values)


def test_the_runner_request_for_an_aws_role():
    payload = svc.runner_payload(
        _account(config={"role_arn": ROLE_ARN, "external_id": "copilot-e", "regions": ["eu-west-1"], "timeout_seconds": 600}),
        AWS_KEYS,
    )
    assert payload == {
        "provider": "aws",
        "auth": {
            "method": "role",
            "role_arn": ROLE_ARN,
            "external_id": "copilot-e",
            "session_duration_seconds": 3600,
            "base_credentials": AWS_KEYS,
        },
        "scope": {"regions": ["eu-west-1"]},
        "options": {"excluded_checks": [], "excluded_services": [], "timeout_seconds": 600},
    }


def test_a_role_without_keys_uses_the_host_s_identity():
    assert "base_credentials" not in svc.runner_payload(_account(), None)["auth"]


def test_an_account_whose_credential_is_gone_says_so():
    with pytest.raises(crypto.CredentialCryptoError) as error:
        svc.runner_payload(_account(auth_method="access_keys", config={}), None)
    assert str(error.value) == "credential_missing"


# --- the routes -----------------------------------------------------------------------------------


@pytest.mark.parametrize("payload", [AWS_ROLE, AWS_KEYS_ACCOUNT, AZURE, M365, GCP])
def test_each_provider_saves_and_lists(payload, monkeypatch, audit_rows):
    async def scenario(world):
        saved = await world.add(payload)
        listed = await world.client.get(BASE.format(code="ACME"), headers=as_user("ana"))
        stored = await world.db.rows(CloudAssessmentAccount)
        return saved, listed, stored

    saved, listed, stored = run(scenario, monkeypatch)
    assert saved.status_code == 200, saved.text
    account = saved.json()["account"]
    assert account["provider"] == payload["provider"] and account["secret_configured"] is True
    assert [item["id"] for item in listed.json()["accounts"]] == [account["id"]]
    assert no_secret_in(saved.text) and no_secret_in(listed.text)
    assert stored[0].secret_ciphertext.startswith("gAAAA") and no_secret_in(stored[0].secret_ciphertext)
    assert [row.action for row in audit_rows] == ["cloud_assessment.account_create"]
    assert no_secret_in(str(audit_rows[0].new_value))


def test_an_aws_role_gets_a_generated_external_id_no_request_can_set(monkeypatch):
    async def scenario(world):
        smuggled = await world.add({**AWS_ROLE, "config": {**AWS_ROLE["config"], "external_id": "attacker-chosen"}})
        first = await world.add(AWS_ROLE)
        second = await world.add({**AWS_ROLE, "name": "Staging"})
        changed = await world.client.put(
            BASE.format(code="ACME") + f"/{first.json()['account']['id']}",
            json={"config": {"role_arn": ROLE_ARN, "external_id": "attacker-chosen"}},
            headers=as_user("admin"),
        )
        renamed = await world.client.put(
            BASE.format(code="ACME") + f"/{first.json()['account']['id']}",
            json={"config": {"role_arn": ROLE_ARN, "regions": ["us-east-1"]}},
            headers=as_user("admin"),
        )
        return smuggled, first.json()["account"], second.json()["account"], changed, renamed.json()["account"]

    smuggled, first, second, changed, renamed = run(scenario, monkeypatch)
    assert smuggled.status_code == 422 and changed.status_code == 422
    assert re.fullmatch(r"copilot-[0-9a-f]{32}", first["external_id"]) and first["external_id"] != second["external_id"]
    assert renamed["external_id"] == first["external_id"] and renamed["config"]["regions"] == ["us-east-1"]
    assert first["cloud_account"] == "123456789012"


def test_a_gcp_account_shows_the_key_s_project_and_email(monkeypatch):
    async def scenario(world):
        return (await world.add(GCP)).json()["account"]

    account = run(scenario, monkeypatch)
    assert account["cloud_account"] == "acme-prod-1"
    assert account["config"]["client_email"] == "prowler@acme-prod-1.iam.gserviceaccount.com"


@pytest.mark.parametrize(("who", "status"), [("ana", 403), ("portal", 403), ("demoted", 403)])
def test_only_an_admin_adds_an_account(who, status, monkeypatch):
    async def scenario(world):
        return await world.add(AWS_ROLE, who=who)

    answer = run(scenario, monkeypatch)
    assert answer.status_code == status


def test_an_analyst_reads_only_their_customers(monkeypatch):
    async def scenario(world):
        theirs = (await world.add(AWS_ROLE, code="GLOBEX")).json()["account"]
        listed = await world.client.get(BASE.format(code="GLOBEX"), headers=as_user("ana"))
        by_id = await world.client.get(BASE.format(code="ACME") + f"/{theirs['id']}", headers=as_user("ana"))
        return listed, by_id

    listed, by_id = run(scenario, monkeypatch)
    assert listed.status_code == 403
    assert by_id.status_code == 404  # another customer's account is the same 404 as none


def test_a_credential_isn_t_saved_without_the_key(monkeypatch):
    async def scenario(world):
        answer = await world.add(AZURE)
        return answer, await world.db.rows(CloudAssessmentAccount)

    answer, stored = run(scenario, monkeypatch, key=False)
    assert answer.status_code == 400 and crypto.KEY_ENV_VAR in answer.json()["detail"] and stored == []


def test_an_account_needs_its_credential(monkeypatch):
    async def scenario(world):
        return await world.add({**AZURE, "secret": None})

    answer = run(scenario, monkeypatch)
    assert answer.status_code == 422 and answer.json()["detail"] == "enter the account's credential"


def test_an_update_without_a_credential_keeps_it_and_one_with_replaces_it(monkeypatch, audit_rows):
    async def scenario(world):
        account = (await world.add(AZURE)).json()["account"]
        url = BASE.format(code="ACME") + f"/{account['id']}"
        before = (await world.db.account(account["id"])).secret_ciphertext
        renamed = await world.client.put(url, json={"name": "Azure prod"}, headers=as_user("admin"))
        kept = (await world.db.account(account["id"])).secret_ciphertext
        replaced = await world.client.put(url, json={"secret": {"client_secret": "Xyz-new-secret"}}, headers=as_user("admin"))
        after = await world.db.account(account["id"])
        return before, renamed.json()["account"], kept, replaced.json()["account"], crypto.decrypt_secret(after.secret_ciphertext)

    before, renamed, kept, replaced, secret = run(scenario, monkeypatch)
    assert renamed["name"] == "Azure prod" and kept == before
    assert replaced["secret_hint"] == "Xyz…" and secret == {"client_secret": "Xyz-new-secret"}
    updates = [row for row in audit_rows if row.action == "cloud_assessment.account_update"]
    assert [row.new_value["secret_changed"] for row in updates] == [False, True]
    assert updates[0].old_value["name"] == "Azure" and updates[0].new_value["name"] == "Azure prod"


def test_a_save_that_changes_nothing_writes_nothing(monkeypatch, audit_rows):
    async def scenario(world):
        account = (await world.add(AZURE)).json()["account"]
        return await world.client.put(BASE.format(code="ACME") + f"/{account['id']}", json={"name": "Azure"}, headers=as_user("admin"))

    answer = run(scenario, monkeypatch)
    assert answer.status_code == 200
    assert [row.action for row in audit_rows] == ["cloud_assessment.account_create"]


def test_only_a_role_can_do_without_its_keys(monkeypatch):
    async def scenario(world):
        role = (await world.add(AWS_ROLE)).json()["account"]
        keys = (await world.add(AWS_KEYS_ACCOUNT)).json()["account"]
        dropped = await world.client.put(
            BASE.format(code="ACME") + f"/{role['id']}",
            json={"remove_secret": True},
            headers=as_user("admin"),
        )
        refused = await world.client.put(
            BASE.format(code="ACME") + f"/{keys['id']}",
            json={"remove_secret": True},
            headers=as_user("admin"),
        )
        return dropped.json()["account"], refused

    dropped, refused = run(scenario, monkeypatch)
    assert dropped["secret_configured"] is False and dropped["secret_hint"] is None
    assert refused.status_code == 422


def test_names_are_unique_per_customer_and_clean(monkeypatch):
    async def scenario(world):
        await world.add(AWS_ROLE)
        again = await world.add(AWS_ROLE)
        elsewhere = await world.add(AWS_ROLE, code="GLOBEX")
        hidden = await world.add({**AWS_ROLE, "name": "Prod\u202eevil"})
        return again, elsewhere, hidden

    again, elsewhere, hidden = run(scenario, monkeypatch)
    assert again.status_code == 409 and elsewhere.status_code == 200 and hidden.status_code == 422


def test_a_schedule_is_saved_and_its_next_run_shown(monkeypatch):
    async def scenario(world):
        account = (await world.add({**AWS_ROLE, "schedule": "weekly", "schedule_hour": 2, "schedule_weekday": 6})).json()["account"]
        off = await world.client.put(BASE.format(code="ACME") + f"/{account['id']}", json={"schedule": "off"}, headers=as_user("admin"))
        return account, off.json()["account"]

    weekly, off = run(scenario, monkeypatch)
    assert (weekly["schedule"], weekly["schedule_hour"], weekly["schedule_weekday"]) == ("weekly", 2, 6)
    assert weekly["next_scheduled_at"].endswith("T02:00:00Z")
    assert (off["schedule"], off["schedule_hour"], off["next_scheduled_at"]) == ("off", None, None)


def test_the_key_changing_is_a_409_asking_to_re_enter_the_credential(monkeypatch):
    async def scenario(world):
        account = (await world.add(AZURE)).json()["account"]
        from cryptography.fernet import Fernet

        monkeypatch.setenv(crypto.KEY_ENV_VAR, Fernet.generate_key().decode())
        return await world.client.post(BASE.format(code="ACME") + f"/{account['id']}/test", headers=as_user("ana"))

    answer = run(scenario, monkeypatch)
    assert answer.status_code == 409 and "Re-enter" in answer.json()["detail"]


def test_a_connection_test_sends_the_credential_and_keeps_the_verdict(monkeypatch, audit_rows):
    runner = FakeRunner()

    async def scenario(world):
        account = (await world.add(M365)).json()["account"]
        passed = await world.client.post(BASE.format(code="ACME") + f"/{account['id']}/test", headers=as_user("ana"))
        runner.connection_verdict = {
            "ok": False,
            "code": "m365_powershell_failed",
            "message": "x",
            "prowler_error": "ExchangeConnectionError",
        }
        failed = await world.client.post(BASE.format(code="ACME") + f"/{account['id']}/test", headers=as_user("ana"))
        return passed.json(), failed.json()

    passed, failed = run(scenario, monkeypatch, runner=runner)
    assert passed["ok"] is True and passed["account"]["last_connection_ok"] is True
    sent = runner.bodies[0]
    assert sent["auth"] == {
        "method": "client_secret",
        "tenant_id": M365["config"]["tenant_id"],
        "client_id": M365["config"]["client_id"],
        "client_secret": CLIENT_SECRET,
    }
    assert sent["scope"] == {"tenant_domain": "acme.onmicrosoft.com"}
    assert failed["ok"] is False and failed["code"] == "m365_powershell_failed" and failed["prowler_error"] == "ExchangeConnectionError"
    assert "Exchange.ManageAsApp" in failed["error_message"]
    assert failed["account"]["last_connection_error"] == "m365_powershell_failed"
    tests = [row for row in audit_rows if row.action == "cloud_assessment.connection_test"]
    assert [row.result for row in tests] == ["success", "failure"] and no_secret_in(str([row.new_value for row in tests]))


@pytest.mark.parametrize(("break_it", "status"), [("unreachable", 502), ("token", 502), ("no_token", 503)])
def test_a_runner_that_can_t_be_asked_changes_nothing(break_it, status, monkeypatch):
    runner = FakeRunner()

    async def scenario(world):
        account = (await world.add(AZURE)).json()["account"]
        if break_it == "unreachable":
            runner.unreachable = True
        elif break_it == "token":
            monkeypatch.setenv("PROWLER_RUNNER_TOKEN", "w" * 40)
        else:
            monkeypatch.setenv("PROWLER_RUNNER_TOKEN", "short")
        answer = await world.client.post(BASE.format(code="ACME") + f"/{account['id']}/test", headers=as_user("ana"))
        return answer, await world.db.account(account["id"])

    answer, stored = run(scenario, monkeypatch, runner=runner)
    assert answer.status_code == status  # never a 401: the frontend would end the analyst's session
    assert stored.last_connection_test_at is None and stored.last_connection_ok is None


def test_deleting_an_account_takes_its_scans_and_stops_a_running_one(monkeypatch, audit_rows):
    runner = FakeRunner()

    async def scenario(world):
        account = (await world.add(AWS_ROLE)).json()["account"]
        started = (await world.client.post(BASE.format(code="ACME") + f"/{account['id']}/scans", headers=as_user("ana"))).json()["scan"]
        analyst = await world.client.delete(BASE.format(code="ACME") + f"/{account['id']}", headers=as_user("ana"))
        deleted = await world.client.delete(BASE.format(code="ACME") + f"/{account['id']}", headers=as_user("admin"))
        from app.cloud_assessment.models.cloud_assessment import CloudAssessmentScan

        return started, analyst, deleted, await world.db.rows(CloudAssessmentAccount), await world.db.rows(CloudAssessmentScan)

    started, analyst, deleted, accounts_left, scans_left = run(scenario, monkeypatch, runner=runner)
    assert started["status"] == "running"
    assert analyst.status_code == 403
    assert deleted.status_code == 200 and deleted.json()["scans_deleted"] == 1
    assert accounts_left == [] and scans_left == []
    assert runner.deleted  # the runner was told to stop the scan
    assert audit_rows[-1].action == "cloud_assessment.account_delete" and audit_rows[-1].old_value["scans"] == 1


def test_no_credential_reaches_a_log_line(monkeypatch):
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="DEBUG")
    runner = FakeRunner()
    runner.connection_verdict = {"ok": False, "code": "auth_failed", "message": "x", "prowler_error": "ClientAuthenticationError"}
    try:

        async def scenario(world):
            for payload in (AWS_ROLE, AZURE, GCP):
                account = (await world.add(payload)).json()["account"]
                await world.client.post(BASE.format(code="ACME") + f"/{account['id']}/test", headers=as_user("admin"))
                if payload is GCP:
                    runner.start_error = (422, "invalid_request")  # a refused scan is logged
                await world.client.post(BASE.format(code="ACME") + f"/{account['id']}/scans", headers=as_user("admin"))
            runner.findings.append("not json")  # a skipped line is logged
            runner.finish(next(iter(runner.jobs)))
            await world.tick()

        run(scenario, monkeypatch, runner=runner)
    finally:
        logger.remove(sink)
    ours = [line for line in lines if "Cloud assessment" in line]
    assert len(ours) >= 2, lines
    assert no_secret_in("\n".join(lines))


def test_routes_that_act_refuse_the_talon_service_account(monkeypatch):
    async def scenario(world):
        account = (await world.add(AWS_ROLE)).json()["account"]
        url = BASE.format(code="ACME") + f"/{account['id']}"
        read = await world.client.get(url, headers=as_user("talon-analyst"))
        test = await world.client.post(url + "/test", headers=as_user("talon-analyst"))
        scan = await world.client.post(url + "/scans", headers=as_user("talon-analyst"))
        return read, test, scan

    read, test, scan = run(scenario, monkeypatch)
    assert read.status_code == 200 and test.status_code == 403 and scan.status_code == 403


def test_the_test_route_gets_longer_than_the_backend_waits_in_nginx():
    """nginx's default 60 s would answer 504 before a slow connection test does."""
    conf = (Path(__file__).resolve().parents[2] / "frontend" / "build" / "etc" / "nginx" / "sites-enabled" / "default.conf").read_text()
    found = re.search(r"location ~ (\^/api/cloud_assessment/[^\s]+test\$) \{\s*proxy_read_timeout (\d+)s;", conf)
    assert found, "the frontend nginx needs a location for the connection test"
    pattern, timeout = re.compile(found.group(1)), int(found.group(2))
    assert timeout > runner_client.CONNECTION_TEST_TIMEOUT
    assert pattern.match("/api/cloud_assessment/ACME/accounts/12/test")
    assert not pattern.match("/api/cloud_assessment/ACME/accounts/12/scans")
