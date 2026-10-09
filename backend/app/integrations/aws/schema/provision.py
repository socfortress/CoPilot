import re
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import SecretStr
from pydantic import field_validator
from pydantic import model_validator

from app.integrations.aws.utils.services import AwsServiceConfig
from app.integrations.aws.utils.services import default_only_logs_after
from app.integrations.aws.utils.services import normalize_only_logs_after
from app.integrations.aws.utils.services import parse_services

# The auth keys of the AWS integration, as registered in `db_populate`.
AWS_INTEGRATION_NAME = "AWS"


class PipelineRuleTitles(Enum):
    WAZUH_INFO = "WAZUH CREATE FIELD SYSLOG LEVEL - INFO"
    WAZUH_WARNING = "WAZUH CREATE FIELD SYSLOG LEVEL - WARNING"
    WAZUH_NOTICE = "WAZUH CREATE FIELD SYSLOG LEVEL - NOTICE"
    WAZUH_ALERT = "WAZUH CREATE FIELD SYSLOG LEVEL - ALERT"
    AWS_SYSLOG_TYPE = "SYSLOG TYPE AWS"
    AWS_TIMESTAMP = "AWS Timestamp - UTC"
    AWS_ACCOUNT_ID = "AWS ACCOUNT ID"


class PipelineTitles(Enum):
    AWS = "AWS PROCESSING PIPELINE"


class ProvisionAwsRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        AWS_INTEGRATION_NAME,
        description="The integration name.",
        examples=[AWS_INTEGRATION_NAME],
    )
    instance_name: Optional[str] = Field(
        None,
        description=(
            "Which AWS account (instance) of this customer to provision. Omit when the customer has a " "single, unnamed AWS integration."
        ),
        examples=["production"],
    )

    # ensure the `integration_name` is always set to "AWS"
    @model_validator(mode="before")
    @classmethod
    def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["integration_name"] = AWS_INTEGRATION_NAME
        return values


class AwsConfigNotice(BaseModel):
    """
    What the operator must do by hand on the Wazuh master, because CoPilot cannot.

    The Wazuh API edits `ossec.conf` only; it cannot read or write `/root/.aws/config`. When that file
    exists and has no `[default]` section, the aws-s3 module exits with code 23 for every bucket that
    has no `aws_profile` — which is every bucket CoPilot provisions.
    """

    detected: bool = Field(
        False,
        description="True when the manager's log showed the exit-23 error after this deployment.",
    )
    file_path: str = "/root/.aws/config"
    summary: str
    steps: List[str]
    contents: str = Field(..., description="The section to add to /root/.aws/config.")


class ProvisionAwsResponse(BaseModel):
    success: bool
    message: str
    warnings: List[str] = Field(default_factory=list)
    aws_config: Optional[AwsConfigNotice] = None


class ProvisionAwsAuthKeys(BaseModel):
    """
    The auth keys of one AWS integration instance.

    `SECRET_ACCESS_KEY` is a `SecretStr` so it cannot end up in a log line or an error message by
    accident: printing the model shows `**********`.
    """

    ACCESS_KEY_ID: str = Field(..., description="Access key ID of the read-only IAM user.", examples=["AKIA..."])
    SECRET_ACCESS_KEY: SecretStr = Field(..., description="Secret access key of the read-only IAM user.")
    AWS_ACCOUNT_ID: str = Field(..., description="12-digit AWS account ID.", examples=["123456789012"])
    AWS_ACCOUNT_ALIAS: Optional[str] = Field(None, description="Optional label for the account.", examples=["example"])
    AWS_ORGANIZATION_ID: Optional[str] = Field(
        None,
        description="AWS Organizations ID, for CloudTrail organization trails only.",
        examples=["o-a1b2c3d4e5"],
    )
    BUCKET_NAME: str = Field(..., description="The S3 bucket the logs are exported to.", examples=["example-cloudtrail-logs"])
    SERVICES: str = Field(
        ...,
        description="Comma-separated services, each optionally `service:prefix`.",
        examples=["cloudtrail,guardduty:guardduty"],
    )
    ONLY_LOGS_AFTER: Optional[str] = Field(None, description="Wazuh `YYYY-MMM-DD`; defaults to today.", examples=["2026-OCT-08"])

    @model_validator(mode="before")
    @classmethod
    def blank_means_unset(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        # Every auth key is stored as a string, so an optional key the operator left empty arrives as "".
        return {key: (value.strip() if isinstance(value, str) else value) or None for key, value in values.items()}

    @field_validator("ACCESS_KEY_ID")
    @classmethod
    def validate_access_key_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Z0-9]{16,128}", value):
            raise ValueError("ACCESS_KEY_ID does not look like an AWS access key ID (e.g. AKIA…).")
        return value

    @field_validator("AWS_ACCOUNT_ID")
    @classmethod
    def validate_account_id(cls, value: str) -> str:
        if not re.fullmatch(r"\d{12}", value):
            raise ValueError("AWS_ACCOUNT_ID must be the 12-digit AWS account ID.")
        return value

    @field_validator("AWS_ORGANIZATION_ID")
    @classmethod
    def validate_organization_id(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not re.fullmatch(r"o-[a-z0-9]{10,32}", value):
            raise ValueError("AWS_ORGANIZATION_ID must look like o-a1b2c3d4e5.")
        return value

    @field_validator("BUCKET_NAME")
    @classmethod
    def validate_bucket_name(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", value):
            raise ValueError("BUCKET_NAME is not a valid S3 bucket name.")
        return value

    @field_validator("AWS_ACCOUNT_ALIAS")
    @classmethod
    def validate_account_alias(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not re.fullmatch(r"[A-Za-z0-9._-]{1,63}", value):
            raise ValueError("AWS_ACCOUNT_ALIAS may only contain letters, digits, '.', '_' and '-'.")
        return value

    @field_validator("SERVICES")
    @classmethod
    def validate_services(cls, value: str) -> str:
        parse_services(value)
        return value

    @field_validator("ONLY_LOGS_AFTER")
    @classmethod
    def validate_only_logs_after(cls, value: Optional[str]) -> Optional[str]:
        return normalize_only_logs_after(value) if value is not None else None

    def service_configs(self) -> List[AwsServiceConfig]:
        return parse_services(self.SERVICES)

    def only_logs_after(self) -> str:
        return self.ONLY_LOGS_AFTER or default_only_logs_after()
