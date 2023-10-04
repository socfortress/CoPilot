from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field

from app.db.universal_models import Agents


class WazuhAgent(BaseModel):
    agent_id: str = Field(..., alias="agent_id")
    agent_name: str = Field(..., alias="hostname")
    agent_ip: str = Field(..., alias="ip_address")
    agent_os: str = Field(..., alias="os")
    agent_label: str = Field(..., alias="label")
    agent_last_seen: str = Field(..., alias="wazuh_last_seen")
    wazuh_agent_version: str = Field(..., alias="wazuh_agent_version")

    @property
    def agent_last_seen_as_datetime(self):
        dt = datetime.strptime(self.agent_last_seen, "%Y-%m-%dT%H:%M:%S%z")
        return dt.replace(tzinfo=None)

    class Config:
        allow_population_by_field_name = True


class WazuhAgentsList(BaseModel):
    agents: List[WazuhAgent]
    success: bool
    message: str

    class Config:
        allow_population_by_field_name = True


class WazuhAgentVulnerabilities(BaseModel):
    severity: Optional[str]
    updated: Optional[str]
    version: Optional[str]
    type: Optional[str]
    name: Optional[str]
    external_references: Optional[List[str]]
    condition: Optional[str]
    detection_time: Optional[str]
    cvss3_score: Optional[float]
    published: Optional[str]
    architecture: Optional[str]
    cve: Optional[str]
    status: Optional[str]
    title: Optional[str]
    cvss2_score: Optional[float]


class WazuhAgentVulnerabilitiesResponse(BaseModel):
    vulnerabilities: Optional[List[WazuhAgentVulnerabilities]]
    success: bool
    message: str
