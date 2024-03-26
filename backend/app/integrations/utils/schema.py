from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field


class WazuhOSInfo(BaseModel):
    arch: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The architecture of the Wazuh Agent.",
    )
    codename: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The codename of the Wazuh Agent.",
    )
    major: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The major version of the Wazuh Agent.",
    )
    minor: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The minor version of the Wazuh Agent.",
    )
    name: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The name of the Wazuh Agent.",
    )
    platform: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The platform of the Wazuh Agent.",
    )
    uname: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The uname of the Wazuh Agent.",
    )
    version: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The version of the Wazuh Agent.",
    )


class WazuhAgent(BaseModel):
    os: Optional[WazuhOSInfo] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The OS info of the Wazuh Agent.",
    )
    lastKeepAlive: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The last keep alive of the Wazuh Agent.",
    )
    id: str
    dateAdd: str
    configSum: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The config sum of the Wazuh Agent.",
    )
    manager: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The manager of the Wazuh Agent.",
    )
    group: Optional[List[str]] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The group of the Wazuh Agent.",
    )
    registerIP: str
    ip: str
    name: str
    status: str
    mergedSum: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The merged sum of the Wazuh Agent.",
    )
    version: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The version of the Wazuh Agent.",
    )
    node_name: str
    group_config_status: str


class WazuhAffectedItems(BaseModel):
    affected_items: List[WazuhAgent]
    total_affected_items: int
    total_failed_items: int
    failed_items: List


class WazuhResponseData(BaseModel):
    data: WazuhAffectedItems


class WazuhAgentResponse(BaseModel):
    data: Optional[WazuhResponseData] = Field(
        None,
        description="The Wazuh API response data.",
    )
    message: Optional[str] = Field(
        "Not Available - Make sure the Wazuh Agent is connected to the Manager.",
        description="The Wazuh API response message.",
    )
    success: Optional[bool] = Field(
        False,
        description="The Wazuh API response success.",
    )


class WazuhSocketPayload(BaseModel):
    integration: str = Field(
        ...,
        description="The integration name.",
        examples="sublime",
    )

    class Config:
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


############################### ! Sublime ! ###############################
class WazuhSublimeSocketPayload(WazuhSocketPayload):
    sender: str = Field(
        ...,
        description="The sender's email address.",
        examples="info@socfortress.co",
    )
    display_name: str = Field(
        ...,
        description="The sender's display name.",
        examples="SOCFortress",
    )
    subject: str = Field(
        ...,
        description="The subject of the email.",
        examples="Test Email",
    )
    canonical_id: str = Field(
        ...,
        description="The canonical ID of the email.",
        examples="123456789",
    )
    rule_names: str = Field(
        ...,
        description="The rule names that were triggered.",
        examples="test rule, test rule 2",
    )
    recipients: str = Field(
        ...,
        description="The recipients of the email.",
        examples="info@socfortress.co",
    )

    def to_dict(self):
        # If `display_name` is an empty string, set it to `None`.
        if self.display_name == "":
            self.display_name = None
        return self.dict(exclude_none=True)


######### ! SEND TO SHUFFLE PAYLOAD ! #########
class ShufflePayload(BaseModel):
    alert_id: str = Field(
        ...,
        description="The alert ID.",
        examples="123456789",
    )
    customer: str = Field(
        ...,
        description="The customer name.",
        examples="SOCFortress",
    )
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples="socfortress",
    )
    alert_source_link: str = Field(
        ...,
        description="The alert source link.",
        examples="https://app.socfortress.co/alerts/123456789",
    )
    rule_description: str = Field(
        ...,
        description="The rule description.",
        examples="Test rule",
    )
    hostname: str = Field(
        ...,
        description="The hostname of the affected asset.",
        examples="test-hostname",
    )

    class Config:
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


######### ! SEND TO EVENT SHIPPER ! #########
class EventShipperPayload(BaseModel):
    integration: str = Field(
        ...,
        description="The integration name.",
        examples="mimecast",
    )
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples="socfortress",
    )

    class Config:
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


class EventShipperPayloadResponse(BaseModel):
    message: str
    success: bool
    data: Optional[dict] = Field(
        None,
        description="The Event Shipper response data.",
    )


######### ! SEND TO ALERT CREATION ! #########
class QueryString(BaseModel):
    query: str


class Query(BaseModel):
    query_string: QueryString


class Filter(BaseModel):
    query: Query


class KibanaDiscoverTimeDelta(BaseModel):
    minutes: int


class Realert(BaseModel):
    minutes: int


class PraecoAlertConfig(BaseModel):
    alert: List[str]
    filter: List[Filter]
    generate_kibana_discover_url: bool
    http_post_ignore_ssl_errors: bool
    http_post_timeout: int
    http_post_url: List[str]
    import_config: str = Field(..., alias="import")  # Using alias
    index: str
    is_enabled: bool
    kibana_discover_from_timedelta: KibanaDiscoverTimeDelta
    kibana_discover_to_timedelta: KibanaDiscoverTimeDelta
    match_enhancements: List[str]
    name: str
    realert: Realert
    timestamp_field: str
    timestamp_type: str
    type: str
    use_strftime_index: bool

    class Config:
        allow_population_by_field_name = True


class PraecoProvisionAlertResponse(BaseModel):
    success: bool
    message: str
