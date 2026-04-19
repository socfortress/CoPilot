import re
from datetime import datetime
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator

# --- Enums ---


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggeredBy(str, Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    WEBHOOK = "webhook"


class SeverityAssessment(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


class IocType(str, Enum):
    IP = "ip"
    DOMAIN = "domain"
    HASH = "hash"
    PROCESS = "process"
    URL = "url"
    USER = "user"
    COMMAND = "command"


class VtVerdict(str, Enum):
    MALICIOUS = "malicious"
    SUSPICIOUS = "suspicious"
    CLEAN = "clean"
    UNKNOWN = "unknown"


# --- Request schemas ---


class CreateJobRequest(BaseModel):
    id: str = Field(..., max_length=64, description="Unique job identifier, e.g. copilot-inv-1234-abc")
    alert_id: int = Field(..., description="The alert ID from incident_management_alert")
    customer_code: str = Field(..., max_length=64, description="Customer code")
    triggered_by: TriggeredBy = Field(..., description="How the investigation was triggered")
    alert_type: Optional[str] = Field(None, max_length=64, description="Detected alert type, e.g. sysmon_event_1")
    template_used: Optional[str] = Field(None, max_length=128, description="Template file used for investigation")


class UpdateJobRequest(BaseModel):
    status: JobStatus = Field(..., description="New job status")
    alert_type: Optional[str] = Field(None, max_length=64)
    template_used: Optional[str] = Field(None, max_length=128)
    error_message: Optional[str] = Field(None, description="Error message if status is failed")


class SubmitReportRequest(BaseModel):
    job_id: str = Field(..., max_length=64, description="The job ID this report belongs to")
    alert_id: int = Field(..., description="The alert ID")
    customer_code: str = Field(..., max_length=64, description="Customer code")
    severity_assessment: Optional[SeverityAssessment] = Field(None, description="Severity assessment of the alert")
    summary: Optional[str] = Field(None, description="Short summary of findings")
    report_markdown: Optional[str] = Field(None, description="Full investigation report in Markdown")
    recommended_actions: Optional[str] = Field(None, description="Recommended response actions")

    @validator("summary", "report_markdown", "recommended_actions", pre=True)
    def strip_control_characters(cls, v):
        """Strip control characters that break JSON serialization.
        Preserves newline (0x0a), carriage return (0x0d), and tab (0x09).
        """
        if v is None:
            return v
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)


class SubmitIocRequest(BaseModel):
    ioc_value: str = Field(..., max_length=512, description="The IOC value")
    ioc_type: IocType = Field(..., description="Type of IOC")
    vt_verdict: VtVerdict = Field(default=VtVerdict.UNKNOWN, description="VirusTotal verdict")
    vt_score: Optional[str] = Field(None, max_length=32, description="VirusTotal score, e.g. 5/70")
    details: Optional[str] = Field(None, description="Additional enrichment details")


class SubmitIocsRequest(BaseModel):
    report_id: int = Field(..., description="The report ID these IOCs belong to")
    alert_id: int = Field(..., description="The alert ID")
    customer_code: str = Field(..., max_length=64, description="Customer code")
    iocs: List[SubmitIocRequest] = Field(..., description="List of IOCs to submit")


# --- Response schemas ---


class JobResponse(BaseModel):
    id: str
    alert_id: int
    customer_code: str
    status: str
    alert_type: Optional[str]
    triggered_by: str
    template_used: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class ReportResponse(BaseModel):
    id: int
    job_id: str
    alert_id: int
    customer_code: str
    severity_assessment: Optional[str]
    summary: Optional[str]
    report_markdown: Optional[str]
    recommended_actions: Optional[str]
    created_at: datetime


class IocResponse(BaseModel):
    id: int
    report_id: int
    alert_id: int
    customer_code: str
    ioc_value: str
    ioc_type: str
    vt_verdict: str
    vt_score: Optional[str]
    details: Optional[str]
    created_at: datetime


class CreateJobResponse(BaseModel):
    success: bool
    message: str
    job: Optional[JobResponse] = None


class UpdateJobResponse(BaseModel):
    success: bool
    message: str
    job: Optional[JobResponse] = None


class SubmitReportResponse(BaseModel):
    success: bool
    message: str
    report: Optional[ReportResponse] = None


class SubmitIocsResponse(BaseModel):
    success: bool
    message: str
    iocs_created: int = 0
    iocs: Optional[List[IocResponse]] = None


class JobListResponse(BaseModel):
    success: bool
    message: str
    jobs: List[JobResponse]


class ReportListResponse(BaseModel):
    success: bool
    message: str
    reports: List[ReportResponse]


class IocListResponse(BaseModel):
    success: bool
    message: str
    iocs: List[IocResponse]


class AlertWithReportResponse(BaseModel):
    alert_id: int
    alert_name: str
    customer_code: str
    status: str
    source: str
    assigned_to: Optional[str]
    alert_creation_time: datetime
    report: ReportResponse


class AlertsWithReportsListResponse(BaseModel):
    success: bool
    message: str
    alerts: List[AlertWithReportResponse]


class AlertAnalysisResponse(BaseModel):
    success: bool
    message: str
    job: Optional[JobResponse] = None
    report: Optional[ReportResponse] = None
    iocs: Optional[List[IocResponse]] = None
