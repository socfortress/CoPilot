from datetime import datetime
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class VulnSeverity(Enum):
    Low = "Low"
    Medium = "Medium"
    High = "High"
    Critical = "Critical"


class WazuhAgent(BaseModel):
    agent_id: str = Field(..., alias="agent_id")
    agent_name: str = Field(..., alias="hostname")
    agent_ip: str = Field(..., alias="ip_address")
    agent_os: str = Field(..., alias="os")
    agent_label: str = Field(..., alias="label")
    agent_last_seen: str = Field(..., alias="wazuh_last_seen")
    wazuh_agent_version: str = Field(..., alias="wazuh_agent_version")
    wazuh_agent_status: Optional[str] = Field(None, alias="wazuh_agent_status")

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
    version: Optional[str]
    type: Optional[str]
    name: Optional[str]
    external_references: Optional[List[str]]
    detection_time: Optional[str]
    cvss3_score: Optional[float]
    published: Optional[str]
    architecture: Optional[str]
    cve: Optional[str]
    status: Optional[str]
    title: Optional[str]


class WazuhAgentVulnerabilitiesResponse(BaseModel):
    vulnerabilities: Optional[List[WazuhAgentVulnerabilities]]
    success: bool
    message: str


class WazuhAgentScaResults(BaseModel):
    description: str
    fail: int
    start_scan: str
    references: str
    name: str
    pass_count: int = Field(..., alias="pass")
    score: int
    end_scan: str
    policy_id: str
    total_checks: int
    hash_file: str
    invalid: int


class WazuhAgentScaResponse(BaseModel):
    sca: Optional[List[WazuhAgentScaResults]]
    success: bool
    message: str


class Compliance(BaseModel):
    value: str
    key: str


class Rules(BaseModel):
    type: str
    rule: str


class WazuhAgentScaPolicyResults(BaseModel):
    description: Optional[str] = Field(
        "Description not found",
        description="Description of the issue",
    )
    id: int
    reason: str
    command: Optional[str] = Field(
        "Command not found",
        description="Command to run to fix the issue",
    )
    rationale: str
    condition: str
    title: str
    result: str
    policy_id: str
    remediation: str
    compliance: List[Compliance]
    rules: List[Rules]


class WazuhAgentScaPolicyResultsResponse(BaseModel):
    sca_policy_results: Optional[List[WazuhAgentScaPolicyResults]]
    success: bool
    message: str
