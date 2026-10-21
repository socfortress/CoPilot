"""The Customer Portal's Exposure page (#1289): vulnerabilities and compliance across a tenant.

Everything is read live from Wazuh for the agents of the caller's customers whose switch is
on: the vulnerability states in the indexer, SCA from the manager. A source that cannot be
read is an ``error`` on the response, never a 500 and never the source's own text.
"""

from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

Severity = Literal["Critical", "High", "Medium", "Low"]
SEVERITIES: List[str] = ["Critical", "High", "Medium", "Low"]


# ── the switch ────────────────────────────────────────────────────────────────


class PortalExposureSettings(BaseModel):
    customer_code: str
    enabled: bool
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None


class PortalExposureSettingsResponse(BaseModel):
    settings: PortalExposureSettings
    success: bool
    message: str


class UpdatePortalExposureSettingsRequest(BaseModel):
    enabled: bool


class PortalExposureAvailabilityResponse(BaseModel):
    customer_code: Optional[str] = None
    enabled: bool
    success: bool
    message: str


# ── vulnerabilities ───────────────────────────────────────────────────────────


class SeverityCount(BaseModel):
    severity: Severity
    cves: int = Field(0, description="Distinct CVEs of this severity")
    hosts: int = Field(0, description="Agents with at least one of them")
    findings: int = Field(0, description="CVE × package × agent rows")


class ExposureTotals(BaseModel):
    cves: int = 0
    hosts: int = 0
    findings: int = 0


class CveRow(BaseModel):
    cve_id: str
    severity: Optional[str] = None
    cvss: Optional[float] = Field(None, description="The highest base score Wazuh gives it")
    epss: Optional[str] = Field(None, description="EPSS probability, best-effort; None when EPSS could not be read")
    hosts: int = 0
    packages: List[str] = Field(default_factory=list, description="The affected packages, most common first (at most 5)")
    first_detected: Optional[str] = Field(None, description="When Wazuh first saw it on one of the agents, ISO 8601 UTC")
    published: Optional[str] = None


class VulnerabilitiesResponse(BaseModel):
    enabled: bool = Field(..., description="False when no customer in the caller's scope has the page on: nothing is read")
    customer_codes: List[str] = Field(default_factory=list)
    agents_in_scope: int = 0
    severities: List[SeverityCount] = Field(default_factory=list, description="Every level, most severe first; not narrowed by `severity`")
    totals: ExposureTotals = Field(default_factory=ExposureTotals, description="For the filter in force")
    cves: List[CveRow] = Field(default_factory=list, description="One page, the highest CVSS first, then the most hosts")
    total_cves: int = Field(0, description="Distinct CVEs matching the filter")
    page: int = 1
    page_size: int = 25
    truncated: bool = Field(False, description="More CVEs match than can be ranked; narrow the filter")
    error: Optional[str] = None
    success: bool = True
    message: str = "Vulnerabilities retrieved"


class CveAgent(BaseModel):
    agent_id: str
    hostname: str
    customer_code: str
    package: Optional[str] = None
    version: Optional[str] = None
    detected: Optional[str] = None


class CveDetailResponse(BaseModel):
    cve_id: str
    severity: Optional[str] = None
    cvss: Optional[float] = None
    epss: Optional[str] = None
    description: Optional[str] = None
    references: List[str] = Field(default_factory=list)
    published: Optional[str] = None
    agents: List[CveAgent] = Field(default_factory=list, description="The caller's agents it affects, one row per package")
    truncated: bool = False
    error: Optional[str] = None
    success: bool = True
    message: str = "Vulnerability retrieved"


# ── compliance ────────────────────────────────────────────────────────────────


class PolicyRow(BaseModel):
    policy_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    agents: int = 0
    average_score: float = 0.0
    min_score: int = 0
    passed: int = 0
    failed: int = 0
    invalid: int = 0
    agents_below: int = Field(0, description="Agents scoring under WEAK_SCORE on it")


class ComplianceResponse(BaseModel):
    enabled: bool
    customer_codes: List[str] = Field(default_factory=list)
    agents_in_scope: int = 0
    agents_assessed: int = Field(0, description="Agents with at least one SCA policy")
    unavailable_agents: int = Field(0, description="Agents Wazuh could not answer for; their results are missing")
    average_score: Optional[float] = Field(None, description="Across every agent × policy; None when nothing was assessed")
    passed: int = 0
    failed: int = 0
    weak_score: int = Field(..., description="The score under which an agent counts as below on a policy")
    policies: List[PolicyRow] = Field(default_factory=list, description="The weakest average first")
    read_at: Optional[str] = Field(None, description="When the results were read from Wazuh (they are kept a few minutes)")
    error: Optional[str] = None
    success: bool = True
    message: str = "Compliance retrieved"


class PolicyAgent(BaseModel):
    agent_id: str
    hostname: str
    customer_code: str
    score: int = 0
    passed: int = 0
    failed: int = 0
    invalid: int = 0
    end_scan: Optional[str] = None


class PolicyAgentsResponse(BaseModel):
    policy_id: str
    name: Optional[str] = None
    agents: List[PolicyAgent] = Field(default_factory=list, description="The weakest score first")
    error: Optional[str] = None
    success: bool = True
    message: str = "Policy agents retrieved"
