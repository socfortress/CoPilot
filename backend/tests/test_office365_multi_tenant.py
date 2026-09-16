"""A customer may hold several Microsoft 365 tenants (#1117).

Before this, `customer_integrations` allowed one row per `(customer_code, integration_name)` and
alert routing translated a tenant GUID to a customer through a single
`custom_alert_creation_settings.office365_organization_id` column -- so an MSSP customer with a
subsidiary's tenant had to be split into a second CoPilot customer, fragmenting its incidents,
assets and reporting.

Each configuration is now an *instance* on `customer_integrations.instance_name`, provisioned into
its own Graylog index set and stream and its own Grafana datasource, folder and dashboards. These
tests pin the parts that decide correctness and are pure enough to run without a database:

* which second configurations the create path accepts and which it rejects,
* that NULL -- the unnamed instance every pre-existing row carries -- stays addressable,
* the per-instance naming of Graylog and Grafana resources,
* and that decommissioning one tenant leaves the other tenants' `<api_auth>` blocks alone.

No DB, no network -- the session and the Wazuh/Graylog lookups are faked.

Run with: cd backend && python -m pytest tests/test_office365_multi_tenant.py
"""

import asyncio
import os
import xml.etree.ElementTree as ET

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.integrations import routes  # noqa: E402
from app.integrations.office365.services import decommission  # noqa: E402
from app.integrations.office365.services import provision  # noqa: E402


class FakeResult:
    """Stands in for a SQLAlchemy `Result` over a canned list of rows."""

    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return self

    def unique(self):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    """Replays one canned result per `execute`, recording the statements it was given."""

    def __init__(self, *results):
        self._results = list(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        rows = self._results.pop(0) if self._results else []
        return FakeResult(rows)


class FakeIntegration:
    def __init__(self, instance_name):
        self.instance_name = instance_name


def run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------------------
# Instance labels
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, None), ("", None), ("   ", None), ("  tenant-a  ", "tenant-a"), ("tenant-a", "tenant-a")],
)
def test_a_blank_instance_label_means_the_unnamed_instance(raw, expected):
    """A form that posts an empty string must land on the same instance as one that omits it."""
    assert routes.normalize_instance_name(raw) == expected


def test_the_unnamed_instance_is_matched_with_is_null():
    """`column == None` renders as `= NULL` and matches nothing, hiding every pre-existing row."""
    clause = routes.instance_name_matches(routes.CustomerIntegrations.instance_name, None)
    assert "IS NULL" in str(clause)

    clause = routes.instance_name_matches(routes.CustomerIntegrations.instance_name, "tenant-a")
    assert "IS NULL" not in str(clause)


# --------------------------------------------------------------------------------------
# Which second configurations are accepted
# --------------------------------------------------------------------------------------


def test_a_first_integration_of_any_kind_is_accepted():
    session = FakeSession([])
    run(routes.check_existing_customer_integration("00002", "Office365", session, instance_name="tenant-a"))


def test_a_single_instance_integration_still_rejects_a_second_one():
    """Only integrations whose provisioning can cope with instances are opted in."""
    session = FakeSession([FakeIntegration(None)])

    with pytest.raises(HTTPException) as err:
        run(routes.check_existing_customer_integration("00002", "Mimecast", session, instance_name="second"))

    assert err.value.status_code == 400
    assert "already exists" in err.value.detail


def test_a_second_office365_tenant_is_accepted_when_it_is_named():
    session = FakeSession([FakeIntegration(None)])
    run(routes.check_existing_customer_integration("00002", "Office365", session, instance_name="subsidiary"))


def test_a_second_office365_tenant_must_be_named():
    """Two NULL instances would be indistinguishable to every lookup downstream."""
    session = FakeSession([FakeIntegration(None)])

    with pytest.raises(HTTPException) as err:
        run(routes.check_existing_customer_integration("00002", "Office365", session, instance_name=None))

    assert err.value.status_code == 400
    assert "instance name" in err.value.detail


def test_two_office365_tenants_cannot_share_a_name():
    session = FakeSession([FakeIntegration("subsidiary")])

    with pytest.raises(HTTPException) as err:
        run(routes.check_existing_customer_integration("00002", "Office365", session, instance_name="subsidiary"))

    assert err.value.status_code == 400
    assert "subsidiary" in err.value.detail


# --------------------------------------------------------------------------------------
# Resolving which instance a caller meant
# --------------------------------------------------------------------------------------


def test_an_unnamed_request_resolves_to_the_only_instance():
    """Callers predating multi-instance support send no label; one instance is unambiguous."""
    session = FakeSession(["tenant-a"])
    assert run(routes.resolve_integration_instance(session, "00002", "Office365", None)) == "tenant-a"


def test_an_unnamed_request_against_several_instances_is_refused():
    """Acting on an arbitrary tenant would provision or delete the wrong one."""
    session = FakeSession(["tenant-a", "tenant-b"])

    with pytest.raises(HTTPException) as err:
        run(routes.resolve_integration_instance(session, "00002", "Office365", None))

    assert err.value.status_code == 400
    assert "tenant-a" in err.value.detail and "tenant-b" in err.value.detail


def test_a_named_request_is_taken_as_given_without_a_query():
    session = FakeSession()
    assert run(routes.resolve_integration_instance(session, "00002", "Office365", "tenant-b")) == "tenant-b"
    assert session.statements == []


# --------------------------------------------------------------------------------------
# Per-instance Graylog and Grafana resources
# --------------------------------------------------------------------------------------


def _patch_index_set_deps(monkeypatch):
    class _Customer:
        customer_name = "Customer A"

    class _CustomerResponse:
        customer = _Customer()

    async def fake_get_customer(customer_code, session):
        return _CustomerResponse()

    async def fake_shards():
        return 1

    monkeypatch.setattr(provision, "get_customer", fake_get_customer)
    monkeypatch.setattr(provision, "output_shard_number_to_be_set_based_on_nodes", fake_shards)


def test_every_tenant_of_a_customer_shares_one_index_set(monkeypatch):
    """Graylog rejects an index prefix that extends an existing one.

    A per-tenant `office365-<code>-<tenant>` is refused against the first tenant's
    `office365-<code>` with "would conflict with existing index set prefix", so the prefix depends
    on the customer alone. It is also the behaviour the feature wants: one customer, one place for
    their Microsoft 365 data, with `data_office365_OrganizationId` still naming the tenant on every
    event.
    """
    _patch_index_set_deps(monkeypatch)

    index_set = run(provision.build_index_set_config("00002", session=None))

    assert index_set.index_prefix == "office365-00002"
    assert index_set.title == "Customer A - Office365"
    # Nothing tenant-derived may reach the prefix, whatever the label looks like.
    assert provision.build_index_set_config.__code__.co_varnames[:2] == ("customer_code", "session")


def test_each_tenant_gets_its_own_stream_pinned_to_its_organization_id(monkeypatch):
    """A Graylog stream rule holds one value, which is why a stream cannot serve two tenants."""
    _patch_index_set_deps(monkeypatch)

    auth_keys = provision.ProvisionOffice365AuthKeys(
        TENANT_ID="11111111-2222-3333-4444-555555555555",
        CLIENT_ID="client",
        CLIENT_SECRET="secret",
        API_TYPE="commercial",
    )

    stream = run(
        provision.build_event_stream_config(
            "00002",
            auth_keys,
            index_set_id="index-1",
            session=None,
            instance_name="subsidiary.onmicrosoft.com",
        ),
    )

    assert stream.title == "Customer A - Office365 - subsidiary.onmicrosoft.com"
    assert stream.index_set_id == "index-1"
    tenant_rules = [rule for rule in stream.rules if rule.field == "data_office365_OrganizationId"]
    assert [rule.value for rule in tenant_rules] == [auth_keys.TENANT_ID]
    assert any(rule.field == "rule_group1" and rule.value == "office365" for rule in stream.rules)


# --------------------------------------------------------------------------------------
# Decommissioning one tenant
# --------------------------------------------------------------------------------------

TWO_TENANT_CONFIG = """<ossec_config>
  <office365>
    <enabled>yes</enabled>
    <api_auth>
      <tenant_id>tenant-a</tenant_id>
      <client_id>client-a</client_id>
    </api_auth>
    <api_auth>
      <tenant_id>tenant-b</tenant_id>
      <client_id>client-b</client_id>
    </api_auth>
    <subscriptions>
      <subscription>Audit.Exchange</subscription>
    </subscriptions>
  </office365>
</ossec_config>"""


def test_removing_one_tenant_leaves_the_others_polling():
    """The surviving tenants' credentials must come through the edit untouched."""
    updated = decommission.remove_api_auth_block(TWO_TENANT_CONFIG, "tenant-a")

    root = ET.fromstring(updated)
    office365 = root.find("office365")
    tenants = [el.find("tenant_id").text for el in office365.findall("api_auth")]

    assert tenants == ["tenant-b"]
    assert office365.find("subscriptions") is not None


def test_removing_the_last_tenant_removes_the_whole_office365_block():
    """Wazuh rejects an `<office365>` block with no `<api_auth>` in it."""
    config = decommission.remove_api_auth_block(TWO_TENANT_CONFIG, "tenant-a")
    config = decommission.remove_api_auth_block(config, "tenant-b")

    assert ET.fromstring(config).find("office365") is None


def test_a_tenant_that_is_not_configured_is_not_an_error():
    """An already-clean manager means there is nothing to push, not a failure to report."""
    assert decommission.remove_api_auth_block(TWO_TENANT_CONFIG, "tenant-z") is None


# --------------------------------------------------------------------------------------
# A failed deployment leaves nothing behind (#1117, follow-up report)
# --------------------------------------------------------------------------------------


def test_rollback_undoes_steps_newest_first():
    """Later steps depend on earlier ones, so they have to come apart in reverse."""
    order = []
    rollback = provision._ProvisioningRollback("00002", "tenant-a")
    rollback.add("first", lambda: _record(order, "first"))
    rollback.add("second", lambda: _record(order, "second"))
    rollback.add("third", lambda: _record(order, "third"))

    failures = run(rollback.run())

    assert order == ["third", "second", "first"]
    assert failures == []


def test_one_failing_undo_does_not_abandon_the_rest():
    """A rollback that gives up halfway recreates the mess it exists to clean up."""
    order = []
    rollback = provision._ProvisioningRollback("00002", None)
    rollback.add("reachable", lambda: _record(order, "reachable"))
    rollback.add("broken", lambda: _raise(RuntimeError("service down")))

    failures = run(rollback.run())

    assert order == ["reachable"]
    assert len(failures) == 1 and "broken" in failures[0] and "service down" in failures[0]


async def _record(sink, name):
    sink.append(name)


async def _raise(exc):
    raise exc


class ProvisioningHarness:
    """Fakes every external call `provision_office365` makes, recording what it did."""

    def __init__(self, monkeypatch, existing_meta=None, fail_on=None):
        self.calls = []
        self.existing_meta = existing_meta
        self.fail_on = fail_on

        async def noop(*args, **kwargs):
            return None

        def record(name, result=None, obj=False):
            async def fake(*args, **kwargs):
                self.calls.append(name)
                if self.fail_on == name:
                    raise HTTPException(status_code=500, detail=f"{name} exploded")
                return result

            return fake

        # Wazuh side
        monkeypatch.setattr(provision, "get_wazuh_configuration", record("get_wazuh_configuration", "<ossec_config/>"))
        monkeypatch.setattr(provision, "check_if_office365_is_already_provisioned", record("check_existing", True))
        monkeypatch.setattr(provision, "check_if_tenant_is_already_provisioned", record("check_tenant"))
        monkeypatch.setattr(provision, "add_api_auth_to_office365_block", record("add_api_auth", "<ossec_config/>"))
        monkeypatch.setattr(provision, "update_wazuh_configuration", record("update_wazuh_configuration"))
        monkeypatch.setattr(provision, "restart_wazuh_manager", record("restart_wazuh_manager"))
        monkeypatch.setattr(provision, "decommission_office365_tenant", record("UNDO_wazuh_api_auth"))

        # Graylog side
        monkeypatch.setattr(provision, "check_pipeline_rules", noop)
        monkeypatch.setattr(provision, "check_pipeline", noop)
        monkeypatch.setattr(provision, "get_existing_office365_meta", record("get_existing_meta", existing_meta))
        monkeypatch.setattr(provision, "create_index_set", record("create_index_set", _IndexSetResponse("index-new")))
        monkeypatch.setattr(provision, "delete_index_by_id", record("UNDO_index_set"))
        monkeypatch.setattr(provision, "create_event_stream", record("create_event_stream", _StreamResponse("stream-new")))
        monkeypatch.setattr(provision, "delete_stream", record("UNDO_stream"))
        monkeypatch.setattr(provision, "get_pipeline_id", record("get_pipeline_id", ["pipeline-1"]))
        monkeypatch.setattr(provision, "connect_stream_to_pipeline", record("connect_stream_to_pipeline"))
        monkeypatch.setattr(provision, "start_stream", record("start_stream"))

        # Grafana side
        monkeypatch.setattr(provision, "get_customer_meta", record("get_customer_meta", _CustomerMetaResponse()))
        monkeypatch.setattr(provision, "create_grafana_datasource", record("create_grafana_datasource", _DatasourceResponse("ds-new")))
        monkeypatch.setattr(provision, "delete_grafana_datasource", record("UNDO_datasource"))
        monkeypatch.setattr(provision, "create_grafana_folder", record("create_grafana_folder", _FolderResponse(77)))
        monkeypatch.setattr(provision, "delete_folder", record("UNDO_folder"))
        monkeypatch.setattr(provision, "provision_dashboards", record("provision_dashboards"))
        monkeypatch.setattr(provision, "get_customer_default_settings_attribute", record("grafana_url", "grafana.local"))

        # Database side
        monkeypatch.setattr(provision, "create_integration_meta_entry", record("create_integration_meta_entry"))
        monkeypatch.setattr(provision, "update_customer_integration_table", record("mark_deployed"))
        monkeypatch.setattr(provision, "update_customermeta_table", record("update_customermeta"))


class _IndexSetResponse:
    def __init__(self, index_id):
        self.data = type("d", (), {"id": index_id})()


class _StreamResponse:
    def __init__(self, stream_id):
        self.data = type("d", (), {"stream_id": stream_id})()


class _DatasourceResponse:
    def __init__(self, uid):
        self.datasource = type("d", (), {"uid": uid})()


class _FolderResponse:
    def __init__(self, folder_id):
        self.id = folder_id


class _CustomerMetaResponse:
    def __init__(self):
        self.customer_meta = type("m", (), {"customer_meta_grafana_org_id": "5"})()


def _auth_keys():
    return provision.ProvisionOffice365AuthKeys(
        TENANT_ID="tenant-guid",
        CLIENT_ID="client",
        CLIENT_SECRET="secret",
        API_TYPE="commercial",
    )


def test_a_failed_index_set_removes_the_wazuh_block_it_already_wrote(monkeypatch):
    """The reported failure, and the trap it left behind.

    Graylog refused the index set after ossec.conf had already been written and the manager
    restarted. Nothing cleaned that up, so the tenant stayed in the manager's config — and the
    retry then failed on `check_if_tenant_is_already_provisioned` instead, leaving the operator
    with a deployment that could neither succeed nor be attempted again.
    """
    harness = ProvisioningHarness(monkeypatch, fail_on="create_index_set")

    with pytest.raises(HTTPException) as err:
        run(provision.provision_office365("00002", _auth_keys(), session=None, instance_name="tenant-b"))

    assert "rolled back" in err.value.detail
    assert "UNDO_wazuh_api_auth" in harness.calls, "the api_auth block must be removed again"
    assert "mark_deployed" not in harness.calls, "a failed deployment must not be marked deployed"
    assert "create_integration_meta_entry" not in harness.calls


def test_a_failed_deployment_removes_the_resources_it_created(monkeypatch):
    """Everything this run created comes back out, newest first."""
    harness = ProvisioningHarness(monkeypatch, fail_on="provision_dashboards")

    with pytest.raises(HTTPException):
        run(provision.provision_office365("00002", _auth_keys(), session=None, instance_name="tenant-b"))

    undone = [c for c in harness.calls if c.startswith("UNDO_")]
    assert undone == ["UNDO_folder", "UNDO_datasource", "UNDO_stream", "UNDO_index_set", "UNDO_wazuh_api_auth"]


def test_rollback_does_not_remove_infrastructure_it_reused(monkeypatch):
    """A second tenant's failure must not take the first tenant's index set with it."""
    existing = type(
        "meta",
        (),
        {"graylog_index_id": "index-shared", "grafana_datasource_uid": "ds-shared", "grafana_dashboard_folder_id": "9"},
    )()
    harness = ProvisioningHarness(monkeypatch, existing_meta=existing, fail_on="create_integration_meta_entry")

    with pytest.raises(HTTPException):
        run(provision.provision_office365("00002", _auth_keys(), session=None, instance_name="tenant-b"))

    undone = [c for c in harness.calls if c.startswith("UNDO_")]
    # Only this tenant's own stream and api_auth block; the shared index set and Grafana stay.
    assert undone == ["UNDO_stream", "UNDO_wazuh_api_auth"]
    assert "create_index_set" not in harness.calls
    assert "create_grafana_datasource" not in harness.calls


def test_a_second_tenant_reuses_the_customers_index_set(monkeypatch):
    """The happy path for tenant two: no new index set, no new Grafana, just a stream."""
    existing = type(
        "meta",
        (),
        {"graylog_index_id": "index-shared", "grafana_datasource_uid": "ds-shared", "grafana_dashboard_folder_id": "9"},
    )()
    harness = ProvisioningHarness(monkeypatch, existing_meta=existing)

    response = run(provision.provision_office365("00002", _auth_keys(), session=None, instance_name="tenant-b"))

    assert response.success is True
    assert "create_index_set" not in harness.calls
    assert "create_grafana_datasource" not in harness.calls
    assert "create_grafana_folder" not in harness.calls
    assert "create_event_stream" in harness.calls
    assert "mark_deployed" in harness.calls
    assert [c for c in harness.calls if c.startswith("UNDO_")] == []


# --------------------------------------------------------------------------------------
# Deleting one tenant must not blind the others
# --------------------------------------------------------------------------------------


def test_a_null_instance_is_counted_as_another_instance():
    """`column != 'x'` is NULL for a NULL column, which would hide the unnamed instance."""
    clause = str(routes.instance_name_differs(routes.CustomerIntegrations.instance_name, "tenant-b"))
    assert "IS NULL" in clause, "the unnamed instance must still count as a sibling"

    clause = str(routes.instance_name_differs(routes.CustomerIntegrations.instance_name, None))
    assert "IS NOT NULL" in clause


def test_the_last_instance_out_takes_the_shared_infrastructure():
    """With no siblings left there is nothing to protect, so the full teardown runs."""
    session = FakeSession([])
    assert run(routes.count_other_integration_instances(session, "00002", "Office365", "tenant-b")) == 0


def test_a_surviving_sibling_keeps_the_shared_infrastructure():
    """Deleting one tenant while another is deployed must only remove that tenant's stream."""
    session = FakeSession([1])  # one other customer_integrations row
    assert run(routes.count_other_integration_instances(session, "00002", "Office365", "tenant-b")) == 1
