"""Phase 0 Sysmon sensor health: the agent.conf block, the vendored assets and the rollout order.

What is pinned here:
* the managed SYSMON-HEALTH block in the Windows template survives provisioning's placeholder substitution, and
  reconciling agent.conf is idempotent, removes hand-added duplicates (ignoring commented-out text) and leaves
  everything else as it is;
* vendored scripts/rules are refused when they do not match manifest.json;
* reads are three-way: a missing file, a Wazuh JSON error envelope and a failed read are told apart, and nothing is
  changed while any read failed;
* agent.conf is compared ignoring indentation, because the Wazuh API re-indents it when it stores it;
* the rollout never writes agent.conf before the rules and the scripts are in place, never installs rules (a
  manager restart) unless asked, rolls a rules file back (verified) on any failure before the restart, and a dry run
  writes nothing;
* the scripts are only ever sent to an authenticated sidecar over https.

No network: the Wazuh API and the WAZUH-UTILS sidecar are fakes that record each call.

Run with: cd backend && python -m pytest tests/test_sysmon_health.py
"""

import asyncio
import hashlib
import json
import os
import shutil

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.active_response.services import sysmon_health as sh  # noqa: E402
from app.customer_provisioning.services import wazuh_manager as provisioning  # noqa: E402

TEMPLATE = sh.WINDOWS_TEMPLATE.read_text()
BOTH = {sh.WATCHDOG_TAG, sh.RELOAD_TAG}

LAB_AGENT_CONF = """<agent_config>
  <labels>
    <label key="customer">lab</label>
  </labels>
    <wodle name="command">
      <disabled>no</disabled>
      <tag>sigcheck</tag>
      <command>Powershell.exe -executionpolicy bypass -File "C:\\Program Files (x86)\\ossec-agent\\active-response\\bin\\sigcheck.ps1"</command>
      <interval>1d</interval>
    </wodle>
    <!--
    <wodle name="command">
      <tag>sysmon-reload</tag>
      <command>old commented-out copy, must stay</command>
    </wodle>
    -->
    <wodle name="command">
      <disabled>no</disabled>
      <tag>sysmon-reload</tag>
      <command>"C:\\Program Files (x86)\\ossec-agent\\active-response\\bin\\run_sysmon_config_reload.cmd"</command>
      <interval>1d</interval>
      <ignore_output>yes</ignore_output>
      <run_on_start>yes</run_on_start>
      <timeout>0</timeout>
    </wodle>
    <wodle name="command">
      <disabled>no</disabled>
      <tag>sysmon-watchdog</tag>
      <command>powershell.exe -File "C:\\Program Files (x86)\\ossec-agent\\shared\\sysmon_watchdog.ps1"</command>
      <interval>5m</interval>
    </wodle>
  </agent_config>
"""


def run(coroutine):
    return asyncio.run(coroutine)


def reindent(text):
    """What the Wazuh API does to agent.conf on write (minidom toprettyxml): new indentation, no blank lines."""
    return "\n".join("  " + line.strip() for line in text.splitlines() if line.strip()) + "\n"


# --------------------------------------------------------------------------------------------------------------------
# Template block and agent.conf reconciliation (pure)
# --------------------------------------------------------------------------------------------------------------------


def test_template_block_has_both_wodles_and_no_provisioning_placeholders():
    block = sh.managed_block()
    assert sh.wodle_tags_present(block) == [sh.RELOAD_TAG, sh.WATCHDOG_TAG]
    # configure_wazuh_group replaces these two strings everywhere in the template.
    assert "REPLACE" not in block and "CLUSTER_NAME" not in block
    assert 'shared\\sysmon_watchdog.ps1"' in block and 'shared\\sysmon_config_reload.ps1"' in block
    # Nothing inside the block's comment may contain "--" (invalid in an XML comment).
    comment = block[: block.index("-->")]
    assert "--" not in comment[len("<!--") :]


def test_template_is_already_reconciled_for_both_wodles():
    assert sh.reconcile_agent_conf(TEMPLATE, BOTH) == TEMPLATE


@pytest.mark.parametrize("wanted", [set(), {sh.WATCHDOG_TAG}, {sh.RELOAD_TAG}, BOTH])
def test_reconcile_keeps_exactly_the_wanted_wodles_and_is_idempotent(wanted):
    once = sh.reconcile_agent_conf(TEMPLATE, wanted)
    assert sh.wodle_tags_present(once) == sorted(wanted)
    assert sh.reconcile_agent_conf(once, wanted) == once
    assert (sh.BLOCK_BEGIN in once) == bool(wanted)
    # Everything before the managed block is untouched.
    assert once.startswith(TEMPLATE[: TEMPLATE.find(sh.BLOCK_BEGIN)].rstrip("\n"))


def test_reconcile_replaces_hand_added_wodles_and_keeps_the_rest():
    updated = sh.reconcile_agent_conf(LAB_AGENT_CONF, BOTH)
    # One managed copy of each, at the end, in its own agent_config.
    assert sh.wodle_tags_present(updated) == [sh.RELOAD_TAG, sh.WATCHDOG_TAG]
    assert len(sh.tagged_wodles(updated)) == 2
    assert updated.endswith(sh.build_block(BOTH))
    assert "run_sysmon_config_reload.cmd" not in updated.split(sh.BLOCK_BEGIN)[0]
    assert "<interval>5m</interval>" not in updated
    # Unrelated wodles and the commented-out copy survive.
    assert "<tag>sigcheck</tag>" in updated
    assert "old commented-out copy, must stay" in updated
    assert sh.reconcile_agent_conf(updated, BOTH) == updated


def test_reconcile_with_nothing_wanted_removes_hand_added_wodles_too():
    updated = sh.reconcile_agent_conf(LAB_AGENT_CONF, set())
    assert sh.wodle_tags_present(updated) == []
    assert sh.BLOCK_BEGIN not in updated
    assert "<tag>sigcheck</tag>" in updated


def test_reconcile_survives_the_managers_reindentation():
    applied = sh.reconcile_agent_conf(LAB_AGENT_CONF, BOTH)
    stored = reindent(applied)
    assert stored != applied
    assert sh.same_agent_conf(sh.reconcile_agent_conf(stored, BOTH), stored)
    assert sh.unified_diff(stored, sh.reconcile_agent_conf(stored, BOTH)) is None


def test_comments_never_hide_or_fake_a_wodle():
    # (a) An unclosed wodle opening inside a comment must not swallow the real hand-added watchdog after it.
    case_a = (
        '<agent_config>\n  <!-- example: <wodle name="command"> -->\n'
        '  <wodle name="command">\n    <tag>sysmon-watchdog</tag>\n    <command>old.ps1</command>\n  </wodle>\n</agent_config>\n'
    )
    assert len(sh.tagged_wodles(case_a)) == 1
    out = sh.reconcile_agent_conf(case_a, {sh.WATCHDOG_TAG})
    assert "old.ps1" not in out and len(sh.tagged_wodles(out)) == 1
    # (b) A managed tag inside a comment within an unrelated wodle must not get that wodle deleted.
    case_b = (
        '<agent_config>\n  <wodle name="command">\n    <!-- <tag>sysmon-watchdog</tag> -->\n'
        "    <tag>my-own</tag>\n  </wodle>\n</agent_config>\n"
    )
    assert sh.tagged_wodles(case_b) == []
    assert "<tag>my-own</tag>" in sh.reconcile_agent_conf(case_b, set())


def test_reconcile_refuses_a_half_marker():
    with pytest.raises(ValueError):
        sh.reconcile_agent_conf(LAB_AGENT_CONF + sh.BLOCK_BEGIN + " broken -->\n", {sh.WATCHDOG_TAG})


def test_wanted_wodles_needs_every_prerequisite():
    scripts = {sh.WATCHDOG_SCRIPT: True, sh.RELOAD_SCRIPT: True}
    assert sh.wanted_wodles(True, scripts, True) == BOTH
    assert sh.wanted_wodles(True, scripts, False) == {sh.WATCHDOG_TAG}
    assert sh.wanted_wodles(False, scripts, True) == set()
    assert sh.wanted_wodles(True, {sh.WATCHDOG_SCRIPT: False, sh.RELOAD_SCRIPT: True}, True) == {sh.RELOAD_TAG}


# --------------------------------------------------------------------------------------------------------------------
# Vendored assets
# --------------------------------------------------------------------------------------------------------------------


def test_vendored_assets_match_the_manifest_and_keep_the_bom():
    for name in (sh.WATCHDOG_SCRIPT, sh.RELOAD_SCRIPT, sh.RULES_FILENAME):
        assert hashlib.sha256(sh.load_asset(name)).hexdigest() == sh.asset_sha256(name)
    assert sh.load_asset(sh.RELOAD_SCRIPT).startswith(b"\xef\xbb\xbf")
    assert not sh.load_asset(sh.RELOAD_SCRIPT)[3:].startswith(b"\xef\xbb\xbf")
    assert sh.expected_rule_count() == 25
    assert sh.asset_version()["source_commit"]


def test_a_tampered_asset_is_refused(tmp_path, monkeypatch):
    shutil.copytree(sh.ASSET_DIR, tmp_path / "assets")
    (tmp_path / "assets" / sh.WATCHDOG_SCRIPT).write_bytes(b"Start-Process calc.exe\n")
    monkeypatch.setattr(sh, "ASSET_DIR", tmp_path / "assets")
    with pytest.raises(sh.SysmonHealthAssetError):
        sh.load_asset(sh.WATCHDOG_SCRIPT)


# --------------------------------------------------------------------------------------------------------------------
# Three-way raw reads
# --------------------------------------------------------------------------------------------------------------------


class _Response:
    def __init__(self, status_code, content, content_type):
        self.status_code = status_code
        self.content = content
        self.headers = {"Content-Type": content_type}


def _patch_http(monkeypatch, response):
    async def attributes(name, session):
        return {"connector_url": "https://wazuh.example:55000"}

    async def client(name):
        return {"Authorization": "Bearer t"}

    async def blocking(fn, *args, **kwargs):
        return response

    class _Session:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(sh, "get_connector_info_from_db", attributes)
    monkeypatch.setattr(sh, "create_wazuh_manager_client", client)
    monkeypatch.setattr(sh, "run_blocking", blocking)
    monkeypatch.setattr(sh, "AsyncSessionLocal", _Session)


def test_raw_read_keeps_exact_bytes(monkeypatch):
    body = sh.load_asset(sh.RELOAD_SCRIPT)
    _patch_http(monkeypatch, _Response(200, body, "text/plain"))
    read = run(sh._get_raw("/groups/Windows_lab/files/sysmon_config_reload.ps1"))
    assert read.state == "ok" and read.content == body


def test_a_json_error_envelope_with_http_200_is_a_missing_file_not_its_content(monkeypatch):
    envelope = {"data": {"affected_items": [], "failed_items": [{"error": {"code": 1415}}], "total_failed_items": 1}, "error": 1}
    _patch_http(monkeypatch, _Response(200, json.dumps(envelope).encode(), "application/json"))
    assert run(sh._get_raw(f"/rules/files/{sh.RULES_FILENAME}")).state == "missing"


def test_a_server_error_is_a_read_failure_not_an_absence(monkeypatch):
    _patch_http(monkeypatch, _Response(500, b'{"title":"Internal error","error":3021}', "application/problem+json"))
    assert run(sh._get_raw("/groups/Windows_lab/files/sysmon_config.xml")).state == "error"


# --------------------------------------------------------------------------------------------------------------------
# Rollout orchestration against a fake manager
# --------------------------------------------------------------------------------------------------------------------


class FakeManager:
    """Files on the manager (rules + one group's shared folder) and every write CoPilot makes."""

    def __init__(self, rules=True, scripts=False, sysmon_config=True, agent_conf=LAB_AGENT_CONF, group="Windows_lab"):
        self.group = group
        self.files = {}
        if rules:
            self.files[f"/rules/files/{sh.RULES_FILENAME}"] = sh.load_asset(sh.RULES_FILENAME)
        if scripts:
            for name in sh.SHARED_SCRIPTS:
                self.files[f"/groups/{group}/files/{name}"] = sh.load_asset(name)
        if sysmon_config:
            self.files[f"/groups/{group}/files/{sh.SYSMON_CONFIG}"] = b"<Sysmon schemaversion='4.60'/>"
        self.files[f"/groups/{group}/files/agent.conf"] = agent_conf.encode()
        self.calls = []
        self.publish_result = (True, "Published to the shared folder.")
        self.agent_conf_reads = 0
        self.mutate_agent_conf_on_read = None
        self.failing_reads = set()

    def install(self, monkeypatch):
        async def get_raw(endpoint, params=None, connector_name="Wazuh-Manager"):
            if endpoint.endswith("/agent.conf"):
                self.agent_conf_reads += 1
                if self.mutate_agent_conf_on_read == self.agent_conf_reads:
                    self.files[endpoint] = self.files[endpoint] + b"<!-- edited by an analyst -->\n"
            if endpoint in self.failing_reads:
                return sh.RawFile("error", detail="HTTP 500")
            content = self.files.get(endpoint)
            return sh.RawFile("ok", content=content) if content is not None else sh.RawFile("missing")

        async def group_exists(group):
            return group == self.group

        async def customer_group(customer_code, session):
            return "lab"

        async def publish(group, names=sh.SHARED_SCRIPTS):
            self.calls.append(("publish", group, tuple(names)))
            ok, detail = self.publish_result
            if ok:
                for name in names:
                    self.files[f"/groups/{group}/files/{name}"] = sh.load_asset(name)
            return ok, detail

        async def put_agent_conf(group, content):
            self.calls.append(("put_agent_conf", group))
            # Like the real API: stored re-indented.
            self.files[f"/groups/{group}/files/agent.conf"] = reindent(content).encode()
            return {"success": True, "data": {"error": 0, "message": "Agent configuration was successfully updated"}}

        async def install_rules():
            self.calls.append(("install_rules",))
            self.files[f"/rules/files/{sh.RULES_FILENAME}"] = sh.load_asset(sh.RULES_FILENAME)
            return sh.SysmonHealthStep(name="rules", status="changed", detail="installed")

        monkeypatch.setattr(sh, "_get_raw", get_raw)
        monkeypatch.setattr(sh, "_group_exists", group_exists)
        monkeypatch.setattr(sh, "get_customer_wazuh_group", customer_group)
        monkeypatch.setattr(sh, "publish_shared_scripts", publish)
        monkeypatch.setattr(sh, "_put_agent_conf", put_agent_conf)
        monkeypatch.setattr(sh, "install_rules", install_rules)
        return self

    def agent_conf(self):
        return self.files[f"/groups/{self.group}/files/agent.conf"].decode()


def test_dry_run_plans_but_writes_nothing(monkeypatch):
    fake = FakeManager(rules=False, scripts=False).install(monkeypatch)
    result = run(sh.apply_sysmon_health("lab", session=None, dry_run=True, install_rules_if_needed=True))
    assert result.success
    assert [(s.name, s.status) for s in result.steps] == [("rules", "planned"), ("shared_files", "planned"), ("agent_conf", "planned")]
    assert fake.calls == []
    assert result.agent_conf_diff and "sysmon_watchdog.ps1" in result.agent_conf_diff


def test_missing_rules_stop_everything_unless_install_is_asked_for(monkeypatch):
    fake = FakeManager(rules=False, scripts=False).install(monkeypatch)
    result = run(sh.apply_sysmon_health("lab", session=None, dry_run=False, install_rules_if_needed=False))
    assert not result.success
    assert [(s.name, s.status) for s in result.steps] == [("rules", "skipped")]
    assert fake.calls == []


def test_full_rollout_runs_in_order_and_converges_despite_reindentation(monkeypatch):
    fake = FakeManager(rules=False, scripts=False).install(monkeypatch)
    result = run(sh.apply_sysmon_health("lab", session=None, dry_run=False, install_rules_if_needed=True))
    assert result.success, result
    assert [call[0] for call in fake.calls] == ["install_rules", "publish", "put_agent_conf"]
    assert sh.wodle_tags_present(fake.agent_conf()) == [sh.RELOAD_TAG, sh.WATCHDOG_TAG]
    assert result.status.agent_conf_current and not result.status.problems
    # Running it again changes nothing, even though the stored agent.conf was re-indented.
    fake.calls.clear()
    again = run(sh.apply_sysmon_health("lab", session=None, dry_run=False))
    assert again.success and fake.calls == []
    assert [s.status for s in again.steps] == ["ok", "ok", "ok"]
    assert again.agent_conf_diff is None


def test_scripts_that_cannot_be_published_leave_agent_conf_alone(monkeypatch):
    fake = FakeManager(rules=True, scripts=False).install(monkeypatch)
    fake.publish_result = (False, "WAZUH_UTILS_API_KEY is not set.")
    before = fake.agent_conf()
    result = run(sh.apply_sysmon_health("lab", session=None, dry_run=False))
    assert not result.success
    assert result.steps[-1].name == "shared_files" and result.steps[-1].status == "failed"
    assert fake.agent_conf() == before
    assert ("put_agent_conf", "Windows_lab") not in fake.calls


def test_reload_wodle_waits_for_a_deployed_sysmon_config(monkeypatch):
    fake = FakeManager(rules=True, scripts=True, sysmon_config=False).install(monkeypatch)
    result = run(sh.apply_sysmon_health("lab", session=None, dry_run=False))
    assert result.success
    assert sh.wodle_tags_present(fake.agent_conf()) == [sh.WATCHDOG_TAG]
    assert "held back" in result.steps[-1].detail


def test_a_failed_read_changes_nothing_and_keeps_a_working_reload_wodle(monkeypatch):
    applied = sh.reconcile_agent_conf(LAB_AGENT_CONF, BOTH)
    fake = FakeManager(rules=True, scripts=True, agent_conf=applied).install(monkeypatch)
    fake.failing_reads.add(f"/groups/Windows_lab/files/{sh.SYSMON_CONFIG}")
    result = run(sh.apply_sysmon_health("lab", session=None, dry_run=False))
    assert not result.success
    assert result.steps[-1].name == "read"
    assert fake.calls == []
    assert sh.wodle_tags_present(fake.agent_conf()) == [sh.RELOAD_TAG, sh.WATCHDOG_TAG]
    status = result.status
    assert status.read_errors and "nothing should be changed" in status.message


def test_a_concurrent_agent_conf_edit_is_not_overwritten(monkeypatch):
    fake = FakeManager(rules=True, scripts=True).install(monkeypatch)
    fake.mutate_agent_conf_on_read = 3  # status read, apply read, then the pre-write re-read sees an edit
    result = run(sh.apply_sysmon_health("lab", session=None, dry_run=False))
    assert not result.success
    assert ("put_agent_conf", "Windows_lab") not in fake.calls
    assert "edited by an analyst" in fake.agent_conf()


def test_apply_all_audits_as_it_goes_and_installs_rules_once(monkeypatch):
    fake = FakeManager(rules=False, scripts=True).install(monkeypatch)

    class _Meta:
        def __init__(self, code):
            self.customer_code = code
            self.customer_meta_wazuh_group = "lab"

    class _Scalars:
        def all(self):
            return [_Meta("lab")]

    class _Result:
        def scalars(self):
            return _Scalars()

    class _Session:
        async def execute(self, statement):
            return _Result()

    seen = []

    async def on_rules(step):
        seen.append(("rules", step.status))

    async def on_result(item):
        seen.append(("group", item.customer_code, item.success))

    result = run(
        sh.apply_sysmon_health_all(_Session(), dry_run=False, install_rules_if_needed=True, on_rules_step=on_rules, on_result=on_result),
    )
    assert result.success
    assert [c[0] for c in fake.calls].count("install_rules") == 1
    assert seen == [("rules", "changed"), ("group", "lab", True)]


# --------------------------------------------------------------------------------------------------------------------
# Sidecar transport policy
# --------------------------------------------------------------------------------------------------------------------


def test_publish_refuses_without_an_api_key(monkeypatch):
    monkeypatch.delenv("WAZUH_UTILS_API_KEY", raising=False)
    ok, detail = run(sh.publish_shared_scripts("Windows_lab"))
    assert not ok and "WAZUH_UTILS_API_KEY" in detail


def test_publish_refuses_cleartext_http_and_a_missing_url(monkeypatch):
    monkeypatch.setenv("WAZUH_UTILS_API_KEY", "k")
    monkeypatch.delenv("WAZUH_UTILS_URL", raising=False)
    ok, detail = run(sh.publish_shared_scripts("Windows_lab"))
    assert not ok and "WAZUH_UTILS_URL" in detail
    monkeypatch.setenv("WAZUH_UTILS_URL", "http://wazuh-master.example:5003")
    monkeypatch.delenv("WAZUH_UTILS_ALLOW_INSECURE_HTTP", raising=False)
    ok, detail = run(sh.publish_shared_scripts("Windows_lab"))
    assert not ok and "https" in detail
    endpoint, refusal, _ = sh._sidecar_settings()
    assert refusal and endpoint is None
    monkeypatch.setenv("WAZUH_UTILS_URL", "https://wazuh-master.example:5003")
    endpoint, refusal, _ = sh._sidecar_settings()
    assert refusal is None and endpoint == "https://wazuh-master.example:5003/provision_worker/shared-files"


def test_sidecar_tls_is_unverified_without_a_ca_bundle_and_verified_with_one(monkeypatch):
    monkeypatch.setenv("WAZUH_UTILS_API_KEY", "k")
    monkeypatch.setenv("WAZUH_UTILS_URL", "https://wazuh-master.example:5003")
    monkeypatch.delenv("WAZUH_UTILS_CA_BUNDLE", raising=False)
    # Only the URL and the key: encrypted, certificate not verified (aiohttp ssl=False), like the Wazuh API calls.
    assert sh._sidecar_settings()[2] is False
    monkeypatch.setenv("WAZUH_UTILS_CA_BUNDLE", "   ")
    assert sh._sidecar_settings()[2] is False

    calls = []
    sentinel = object()

    def fake_context(cafile=None):
        calls.append(cafile)
        return sentinel

    monkeypatch.setattr(sh.ssl, "create_default_context", fake_context)
    monkeypatch.setenv("WAZUH_UTILS_CA_BUNDLE", "/etc/copilot/wazuh-utils.crt")
    assert sh._sidecar_settings()[2] is sentinel and calls == ["/etc/copilot/wazuh-utils.crt"]

    # Plain http (loopback, or explicitly allowed) has no TLS settings at all.
    monkeypatch.setenv("WAZUH_UTILS_URL", "http://127.0.0.1:5003")
    assert sh._sidecar_settings()[2] is None


def test_publish_refuses_an_invalid_group_name(monkeypatch):
    monkeypatch.setenv("WAZUH_UTILS_API_KEY", "k")
    monkeypatch.setenv("WAZUH_UTILS_URL", "https://wazuh-master.example:5003")
    ok, detail = run(sh.publish_shared_scripts("Windows_../../etc"))
    assert not ok and "not a valid Wazuh group name" in detail


# --------------------------------------------------------------------------------------------------------------------
# Rules install guard
# --------------------------------------------------------------------------------------------------------------------


def _patch_rules_io(monkeypatch, previous, valid, restart_ok=True, uptimes=None):
    calls = []
    uptime_reads = iter(uptimes or [{"manager": "t0"}, {"manager": "t1"}])

    async def get_raw(endpoint, params=None, connector_name="Wazuh-Manager"):
        return previous

    async def upload(content):
        calls.append(("upload", hashlib.sha256(content).hexdigest()))
        return {"success": True, "data": {"error": 0}}

    async def validate():
        return valid

    async def delete(endpoint, params=None, connector_name="Wazuh-Manager"):
        calls.append(("delete", endpoint))
        return {"success": True, "data": {"error": 0}}

    async def restart():
        calls.append(("restart",))
        return {"success": restart_ok, "message": "ok" if restart_ok else "refused"}

    async def analysisd():
        return next(uptime_reads, {"manager": "t1"})

    async def cluster():
        return False

    monkeypatch.setattr(sh, "_get_raw", get_raw)
    monkeypatch.setattr(sh, "_upload_rules", upload)
    monkeypatch.setattr(sh, "validate_manager_configuration", validate)
    monkeypatch.setattr(sh, "send_delete_request", delete)
    monkeypatch.setattr(sh, "restart_wazuh_manager_service", restart)
    monkeypatch.setattr(sh, "_analysisd_uptimes", analysisd)
    monkeypatch.setattr(sh, "_cluster_enabled", cluster)
    return calls


async def _no_sleep(_seconds):
    return None


def test_invalid_rules_are_rolled_back_without_a_restart(monkeypatch):
    previous = sh.RawFile("ok", content=b"<group/>")
    calls = _patch_rules_io(monkeypatch, previous=previous, valid=(False, "analysisd -t failed"))
    step = run(sh.install_rules(sleep=_no_sleep))
    assert step.status == "failed" and "restored the previous file" in step.detail
    assert ("restart",) not in calls
    assert calls[-1] == ("upload", hashlib.sha256(b"<group/>").hexdigest())


def test_a_validation_that_could_not_run_also_rolls_back(monkeypatch):
    calls = _patch_rules_io(monkeypatch, previous=sh.RawFile("missing"), valid=(None, "HTTP 500"))
    step = run(sh.install_rules(sleep=_no_sleep))
    assert step.status == "failed" and "could not be validated" in step.detail
    assert ("delete", f"/rules/files/{sh.RULES_FILENAME}") in calls and ("restart",) not in calls


def test_an_unreadable_previous_file_aborts_before_any_upload(monkeypatch):
    calls = _patch_rules_io(monkeypatch, previous=sh.RawFile("error", detail="HTTP 500"), valid=(True, ""))
    step = run(sh.install_rules(sleep=_no_sleep))
    assert step.status == "failed" and calls == []


def test_a_failed_restart_request_rolls_back(monkeypatch):
    calls = _patch_rules_io(monkeypatch, previous=sh.RawFile("missing"), valid=(True, ""), restart_ok=False)
    step = run(sh.install_rules(sleep=_no_sleep))
    assert step.status == "failed"
    assert ("delete", f"/rules/files/{sh.RULES_FILENAME}") in calls


def test_valid_rules_restart_and_the_restart_is_confirmed(monkeypatch):
    calls = _patch_rules_io(monkeypatch, previous=sh.RawFile("missing"), valid=(True, ""))
    step = run(sh.install_rules(sleep=_no_sleep))
    assert step.status == "changed"
    assert [c[0] for c in calls] == ["upload", "restart"]


def test_an_unconfirmed_restart_is_reported_as_failed(monkeypatch):
    stuck = [{"manager": "t0"}] + [{"manager": "t0"}] * 100
    _patch_rules_io(monkeypatch, previous=sh.RawFile("missing"), valid=(True, ""), uptimes=stuck)
    step = run(sh.install_rules(sleep=_no_sleep))
    assert step.status == "failed" and "did not report a new start time" in step.detail


# --------------------------------------------------------------------------------------------------------------------
# Customer provisioning
# --------------------------------------------------------------------------------------------------------------------


class _Request:
    customer_code = "acme"
    customer_name = "Acme"
    wazuh_cluster_name = "acme-cluster"


@pytest.mark.parametrize("wanted", [set(), {sh.WATCHDOG_TAG}])
def test_provisioning_writes_only_the_wodles_whose_prerequisites_are_met(monkeypatch, wanted):
    sent = {}

    async def put(endpoint, data, xml_data=False, **kwargs):
        sent["endpoint"], sent["data"] = endpoint, data
        return {"success": True, "data": {"error": 0}}

    monkeypatch.setattr(provisioning, "send_wazuh_put_request", put)
    template_path = provisioning.get_template_path(provisioning.WazuhAgentsTemplatePaths.WINDOWS_AGENT)
    run(provisioning.configure_wazuh_group("Windows_acme", template_path, _Request(), sysmon_health_wodles=wanted))
    assert sent["endpoint"] == "/groups/Windows_acme/configuration"
    assert '<label key="customer">acme</label>' in sent["data"]
    assert sh.wodle_tags_present(sent["data"]) == sorted(wanted)


def test_provisioning_wodles_degrade_quietly_and_say_why(monkeypatch):
    warnings = []
    handler = sh.logger.add(lambda message: warnings.append(message.record["message"]), level="WARNING")

    async def rules_missing():
        return sh.SysmonHealthFileState(name=sh.RULES_FILENAME, expected_sha256="x")

    monkeypatch.setattr(sh, "rules_state", rules_missing)
    try:
        wodles, reason = run(sh.provisioning_wodles("Windows_acme"))
        assert wodles == set() and reason == f"{sh.RULES_FILENAME} is missing on the manager"

        async def rules_outdated():
            return sh.SysmonHealthFileState(name=sh.RULES_FILENAME, present=True, expected_sha256="x")

        monkeypatch.setattr(sh, "rules_state", rules_outdated)
        assert run(sh.provisioning_wodles("Windows_acme")) == (set(), f"{sh.RULES_FILENAME} is outdated on the manager")

        async def rules_unreadable():
            return sh.SysmonHealthFileState(name=sh.RULES_FILENAME, readable=False, read_error="HTTP 500", expected_sha256="x")

        monkeypatch.setattr(sh, "rules_state", rules_unreadable)
        assert run(sh.provisioning_wodles("Windows_acme")) == (set(), f"{sh.RULES_FILENAME} could not be read on the manager (HTTP 500)")

        async def rules_current():
            return sh.SysmonHealthFileState(name=sh.RULES_FILENAME, present=True, current=True, expected_sha256="x")

        async def publish_fails(group, names=sh.SHARED_SCRIPTS):
            return False, "WAZUH_UTILS_API_KEY is not set."

        monkeypatch.setattr(sh, "rules_state", rules_current)
        monkeypatch.setattr(sh, "publish_shared_scripts", publish_fails)
        wodles, reason = run(sh.provisioning_wodles("Windows_acme"))
        assert wodles == set() and "not published" in reason and "WAZUH_UTILS_API_KEY is not set." in reason

        async def publish_ok(group, names=sh.SHARED_SCRIPTS):
            return True, "ok"

        def scripts(current):
            async def states(group):
                return [
                    sh.SysmonHealthFileState(name=name, present=True, current=current, expected_sha256=sh.asset_sha256(name))
                    for name in sh.SHARED_SCRIPTS
                ]

            return states

        monkeypatch.setattr(sh, "publish_shared_scripts", publish_ok)
        monkeypatch.setattr(sh, "shared_script_states", scripts(False))
        wodles, reason = run(sh.provisioning_wodles("Windows_acme"))
        assert wodles == set() and "could not be verified" in reason

        async def explodes(group):
            raise RuntimeError("manager unreachable")

        monkeypatch.setattr(sh, "shared_script_states", explodes)
        wodles, reason = run(sh.provisioning_wodles("Windows_acme"))
        assert wodles == set() and "manager unreachable" in reason

        warned = len(warnings)
        monkeypatch.setattr(sh, "shared_script_states", scripts(True))
        assert run(sh.provisioning_wodles("Windows_acme")) == ({sh.WATCHDOG_TAG}, None)
        assert len(warnings) == warned  # nothing to warn about when the watchdog is kept
    finally:
        sh.logger.remove(handler)
    # Every dropped watchdog was logged at WARNING, with its reason.
    assert len(warnings) == 6 and all("without the sysmon-watchdog wodle" in line for line in warnings)


def test_provisioning_reports_a_dropped_watchdog_and_still_configures_every_group(monkeypatch):
    configured = []

    async def wodles(group):
        return set(), "sysmon_sensor_health_rules.xml is missing on the manager"

    async def configure(group_code, template_path, request, sysmon_health_wodles=None):
        configured.append((group_code, sysmon_health_wodles))

    monkeypatch.setattr(provisioning, "provisioning_wodles", wodles)
    monkeypatch.setattr(provisioning, "configure_wazuh_group", configure)
    reason = run(provisioning.apply_group_configurations(_Request()))
    assert reason == "sysmon_sensor_health_rules.xml is missing on the manager"
    assert configured == [("Linux_acme", None), ("Windows_acme", set()), ("Mac_acme", None)]

    async def kept(group):
        return {sh.WATCHDOG_TAG}, None

    monkeypatch.setattr(provisioning, "provisioning_wodles", kept)
    assert run(provisioning.apply_group_configurations(_Request())) is None


def test_routes_are_registered_under_sysmon_config_health():
    from app.routers.active_response import router

    paths = {route.path for route in router.routes}
    assert "/sysmon_config/health/{customer_code}" in paths
    assert "/sysmon_config/health/{customer_code}/apply" in paths
    assert "/sysmon_config/health/apply-all" in paths


# --------------------------------------------------------------------------------------------------------------------
# Sysmon config deploy follows the authenticated sidecar once a key is configured
# --------------------------------------------------------------------------------------------------------------------


def test_sysmon_config_deploy_uses_the_authenticated_sidecar_when_a_key_is_set(monkeypatch):
    from app.active_response.services import sysmon_config

    monkeypatch.setenv("WAZUH_UTILS_API_KEY", "k")
    monkeypatch.setenv("WAZUH_UTILS_URL", "https://wazuh-master.example:5003")
    assert run(sysmon_config.get_wazuh_endpoint(session=None)) == "https://wazuh-master.example:5003/provision_worker/sysmon-config"

    monkeypatch.setenv("WAZUH_UTILS_URL", "http://wazuh-master.example:5003")
    monkeypatch.delenv("WAZUH_UTILS_ALLOW_INSECURE_HTTP", raising=False)
    with pytest.raises(ValueError):
        run(sysmon_config.get_wazuh_endpoint(session=None))


def test_sysmon_config_deploy_keeps_the_legacy_endpoint_without_a_key(monkeypatch):
    from app.active_response.services import sysmon_config

    monkeypatch.delenv("WAZUH_UTILS_API_KEY", raising=False)

    async def connector_url(column_name, connector_name, session):
        return "https://wazuh-master.example:55000"

    monkeypatch.setattr(sysmon_config, "get_connector_attribute", connector_url)
    assert run(sysmon_config.get_wazuh_endpoint(session=None)) == "http://wazuh-master.example:5003/provision_worker/sysmon-config"


def test_publish_sends_bearer_group_files_and_hashes_and_maps_refusals(monkeypatch):
    """Drive the real request against a local server: headers, form fields, and the sidecar's error answers."""
    from aiohttp import web

    seen = {}
    answer = {"status": 200, "body": {"success": True, "message": "ok"}}

    async def handler(request):
        seen["auth"] = request.headers.get("Authorization")
        form = await request.post()
        seen["group"] = form.get("group")
        seen["files"] = [(f.filename, f.file.read()) for f in form.getall("files")]
        seen["sha256"] = form.getall("sha256")
        return web.json_response(answer["body"], status=answer["status"])

    async def scenario():
        app = web.Application()
        app.router.add_post("/provision_worker/shared-files", handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        monkeypatch.setenv("WAZUH_UTILS_URL", f"http://127.0.0.1:{port}")  # loopback: allowed over http
        monkeypatch.setenv("WAZUH_UTILS_API_KEY", "secret-key")
        try:
            results = [await sh.publish_shared_scripts("Windows_lab")]
            answer.update(status=403, body={"success": False, "message": "sysmon_watchdog.ps1 is not in WAZUH_UTILS_ALLOWED_SHA256"})
            results.append(await sh.publish_shared_scripts("Windows_lab", [sh.WATCHDOG_SCRIPT]))
            answer.update(status=404, body={"success": False, "message": "Group Windows_lab does not exist"})
            results.append(await sh.publish_shared_scripts("Windows_lab", [sh.WATCHDOG_SCRIPT]))
            answer.update(status=404, body={"detail": "Not Found"})
            results.append(await sh.publish_shared_scripts("Windows_lab", [sh.WATCHDOG_SCRIPT]))
            return results
        finally:
            await runner.cleanup()

    published, pinned, no_group, old_sidecar = run(scenario())
    assert published == (True, "Published to the shared folder.")
    assert seen["auth"] == "Bearer secret-key"
    assert seen["group"] == "Windows_lab"
    assert seen["files"] == [(sh.WATCHDOG_SCRIPT, sh.load_asset(sh.WATCHDOG_SCRIPT))]
    assert seen["sha256"] == [sh.asset_sha256(sh.WATCHDOG_SCRIPT)]
    assert not pinned[0] and "ALLOWED_SHA256" in pinned[1]
    assert not no_group[0] and "does not exist" in no_group[1]
    assert not old_sidecar[0] and "no /shared-files endpoint" in old_sidecar[1]
