"""Deploying and re-syncing an AWS integration instance, and what a failure leaves behind.

Mirrors `test_office365_multi_tenant.py`: every external call `provision_aws` makes is faked and
recorded, so these tests pin the order of operations — validate before changing anything, write
the metadata before flagging the instance deployed, roll back newest-first — and what is shared
between a customer's AWS accounts (index sets, datasources, folder) versus owned by one (streams,
buckets).

Also covers the generic integration routes' AWS handling: the write-only secret and the identity
keys that cannot change on a deployed instance.

No DB, no network.

Run with: cd backend && python -m pytest tests/test_aws_provision.py
"""

import asyncio
import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.integrations import routes  # noqa: E402
from app.integrations.aws.schema.provision import ProvisionAwsAuthKeys  # noqa: E402
from app.integrations.aws.services import provision  # noqa: E402
from app.integrations.aws.services.validate import AwsValidationError  # noqa: E402
from app.integrations.aws.services.validate import AwsValidationResult  # noqa: E402
from app.integrations.aws.services.wazuh_config import ReconcileResult  # noqa: E402
from app.integrations.schema import REDACTED_AUTH_VALUE  # noqa: E402
from app.integrations.schema import IntegrationAuthKeys  # noqa: E402
from app.integrations.schema import is_unchanged_secret  # noqa: E402

ACCOUNT = "123456789012"
BUCKET = "example-cloudtrail-logs"


def run(coroutine):
    return asyncio.run(coroutine)


def auth_keys(services="cloudtrail,guardduty:guardduty"):
    return ProvisionAwsAuthKeys(
        ACCESS_KEY_ID="AKIAABCDEFGHIJKLMNOP",
        SECRET_ACCESS_KEY="the-secret",
        AWS_ACCOUNT_ID=ACCOUNT,
        BUCKET_NAME=BUCKET,
        SERVICES=services,
    )


def meta(instance_name=None, streams="", index_sets="", datasources="", folder="77"):
    return SimpleNamespace(
        instance_name=instance_name,
        graylog_stream_id=streams,
        graylog_index_id=index_sets,
        grafana_datasource_uid=datasources,
        grafana_dashboard_folder_id=folder,
        grafana_org_id="5",
    )


class Harness:
    """Fakes every external call `provision_aws` makes, recording what it did."""

    def __init__(self, monkeypatch, metas=(), fail_on=None, validation=None, wazuh_changed=True):
        self.calls = []
        self.saved_meta = None
        self.fail_on = fail_on
        counter = {"n": 0}

        def record(name, result=None):
            async def fake(*args, **kwargs):
                self.calls.append(name)
                if self.fail_on == name:
                    raise HTTPException(status_code=500, detail=f"{name} exploded")
                return result(*args, **kwargs) if callable(result) else result

            return fake

        def new_id(prefix):
            def make(*args, **kwargs):
                counter["n"] += 1
                return f"{prefix}-{counter['n']}"

            return make

        async def apply(desired, bucket_name, account_id, adopt_existing, keep_only_logs_after=True):
            self.calls.append("UNDO_wazuh" if self.calls and "wazuh_buckets" in self.calls else "wazuh_buckets")
            self.adopt_existing = self.adopt_existing if hasattr(self, "adopt_existing") else adopt_existing
            if self.fail_on == "wazuh_buckets":
                raise HTTPException(status_code=400, detail="conflict")
            return ReconcileResult(config="<x/>", changed=wazuh_changed, previous=[])

        async def save(session, **kwargs):
            self.calls.append("save_meta")
            if self.fail_on == "save_meta":
                raise HTTPException(status_code=500, detail="db down")
            self.saved_meta = kwargs

        async def removed(services, **kwargs):
            self.calls.append(f"remove_resources:{','.join(services)}:keep={','.join(sorted(kwargs['keep_shared']))}")
            return []

        if validation is None:
            validation = record("validate", AwsValidationResult(validated=True, bucket_region="eu-west-1"))

        monkeypatch.setattr(provision, "ensure_account_is_free", record("ensure_account_is_free"))
        monkeypatch.setattr(provision, "validate_aws_access", validation)
        monkeypatch.setattr(provision, "get_customer_aws_metas", record("get_metas", list(metas)))
        monkeypatch.setattr(provision, "log_markers", record("log_markers", (None, None)))
        monkeypatch.setattr(provision, "apply_instance_buckets", apply)
        monkeypatch.setattr(provision, "wait_for_profile_error", record("wait_for_profile_error", False))
        monkeypatch.setattr(provision, "ensure_pipeline_rules", record("ensure_pipeline_rules"))
        monkeypatch.setattr(provision, "ensure_pipeline", record("ensure_pipeline", "pipeline-1"))
        monkeypatch.setattr(provision, "create_index_set", record("create_index_set", new_id("index")))
        monkeypatch.setattr(provision, "delete_index_by_id", record("UNDO_index_set"))
        monkeypatch.setattr(provision, "create_event_stream", record("create_event_stream", new_id("stream")))
        monkeypatch.setattr(provision, "delete_stream", record("UNDO_stream"))
        monkeypatch.setattr(provision, "connect_and_start_stream", record("connect_and_start_stream"))
        monkeypatch.setattr(
            provision,
            "get_customer_meta",
            record("get_customer_meta", SimpleNamespace(customer_meta=SimpleNamespace(customer_meta_grafana_org_id="5"))),
        )
        monkeypatch.setattr(provision, "create_grafana_folder", record("create_grafana_folder", SimpleNamespace(id=77)))
        monkeypatch.setattr(provision, "delete_folder", record("UNDO_folder"))
        monkeypatch.setattr(provision, "create_grafana_datasource", record("create_grafana_datasource", new_id("ds")))
        monkeypatch.setattr(provision, "delete_grafana_datasource", record("UNDO_datasource"))
        monkeypatch.setattr(provision, "save_aws_meta", save)
        monkeypatch.setattr(provision, "update_customer_integration_table", record("mark_deployed"))
        monkeypatch.setattr(provision, "remove_service_resources", removed)

    def undone(self):
        return [call for call in self.calls if call.startswith("UNDO_")]


def deploy(keys=None, instance_name=None):
    return run(provision.provision_aws("examplecorp", keys or auth_keys(), session=None, instance_name=instance_name))


# --- first deployment ---------------------------------------------------------------------------


def test_a_first_deployment_creates_one_of_each_per_service(monkeypatch):
    harness = Harness(monkeypatch)

    response = deploy()

    assert response.success
    assert harness.calls.count("create_index_set") == 2
    assert harness.calls.count("create_event_stream") == 2
    assert harness.calls.count("create_grafana_datasource") == 2
    assert harness.calls.count("create_grafana_folder") == 1
    assert set(harness.saved_meta["stream_ids"]) == {"cloudtrail", "guardduty"}
    assert harness.calls.index("save_meta") < harness.calls.index("mark_deployed")
    assert harness.adopt_existing is False, "a first deployment never takes over existing buckets"


def test_the_response_always_explains_the_aws_config_file(monkeypatch):
    Harness(monkeypatch)

    response = deploy()

    assert response.aws_config is not None
    assert response.aws_config.contents == "[default]\nregion = eu-west-1\n"


def test_failed_validation_changes_nothing(monkeypatch):
    async def refuse(*args, **kwargs):
        raise AwsValidationError("AWS rejected the access key")

    harness = Harness(monkeypatch, validation=refuse)

    with pytest.raises(HTTPException) as err:
        deploy()

    assert err.value.status_code == 400 and "nothing was changed" in err.value.detail
    assert "wazuh_buckets" not in harness.calls and "create_index_set" not in harness.calls


def test_a_failure_rolls_everything_back_newest_first(monkeypatch):
    harness = Harness(monkeypatch, fail_on="save_meta")

    with pytest.raises(HTTPException) as err:
        deploy(auth_keys(services="cloudtrail"))

    assert "rolled back" in err.value.detail
    assert harness.undone() == ["UNDO_datasource", "UNDO_folder", "UNDO_stream", "UNDO_index_set", "UNDO_wazuh"]
    assert "mark_deployed" not in harness.calls


def test_an_unchanged_manager_registers_no_wazuh_undo(monkeypatch):
    harness = Harness(monkeypatch, fail_on="save_meta", wazuh_changed=False)

    with pytest.raises(HTTPException):
        deploy(auth_keys(services="cloudtrail"))

    assert "UNDO_wazuh" not in harness.undone()
    assert "wait_for_profile_error" not in harness.calls


# --- a second AWS account of the same customer --------------------------------------------------


def test_a_second_account_reuses_the_shared_index_sets_datasources_and_folder(monkeypatch):
    sibling = meta(
        instance_name="prod",
        streams="cloudtrail:s1,guardduty:s2",
        index_sets="cloudtrail:i1,guardduty:i2",
        datasources="cloudtrail:d1,guardduty:d2",
    )
    harness = Harness(monkeypatch, metas=[sibling], fail_on="save_meta")

    with pytest.raises(HTTPException):
        deploy(instance_name="staging")

    assert "create_index_set" not in harness.calls and "create_grafana_datasource" not in harness.calls
    assert "create_grafana_folder" not in harness.calls
    assert harness.calls.count("create_event_stream") == 2, "streams are always per account"
    # The rollback removes only what this run created.
    assert harness.undone() == ["UNDO_stream", "UNDO_stream", "UNDO_wazuh"]


# --- re-sync of a deployed instance -------------------------------------------------------------


def test_a_resync_keeps_existing_streams_and_adopts_its_buckets(monkeypatch):
    own = meta(streams="cloudtrail:s1,guardduty:s2", index_sets="cloudtrail:i1,guardduty:i2", datasources="cloudtrail:d1,guardduty:d2")
    harness = Harness(monkeypatch, metas=[own])

    deploy()

    assert harness.adopt_existing is True
    assert not [c for c in harness.calls if c.startswith("create_")]
    assert harness.saved_meta["stream_ids"] == {"cloudtrail": "s1", "guardduty": "s2"}


def test_a_service_added_on_resync_gets_its_own_resources(monkeypatch):
    own = meta(streams="cloudtrail:s1", index_sets="cloudtrail:i1", datasources="cloudtrail:d1")
    harness = Harness(monkeypatch, metas=[own])

    deploy()

    assert harness.calls.count("create_index_set") == 1
    assert harness.calls.count("create_event_stream") == 1
    assert harness.saved_meta["index_ids"]["cloudtrail"] == "i1"


def test_a_service_dropped_on_resync_is_removed_after_the_new_state_is_recorded(monkeypatch):
    own = meta(streams="cloudtrail:s1,guardduty:s2", index_sets="cloudtrail:i1,guardduty:i2", datasources="cloudtrail:d1,guardduty:d2")
    sibling = meta(instance_name="other", streams="guardduty:s9")
    harness = Harness(monkeypatch, metas=[own, sibling])

    deploy(auth_keys(services="cloudtrail"))

    removal = next(c for c in harness.calls if c.startswith("remove_resources"))
    assert removal == "remove_resources:guardduty:keep=guardduty", "the sibling still collects GuardDuty"
    assert harness.calls.index("mark_deployed") < harness.calls.index(removal)
    assert set(harness.saved_meta["stream_ids"]) == {"cloudtrail"}


# --- generic routes -----------------------------------------------------------------------------


def test_the_aws_secret_is_redacted_in_responses_but_readable_in_code():
    key = IntegrationAuthKeys(id=1, auth_key_name="SECRET_ACCESS_KEY", auth_value="the-secret", subscription_id=1)

    assert key.model_dump()["auth_value"] == REDACTED_AUTH_VALUE
    assert "the-secret" not in key.model_dump_json()
    assert key.auth_value == "the-secret", "provisioning reads the model attribute and needs the real value"


def test_other_auth_keys_are_not_redacted():
    key = IntegrationAuthKeys(id=1, auth_key_name="CLIENT_SECRET", auth_value="o365", subscription_id=1)

    assert key.model_dump()["auth_value"] == "o365"


@pytest.mark.parametrize("value, unchanged", [(REDACTED_AUTH_VALUE, True), ("", True), ("  ", True), ("new-secret", False)])
def test_sending_the_placeholder_back_keeps_the_stored_secret(value, unchanged):
    assert is_unchanged_secret("SECRET_ACCESS_KEY", value) is unchanged
    assert is_unchanged_secret("ACCESS_KEY_ID", "") is False


def _integration(**stored):
    return SimpleNamespace(
        integration_subscriptions=[
            SimpleNamespace(integration_auth_keys=[SimpleNamespace(auth_key_name=name, auth_value=value)]) for name, value in stored.items()
        ],
    )


def test_the_account_and_bucket_of_a_deployed_instance_cannot_change():
    integration = _integration(AWS_ACCOUNT_ID=ACCOUNT, BUCKET_NAME=BUCKET, SERVICES="cloudtrail")

    routes.ensure_aws_identity_unchanged(
        integration,
        [
            SimpleNamespace(auth_key_name="SERVICES", auth_value="cloudtrail,guardduty"),
            SimpleNamespace(auth_key_name="BUCKET_NAME", auth_value=BUCKET),
        ],
    )

    with pytest.raises(HTTPException) as err:
        routes.ensure_aws_identity_unchanged(integration, [SimpleNamespace(auth_key_name="BUCKET_NAME", auth_value="another-bucket")])
    assert "Delete the integration and add it again" in err.value.detail


def test_aws_is_multi_instance():
    assert "AWS" in routes.MULTI_INSTANCE_INTEGRATIONS


# --- account → customer -------------------------------------------------------------------------


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class _Session:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    async def execute(self, statement):
        self.statements.append(str(statement))
        return _Rows(self.rows)


def test_an_account_resolves_through_deployed_instances_only():
    from app.integrations.aws.services.account_lookup import (
        resolve_customer_code_from_aws_account,
    )

    session = _Session(["examplecorp"])

    assert run(resolve_customer_code_from_aws_account(ACCOUNT, session)) == "examplecorp"
    assert "customer_integrations.deployed is true" in session.statements[0].lower()


def test_an_account_claimed_by_two_customers_routes_to_neither():
    """Routing an alert to the wrong tenant is worse than not routing it."""
    from app.integrations.aws.services.account_lookup import (
        resolve_customer_code_from_aws_account,
    )

    assert run(resolve_customer_code_from_aws_account(ACCOUNT, _Session(["examplecorp", "othercorp"]))) is None


def test_another_customers_account_is_refused_when_the_integration_is_created(monkeypatch):
    from app.integrations.aws.services import account_lookup

    async def instances(session):
        return [account_lookup.AwsInstanceRecord("othercorp", None, ACCOUNT, BUCKET)]

    monkeypatch.setattr(account_lookup, "list_aws_instances", instances)

    with pytest.raises(HTTPException) as err:
        run(account_lookup.ensure_aws_account_not_owned_elsewhere("examplecorp", ACCOUNT, session=None))
    assert "othercorp" in err.value.detail

    # The same customer may hold the account again (another bucket), and an empty value is not checked.
    run(account_lookup.ensure_aws_account_not_owned_elsewhere("othercorp", ACCOUNT, session=None))
    run(account_lookup.ensure_aws_account_not_owned_elsewhere("examplecorp", "", session=None))
