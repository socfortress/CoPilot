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


class OverallVerdict(str, Enum):
    UP = "up"
    DOWN = "down"


class TemplateChoice(str, Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    PARTIAL = "partial"


class LessonType(str, Enum):
    ENVIRONMENT = "environment"
    FALSE_POSITIVES = "false_positives"
    ASSETS = "assets"
    THREAT_INTEL = "threat_intel"
    ALERTS = "alerts"


class Durability(str, Enum):
    ONE_OFF = "one_off"
    DURABLE = "durable"


class PalaceLessonStatus(str, Enum):
    PENDING = "pending"
    INGESTED = "ingested"
    FAILED = "failed"


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


# --- Review / Palace Lesson / Replay schemas ---


class IocVerdictCorrection(BaseModel):
    ioc_id: int = Field(..., description="The AiAnalystIoc.id being reviewed")
    verdict_correct: bool = Field(..., description="True if the original VT verdict was correct")
    note: Optional[str] = Field(None, max_length=2000, description="Optional reviewer note")

    @validator("note", pre=True)
    def strip_control_characters_note(cls, v):
        if v is None:
            return v
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)


class SubmitReviewRequest(BaseModel):
    overall_verdict: Optional[OverallVerdict] = Field(None, description="Overall thumbs up/down")
    template_choice: Optional[TemplateChoice] = Field(None, description="Was the selected template correct")
    template_used: Optional[str] = Field(None, max_length=128, description="Template filename that ran (mirrored from report)")
    rating_instructions: Optional[int] = Field(None, ge=1, le=5, description="Rating 1–5 on instructions quality")
    rating_artifacts: Optional[int] = Field(None, ge=1, le=5, description="Rating 1–5 on collected artifacts")
    rating_severity: Optional[int] = Field(None, ge=1, le=5, description="Rating 1–5 on severity assessment accuracy")
    missing_steps: Optional[str] = Field(None, description="Free-text list of steps the analyst missed")
    suggested_edits: Optional[str] = Field(None, description="Free-text suggested prompt / template edits")
    ioc_reviews: List[IocVerdictCorrection] = Field(default_factory=list, description="Per-IOC verdict corrections")

    @validator("missing_steps", "suggested_edits", pre=True)
    def strip_control_characters(cls, v):
        if v is None:
            return v
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)


class IocReviewResponse(BaseModel):
    id: int
    review_id: int
    ioc_id: int
    verdict_correct: bool
    note: Optional[str]
    created_at: datetime


class ReviewResponse(BaseModel):
    id: int
    report_id: int
    alert_id: int
    customer_code: str
    reviewer_user_id: int
    overall_verdict: Optional[str]
    template_choice: Optional[str]
    template_used: Optional[str]
    rating_instructions: Optional[int]
    rating_artifacts: Optional[int]
    rating_severity: Optional[int]
    missing_steps: Optional[str]
    suggested_edits: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    ioc_reviews: List[IocReviewResponse] = Field(default_factory=list)


class MyReviewResponse(BaseModel):
    """Response for 'fetch my existing review for this report' — used by the UI to
    decide whether to show the rubric in create mode or edit-existing mode."""

    success: bool
    message: str
    review: Optional[ReviewResponse] = None


class SubmitReviewResponse(BaseModel):
    success: bool
    message: str
    review: Optional[ReviewResponse] = None


class ReviewListResponse(BaseModel):
    success: bool
    message: str
    reviews: List[ReviewResponse]


class QueuePalaceLessonRequest(BaseModel):
    customer_code: str = Field(..., max_length=64, description="Customer code this lesson applies to")
    lesson_type: LessonType = Field(..., description="MemPalace room / category")
    lesson_text: str = Field(..., min_length=1, description="The lesson text to store")
    durability: Durability = Field(default=Durability.DURABLE, description="one_off = single-session hint, durable = persistent knowledge")
    review_id: Optional[int] = Field(None, description="Optional review.id this lesson was born from")

    @validator("lesson_text", pre=True)
    def strip_control_characters_lesson(cls, v):
        if v is None:
            return v
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)


class PalaceLessonResponse(BaseModel):
    id: int
    review_id: Optional[int]
    customer_code: str
    lesson_type: str
    lesson_text: str
    durability: str
    status: str
    ingested_at: Optional[datetime]
    created_at: datetime


class QueuePalaceLessonResponse(BaseModel):
    success: bool
    message: str
    lesson: Optional[PalaceLessonResponse] = None


class ReplayRequest(BaseModel):
    template_override: str = Field(
        ...,
        max_length=128,
        description="Template filename to force for this replay (e.g. sysmon_event_1.txt)",
    )
    customer_code: str = Field(..., max_length=64, description="Customer code for the alert")
    sender: str = Field(default="copilot-replay", max_length=64, description="Sender identifier for audit")

    @validator("template_override")
    def validate_template_filename(cls, v):
        if not re.match(r"^[a-zA-Z0-9._-]+\.txt$", v):
            raise ValueError("template_override must be a filename matching ^[a-zA-Z0-9._-]+\\.txt$")
        return v


class ReplayResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class PalaceSearchHit(BaseModel):
    id: Optional[str] = None
    room: Optional[str] = None
    wing: Optional[str] = None
    text: Optional[str] = None
    source_file: Optional[str] = None
    score: Optional[float] = None
    metadata: Optional[dict] = None


class PalaceSearchResponse(BaseModel):
    success: bool
    message: str
    lessons: List[PalaceSearchHit] = Field(default_factory=list)


# --- Review stats / feedback dashboard ---


class ReviewStatsTemplate(BaseModel):
    """Per-template slice of review metrics (grouped by template_used)."""

    template_used: Optional[str] = Field(None, description="Template filename, or None for untemplated runs")
    total: int = 0
    thumbs_up: int = 0
    thumbs_down: int = 0
    correct: int = 0
    partial: int = 0
    wrong: int = 0
    avg_rating_instructions: Optional[float] = None
    avg_rating_artifacts: Optional[float] = None
    avg_rating_severity: Optional[float] = None


class ReviewStatsIocAccuracy(BaseModel):
    """Aggregate IOC verdict accuracy — derived from analyst per-IOC corrections."""

    total: int = 0
    correct: int = 0
    incorrect: int = 0
    accuracy_pct: Optional[float] = None


class ReviewStatsResponse(BaseModel):
    success: bool
    message: str
    customer_code: str
    total_reviews: int = 0
    thumbs_up: int = 0
    thumbs_down: int = 0
    thumbs_up_pct: Optional[float] = None
    template_choice_correct: int = 0
    template_choice_partial: int = 0
    template_choice_wrong: int = 0
    avg_rating_instructions: Optional[float] = None
    avg_rating_artifacts: Optional[float] = None
    avg_rating_severity: Optional[float] = None
    ioc_accuracy: ReviewStatsIocAccuracy = Field(default_factory=ReviewStatsIocAccuracy)
    per_template: List[ReviewStatsTemplate] = Field(default_factory=list)
    recent_reviews: List[ReviewResponse] = Field(default_factory=list)


# --- Palace consolidation (Step 21.B) ---


class PalaceConsolidationLesson(BaseModel):
    """A single lesson row, shaped for the consolidation digest UI."""

    id: int
    lesson_type: str
    lesson_text: str
    durability: str
    status: str
    drawer_id: Optional[str] = None
    created_at: datetime
    ingested_at: Optional[datetime] = None
    # For one_off lessons only — how many days until the sweeper expires
    # this row. Negative numbers mean the sweeper is about to take it on
    # the next tick. None for durable rows (no expiry).
    days_until_expiry: Optional[int] = None


class PalaceConsolidationRoomGroup(BaseModel):
    """Per-room slice — lessons grouped by lesson_type."""

    room: str
    total: int
    durable: int
    one_off: int
    lessons: List[PalaceConsolidationLesson] = Field(default_factory=list)


class PalaceConsolidationDuplicatePair(BaseModel):
    """Near-duplicate candidate flagged for reviewer attention."""

    room: str
    lesson_a_id: int
    lesson_b_id: int
    lesson_a_text: str
    lesson_b_text: str
    similarity: float  # 0.0 – 1.0, difflib SequenceMatcher ratio


class PalaceConsolidationResponse(BaseModel):
    """Full digest for a customer — renders inline in a drawer; the
    reviewer can also grab the pre-rendered markdown for export."""

    success: bool
    message: str
    customer_code: str
    generated_at: datetime
    # Top-level counts across active (non-expired, non-failed) lessons
    total_lessons: int = 0
    total_durable: int = 0
    total_one_off: int = 0
    total_pending: int = 0
    total_ingested: int = 0
    # One-off lessons whose expiry is within SOON_WINDOW_DAYS — reviewer
    # may want to promote them to durable before the sweeper deletes them.
    upcoming_expirations: List[PalaceConsolidationLesson] = Field(default_factory=list)
    rooms: List[PalaceConsolidationRoomGroup] = Field(default_factory=list)
    duplicate_candidates: List[PalaceConsolidationDuplicatePair] = Field(default_factory=list)
    # Rendered markdown digest — pre-baked so the drawer can offer a
    # "copy as markdown" button without client-side templating.
    markdown: str = ""
