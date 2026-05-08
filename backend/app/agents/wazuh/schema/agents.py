from datetime import datetime
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class VulnSeverity(Enum):
    Low = "Low"
    Medium = "Medium"
    High = "High"
    Critical = "Critical"
    All = "All"


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

    model_config = ConfigDict(populate_by_name=True)


class WazuhAgentsList(BaseModel):
    agents: List[WazuhAgent]
    success: bool
    message: str
    model_config = ConfigDict(populate_by_name=True)


class WazuhAgentVulnerabilities(BaseModel):
    severity: Optional[str] = None
    version: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    external_references: Optional[List[str]] = None
    detection_time: Optional[str] = None
    cvss3_score: Optional[float] = None
    published: Optional[str] = None
    architecture: Optional[str] = None
    cve: Optional[str] = None
    status: Optional[str] = None
    title: Optional[str] = None


class WazuhAgentVulnerabilitiesResponse(BaseModel):
    vulnerabilities: Optional[List[WazuhAgentVulnerabilities]] = None
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
    sca: Optional[List[WazuhAgentScaResults]] = None
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
    reason: Optional[str] = Field(
        "Reason not found",
        description="Reason for the issue",
    )
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
    sca_policy_results: Optional[List[WazuhAgentScaPolicyResults]] = None
    success: bool
    message: str
