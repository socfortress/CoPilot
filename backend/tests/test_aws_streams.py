"""AWS services, auth keys, Graylog streams and pipeline rules, and the per-service meta encoding.

The stream rules are what route a customer's AWS events out of the default stream, and the field
names in them are confirmed from real events (CloudTrail `data_aws_aws_account_id`, GuardDuty
`data_aws_accountId`). A wrong name matches nothing, silently, so they are pinned here.

No DB, no network.

Run with: cd backend && python -m pytest tests/test_aws_streams.py
"""

import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.integrations.aws.schema.provision import ProvisionAwsAuthKeys  # noqa: E402
from app.integrations.aws.services import provision  # noqa: E402
from app.integrations.aws.utils.services import AWS_SERVICES  # noqa: E402
from app.integrations.aws.utils.services import decode_service_ids  # noqa: E402
from app.integrations.aws.utils.services import encode_service_ids  # noqa: E402
from app.integrations.aws.utils.services import parse_services  # noqa: E402
from app.integrations.aws.utils.services import s3_log_prefix  # noqa: E402
from app.integrations.aws.utils.services import wazuh_date  # noqa: E402

ACCOUNT = "123456789012"
BUCKET = "example-cloudtrail-logs"


def keys(**overrides):
    values = {
        "ACCESS_KEY_ID": "AKIAABCDEFGHIJKLMNOP",
        "SECRET_ACCESS_KEY": "the-secret",
        "AWS_ACCOUNT_ID": ACCOUNT,
        "AWS_ACCOUNT_ALIAS": "",
        "AWS_ORGANIZATION_ID": "",
        "BUCKET_NAME": BUCKET,
        "SERVICES": "cloudtrail,guardduty:guardduty",
        "ONLY_LOGS_AFTER": "",
    }
    values.update(overrides)
    return ProvisionAwsAuthKeys(**values)


# --- streams ------------------------------------------------------------------------------------


def test_cloudtrail_stream_routes_on_bucket_service_and_cloudtrail_account_field():
    rules = provision.build_stream_rules(AWS_SERVICES["cloudtrail"], BUCKET, ACCOUNT)

    assert rules == [
        {"field": "data_aws_log_info_s3bucket", "type": 1, "inverted": False, "value": BUCKET},
        {"field": "data_aws_source", "type": 1, "inverted": False, "value": "cloudtrail"},
        {"field": "data_aws_aws_account_id", "type": 1, "inverted": False, "value": ACCOUNT},
    ]


def test_guardduty_stream_routes_on_the_guardduty_account_field():
    rules = provision.build_stream_rules(AWS_SERVICES["guardduty"], BUCKET, ACCOUNT)

    assert {rule["field"]: rule["value"] for rule in rules} == {
        "data_aws_log_info_s3bucket": BUCKET,
        "data_aws_source": "guardduty",
        "data_aws_accountId": ACCOUNT,
    }


def test_a_stream_is_and_matched_and_leaves_the_default_stream():
    stream = provision.build_event_stream_config("ExampleCorp", AWS_SERVICES["guardduty"], keys(), "index-1", instance_name="prod")

    assert stream.matching_type == "AND"
    assert stream.remove_matches_from_default_stream is True
    assert stream.title == "ExampleCorp - AWS GuardDuty - prod"
    assert stream.index_set_id == "index-1"


def test_the_index_set_is_per_customer_and_service():
    index_set = provision.build_index_set_config("ExampleCorp", "ExampleCorp", AWS_SERVICES["cloudtrail"], shards=1)

    assert index_set.index_prefix == "cloudtrail-examplecorp"
    assert index_set.title == "ExampleCorp - AWS CloudTrail"
    assert index_set.rotation_strategy.rotation_period == "P1D"
    # The shared schema does not carry `rotate_empty_index_set`; Graylog's default for it is false.
    assert "rotate_empty_index_set" not in index_set.model_dump()["rotation_strategy"]
    assert index_set.retention_strategy.max_number_of_indices == 30
    assert index_set.replicas == 0


# --- pipeline -----------------------------------------------------------------------------------


def test_the_account_rule_covers_every_services_account_field():
    source = provision.aws_rule_sources()["AWS ACCOUNT ID"]

    for definition in AWS_SERVICES.values():
        assert f'has_field("{definition.account_field}")' in source
    assert 'set_field("aws_account_id", to_string($message.data_aws_aws_account_id, to_string($message.data_aws_accountId)));' in source


def test_the_timestamp_rule_reads_eventtime_then_updatedat():
    source = provision.aws_rule_sources()["AWS Timestamp - UTC"]

    assert 'set_field("timestamp_utc", to_string($message.data_aws_eventTime, to_string($message.data_aws_updatedAt)));' in source


def test_the_pipeline_runs_every_rule_including_the_shared_wazuh_levels():
    source = provision.aws_pipeline_source()

    for title in (
        "WAZUH CREATE FIELD SYSLOG LEVEL - INFO",
        "WAZUH CREATE FIELD SYSLOG LEVEL - ALERT",
        "SYSLOG TYPE AWS",
        "AWS Timestamp - UTC",
        "AWS ACCOUNT ID",
    ):
        assert f'rule "{title}"' in source
    assert source.startswith('pipeline "AWS PROCESSING PIPELINE"\nstage 0 match either\n')


def test_rule_sources_compare_whitespace_insensitively():
    source = provision.aws_rule_sources()["SYSLOG TYPE AWS"]

    assert provision._same_source(source.replace("\n", "\r\n  "), source)
    assert not provision._same_source(source.replace("aws", "azure"), source)


# --- SERVICES -----------------------------------------------------------------------------------


def test_services_parse_with_optional_prefixes():
    configs = parse_services(" cloudtrail , guardduty:/guardduty/ ")

    assert [(c.key, c.prefix) for c in configs] == [("cloudtrail", None), ("guardduty", "guardduty")]


@pytest.mark.parametrize(
    "raw, message",
    [
        ("vpcflow", "not supported yet"),
        ("cloudtrail,cloudtrail", "more than once"),
        ("", "empty"),
        ("guardduty:bad<prefix>", "characters"),
        ("route53", "Unknown AWS service"),
    ],
)
def test_bad_services_are_refused(raw, message):
    with pytest.raises(ValueError) as err:
        parse_services(raw)

    assert message in str(err.value)


def test_s3_prefixes_follow_the_wazuh_layout():
    cloudtrail, guardduty = parse_services("cloudtrail,guardduty:guardduty")

    assert s3_log_prefix(cloudtrail, ACCOUNT) == f"AWSLogs/{ACCOUNT}/CloudTrail/"
    assert s3_log_prefix(cloudtrail, ACCOUNT, "o-a1b2c3d4e5") == f"AWSLogs/o-a1b2c3d4e5/{ACCOUNT}/CloudTrail/"
    assert s3_log_prefix(guardduty, ACCOUNT, "o-a1b2c3d4e5") == f"guardduty/AWSLogs/{ACCOUNT}/GuardDuty/"


# --- auth keys ----------------------------------------------------------------------------------


def test_the_secret_never_appears_when_the_keys_are_printed():
    auth_keys = keys(SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG")

    assert "wJalrXUtnFEMI" not in repr(auth_keys)
    assert "wJalrXUtnFEMI" not in str(auth_keys)
    assert auth_keys.SECRET_ACCESS_KEY.get_secret_value() == "wJalrXUtnFEMI/K7MDENG"


def test_blank_optional_keys_mean_unset_and_the_start_date_defaults():
    auth_keys = keys()

    assert auth_keys.AWS_ACCOUNT_ALIAS is None and auth_keys.AWS_ORGANIZATION_ID is None and auth_keys.ONLY_LOGS_AFTER is None
    assert len(auth_keys.only_logs_after()) == len("2026-OCT-08")


@pytest.mark.parametrize(
    "field, value",
    [
        ("AWS_ACCOUNT_ID", "96717015228"),
        ("AWS_ORGANIZATION_ID", "org-123"),
        ("BUCKET_NAME", "Bad_Bucket"),
        ("ONLY_LOGS_AFTER", "2026-10-08"),
        ("ONLY_LOGS_AFTER", "2026-FEB-30"),
        ("SERVICES", "vpcflow"),
    ],
)
def test_bad_auth_keys_are_refused(field, value):
    with pytest.raises(ValidationError):
        keys(**{field: value})


def test_a_validation_error_never_echoes_the_secret():
    with pytest.raises(ValidationError) as err:
        keys(SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG", AWS_ACCOUNT_ID="nope")

    assert "wJalrXUtnFEMI" not in str(err.value)


def test_wazuh_dates_use_english_months():
    from datetime import datetime

    assert wazuh_date(datetime(2026, 10, 8)) == "2026-OCT-08"
    assert keys(ONLY_LOGS_AFTER="2026-oct-08").ONLY_LOGS_AFTER == "2026-OCT-08"


# --- meta ---------------------------------------------------------------------------------------


def test_per_service_ids_round_trip_through_one_column():
    ids = {"guardduty": "66a1", "cloudtrail": "66f2"}

    encoded = encode_service_ids(ids)

    assert encoded == "cloudtrail:66f2,guardduty:66a1"
    assert decode_service_ids(encoded) == ids
    assert decode_service_ids(None) == {} and decode_service_ids("") == {}
    assert decode_service_ids("legacy-id-without-service") == {}
