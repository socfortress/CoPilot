from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import field_validator, ConfigDict, BaseModel
from pydantic import Field


class AgentModel(BaseModel):
    id: Optional[int] = None
    os: Optional[str] = None
    label: Optional[str] = None
    wazuh_last_seen: Optional[datetime] = None
    velociraptor_last_seen: Optional[datetime] = None
    velociraptor_agent_version: Optional[str] = None
    ip_address: Optional[str] = None
    agent_id: Optional[str] = None
    hostname: Optional[str] = None
    critical_asset: Optional[bool] = None
    velociraptor_id: Optional[str] = None
    wazuh_agent_version: Optional[str] = None
    customer_code: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ExtendedAgentModel(AgentModel):
    unhealthy_wazuh_agent: Optional[bool] = Field(
        None,
        description="Whether the agent is unhealthy in Wazuh",
    )
    unhealthy_velociraptor_agent: Optional[bool] = Field(
        None,
        description="Whether the agent is unhealthy in Velociraptor",
    )
    unhealthy_recent_logs_collected: Optional[bool] = Field(
        None,
        description="Whether the agent has not collected logs recently",
    )


class AgentHealthCheckResponse(BaseModel):
    healthy_wazuh_agents: Optional[List[ExtendedAgentModel]] = None
    unhealthy_wazuh_agents: Optional[List[ExtendedAgentModel]] = None
    healthy_velociraptor_agents: Optional[List[ExtendedAgentModel]] = None
    unhealthy_velociraptor_agents: Optional[List[ExtendedAgentModel]] = None
    healthy_recent_logs_collected: Optional[List[ExtendedAgentModel]] = None
    unhealthy_recent_logs_collected: Optional[List[ExtendedAgentModel]] = None
    message: str
    success: bool


class TimeCriteriaModel(BaseModel):
    minutes: int = Field(
        60,
        description="Number of minutes within which the agent should have been last seen to be considered healthy.",
    )
    hours: int = Field(
        0,
        description="Number of hours within which the agent should have been last seen to be considered healthy.",
    )
    days: int = Field(
        0,
        description="Number of days within which the agent should have been last seen to be considered healthy.",
    )


########## Logs Schemas ##########


class Log(BaseModel):
    index_name: str
    total_logs: int
    logs: Optional[List[Dict[str, Any]]] = Field(
        [],
        description="The logs returned from the search.",
    )


class LogsSearchBody(BaseModel):
    size: int = Field(1, description="The number of logs to return.")
    timerange: str = Field("24h", description="The time range to search logs in.")
    log_field: str = Field("syslog_level", description="The field to search logs in.")
    log_value: str = Field("INFO", description="The value to search logs for.")
    timestamp_field: str = Field(
        "timestamp_utc",
        description="The timestamp field to search logs in.",
    )

    @field_validator("timerange")
    @classmethod
    def validate_timerange(cls, value):
        if value[-1] not in ("h", "d", "w", "m"):
            raise ValueError(
                "Invalid timerange format. The string should end with either 'h', 'd', 'w', or 'm'.",
            )

        # Optionally, you can check that the prefix is a number
        if not value[:-1].isdigit():
            raise ValueError(
                "Invalid timerange format. The string should start with a number.",
            )

        return value


class LogsSearchResponse(BaseModel):
    logs_summary: List[Log]
    success: bool
    message: str


class CollectLogsResponse(BaseModel):
    logs: List[Dict[str, Any]]
    success: bool
    message: str


class HostLogsSearchBody(LogsSearchBody):
    agent_name: str = Field(
        ...,
        description="The name of the agent to search logs for.",
    )


class HostLogsSearchResponse(BaseModel):
    logs_summary: Optional[List[Log]] = Field(
        [],
        description="The logs summary returned from the search.",
    )
    healthy: bool = Field(False, description="Whether the host is healthy or not.")
    success: bool
    message: str
