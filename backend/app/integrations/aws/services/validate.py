"""Checking an AWS instance's credentials from CoPilot before anything is provisioned.

The Wazuh master is what reads the bucket, but a bad key only shows up there as a warning in
`ossec.log` minutes later. Running the same reads from CoPilot first turns that into an error on the
Deploy button, before ossec.conf, Graylog or Grafana are touched:

1. `sts.get_caller_identity()` — the key works, and belongs to `AWS_ACCOUNT_ID`.
2. `s3.head_bucket` — the bucket exists and is readable (and tells us its region).
3. `s3.list_objects_v2` on each service's prefix — `s3:ListBucket`, and logs actually exist there.
4. `s3.get_object` on one *recent* object per service, one byte only — `s3:GetObject` and, for
   KMS-encrypted exports such as GuardDuty's, `kms:Decrypt`. Recent, because older logs are often
   archived to Glacier and unreadable regardless of permissions; when only archived logs exist,
   read access is reported as unchecked rather than failed.

CoPilot does not always have a route to AWS when the Wazuh master does. A *network* failure is
therefore not fatal: the checks are skipped with a warning and the deployment goes ahead. A
credential or permission failure is fatal, because the master would fail the same way.

boto3 is synchronous, so the checks run in a worker thread. No message produced here contains the
secret access key.
"""

import asyncio
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Optional
from typing import Tuple

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError
from botocore.exceptions import ClientError
from botocore.exceptions import ConnectionClosedError
from botocore.exceptions import ConnectTimeoutError
from botocore.exceptions import EndpointConnectionError
from botocore.exceptions import ProxyConnectionError
from botocore.exceptions import ReadTimeoutError
from loguru import logger

from app.integrations.aws.schema.provision import ProvisionAwsAuthKeys
from app.integrations.aws.utils.services import AwsServiceConfig
from app.integrations.aws.utils.services import s3_log_prefix

_NETWORK_ERRORS = (EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError, ConnectionClosedError, ProxyConnectionError)
_BAD_CREDENTIAL_CODES = {
    "InvalidClientTokenId",
    "SignatureDoesNotMatch",
    "UnrecognizedClientException",
    "InvalidAccessKeyId",
    "AuthFailure",
}
_BOTO_CONFIG = Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 2, "mode": "standard"})
# How many keys to look at when searching a prefix for a real log object (skipping folder markers).
_LIST_PAGE = 25
# How many days back (today included) to look for a recent log before falling back to the oldest.
_RECENT_DAYS = 3
# Storage classes GetObject cannot read without a restore. GLACIER_IR (instant retrieval) is readable.
_ARCHIVED_STORAGE_CLASSES = {"GLACIER", "DEEP_ARCHIVE"}


class AwsValidationError(Exception):
    """A check failed in a way the Wazuh master would fail too. The message is fit to show the operator."""


@dataclass
class AwsValidationResult:
    validated: bool
    bucket_region: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class _Unreachable(Exception):
    pass


def _error_code(err: ClientError) -> str:
    return str(err.response.get("Error", {}).get("Code", ""))


def _error_message(err: ClientError) -> str:
    return str(err.response.get("Error", {}).get("Message", "")) or _error_code(err)


def _region_from_error(err: ClientError) -> Optional[str]:
    headers = err.response.get("ResponseMetadata", {}).get("HTTPHeaders", {})
    return headers.get("x-amz-bucket-region")


def _call(description: str, fn, **kwargs):
    """Run one AWS call, turning network failures into `_Unreachable`."""
    try:
        return fn(**kwargs)
    except _NETWORK_ERRORS as e:
        raise _Unreachable(f"{description}: {e}")


def _check_identity(session: boto3.Session, account_id: str) -> None:
    sts = session.client("sts", region_name="us-east-1", config=_BOTO_CONFIG)
    try:
        identity = _call("sts:GetCallerIdentity", sts.get_caller_identity)
    except ClientError as e:
        if _error_code(e) in _BAD_CREDENTIAL_CODES:
            raise AwsValidationError("AWS rejected the access key: ACCESS_KEY_ID or SECRET_ACCESS_KEY is wrong, or the key is inactive.")
        raise AwsValidationError(f"AWS refused sts:GetCallerIdentity: {_error_message(e)}")

    actual = identity.get("Account")
    if actual != account_id:
        raise AwsValidationError(
            f"The access key belongs to AWS account {actual}, not AWS_ACCOUNT_ID {account_id}. "
            "Correct AWS_ACCOUNT_ID or use a key from that account.",
        )


def _bucket_region(session: boto3.Session, bucket: str) -> str:
    s3 = session.client("s3", region_name="us-east-1", config=_BOTO_CONFIG)
    try:
        response = _call("s3:HeadBucket", s3.head_bucket, Bucket=bucket)
        return response.get("ResponseMetadata", {}).get("HTTPHeaders", {}).get("x-amz-bucket-region") or "us-east-1"
    except ClientError as e:
        region = _region_from_error(e)
        code = _error_code(e)
        if code in ("404", "NoSuchBucket"):
            raise AwsValidationError(f"S3 bucket {bucket} does not exist. Check BUCKET_NAME.")
        if code in ("301", "PermanentRedirect", "400") and region:
            # Wrong region for the request; the response still names the right one.
            return region
        if code in ("403", "AccessDenied"):
            raise AwsValidationError(
                f"The IAM user may not read S3 bucket {bucket} (s3:ListBucket denied). Check the bucket policy and the user's policy.",
            )
        raise AwsValidationError(f"Could not reach S3 bucket {bucket}: {_error_message(e)}")


def _list(s3, bucket: str, prefix: str, service_title: str, **kwargs) -> dict:
    try:
        return _call(f"s3:ListObjectsV2 {prefix}", s3.list_objects_v2, Bucket=bucket, Prefix=prefix, **kwargs)
    except ClientError as e:
        if _error_code(e) == "AccessDenied":
            raise AwsValidationError(
                f"{service_title}: the IAM user may not list s3://{bucket}/{prefix} (s3:ListBucket denied for that prefix).",
            )
        raise AwsValidationError(f"{service_title}: listing s3://{bucket}/{prefix} failed: {_error_message(e)}")


def _readable_object(response: dict) -> Optional[str]:
    """The first real log object in a listing: not a folder marker, not empty, not archived."""
    for item in response.get("Contents", []):
        if item["Key"].endswith("/") or item.get("Size", 0) == 0:
            continue
        if item.get("StorageClass") in _ARCHIVED_STORAGE_CLASSES:
            continue
        return item["Key"]
    return None


def _find_log_object(s3, bucket: str, prefix: str, service_title: str, today: date) -> Tuple[Optional[str], bool]:
    """
    Find a recent log object to read under a service's prefix. Returns ``(key, any_logs_at_all)``.

    Recent, because a plain listing returns the *oldest* logs first, and buckets commonly archive
    those to Glacier, where GetObject fails whatever the permissions. The Wazuh layout is
    ``<prefix><region>/<YYYY>/<MM>/<DD>/``, so the last few days are probed directly per region; only
    when none of them has a log does it fall back to the first readable object in the prefix.
    """
    regions = [p["Prefix"] for p in _list(s3, bucket, prefix, service_title, Delimiter="/").get("CommonPrefixes", [])]
    for days_back in range(_RECENT_DAYS):
        day = today - timedelta(days=days_back)
        for region in regions:
            key = _readable_object(_list(s3, bucket, f"{region}{day:%Y/%m/%d}/", service_title, MaxKeys=_LIST_PAGE))
            if key:
                return key, True

    response = _list(s3, bucket, prefix, service_title, MaxKeys=_LIST_PAGE)
    return _readable_object(response), bool(response.get("Contents"))


def _check_readable(s3, bucket: str, key: str, service_title: str) -> None:
    try:
        response = _call(f"s3:GetObject {key}", s3.get_object, Bucket=bucket, Key=key, Range="bytes=0-0")
        response["Body"].close()
    except ClientError as e:
        message = _error_message(e)
        code = _error_code(e)
        if "kms" in message.lower() or code.startswith("KMS"):
            raise AwsValidationError(
                f"{service_title}: the IAM user may list the logs but not decrypt them (kms:Decrypt denied). "
                f"Allow the user to use the KMS key in that key's policy. AWS said: {message}",
            )
        if code == "AccessDenied":
            raise AwsValidationError(f"{service_title}: the IAM user may list the logs but not read them (s3:GetObject denied).")
        raise AwsValidationError(f"{service_title}: reading s3://{bucket}/{key} failed: {message}")


def _validate(keys: ProvisionAwsAuthKeys, services: List[AwsServiceConfig]) -> AwsValidationResult:
    warnings: List[str] = []
    session = boto3.Session(
        aws_access_key_id=keys.ACCESS_KEY_ID,
        aws_secret_access_key=keys.SECRET_ACCESS_KEY.get_secret_value(),
    )
    try:
        _check_identity(session, keys.AWS_ACCOUNT_ID)
        region = _bucket_region(session, keys.BUCKET_NAME)
        s3 = session.client("s3", region_name=region, config=_BOTO_CONFIG)
        today = datetime.now(timezone.utc).date()
        for config in services:
            title = config.definition.title
            prefix = s3_log_prefix(config, keys.AWS_ACCOUNT_ID, keys.AWS_ORGANIZATION_ID)
            key, any_logs = _find_log_object(s3, keys.BUCKET_NAME, prefix, title, today)
            if key:
                _check_readable(s3, keys.BUCKET_NAME, key, title)
            elif any_logs:
                # Logs exist but every one we looked at is archived: listing works, reading is unproven.
                warnings.append(
                    f"{title}: logs exist under s3://{keys.BUCKET_NAME}/{prefix} but none from the last {_RECENT_DAYS} days, and the "
                    f"older ones are archived, so read access (s3:GetObject{', kms:Decrypt' if title == 'GuardDuty' else ''}) "
                    f"could not be checked. If {title} has stopped exporting, the Wazuh manager will collect nothing.",
                )
            else:
                raise AwsValidationError(
                    f"{title}: no logs found under s3://{keys.BUCKET_NAME}/{prefix}. Check the account ID, the service's prefix "
                    f"in SERVICES, and that {title} exports to this bucket.",
                )
    except _Unreachable as e:
        logger.warning(f"Could not reach AWS to validate account {keys.AWS_ACCOUNT_ID}: {e}")
        return AwsValidationResult(
            validated=False,
            warnings=[
                f"CoPilot could not reach AWS ({e}), so the credentials and bucket were not checked. The Wazuh manager "
                "reports any problem in ossec.log under wazuh-modulesd:aws-s3.",
            ],
        )
    except BotoCoreError as e:
        raise AwsValidationError(f"Could not check the AWS credentials: {e}")

    logger.info(f"AWS credentials for account {keys.AWS_ACCOUNT_ID} validated against bucket {keys.BUCKET_NAME} ({region}).")
    return AwsValidationResult(validated=True, bucket_region=region, warnings=warnings)


async def validate_aws_access(keys: ProvisionAwsAuthKeys, services: List[AwsServiceConfig]) -> AwsValidationResult:
    """Run every check; raises :class:`AwsValidationError` on a failure the Wazuh master would share."""
    return await asyncio.to_thread(_validate, keys, services)
