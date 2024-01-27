from enum import Enum
from typing import Any
from typing import Dict

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class PipelineRuleTitles(Enum):
    WAZUH_INFO = "WAZUH CREATE FIELD SYSLOG LEVEL - INFO"
    WAZUH_WARNING = "WAZUH CREATE FIELD SYSLOG LEVEL - WARNING"
    WAZUH_NOTICE = "WAZUH CREATE FIELD SYSLOG LEVEL - NOTICE"
    WAZUH_ALERT = "WAZUH CREATE FIELD SYSLOG LEVEL - ALERT"
    OFFICE365_TIMESTAMP = "Office365 Timestamp - UTC"


class PipelineTitles(Enum):
    OFFICE365 = "OFFICE365 PROCESSING PIPELINE"


class ProvisionOffice365Request(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "Office365",
        description="The integration name.",
        examples=["Office365"],
    )

    # ensure the `integration_name` is always set to "Office365"
    @root_validator(pre=True)
    def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["integration_name"] = "Office365"
        return values


class ProvisionOffice365Response(BaseModel):
    success: bool
    message: str


class ProvisionOffice365AuthKeys(BaseModel):
    TENANT_ID: str = Field(
        ...,
        description="The tenant id.",
        examples=["00002"],
    )
    CLIENT_ID: str = Field(
        ...,
        description="The client id.",
        examples=["00002"],
    )
    CLIENT_SECRET: str = Field(
        ...,
        description="The client secret.",
        examples=["00002"],
    )
    API_TYPE: str = Field(
        ...,
        description="The api type.",
        examples=["00002"],
    )
