"""The AWS services CoPilot can provision, and the pure helpers built on that table.

Everything that differs between AWS services lives in ``AWS_SERVICES``: the Wazuh bucket type, the
directory the service writes under ``AWSLogs/<account>/``, and the Graylog fields that carry the
account and the event time. Adding a service is one entry here — but only once a real event from it
has confirmed ``account_field`` and ``timestamp_field``. The stream that routes a customer's events
pins the account through ``account_field``; a guessed name matches nothing, and the customer's events
silently stay in the default stream.

No FastAPI and no database in this module, so it can be tested and imported from anywhere.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Dict
from typing import List
from typing import Optional


@dataclass(frozen=True)
class AwsServiceDefinition:
    # Value used in `SERVICES`, in Wazuh's `data_aws_source` and in the index prefix.
    key: str
    # Human-readable name for Graylog and Grafana titles.
    title: str
    # `<bucket type="…">` in the aws-s3 wodle.
    wazuh_type: str
    # Directory the service writes under `AWSLogs/[<org-id>/]<account>/`.
    log_dir: str
    # Graylog field carrying the AWS account the event belongs to (confirmed from real events).
    account_field: str
    # Graylog field carrying the event's own time, copied to `timestamp_utc`.
    timestamp_field: str
    # Whether the service's S3 layout includes the organization ID (CloudTrail organization trails).
    supports_organization_id: bool


AWS_SERVICES: Dict[str, AwsServiceDefinition] = {
    "cloudtrail": AwsServiceDefinition(
        key="cloudtrail",
        title="CloudTrail",
        wazuh_type="cloudtrail",
        log_dir="CloudTrail",
        account_field="data_aws_aws_account_id",
        timestamp_field="data_aws_eventTime",
        supports_organization_id=True,
    ),
    "guardduty": AwsServiceDefinition(
        key="guardduty",
        title="GuardDuty",
        wazuh_type="guardduty",
        log_dir="GuardDuty",
        account_field="data_aws_accountId",
        timestamp_field="data_aws_updatedAt",
        supports_organization_id=False,
    ),
}

# Services Wazuh supports but CoPilot refuses until a real event has confirmed their field names.
KNOWN_UNSUPPORTED_SERVICES = ("vpcflow", "alb", "clb", "nlb", "server_access", "config", "waf")


@dataclass(frozen=True)
class AwsServiceConfig:
    """One entry of `SERVICES`: which service, and the S3 key prefix it writes under (if any)."""

    definition: AwsServiceDefinition
    prefix: Optional[str] = None

    @property
    def key(self) -> str:
        return self.definition.key


_PREFIX_PATTERN = re.compile(r"^[A-Za-z0-9!_.*'()/-]+$")


def parse_services(raw: str) -> List[AwsServiceConfig]:
    """
    Parse `SERVICES`, e.g. ``cloudtrail,guardduty:guardduty``.

    Each comma-separated entry is ``service`` or ``service:prefix``, where the prefix is the S3 key
    prefix the service exports under (``<prefix>/AWSLogs/<account>/…``). CloudTrail trails can carry a
    prefix as well as GuardDuty exports, which is why this is per service rather than one key per
    service. Raises ``ValueError`` with a message naming the offending entry.
    """
    if not raw or not raw.strip():
        raise ValueError(f"SERVICES is empty. Supported services: {', '.join(AWS_SERVICES)}.")

    configs: List[AwsServiceConfig] = []
    seen = set()
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        service, _, prefix = entry.partition(":")
        service = service.strip().lower()
        prefix = prefix.strip().strip("/") or None

        if service not in AWS_SERVICES:
            hint = " It is not supported yet." if service in KNOWN_UNSUPPORTED_SERVICES else ""
            raise ValueError(
                f"Unknown AWS service '{service}' in SERVICES.{hint} Supported services: {', '.join(AWS_SERVICES)}.",
            )
        if service in seen:
            raise ValueError(f"AWS service '{service}' is listed more than once in SERVICES.")
        if prefix is not None and not _PREFIX_PATTERN.match(prefix):
            raise ValueError(f"The S3 prefix '{prefix}' for {service} contains characters S3 key prefixes do not use.")

        seen.add(service)
        configs.append(AwsServiceConfig(definition=AWS_SERVICES[service], prefix=prefix))

    if not configs:
        raise ValueError(f"SERVICES is empty. Supported services: {', '.join(AWS_SERVICES)}.")
    return configs


def s3_log_prefix(
    config: AwsServiceConfig,
    account_id: str,
    organization_id: Optional[str] = None,
) -> str:
    """
    The S3 prefix a service's logs for one account live under, as the Wazuh wodle reads it.

    ``[<prefix>/]AWSLogs/[<org-id>/]<account>/<LogDir>/`` — the organization ID only for services
    whose layout has it (CloudTrail organization trails).
    """
    parts = []
    if config.prefix:
        parts.append(config.prefix)
    parts.append("AWSLogs")
    if organization_id and config.definition.supports_organization_id:
        parts.append(organization_id)
    parts.extend([account_id, config.definition.log_dir])
    return "/".join(parts) + "/"


# Wazuh's `only_logs_after` format is `YYYY-MMM-DD` with an English month abbreviation. Built by hand
# rather than with `strftime("%b")`, which follows the process locale.
_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
_ONLY_LOGS_AFTER_PATTERN = re.compile(r"^(\d{4})-([A-Za-z]{3})-(\d{2})$")


def wazuh_date(value: datetime) -> str:
    return f"{value.year:04d}-{_MONTHS[value.month - 1]}-{value.day:02d}"


def default_only_logs_after() -> str:
    return wazuh_date(datetime.now(timezone.utc))


def normalize_only_logs_after(value: str) -> str:
    """Validate a `YYYY-MMM-DD` date and return it upper-cased; raises ``ValueError`` otherwise."""
    match = _ONLY_LOGS_AFTER_PATTERN.match(value.strip())
    if not match or match.group(2).upper() not in _MONTHS:
        raise ValueError(f"ONLY_LOGS_AFTER must look like 2026-OCT-08 (YYYY-MMM-DD), got '{value}'.")
    year, month, day = int(match.group(1)), _MONTHS.index(match.group(2).upper()) + 1, int(match.group(3))
    try:
        datetime(year, month, day)
    except ValueError:
        raise ValueError(f"ONLY_LOGS_AFTER '{value}' is not a real date.")
    return f"{match.group(1)}-{match.group(2).upper()}-{match.group(3)}"


# ---------------------------------------------------------------------------------------------
# Per-service IDs in `customer_integrations_meta`
#
# The meta table has one `graylog_index_id`, `graylog_stream_id` and `grafana_datasource_uid` per
# instance, but an AWS instance owns one of each *per service*. They are stored in those same
# columns as `service:id` pairs (`cloudtrail:66f…,guardduty:66a…`) rather than adding a column.
# Only the AWS code reads them this way — the generic infrastructure cleanup is bypassed for AWS.
# ---------------------------------------------------------------------------------------------


def encode_service_ids(ids: Dict[str, str]) -> str:
    return ",".join(f"{service}:{ids[service]}" for service in sorted(ids) if ids[service])


def decode_service_ids(value: Optional[str]) -> Dict[str, str]:
    ids: Dict[str, str] = {}
    for entry in (value or "").split(","):
        service, separator, identifier = entry.strip().partition(":")
        if separator and service and identifier:
            ids[service] = identifier
    return ids
