from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


class Alert(BaseModel):
    index_name: str
    total_alerts: int
    alerts: Optional[List[Dict[str, Any]]] = Field(
        [],
        description="The alerts returned from the search.",
    )


class AlertsSearchBody(BaseModel):
    size: int = Field(10, description="The number of alerts to return.")
    timerange: str = Field("24h", description="The time range to search alerts in.")
    alert_field: str = Field(
        "syslog_level",
        description="The field to search alerts in.",
    )
    alert_value: str = Field("ALERT", description="The value to search alerts for.")
    timestamp_field: str = Field(
        "timestamp_utc",
        description="The timestamp field to search alerts in.",
    )

    @validator("timerange")
    def validate_timerange(cls, value):
        if value[-1] not in ("h", "d", "w"):
            raise ValueError(
                "Invalid timerange format. The string should end with either 'h', 'd', 'w'.",
            )

        # Optionally, you can check that the prefix is a number
        if not value[:-1].isdigit():
            raise ValueError(
                "Invalid timerange format. The string should start with a number.",
            )

        return value


class AlertsSearchResponse(BaseModel):
    alerts_summary: List[Alert]
    success: bool
    message: str


class CollectAlertsResponse(BaseModel):
    alerts: List[Dict[str, Any]]
    success: bool
    message: str


class HostAlertsSearchBody(AlertsSearchBody):
    agent_name: str = Field(
        ...,
        description="The name of the agent to search alerts for.",
    )


class HostAlertsSearchResponse(BaseModel):
    alerts_summary: List[Alert]
    success: bool
    message: str


class IndexAlertsSearchBody(AlertsSearchBody):
    index_name: str = Field(
        ...,
        description="The name of the index to search alerts for.",
    )


class IndexAlertsSearchResponse(BaseModel):
    alerts_summary: List[Alert]
    success: bool
    message: str


class AlertsByHost(BaseModel):
    agent_name: str
    number_of_alerts: int


class AlertsByHostResponse(BaseModel):
    alerts_by_host: List[AlertsByHost]
    success: bool
    message: str


class AlertsByRule(BaseModel):
    rule: str
    number_of_alerts: int


class AlertsByRuleResponse(BaseModel):
    alerts_by_rule: List[AlertsByRule]
    success: bool
    message: str


class AlertsByRulePerHost(BaseModel):
    agent_name: str
    number_of_alerts: int
    rule: str


class AlertsByRulePerHostResponse(BaseModel):
    alerts_by_rule_per_host: List[AlertsByRulePerHost]
    success: bool
    message: str


############# ! PASSABLE MESSAGES FROM ES CLIENT ! #############
class SkippableWazuhIndexerClientErrors(Enum):
    NO_MAPPING_FOR_TIMESTAMP = "No mapping found for [timestamp_utc] in order to sort on"
    # Add other error messages here, for example:
    # ANOTHER_ERROR = "Another specific error message"
