from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field


class ValidSyslogType(str, Enum):
    WAZUH = "wazuh"


class CreateAlertRequest(BaseModel):
    index_name: str = Field(
        ...,
        description="The name of the index to search alerts for.",
    )
    alert_id: str = Field(..., description="The alert id.")


class CreateAlertResponse(BaseModel):
    success: bool
    message: str
    alert_id: int = Field(..., description="The alert id as created in CoPilot.")

class AutoCreateAlertResponse(BaseModel):
    success: bool
    message: str

class IndexNamesResponse(BaseModel):
    index_names: List[str]
    success: bool
    message: str


class FieldNames(BaseModel):
    field_names: List[str]
    asset_name: str
    timefield_name: str
    alert_title_name: str


class GenericSourceModel(BaseModel):
    timestamp: str = Field(..., description="The timestamp of the alert.")
    timestamp_utc: Optional[str] = Field(
        ...,
        description="The UTC timestamp of the alert.",
    )
    rule_description: Optional[str] = Field(
        "No autogenerated rule_description found",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    syslog_level: Optional[str] = Field(
        "No autogenerated syslog_level found",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    syslog_type: Optional[str] = Field(
        None,
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )

    class Config:
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


class GenericAlertModel(BaseModel):
    _index: str
    _id: str
    _version: int
    _source: GenericSourceModel  # Nested model
    asset_type_id: Optional[int] = Field(
        None,
        description="The asset type id of the alert which is needed for when we add the asset to IRIS.",
    )
    ioc_value: Optional[str] = Field(
        None,
        description="The IoC value of the alert which is needed for when we add the IoC to IRIS.",
    )
    ioc_type: Optional[str] = Field(
        None,
        description="The IoC type of the alert which is needed for when we add the IoC to IRIS.",
    )
    time_field: Optional[str] = Field(
        "timestamp",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    syslog_type: Optional[str] = Field(
        None,
        description="The type of the alert to be used when creating the CoPilot alert.",
    )

    class Config:
        extra = Extra.allow


class CreatedAlertPayload(BaseModel):
    alert_context_payload: dict
    asset_payload: str
    timefield_payload: str
    alert_title_payload: str
    source: str
    index_name: Optional[str] = None
    index_id: Optional[str] = None
