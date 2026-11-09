"""Guards that keep a new customer on the installer's Sysmon config until a real one is deployed.

What is pinned here:
* validation refuses the empty skeleton "Add new Configuration" creates and an installer template that still carries
  an unrendered token such as __INSTALLDIRNAME__, and keeps accepting what it accepted before (a config with some
  empty RuleGroups alongside populated ones, an empty onmatch="exclude");
* a deploy validates the stored (MinIO) copy before anything reaches the sidecar, and reports a refusal instead of
  raising;
* an admin's successful deploy runs the Sysmon health apply (never installing the rules), audits it, and says when
  the endpoints will not pick the config up; a responder's deploy never applies, only checks for the reload wodle;
* the deploy audit row carries the deploy's real outcome;
* provisioning reports a dropped watchdog in its response, and decommission removes the stored config (best effort).

No network, no database: MinIO, the sidecar, the Sysmon health apply and the Wazuh calls are fakes.

Run with: cd backend && python -m pytest tests/test_sysmon_config_guards.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.active_response.routes.sysmon_config as routes  # noqa: E402
from app.active_response.schema.sysmon_config import (  # noqa: E402
    SysmonConfigDeploymentResult,
)
from app.active_response.schema.sysmon_health import (  # noqa: E402
    SysmonHealthApplyResult,
)
from app.active_response.schema.sysmon_health import SysmonHealthStatus  # noqa: E402
from app.active_response.schema.sysmon_health import SysmonHealthStep  # noqa: E402
from app.active_response.services import sysmon_config as service  # noqa: E402
from app.active_response.services import sysmon_health as sh  # noqa: E402
from app.audit.models.audit import AuditAction  # noqa: E402
from app.audit.models.audit import AuditResult  # noqa: E402
from app.auth.models.users import RoleEnum  # noqa: E402

SKELETON = """<Sysmon schemaversion="4.60">
\t<EventFiltering>
\t\t<RuleGroup groupRelation="or"></RuleGroup>
\t</EventFiltering>
</Sysmon>"""

POPULATED = """<Sysmon schemaversion="4.90">
  <HashAlgorithms>md5,sha256</HashAlgorithms>
  <EventFiltering>
    <RuleGroup name="" groupRelation="or"></RuleGroup>
    <RuleGroup name="" groupRelation="or">
      <ProcessCreate onmatch="include">
        <Image name="technique_id=T1059.001,technique_name=PowerShell" condition="end with">powershell.exe</Image>
      </ProcessCreate>
    </RuleGroup>
    <RuleGroup name="" groupRelation="or">
      <DriverLoad onmatch="include"/>
    </RuleGroup>
  </EventFiltering>
</Sysmon>"""

# The installer's committed sysmon_config.xml (Client-Kickstart-Automated main) before build.ps1 renders it.
TEMPLATE = """<Sysmon schemaversion="4.90">
  <EventFiltering>
    <RuleGroup name="" groupRelation="or">
      <ProcessCreate onmatch="exclude">
        <CommandLine condition="begin with">"C:\\Program Files\\__INSTALLDIRNAME__\\chainsaw\\chainsaw.exe"  hunt</CommandLine>
      </ProcessCreate>
    </RuleGroup>
  </EventFiltering>
</Sysmon>"""


def run(coroutine):
    return asyncio.run(coroutine)


def refusal(xml):
    with pytest.raises(HTTPException) as exc:
        run(service.validate_sysmon_config(xml))
    assert exc.value.status_code == 400
    return exc.value.detail


# --------------------------------------------------------------------------------------------------------------------
# Content validation
# --------------------------------------------------------------------------------------------------------------------


def test_the_new_configuration_skeleton_is_refused():
    assert "no event filters" in refusal(SKELETON)


@pytest.mark.parametrize(
    "event",
    ['<ProcessCreate onmatch="include"/>', '<ProcessCreate onmatch="include"><!-- <Image>x</Image> --></ProcessCreate>'],
)
def test_event_elements_without_a_filter_do_not_count(event):
    xml = f'<Sysmon schemaversion="4.90"><EventFiltering><RuleGroup groupRelation="or">{event}</RuleGroup></EventFiltering></Sysmon>'
    assert "no event filters" in refusal(xml)


def test_empty_rule_groups_next_to_populated_ones_still_pass():
    run(service.validate_sysmon_config(POPULATED))


def test_an_empty_exclude_still_passes_because_it_logs_every_event_of_its_type():
    xml = '<Sysmon schemaversion="4.90"><EventFiltering><RuleGroup groupRelation="or"><NetworkConnect onmatch="exclude"/></RuleGroup></EventFiltering></Sysmon>'
    run(service.validate_sysmon_config(xml))


def test_an_unrendered_installer_token_is_refused_and_points_at_the_rendered_artifact():
    detail = refusal(TEMPLATE)
    assert "__INSTALLDIRNAME__" in detail
    assert "rendered sysmon_config artifact from the customer's installer build" in detail
    # Once build.ps1 has substituted it, the same config passes.
    run(service.validate_sysmon_config(TEMPLATE.replace("__INSTALLDIRNAME__", "acme")))


def test_a_token_in_an_attribute_is_refused_too_but_one_in_a_comment_is_not():
    in_attribute = POPULATED.replace('name="technique_id', 'name="__RULE_PREFIX__technique_id')
    assert "__RULE_PREFIX__" in refusal(in_attribute)
    in_comment = POPULATED.replace("<HashAlgorithms>", "<!-- rendered from __INSTALLDIRNAME__ --><HashAlgorithms>")
    run(service.validate_sysmon_config(in_comment))


@pytest.mark.parametrize(
    "value",
    ["__PSScriptPolicyTest_", "C:\\Windows\\Temp\\__PSScriptPolicyTest_x.ps1", "__init__.py", "a__b__c", "___"],
)
def test_common_double_underscore_values_are_not_mistaken_for_tokens(value):
    run(service.validate_sysmon_config(POPULATED.replace("powershell.exe", value)))


@pytest.mark.parametrize(
    "xml, expected",
    [
        ("<Sysmon><EventFiltering>", "Invalid XML syntax"),
        ("<NotSysmon/>", "Root element must be 'Sysmon'"),
        ("<Sysmon/>", "Missing required 'EventFiltering' element"),
        ("<Sysmon><EventFiltering/></Sysmon>", "at least one RuleGroup"),
        ("<Sysmon><EventFiltering><RuleGroup/></EventFiltering></Sysmon>", "groupRelation"),
    ],
)
def test_the_existing_checks_are_unchanged(xml, expected):
    assert expected in refusal(xml)


# --------------------------------------------------------------------------------------------------------------------
# Deploy validates the stored copy before shipping it
# --------------------------------------------------------------------------------------------------------------------


def _deploy(monkeypatch, stored: bytes):
    uploads = []

    async def fetch(customer_code):
        return stored

    async def endpoint(session):
        return "https://wazuh-master.example:5003/provision_worker/sysmon-config"

    async def upload(endpoint, customer_code, file_path):
        with open(file_path, "rb") as sent:
            uploads.append(sent.read())
        return True, {"success": True, "message": "written"}, None

    monkeypatch.setattr(service, "fetch_sysmon_config", fetch)
    monkeypatch.setattr(service, "get_wazuh_endpoint", endpoint)
    monkeypatch.setattr(service, "upload_to_wazuh", upload)
    return run(service.deploy_sysmon_config_to_worker("acme", session=None)), uploads


@pytest.mark.parametrize(
    "stored, reason",
    [
        (SKELETON.encode(), "no event filters"),
        (TEMPLATE.encode(), "__INSTALLDIRNAME__"),
        (b"<Sysmon><EventFiltering>", "Invalid XML syntax"),
        (b"\xff\xfe<\x00S\x00", "not valid UTF-8"),
    ],
)
def test_an_invalid_stored_config_is_not_shipped(monkeypatch, stored, reason):
    result, uploads = _deploy(monkeypatch, stored)
    assert uploads == []
    assert result.success is False
    assert result.message.startswith("Not deployed") and reason in result.message
    assert reason in result.error_detail


def test_a_valid_stored_config_is_shipped_byte_for_byte(monkeypatch):
    result, uploads = _deploy(monkeypatch, POPULATED.encode())
    assert result.success is True and result.worker_message == "written"
    assert uploads == [POPULATED.encode()]


# --------------------------------------------------------------------------------------------------------------------
# The deploy route: outcome audit and the Sysmon health apply
# --------------------------------------------------------------------------------------------------------------------

ADMIN = SimpleNamespace(id=1, username="admin", role_id=RoleEnum.admin.value)
RESPONDER = SimpleNamespace(id=9, username="resp", role_id=RoleEnum.responder.value)
DEPLOYED = SysmonConfigDeploymentResult(success=True, message="Sysmon config successfully deployed for acme", customer_code="acme")


def _health(success, wodles_present, steps, message):
    status = SysmonHealthStatus(customer_code="acme", group="Windows_acme", group_exists=True, wodles_present=wodles_present)
    return SysmonHealthApplyResult(
        success=success,
        customer_code="acme",
        group="Windows_acme",
        dry_run=False,
        steps=[SysmonHealthStep(name=name, status=state, detail=detail) for name, state, detail in steps],
        status=status,
        message=message,
    )


APPLIED = _health(
    True,
    [sh.RELOAD_TAG, sh.WATCHDOG_TAG],
    [("rules", "ok", ""), ("shared_files", "ok", ""), ("agent_conf", "changed", "Wrote both")],
    "Applied.",
)
RULES_MISSING = _health(
    False,
    [],
    [("rules", "skipped", "sysmon_sensor_health_rules.xml is missing; re-run with install_rules=true (restarts the manager).")],
    "Stopped: the sensor-health rules must be on the manager before the endpoint pieces.",
)
NO_SIDECAR = _health(
    False,
    [],
    [("rules", "ok", ""), ("shared_files", "failed", "WAZUH_UTILS_API_KEY is not set.")],
    "Stopped: the scripts are not verified in the shared folder, so agent.conf was not touched.",
)
# An existing customer whose agent.conf already has a (hand-added) sysmon-reload wodle, on a manager without the rules.
LEGACY_RELOAD = _health(False, [sh.RELOAD_TAG], [("rules", "skipped", "sysmon_sensor_health_rules.xml is missing.")], "Stopped: rules.")


def _route(user, deployed=DEPLOYED, health=None, status=None):
    deploy = AsyncMock(return_value=deployed.model_copy(deep=True) if isinstance(deployed, SysmonConfigDeploymentResult) else None)
    if isinstance(deployed, BaseException):
        deploy.side_effect = deployed
    apply = AsyncMock(side_effect=health) if isinstance(health, BaseException) else AsyncMock(return_value=health)
    read_status = AsyncMock(side_effect=status) if isinstance(status, BaseException) else AsyncMock(return_value=status)
    session = object()
    with patch.object(routes, "deploy_sysmon_config_to_worker", deploy), patch.object(routes, "apply_sysmon_health", apply), patch.object(
        routes,
        "get_sysmon_health_status",
        read_status,
    ):
        result = run(routes.deploy_sysmon_config("acme", request=None, current_user=user, session=session))
    return result, apply, read_status, session


def _rows(audit_rows, action):
    return [row for row in audit_rows if row.action == action.value]


def test_an_admin_deploy_applies_sysmon_health_without_installing_rules_and_audits_both(audit_rows):
    result, apply, read_status, session = _route(ADMIN, health=APPLIED)
    apply.assert_awaited_once_with("acme", session, dry_run=False, install_rules_if_needed=False)
    read_status.assert_not_awaited()
    assert result.success and result.sysmon_health.success and result.sysmon_health_warning is None
    deploy_rows = _rows(audit_rows, AuditAction.SYSMON_CONFIG_DEPLOY)
    assert [(row.result, row.customer_code) for row in deploy_rows] == [(AuditResult.SUCCESS.value, "acme")]
    health_rows = _rows(audit_rows, AuditAction.SYSMON_HEALTH_APPLY)
    assert len(health_rows) == 1
    assert (health_rows[0].result, health_rows[0].entity_type, health_rows[0].entity_id) == (
        AuditResult.SUCCESS.value,
        "wazuh_group",
        "Windows_acme",
    )
    assert health_rows[0].new_value["install_rules"] is False and health_rows[0].new_value["dry_run"] is False


@pytest.mark.parametrize("health, why", [(RULES_MISSING, "install_rules=true"), (NO_SIDECAR, "WAZUH_UTILS_API_KEY is not set.")])
def test_a_blocked_apply_warns_that_endpoints_will_not_apply_the_config(audit_rows, health, why):
    result, _, _, _ = _route(ADMIN, health=health)
    assert result.success  # the deploy itself worked
    assert result.sysmon_health.success is False
    assert "Endpoints will not apply this config until the Sysmon health apply succeeds" in result.sysmon_health_warning
    assert why in result.sysmon_health_warning
    assert [row.result for row in _rows(audit_rows, AuditAction.SYSMON_HEALTH_APPLY)] == [AuditResult.FAILURE.value]


def test_a_blocked_apply_with_a_reload_wodle_already_in_place_says_the_config_still_applies(audit_rows):
    result, _, _, _ = _route(ADMIN, health=LEGACY_RELOAD)
    assert "will still apply this config" in result.sysmon_health_warning


def test_an_apply_that_raises_warns_and_writes_no_apply_row(audit_rows):
    result, _, _, _ = _route(ADMIN, health=RuntimeError("manager unreachable"))
    assert result.success and result.sysmon_health is None
    assert "could not run: manager unreachable" in result.sysmon_health_warning
    assert _rows(audit_rows, AuditAction.SYSMON_HEALTH_APPLY) == []
    assert len(_rows(audit_rows, AuditAction.SYSMON_CONFIG_DEPLOY)) == 1


@pytest.mark.parametrize(
    "status, warned, unconfirmed",
    [
        (SysmonHealthStatus(customer_code="acme", group="Windows_acme", wodles_present=[sh.RELOAD_TAG]), False, False),
        (SysmonHealthStatus(customer_code="acme", group="Windows_acme", wodles_present=[sh.WATCHDOG_TAG]), True, False),
        (
            SysmonHealthStatus(customer_code="acme", group="Windows_acme", read_errors=["Could not read the group's agent.conf."]),
            True,
            True,
        ),
        (RuntimeError("manager unreachable"), True, True),
    ],
)
def test_a_responder_deploy_never_applies_and_warns_only_without_a_reload_wodle(audit_rows, status, warned, unconfirmed):
    result, apply, read_status, _ = _route(RESPONDER, status=status)
    apply.assert_not_awaited()
    read_status.assert_awaited_once()
    assert result.success and result.sysmon_health is None
    assert (result.sysmon_health_warning is not None) == warned
    if warned:
        assert "Endpoints will not apply this config" in result.sysmon_health_warning
        assert "/api/sysmon_config/health/acme/apply" in result.sysmon_health_warning
        assert ("Could not read" in result.sysmon_health_warning) == unconfirmed
    assert _rows(audit_rows, AuditAction.SYSMON_HEALTH_APPLY) == []


def test_a_failed_deploy_applies_nothing_and_is_audited_as_a_failure(audit_rows):
    failed = SysmonConfigDeploymentResult(success=False, message="Not deployed: the config has no event filters", customer_code="acme")
    result, apply, read_status, _ = _route(ADMIN, deployed=failed, health=APPLIED)
    apply.assert_not_awaited()
    read_status.assert_not_awaited()
    assert result.success is False and result.sysmon_health is None and result.sysmon_health_warning is None
    rows = _rows(audit_rows, AuditAction.SYSMON_CONFIG_DEPLOY)
    assert [(row.result, row.details) for row in rows] == [(AuditResult.FAILURE.value, failed.message)]


def test_a_deploy_that_raises_is_still_audited(audit_rows):
    with pytest.raises(HTTPException):
        _route(RESPONDER, deployed=HTTPException(status_code=418, detail="stub"))
    assert [row.result for row in _rows(audit_rows, AuditAction.SYSMON_CONFIG_DEPLOY)] == [AuditResult.FAILURE.value]


# --------------------------------------------------------------------------------------------------------------------
# Provisioning reports a dropped watchdog
# --------------------------------------------------------------------------------------------------------------------


def _provision(watchdog_reason):
    from app.customer_provisioning.services import provision

    request = SimpleNamespace(
        customer_name="Acme",
        customer_code="acme",
        grafana_url="https://grafana.example",
        dashboards_to_include=SimpleNamespace(dashboards=[]),
        provision_wazuh_worker=False,
        provision_ha_proxy=False,
    )
    meta = SimpleNamespace(model_dump=lambda: {"customer_code": "acme", "customer_name": "Acme"})
    stubs = {
        "verify_required_tools": AsyncMock(),
        "get_pipeline_id": AsyncMock(return_value=["p1"]),
        "create_index_set": AsyncMock(return_value=SimpleNamespace(data=SimpleNamespace(id="idx"))),
        "create_event_stream": AsyncMock(return_value=SimpleNamespace(data=SimpleNamespace(stream_id="stream"))),
        "connect_stream_to_pipeline": AsyncMock(),
        "start_stream": AsyncMock(return_value=True),
        "create_wazuh_groups": AsyncMock(),
        "apply_group_configurations": AsyncMock(return_value=watchdog_reason),
        "create_grafana_organization": AsyncMock(return_value=SimpleNamespace(orgId=7)),
        "create_grafana_datasource": AsyncMock(return_value=SimpleNamespace(datasource=SimpleNamespace(uid="ds"))),
        "create_grafana_folder": AsyncMock(return_value=SimpleNamespace(id=3)),
        "provision_dashboards": AsyncMock(),
        "update_customer_meta_table": AsyncMock(return_value=meta),
        "update_customer_alert_settings_table": AsyncMock(),
    }
    with patch.multiple(provision, **stubs):
        return run(provision.provision_wazuh_customer(request, session=None))


def test_provisioning_says_why_the_watchdog_was_left_out_and_still_succeeds():
    reason = "sysmon_sensor_health_rules.xml is missing on the manager"
    response = _provision(reason)
    assert response.success is True
    assert response.sysmon_health_warning == reason
    assert response.message == f"Customer Acme provisioned successfully. Sysmon watchdog not enabled: {reason}"


def test_provisioning_with_the_watchdog_keeps_its_message():
    response = _provision(None)
    assert response.sysmon_health_warning is None
    assert response.message == "Customer Acme provisioned successfully"


# --------------------------------------------------------------------------------------------------------------------
# Decommission removes the stored config
# --------------------------------------------------------------------------------------------------------------------


def _decommission(delete_file):
    from app.customer_provisioning.services import decommission

    order = []

    async def groups(code):
        order.append("groups")
        return [f"Windows_{code}"]

    async def delete(bucket, key):
        order.append(("delete", bucket, key))
        return await delete_file(bucket, key)

    customer_meta = SimpleNamespace(
        customer_name="Acme",
        customer_code="acme",
        customer_meta_graylog_stream="stream",
        customer_meta_graylog_index="index",
        customer_meta_grafana_org_id="7",
    )
    session = SimpleNamespace(delete=AsyncMock(), commit=AsyncMock())
    stubs = {
        "is_connector_verified": AsyncMock(return_value=False),
        "gather_wazuh_agents": AsyncMock(return_value=[]),
        "delete_wazuh_agents": AsyncMock(return_value=[]),
        "delete_wazuh_groups": groups,
        "delete_file_from_minio": delete,
        "delete_stream": AsyncMock(),
        "delete_index_set": AsyncMock(),
        "delete_grafana_organization": AsyncMock(),
        "decommission_wazuh_worker": AsyncMock(),
        "decommission_haproxy": AsyncMock(),
    }
    with patch.multiple(decommission, **stubs):
        response = run(decommission.decomission_wazuh_customer(customer_meta, session))
    return response, order


def test_decommission_deletes_the_stored_sysmon_config_after_the_groups():
    async def deleted(bucket, key):
        return {"success": True, "message": f"File {key} deleted successfully"}

    response, order = _decommission(deleted)
    assert response.success
    assert order == ["groups", ("delete", "sysmon-configs", "acme/sysmon_config.xml")]


@pytest.mark.parametrize("outcome", ["missing", "raises"])
def test_a_missing_or_unreachable_stored_config_never_fails_decommission(outcome):
    async def delete(bucket, key):
        if outcome == "raises":
            raise ConnectionError("MinIO is down")
        return {"success": False, "error": "Object does not exist"}

    response, order = _decommission(delete)
    assert response.success
    assert ("delete", "sysmon-configs", "acme/sysmon_config.xml") in order
