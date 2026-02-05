from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


# Request schemas
class PatchTuesdayRequest(BaseModel):
    """Request to fetch Patch Tuesday data for a specific cycle"""

    cycle: Optional[str] = Field(
        None,
        description="CVRF doc id in format YYYY-Mmm (e.g., 2026-Jan). Defaults to current month.",
        pattern=r"^\d{4}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$",
    )
    include_epss: bool = Field(True, description="Include EPSS scores in the response")
    include_kev: bool = Field(True, description="Include CISA KEV data in the response")


class PatchTuesdayCVESearchRequest(BaseModel):
    """Request to search for specific CVEs in Patch Tuesday data"""

    cve_ids: List[str] = Field(..., description="List of CVE IDs to search for")
    cycle: Optional[str] = Field(None, description="Optional cycle to limit search to")


# Response component schemas
class CVSSInfo(BaseModel):
    """CVSS score information"""

    base: Optional[float] = Field(None, description="CVSS base score")
    vector: Optional[str] = Field(None, description="CVSS vector string")


class EPSSInfo(BaseModel):
    """EPSS score information"""

    score: Optional[float] = Field(None, description="EPSS probability score")
    percentile: Optional[float] = Field(None, description="EPSS percentile ranking")
    date: Optional[str] = Field(None, description="Date of EPSS score")


class KEVInfo(BaseModel):
    """CISA Known Exploited Vulnerabilities information"""

    in_kev: bool = Field(False, description="Whether the CVE is in CISA KEV")
    date_added: Optional[str] = Field(None, description="Date added to KEV")
    due_date: Optional[str] = Field(None, description="Required remediation due date")
    required_action: Optional[str] = Field(None, description="Required remediation action")
    known_ransomware_campaign_use: Optional[str] = Field(None, description="Known ransomware usage")
    vendor_project: Optional[str] = Field(None, description="Vendor or project name")
    product: Optional[str] = Field(None, description="Product name")
    vulnerability_name: Optional[str] = Field(None, description="Vulnerability name")
    short_description: Optional[str] = Field(None, description="Short description")
    notes: Optional[str] = Field(None, description="Additional notes")


class AffectedProduct(BaseModel):
    """Affected product information"""

    product: str = Field(..., description="Product name")
    family: str = Field(..., description="Product family classification")
    component_hint: Optional[str] = Field(None, description="Component hint from title")


class RemediationInfo(BaseModel):
    """Remediation information"""

    kbs: List[str] = Field(default_factory=list, description="Related KB article numbers")


class PrioritizationInfo(BaseModel):
    """Prioritization recommendation"""

    priority: str = Field(..., description="Priority level (P0-P3)")
    reason: List[str] = Field(default_factory=list, description="Reasons for priority assignment")
    suggested_sla: str = Field(..., description="Suggested SLA for remediation")


class SourceInfo(BaseModel):
    """Source information for the vulnerability data"""

    msrc_cvrf_id: str = Field(..., description="MSRC CVRF document ID")
    msrc_cvrf_url: str = Field(..., description="MSRC CVRF document URL")
    cisa_kev_url: str = Field(..., description="CISA KEV feed URL")


class PatchTuesdayItem(BaseModel):
    """Individual Patch Tuesday vulnerability item"""

    cycle: str = Field(..., description="Patch Tuesday cycle (e.g., 2026-Jan)")
    release_type: str = Field("patch_tuesday", description="Release type")
    cve: str = Field(..., description="CVE identifier")
    title: Optional[str] = Field(None, description="Vulnerability title")
    severity: Optional[str] = Field(None, description="Microsoft severity rating")
    cvss: CVSSInfo = Field(default_factory=CVSSInfo, description="CVSS information")
    epss: EPSSInfo = Field(default_factory=EPSSInfo, description="EPSS information")
    kev: KEVInfo = Field(default_factory=KEVInfo, description="KEV information")
    affected: AffectedProduct = Field(..., description="Affected product information")
    remediation: RemediationInfo = Field(default_factory=RemediationInfo, description="Remediation information")
    prioritization: PrioritizationInfo = Field(..., description="Prioritization recommendation")
    source: SourceInfo = Field(..., description="Data source information")
    timestamp_utc: str = Field(..., description="Timestamp when data was fetched")


class PriorityCounts(BaseModel):
    """Counts by priority level"""

    P0: int = Field(0, description="Emergency priority count")
    P1: int = Field(0, description="High priority count")
    P2: int = Field(0, description="Medium priority count")
    P3: int = Field(0, description="Low priority count")


class PatchTuesdaySummary(BaseModel):
    """Summary of Patch Tuesday data"""

    cycle: str = Field(..., description="Patch Tuesday cycle")
    patch_tuesday_date: str = Field(..., description="Date of Patch Tuesday")
    generated_utc: str = Field(..., description="When the summary was generated")
    unique_cves: int = Field(..., description="Number of unique CVEs")
    total_records: int = Field(..., description="Total CVE x product records")
    by_priority: PriorityCounts = Field(..., description="Counts by priority level")
    by_family: Dict[str, int] = Field(default_factory=dict, description="Counts by product family")
    by_severity: Dict[str, int] = Field(default_factory=dict, description="Counts by severity")


class PatchTuesdayResponse(BaseModel):
    """Full Patch Tuesday response"""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    summary: Optional[PatchTuesdaySummary] = Field(None, description="Summary of the data")
    items: List[PatchTuesdayItem] = Field(default_factory=list, description="Vulnerability items")


class PatchTuesdaySummaryResponse(BaseModel):
    """Summary-only Patch Tuesday response (without full items)"""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    summary: Optional[PatchTuesdaySummary] = Field(None, description="Summary of the data")
    top_items: List[PatchTuesdayItem] = Field(default_factory=list, description="Top prioritized items")


class AvailableCyclesResponse(BaseModel):
    """Response with available Patch Tuesday cycles"""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    cycles: List[str] = Field(default_factory=list, description="Available cycles")
    current_cycle: str = Field(..., description="Current/default cycle")
    next_patch_tuesday: str = Field(..., description="Date of next Patch Tuesday")
