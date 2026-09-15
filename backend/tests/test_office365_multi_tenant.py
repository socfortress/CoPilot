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


@pytest.mark.parametrize(
    ("instance_name", "expected"),
    [
        (None, ""),
        ("", ""),
        ("company.onmicrosoft.com", "company-onmicrosoft-com"),
        ("Subsidiary Ltd", "subsidiary-ltd"),
        ("--weird__name--", "weird-name"),
    ],
)
def test_an_instance_label_is_reduced_to_an_index_safe_slug(instance_name, expected):
    """Index prefixes are lowercase and cannot carry the dots a tenant domain is full of."""
    assert provision.instance_slug(instance_name) == expected


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


def test_the_unnamed_instance_keeps_its_original_index_prefix(monkeypatch):
    """A customer provisioned before this feature must not have its index prefix change."""
    _patch_index_set_deps(monkeypatch)

    index_set = run(provision.build_index_set_config("00002", session=None, instance_name=None))

    assert index_set.index_prefix == "office365-00002"
    assert index_set.title == "Customer A - Office365"


def test_each_tenant_gets_its_own_index_set(monkeypatch):
    _patch_index_set_deps(monkeypatch)

    index_set = run(
        provision.build_index_set_config("00002", session=None, instance_name="company.onmicrosoft.com"),
    )

    assert index_set.index_prefix == "office365-00002-company-onmicrosoft-com"
    assert index_set.title == "Customer A - Office365 - company.onmicrosoft.com"


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
