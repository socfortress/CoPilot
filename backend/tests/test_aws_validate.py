"""Checking AWS credentials from CoPilot before anything is provisioned.

Each failure the Wazuh master would hit later — a wrong key, a key from another account, a bucket
the user may not list, logs it may not decrypt, an empty prefix — must stop the deployment with a
message that says which, before ossec.conf is touched. Not being able to reach AWS from CoPilot is
different: the master may well reach it, so that only warns.

No network: boto3's session is replaced by fakes.

Run with: cd backend && python -m pytest tests/test_aws_validate.py
"""

import os

import pytest
from botocore.exceptions import ClientError
from botocore.exceptions import EndpointConnectionError

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.integrations.aws.schema.provision import ProvisionAwsAuthKeys  # noqa: E402
from app.integrations.aws.services import validate  # noqa: E402

ACCOUNT = "123456789012"
BUCKET = "example-cloudtrail-logs"
SECRET = "wJalrXUtnFEMI/K7MDENG"


def client_error(code, message="", headers=None):
    return ClientError(
        {"Error": {"Code": code, "Message": message}, "ResponseMetadata": {"HTTPHeaders": headers or {}}},
        "Operation",
    )


class FakeBody:
    def close(self):
        pass


class FakeAws:
    """Scriptable STS and S3; each attribute is a value to return or an exception to raise."""

    def __init__(self, **overrides):
        self.identity = {"Account": ACCOUNT}
        self.head = {"ResponseMetadata": {"HTTPHeaders": {"x-amz-bucket-region": "eu-west-1"}}}
        self.listing = {
            f"AWSLogs/{ACCOUNT}/CloudTrail/": {
                "Contents": [{"Key": f"AWSLogs/{ACCOUNT}/CloudTrail/eu-west-1/2026/10/08/a.json.gz", "Size": 900}],
            },
            f"guardduty/AWSLogs/{ACCOUNT}/GuardDuty/": {
                "Contents": [
                    {"Key": f"guardduty/AWSLogs/{ACCOUNT}/GuardDuty/", "Size": 0},
                    {"Key": f"guardduty/AWSLogs/{ACCOUNT}/GuardDuty/eu-west-1/2026/10/08/b.jsonl.gz", "Size": 500},
                ],
            },
        }
        self.get = {"Body": FakeBody()}
        # Per service prefix, the region folders under it; per dated prefix, its listing.
        self.regions = {}
        self.dated = {}
        self.read_keys = []
        self.s3_region = None
        self.__dict__.update(overrides)

    @staticmethod
    def _answer(value):
        if isinstance(value, Exception):
            raise value
        return value

    def session(self, **credentials):
        assert credentials["aws_secret_access_key"] == SECRET
        fake = self

        class Session:
            def client(self, service, region_name=None, config=None):
                if service == "sts":
                    return type("Sts", (), {"get_caller_identity": lambda _self: fake._answer(fake.identity)})()
                fake.s3_region = region_name
                return S3()

        class S3:
            def head_bucket(self, Bucket):
                return fake._answer(fake.head)

            def list_objects_v2(self, Bucket, Prefix, MaxKeys=1000, Delimiter=None):
                if isinstance(fake.listing, Exception):
                    raise fake.listing
                if Delimiter:
                    # Region "folders" directly under the service prefix.
                    regions = fake.regions.get(Prefix, [])
                    return {"CommonPrefixes": [{"Prefix": f"{Prefix}{region}/"} for region in regions]}
                if Prefix in fake.dated:
                    return fake.dated[Prefix]
                return fake.listing.get(Prefix, {"Contents": []})

            def get_object(self, Bucket, Key, Range):
                assert Range == "bytes=0-0", "only one byte is ever read"
                fake.read_keys.append(Key)
                return fake._answer(fake.get)

        return Session()


def auth_keys(**overrides):
    values = {
        "ACCESS_KEY_ID": "AKIAABCDEFGHIJKLMNOP",
        "SECRET_ACCESS_KEY": SECRET,
        "AWS_ACCOUNT_ID": ACCOUNT,
        "BUCKET_NAME": BUCKET,
        "SERVICES": "cloudtrail,guardduty:guardduty",
    }
    values.update(overrides)
    return ProvisionAwsAuthKeys(**values)


def check(monkeypatch, fake, **overrides):
    monkeypatch.setattr(validate.boto3, "Session", fake.session)
    keys = auth_keys(**overrides)
    return validate._validate(keys, keys.service_configs())


def expect_failure(monkeypatch, fake, fragment, **overrides):
    with pytest.raises(validate.AwsValidationError) as err:
        check(monkeypatch, fake, **overrides)
    assert fragment in str(err.value)
    assert SECRET not in str(err.value)
    return str(err.value)


def test_good_credentials_pass_and_read_one_real_object_per_service(monkeypatch):
    fake = FakeAws()

    result = check(monkeypatch, fake)

    assert result.validated and result.bucket_region == "eu-west-1" and not result.warnings
    assert fake.s3_region == "eu-west-1"
    assert [key.rsplit("/", 1)[-1] for key in fake.read_keys] == ["a.json.gz", "b.jsonl.gz"], "folder markers are skipped"


def test_a_rejected_key_is_named(monkeypatch):
    expect_failure(monkeypatch, FakeAws(identity=client_error("InvalidClientTokenId")), "rejected the access key")


def test_a_key_from_another_account_is_refused(monkeypatch):
    message = expect_failure(monkeypatch, FakeAws(identity={"Account": "111122223333"}), "belongs to AWS account 111122223333")
    assert ACCOUNT in message


def test_a_missing_bucket_is_named(monkeypatch):
    expect_failure(monkeypatch, FakeAws(head=client_error("404")), "does not exist")


def test_a_bucket_in_another_region_is_followed(monkeypatch):
    fake = FakeAws(head=client_error("301", headers={"x-amz-bucket-region": "ap-southeast-2"}))

    assert check(monkeypatch, fake).bucket_region == "ap-southeast-2"


def test_a_denied_listing_is_named(monkeypatch):
    expect_failure(monkeypatch, FakeAws(listing=client_error("AccessDenied")), "s3:ListBucket denied")


def test_an_empty_prefix_is_named(monkeypatch):
    fake = FakeAws()
    del fake.listing[f"guardduty/AWSLogs/{ACCOUNT}/GuardDuty/"]

    expect_failure(monkeypatch, fake, "GuardDuty: no logs found under s3://example-cloudtrail-logs/guardduty/AWSLogs/")


def test_a_kms_denial_is_told_apart_from_an_s3_denial(monkeypatch):
    kms = client_error("AccessDenied", "User is not authorized to perform: kms:Decrypt on the resource")
    expect_failure(monkeypatch, FakeAws(get=kms), "kms:Decrypt denied")

    expect_failure(monkeypatch, FakeAws(get=client_error("AccessDenied", "Access Denied")), "s3:GetObject denied")


def test_an_unreachable_aws_only_warns(monkeypatch):
    fake = FakeAws(identity=EndpointConnectionError(endpoint_url="https://sts.amazonaws.com"))

    result = check(monkeypatch, fake)

    assert not result.validated
    assert "could not reach AWS" in result.warnings[0]
    assert SECRET not in result.warnings[0]


def test_an_organization_trail_is_looked_up_under_the_organization(monkeypatch):
    fake = FakeAws()
    fake.listing[f"AWSLogs/o-a1b2c3d4e5/{ACCOUNT}/CloudTrail/"] = fake.listing.pop(f"AWSLogs/{ACCOUNT}/CloudTrail/")

    assert check(monkeypatch, fake, AWS_ORGANIZATION_ID="o-a1b2c3d4e5").validated


def test_a_recent_log_is_preferred_over_the_oldest(monkeypatch):
    """Found against a real bucket: the oldest CloudTrail logs were archived to Glacier."""
    from datetime import datetime
    from datetime import timezone

    today = datetime.now(timezone.utc).date()
    prefix = f"AWSLogs/{ACCOUNT}/CloudTrail/"
    fake = FakeAws()
    fake.regions[prefix] = ["eu-west-1"]
    fake.dated[f"{prefix}eu-west-1/{today:%Y/%m/%d}/"] = {
        "Contents": [{"Key": f"{prefix}eu-west-1/{today:%Y/%m/%d}/today.json.gz", "Size": 10}],
    }
    fake.listing[prefix] = {"Contents": [{"Key": f"{prefix}ap-northeast-1/2025/10/14/old.json.gz", "Size": 10, "StorageClass": "GLACIER"}]}

    assert check(monkeypatch, fake, SERVICES="cloudtrail").validated
    assert fake.read_keys[0].endswith("today.json.gz")


def test_archived_logs_are_skipped(monkeypatch):
    prefix = f"AWSLogs/{ACCOUNT}/CloudTrail/"
    fake = FakeAws()
    fake.listing[prefix] = {
        "Contents": [
            {"Key": f"{prefix}a/old.json.gz", "Size": 10, "StorageClass": "DEEP_ARCHIVE"},
            {"Key": f"{prefix}b/readable.json.gz", "Size": 10, "StorageClass": "STANDARD"},
        ],
    }

    check(monkeypatch, fake, SERVICES="cloudtrail")

    assert fake.read_keys == [f"{prefix}b/readable.json.gz"]


def test_only_archived_logs_warn_instead_of_failing(monkeypatch):
    prefix = f"guardduty/AWSLogs/{ACCOUNT}/GuardDuty/"
    fake = FakeAws()
    fake.listing[prefix] = {"Contents": [{"Key": f"{prefix}eu-west-1/2025/01/01/x.jsonl.gz", "Size": 10, "StorageClass": "GLACIER"}]}

    result = check(monkeypatch, fake, SERVICES="guardduty:guardduty")

    assert result.validated
    assert "could not be checked" in result.warnings[0] and "kms:Decrypt" in result.warnings[0]
    assert fake.read_keys == []
