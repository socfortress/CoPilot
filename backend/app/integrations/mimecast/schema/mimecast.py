from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Extra, HttpUrl
from pydantic import Field, root_validator

from enum import Enum

class PipelineRuleTitles(Enum):
    WAZUH_INFO = "WAZUH CREATE FIELD SYSLOG LEVEL - INFO"
    WAZUH_WARNING = "WAZUH CREATE FIELD SYSLOG LEVEL - WARNING"
    WAZUH_NOTICE = "WAZUH CREATE FIELD SYSLOG LEVEL - NOTICE"
    WAZUH_ALERT = "WAZUH CREATE FIELD SYSLOG LEVEL - ALERT"
    OFFICE365_TIMESTAMP = "Office365 Timestamp - UTC"

class PipelineTitles(Enum):
    OFFICE365 = "OFFICE365 PROCESSING PIPELINE"

class MimecastRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "Mimecast",
        description="The integration name.",
        examples=["Office365"],
    )

    # # ensure the `integration_name` is always set to "Office365"
    # @root_validator(pre=True)
    # def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
    #     values["integration_name"] = "Office365"
    #     return values


class MimecastResponse(BaseModel):
    success: bool
    message: str

class MimecastAuthKeys(BaseModel):
    APP_ID: str = Field(
        ...,
        description="YOUR DEVELOPER APPLICATION ID",
        examples=["00002"],
    )
    APP_KEY: str = Field(
        ...,
        description="YOUR DEVELOPER APPLICATION KEY",
        examples=["00002"],
    )
    EMAIL_ADDRESS: str = Field(
        ...,
        description="EMAIL ADDRESS OF YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    ACCESS_KEY: str = Field(
        ...,
        description="ACCESS KEY FOR YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    SECRET_KEY: str = Field(
        ...,
        description="SECRET KEY FOR YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    URI = str = Field(
        '/api/audit/get-siem-logs',
        description="URI FOR YOUR API Endpoint",
        examples=["/api/audit/get-siem-logs"],
    )

class APIEndpointRegion(BaseModel):
    code: str
    api: HttpUrl
    mpp: HttpUrl
    adminConsole: HttpUrl
    name: str

class APIEndpointDataItem(BaseModel):
    emailAddress: str
    emailToken: str
    authenticate: List
    region: APIEndpointRegion

class APIEndpointMeta(BaseModel):
    status: int

class APIEndpointData(BaseModel):
    meta: APIEndpointMeta
    data: List[APIEndpointDataItem]
    fail: List

class MimecastAPIEndpointResponse(BaseModel):
    data: APIEndpointData
    success: bool
    message: str


class MimecastScheduledResponse(BaseModel):
    success: bool
    message: str
