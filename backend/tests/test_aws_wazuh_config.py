"""Editing the Wazuh manager's aws-s3 wodle for one AWS integration instance.

One `<wodle name="aws-s3">` holds every customer's `<bucket>` entries, so provisioning and
decommissioning one instance must touch that instance's buckets and nothing else — another
customer's buckets, the wodle's own settings, comments and unrelated `<ossec_config>` blocks all
have to come through byte-for-byte. These tests pin that, plus the refusals that keep the manager
from collecting the same logs twice.

No DB, no network: `reconcile_aws_buckets` is a pure string transformation.

Run with: cd backend && python -m pytest tests/test_aws_wazuh_config.py
"""

import os
import xml.etree.ElementTree as ET

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.integrations.aws.schema.provision import ProvisionAwsAuthKeys  # noqa: E402
from app.integrations.aws.services.wazuh_config import AwsWazuhConfigError  # noqa: E402
from app.integrations.aws.services.wazuh_config import desired_buckets  # noqa: E402
from app.integrations.aws.services.wazuh_config import parse_ossec_config  # noqa: E402
from app.integrations.aws.services.wazuh_config import (  # noqa: E402
    reconcile_aws_buckets,
)
from app.integrations.aws.services.wazuh_config import (  # noqa: E402
    verify_only_instance_changed,
)

ACCOUNT = "123456789012"
BUCKET = "example-cloudtrail-logs"

OTHER_CUSTOMER_BUCKET = """<bucket type="cloudtrail">
      <name>acme-trail</name>
      <access_key>AKIAOTHERCUSTOMER000</access_key>
      <secret_key>other-secret</secret_key>
      <aws_account_id>111122223333</aws_account_id>
      <only_logs_after>2025-JAN-01</only_logs_after>
    </bucket>"""

BASE = """<ossec_config>
  <!-- engineer's note: do not touch -->
  <global>
    <jsonout_output>yes</jsonout_output>
  </global>
</ossec_config>

<ossec_config>
  <localfile>
    <location>/var/log/syslog</location>
  </localfile>
</ossec_config>
"""

WITH_WODLE = """<ossec_config>
  <!-- engineer's note: do not touch -->
  <global>
    <jsonout_output>yes</jsonout_output>
  </global>
  <wodle name="aws-s3">
    <disabled>no</disabled>
    <interval>30m</interval>
    <run_on_start>yes</run_on_start>
    <skip_on_error>yes</skip_on_error>
    OTHER_CUSTOMER_BUCKET
  </wodle>
</ossec_config>
""".replace(
    "OTHER_CUSTOMER_BUCKET",
    OTHER_CUSTOMER_BUCKET,
)


def keys(**overrides):
    values = {
        "ACCESS_KEY_ID": "AKIAABCDEFGHIJKLMNOP",
        "SECRET_ACCESS_KEY": "the-secret",
        "AWS_ACCOUNT_ID": ACCOUNT,
        "AWS_ACCOUNT_ALIAS": "example",
        "AWS_ORGANIZATION_ID": "",
        "BUCKET_NAME": BUCKET,
        "SERVICES": "cloudtrail,guardduty:guardduty",
        "ONLY_LOGS_AFTER": "2026-OCT-08",
    }
    values.update(overrides)
    return ProvisionAwsAuthKeys(**values)


def provision(raw, auth_keys=None, adopt_existing=False, **kwargs):
    auth_keys = auth_keys or keys()
    return reconcile_aws_buckets(
        raw,
        desired_buckets(auth_keys),
        auth_keys.BUCKET_NAME,
        auth_keys.AWS_ACCOUNT_ID,
        adopt_existing=adopt_existing,
        **kwargs,
    )


def remove(raw, bucket=BUCKET, account=ACCOUNT):
    return reconcile_aws_buckets(raw, [], bucket, account, adopt_existing=True)


def buckets(raw):
    wrapper = parse_ossec_config(raw)
    return [bucket for wodle in wrapper.iter("wodle") if wodle.get("name") == "aws-s3" for bucket in wodle.findall("bucket")]


def bucket_of_type(raw, bucket_type, name=BUCKET):
    return next(b for b in buckets(raw) if b.get("type") == bucket_type and b.findtext("name") == name)


def aws_wodles(raw):
    return [w for w in parse_ossec_config(raw).iter("wodle") if w.get("name") == "aws-s3"]


# --- creating -------------------------------------------------------------------------------------


def test_the_wodle_is_created_with_the_defaults_when_absent():
    result = provision(BASE)

    assert result.changed and result.wodle_created
    assert result.added == ["cloudtrail", "guardduty"]
    (wodle,) = aws_wodles(result.config)
    assert [(child.tag, child.text) for child in list(wodle)[:4]] == [
        ("disabled", "no"),
        ("interval", "10m"),
        ("run_on_start", "yes"),
        ("skip_on_error", "yes"),
    ]


def test_buckets_have_the_documented_shape():
    result = provision(BASE)

    cloudtrail = bucket_of_type(result.config, "cloudtrail")
    assert [child.tag for child in cloudtrail] == [
        "name",
        "access_key",
        "secret_key",
        "aws_account_id",
        "aws_account_alias",
        "only_logs_after",
    ]
    assert cloudtrail.findtext("secret_key") == "the-secret"
    assert cloudtrail.findtext("only_logs_after") == "2026-OCT-08"

    guardduty = bucket_of_type(result.config, "guardduty")
    assert guardduty.findtext("path") == "guardduty"
    # The account scopes the wodle to this customer's logs even on a shared bucket.
    assert guardduty.findtext("aws_account_id") == ACCOUNT


def test_never_remove_from_bucket_and_never_regions():
    result = provision(BASE)

    for bucket in buckets(result.config):
        assert bucket.find("remove_from_bucket") is None
        assert bucket.find("regions") is None


def test_organization_id_only_when_given_and_only_on_cloudtrail():
    assert bucket_of_type(provision(BASE).config, "cloudtrail").find("aws_organization_id") is None

    result = provision(BASE, keys(AWS_ORGANIZATION_ID="o-a1b2c3d4e5"))
    assert bucket_of_type(result.config, "cloudtrail").findtext("aws_organization_id") == "o-a1b2c3d4e5"
    assert bucket_of_type(result.config, "guardduty").find("aws_organization_id") is None


def test_comments_and_other_ossec_config_blocks_survive():
    result = provision(BASE)

    assert "<!-- engineer's note: do not touch -->" in result.config
    assert result.config.count("<ossec_config>") == 2
    assert "<location>/var/log/syslog</location>" in result.config
    assert len(aws_wodles(result.config)) == 1, "the wodle goes into the first block only"


# --- adding to an existing wodle ------------------------------------------------------------------


def test_buckets_are_added_to_an_existing_wodle_without_changing_its_settings():
    result = provision(WITH_WODLE)

    assert not result.wodle_created
    (wodle,) = aws_wodles(result.config)
    assert wodle.findtext("interval") == "30m", "an existing wodle's settings are the operator's"
    assert [b.findtext("name") for b in wodle.findall("bucket")] == ["acme-trail", BUCKET, BUCKET]


def test_another_customers_bucket_is_left_exactly_as_it_was():
    result = provision(WITH_WODLE)

    other = bucket_of_type(result.config, "cloudtrail", name="acme-trail")
    original = ET.fromstring(OTHER_CUSTOMER_BUCKET)
    assert ET.canonicalize(ET.tostring(other), strip_text=True) == ET.canonicalize(ET.tostring(original), strip_text=True)


def test_a_disabled_wodle_is_reported_and_not_enabled():
    raw = WITH_WODLE.replace("<disabled>no</disabled>", "<disabled>yes</disabled>")

    result = provision(raw)

    assert result.wodle_disabled
    assert aws_wodles(result.config)[0].findtext("disabled") == "yes"


# --- duplicates -----------------------------------------------------------------------------------


def test_a_hand_configured_bucket_for_the_same_account_is_refused():
    deployed = provision(BASE).config

    with pytest.raises(AwsWazuhConfigError) as err:
        # A first deployment of an instance whose buckets are already on the manager.
        provision(deployed, adopt_existing=False)

    assert "already collects" in str(err.value)
    assert BUCKET in str(err.value)


def test_a_bucket_without_an_account_overlaps_every_account():
    raw = WITH_WODLE.replace(
        OTHER_CUSTOMER_BUCKET,
        '<bucket type="cloudtrail">\n      <name>' + BUCKET + "</name>\n      <aws_profile>examplecorp</aws_profile>\n    </bucket>",
    )

    with pytest.raises(AwsWazuhConfigError):
        provision(raw)


def test_the_same_bucket_for_another_account_is_not_a_duplicate():
    """An organization bucket legitimately holds several accounts, each its own instance."""
    first = provision(BASE).config

    result = provision(first, keys(AWS_ACCOUNT_ID="444455556666"))

    assert result.added == ["cloudtrail", "guardduty"]
    assert len(buckets(result.config)) == 4


def test_a_refused_deployment_changes_nothing():
    deployed = provision(BASE).config

    with pytest.raises(AwsWazuhConfigError):
        provision(deployed)

    # Nothing to compare against but the input itself: the function raised before serializing.
    assert len(buckets(deployed)) == 2


# --- re-sync of a deployed instance ---------------------------------------------------------------


def test_key_rotation_updates_only_the_keys():
    deployed = provision(WITH_WODLE).config

    result = provision(deployed, keys(ACCESS_KEY_ID="AKIANEWKEY0000000000", SECRET_ACCESS_KEY="rotated"), adopt_existing=True)

    assert result.updated == ["cloudtrail", "guardduty"] and not result.added and not result.removed
    for bucket_type in ("cloudtrail", "guardduty"):
        bucket = bucket_of_type(result.config, bucket_type)
        assert bucket.findtext("access_key") == "AKIANEWKEY0000000000"
        assert bucket.findtext("secret_key") == "rotated"
    assert bucket_of_type(result.config, "cloudtrail", name="acme-trail").findtext("secret_key") == "other-secret"


def test_a_resync_without_an_explicit_start_date_keeps_the_existing_one():
    deployed = provision(BASE).config

    result = provision(deployed, keys(ONLY_LOGS_AFTER="", SECRET_ACCESS_KEY="rotated"), adopt_existing=True)

    assert bucket_of_type(result.config, "cloudtrail").findtext("only_logs_after") == "2026-OCT-08"


def test_an_unchanged_resync_changes_nothing():
    deployed = provision(BASE).config

    result = provision(deployed, adopt_existing=True)

    assert not result.changed
    assert result.config == deployed


def test_a_service_can_be_added_to_a_deployed_instance():
    deployed = provision(BASE, keys(SERVICES="cloudtrail")).config
    assert [b.get("type") for b in buckets(deployed)] == ["cloudtrail"]

    result = provision(deployed, keys(SERVICES="cloudtrail,guardduty:guardduty"), adopt_existing=True)

    assert result.added == ["guardduty"] and not result.updated
    assert sorted(b.get("type") for b in buckets(result.config)) == ["cloudtrail", "guardduty"]


def test_a_service_dropped_from_services_is_removed():
    deployed = provision(BASE).config

    result = provision(deployed, keys(SERVICES="cloudtrail"), adopt_existing=True)

    assert result.removed == ["guardduty"]
    assert [b.get("type") for b in buckets(result.config)] == ["cloudtrail"]


def test_the_previous_buckets_are_returned_for_a_rollback():
    deployed = provision(BASE).config

    result = provision(deployed, keys(SECRET_ACCESS_KEY="rotated"), adopt_existing=True)
    restored = reconcile_aws_buckets(result.config, result.previous, BUCKET, ACCOUNT, adopt_existing=True, keep_only_logs_after=False)

    assert bucket_of_type(restored.config, "cloudtrail").findtext("secret_key") == "the-secret"


# --- removing -------------------------------------------------------------------------------------


def test_removing_one_instance_leaves_another_customers_buckets_untouched():
    deployed = provision(WITH_WODLE).config

    result = remove(deployed)

    assert sorted(result.removed) == ["cloudtrail", "guardduty"]
    assert not result.wodle_removed
    assert [b.findtext("name") for b in buckets(result.config)] == ["acme-trail"]
    assert aws_wodles(result.config)[0].findtext("interval") == "30m"


def test_removing_one_account_leaves_another_account_of_the_same_bucket():
    first = provision(BASE).config
    both = provision(first, keys(AWS_ACCOUNT_ID="444455556666")).config

    result = remove(both, account="444455556666")

    assert {b.findtext("aws_account_id") for b in buckets(result.config)} == {ACCOUNT}


def test_removing_the_last_bucket_removes_the_wodle():
    deployed = provision(BASE).config

    result = remove(deployed)

    assert result.wodle_removed
    assert aws_wodles(result.config) == []
    assert "<!-- engineer's note: do not touch -->" in result.config


def test_a_wodle_with_services_survives_its_last_bucket():
    raw = BASE.replace(
        "</global>",
        """</global>
  <wodle name="aws-s3">
    <disabled>no</disabled>
    <service type="cloudwatchlogs">
      <aws_profile>default</aws_profile>
      <aws_log_groups>example</aws_log_groups>
    </service>
  </wodle>""",
        1,
    )
    deployed = provision(raw).config

    result = remove(deployed)

    assert not result.wodle_removed
    assert aws_wodles(result.config)[0].find("service") is not None


def test_removing_an_instance_that_is_not_configured_is_not_an_error():
    result = remove(WITH_WODLE)

    assert not result.changed
    assert result.config == WITH_WODLE


def test_an_unparseable_configuration_is_refused():
    with pytest.raises(AwsWazuhConfigError):
        provision("<ossec_config><global></ossec_config>")


# --- the safety net -------------------------------------------------------------------------------


def test_the_guard_accepts_a_change_to_this_instance_only():
    result = provision(WITH_WODLE)

    verify_only_instance_changed(WITH_WODLE, result.config, BUCKET, ACCOUNT)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda c: c.replace("<jsonout_output>yes</jsonout_output>", "<jsonout_output>no</jsonout_output>"),
        lambda c: c.replace("other-secret", "changed"),
        lambda c: c.replace("<interval>30m</interval>", "<interval>10m</interval>"),
        lambda c: c.replace("<!-- engineer's note: do not touch -->", ""),
        lambda c: c.replace("<global>", "<removed>").replace("</global>", "</removed>"),
    ],
    ids=["another-block", "another-customers-bucket", "wodle-setting", "comment", "element-renamed"],
)
def test_the_guard_refuses_anything_beyond_this_instance(tamper):
    """However the edit went wrong, a file differing outside this instance's buckets is never pushed."""
    result = provision(WITH_WODLE)

    with pytest.raises(AwsWazuhConfigError) as err:
        verify_only_instance_changed(WITH_WODLE, tamper(result.config), BUCKET, ACCOUNT)

    assert "Nothing was written" in str(err.value)


def test_the_guard_refuses_a_lost_block():
    result = provision(BASE)
    truncated = result.config[: result.config.index("<ossec_config>", 10)]

    with pytest.raises(AwsWazuhConfigError):
        verify_only_instance_changed(BASE, truncated, BUCKET, ACCOUNT)


def test_an_empty_configuration_is_refused():
    with pytest.raises(AwsWazuhConfigError):
        provision("   ")


def test_a_dtd_is_refused():
    raw = '<!DOCTYPE x [<!ENTITY a "aaaa">]>' + BASE

    with pytest.raises(AwsWazuhConfigError):
        provision(raw)


def test_a_masked_configuration_is_never_written_back():
    raw = WITH_WODLE.replace("other-secret", "*****")

    with pytest.raises(AwsWazuhConfigError) as err:
        provision(raw)

    assert "masked" in str(err.value)
