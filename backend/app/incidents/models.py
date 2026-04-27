from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

from sqlalchemy import PrimaryKeyConstraint
from sqlmodel import JSON
from sqlmodel import Column
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel
from sqlmodel import Text


class IoC(SQLModel, table=True):
    __tablename__ = "incident_management_ioc"
    id: Optional[int] = Field(default=None, primary_key=True)
    value: str = Field(nullable=False)
    type: str = Field(max_length=50, nullable=False)  # e.g., IP address, domain, URL, etc.
    description: Optional[str] = Field(sa_column=Text, nullable=True)

    alerts: List["AlertToIoC"] = Relationship(back_populates="ioc")


class AlertToIoC(SQLModel, table=True):
    __tablename__ = "incident_management_alert_to_ioc"
    alert_id: int = Field(foreign_key="incident_management_alert.id", primary_key=True)
    ioc_id: int = Field(foreign_key="incident_management_ioc.id", primary_key=True)

    alert: "Alert" = Relationship(back_populates="iocs")
    ioc: "IoC" = Relationship(back_populates="alerts")


class Alert(SQLModel, table=True):
    __tablename__ = "incident_management_alert"
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_name: str = Field(sa_column=Text, nullable=False)
    alert_description: str = Field(sa_column=Text, nullable=False)
    status: str = Field(max_length=50, nullable=False)
    alert_creation_time: datetime = Field(default_factory=datetime.utcnow)
    customer_code: str = Field(max_length=50, nullable=False)
    time_closed: Optional[datetime] = Field(default=None)
    source: str = Field(max_length=50, nullable=False)
    assigned_to: Optional[str] = Field(max_length=50, nullable=True)
    escalated: bool = Field(default=False, nullable=False)

    comments: List["Comment"] = Relationship(back_populates="alert")
    assets: List["Asset"] = Relationship(back_populates="alert")
    cases: List["CaseAlertLink"] = Relationship(back_populates="alert")
    tags: List["AlertToTag"] = Relationship(back_populates="alert")
    iocs: List["AlertToIoC"] = Relationship(back_populates="alert")


class AlertTag(SQLModel, table=True):
    __tablename__ = "incident_management_alerttag"
    id: Optional[int] = Field(default=None, primary_key=True)
    tag: str = Field(max_length=50, nullable=False)

    alerts: List["AlertToTag"] = Relationship(back_populates="tag")


class AlertToTag(SQLModel, table=True):
    __tablename__ = "incident_management_alert_to_tag"
    alert_id: int = Field(foreign_key="incident_management_alert.id", primary_key=True)
    tag_id: int = Field(foreign_key="incident_management_alerttag.id", primary_key=True)

    alert: Alert = Relationship(back_populates="tags")
    tag: AlertTag = Relationship(back_populates="alerts")


class Comment(SQLModel, table=True):
    __tablename__ = "incident_management_comment"
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_id: int = Field(default=None, foreign_key="incident_management_alert.id")
    comment: str = Field(sa_column=Text)
    user_name: str = Field(max_length=50, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    alert: Alert = Relationship(back_populates="comments")


class AlertContext(SQLModel, table=True):
    __tablename__ = "incident_management_alertcontext"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(max_length=50, nullable=False)
    context: Optional[Dict] = Field(sa_column=Column(JSON), nullable=True)

    assets: List["Asset"] = Relationship(back_populates="alert_context")


class Asset(SQLModel, table=True):
    __tablename__ = "incident_management_asset"
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_linked: int = Field(default=None, foreign_key="incident_management_alert.id")
    asset_name: str = Field(max_length=255, nullable=False)
    alert_context_id: int = Field(foreign_key="incident_management_alertcontext.id")
    agent_id: Optional[str] = Field(default=None, max_length=50)
    velociraptor_id: Optional[str] = Field(default=None, max_length=150)
    customer_code: str = Field(max_length=50, nullable=False)
    index_name: str = Field(max_length=255, nullable=False)
    index_id: str = Field(max_length=255, nullable=False)

    alert: Alert = Relationship(back_populates="assets")
    alert_context: AlertContext = Relationship(back_populates="assets")


class FieldName(SQLModel, table=True):
    __tablename__ = "incident_management_fieldname"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(max_length=50, nullable=False)
    field_name: str = Field(max_length=100, nullable=False)


class AssetFieldName(SQLModel, table=True):
    __tablename__ = "incident_management_assetfieldname"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(max_length=50, nullable=False)
    field_name: str = Field(max_length=100, nullable=False)


class TimestampFieldName(SQLModel, table=True):
    __tablename__ = "incident_management_timestampfieldname"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(max_length=50, nullable=False)
    field_name: str = Field(max_length=100, nullable=False)


class AlertTitleFieldName(SQLModel, table=True):
    __tablename__ = "incident_management_alerttitlefieldname"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(max_length=50, nullable=False)
    field_name: str = Field(max_length=100, nullable=False)


class IoCFieldName(SQLModel, table=True):
    __tablename__ = "incident_management_iocfieldname"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(max_length=50, nullable=False)
    field_name: str = Field(max_length=100, nullable=False)


class CustomerCodeFieldName(SQLModel, table=True):
    __tablename__ = "incident_management_customercodefieldname"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(max_length=50, nullable=False)
    field_name: str = Field(max_length=100, nullable=False)


class CaseComment(SQLModel, table=True):
    __tablename__ = "incident_management_case_comment"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(default=None, foreign_key="incident_management_case.id")
    comment: str = Field(sa_column=Text)
    user_name: str = Field(max_length=50, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    case: "Case" = Relationship(back_populates="comments")


class Case(SQLModel, table=True):
    __tablename__ = "incident_management_case"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_name: str = Field(max_length=10000, nullable=False)
    case_description: str = Field(sa_column=Text)
    case_creation_time: datetime = Field(default_factory=datetime.utcnow)
    case_status: str = Field(max_length=50, nullable=False)
    case_closed_time: Optional[datetime] = Field(default=None, nullable=True)
    assigned_to: Optional[str] = Field(max_length=50, nullable=True)
    customer_code: Optional[str] = Field(max_length=50, nullable=True)
    notification_invoked_number: Optional[int] = Field(default=0, nullable=True)
    escalated: bool = Field(default=False, nullable=False)

    alerts: List["CaseAlertLink"] = Relationship(back_populates="case")
    data_store: List["CaseDataStore"] = Relationship(back_populates="case")
    comments: List["CaseComment"] = Relationship(back_populates="case")


class CaseAlertLink(SQLModel, table=True):
    __tablename__ = "incident_management_casealertlink"
    case_id: Optional[int] = Field(default=None, foreign_key="incident_management_case.id")
    alert_id: Optional[int] = Field(default=None, foreign_key="incident_management_alert.id")

    case: Case = Relationship(back_populates="alerts")
    alert: Alert = Relationship(back_populates="cases")

    __table_args__ = (PrimaryKeyConstraint("case_id", "alert_id"),)


class Notification(SQLModel, table=True):
    __tablename__ = "incident_management_notification"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(max_length=50, nullable=False)
    shuffle_workflow_id: str = Field(max_length=1000, nullable=False)
    enabled: bool = Field(default=True)


class AIAnalystTriggerEnabled(SQLModel, table=True):
    __tablename__ = "incident_management_ai_analyst_trigger_enabled"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(max_length=50, nullable=False, unique=True)
    enabled: bool = Field(default=True)


class CaseDataStore(SQLModel, table=True):
    __tablename__ = "incident_management_case_datastore"
    id: Optional[int] = Field(default=None, primary_key=True)

    case_id: int = Field(foreign_key="incident_management_case.id", nullable=False)
    bucket_name: str = Field(max_length=255, nullable=False)  # Name of the MinIO bucket
    object_key: str = Field(max_length=1024, nullable=False)  # Path/key of the file in MinIO
    file_name: str = Field(max_length=255, nullable=False)  # Original file name uploaded by the user
    content_type: Optional[str] = Field(max_length=100, nullable=True)  # MIME type of the file
    file_size: Optional[int] = Field(nullable=True)  # File size in bytes
    upload_time: datetime = Field(default_factory=datetime.utcnow)  # Time of upload
    file_hash: str = Field(max_length=128, nullable=False)  # Hash of the file (e.g., SHA-256)

    case: "Case" = Relationship(back_populates="data_store")


class CaseReportTemplateDataStore(SQLModel, table=True):
    __tablename__ = "incident_management_case_report_template_datastore"
    id: Optional[int] = Field(default=None, primary_key=True)

    report_template_name: str = Field(max_length=255, nullable=False)
    bucket_name: str = Field(max_length=255, nullable=False)  # Name of the MinIO bucket
    object_key: str = Field(max_length=1024, nullable=False)  # Path/key of the file in MinIO
    file_name: str = Field(max_length=255, nullable=False)  # Original file name uploaded by the user
    content_type: Optional[str] = Field(max_length=100, nullable=True)  # MIME type of the file
    file_size: Optional[int] = Field(nullable=True)  # File size in bytes
    upload_time: datetime = Field(default_factory=datetime.utcnow)  # Time of upload
    file_hash: str = Field(max_length=128, nullable=False)  # Hash of the file (e.g., SHA-256)


class VeloSigmaExclusion(SQLModel, table=True):
    """Exclusion rules for Velociraptor Sigma alerts."""

    __tablename__ = "incident_management_velo_sigma_exclusion"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, nullable=False, description="Friendly name for this exclusion rule")
    description: Optional[str] = Field(sa_column=Text, nullable=True, description="Description of why this exclusion exists")

    # Core matching criteria
    channel: Optional[str] = Field(max_length=255, nullable=True, description="Windows event channel to match (exact match)")
    title: Optional[str] = Field(max_length=255, nullable=True, description="Sigma rule title to match (exact match)")

    # Field matching data - stored as JSON to allow flexible field matching
    field_matches: Optional[Dict] = Field(
        sa_column=Column(JSON),
        nullable=True,
        description="JSON of field names and values to match in the event data",
    )

    # Metadata
    customer_code: Optional[str] = Field(
        max_length=50,
        nullable=True,
        description="Customer code this exclusion applies to (null means all customers)",
    )
    created_by: str = Field(max_length=100, nullable=False, description="User who created this exclusion")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When this exclusion was created")
    last_matched_at: Optional[datetime] = Field(nullable=True, description="When this exclusion last matched an alert")
    match_count: int = Field(default=0, description="How many times this exclusion has matched")
    enabled: bool = Field(default=True, description="Whether this exclusion is active")


class ThresholdAlertMetadata(SQLModel, table=True):
    """Metadata for threshold alerts to enable event resolution and timeline retrieval."""

    __tablename__ = "incident_management_threshold_alert_metadata"

    id: Optional[int] = Field(default=None, primary_key=True)
    alert_id: int = Field(foreign_key="incident_management_alert.id", nullable=False, unique=True)
    event_definition_id: str = Field(max_length=255, nullable=False, description="Graylog event definition ID")
    replay_query: str = Field(sa_column=Text, nullable=False, description="Lucene query from Graylog replay_info")
    timerange_start: datetime = Field(nullable=False, description="Start of the threshold evaluation window")
    timerange_end: datetime = Field(nullable=False, description="End of the threshold evaluation window")
    group_by_fields: Optional[Dict] = Field(
        sa_column=Column(JSON),
        nullable=True,
        description="Group-by field key/value pairs from the threshold event",
    )
    source_streams: Optional[List] = Field(
        sa_column=Column(JSON),
        nullable=True,
        description="Graylog source stream IDs",
    )
    source: str = Field(max_length=50, nullable=False, description="SOURCE field value (e.g. wazuh)")
    resolved_index_name: str = Field(max_length=255, nullable=False, description="OpenSearch index of the resolved event")
    resolved_index_id: str = Field(max_length=255, nullable=False, description="OpenSearch document ID of the resolved event")

    alert: Alert = Relationship()


class CaseTemplate(SQLModel, table=True):
    """
    Reusable investigation playbook applied to a Case at creation time.

    Templates are scoped via ``customer_code`` (NULL = global) and ``source``
    (NULL = any alert source). Selection priority on case creation is
    customer+source > customer > source > is_default. Templates carry a
    set of ``CaseTemplateTask`` rows that are snapshot-copied into
    ``CaseTask`` rows on the target case.
    """

    __tablename__ = "incident_management_case_template"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, nullable=False, description="Friendly template name")
    description: Optional[str] = Field(sa_column=Text, nullable=True, description="What this template is for")
    customer_code: Optional[str] = Field(
        max_length=50,
        nullable=True,
        description="Customer this template applies to. NULL = global / any customer.",
    )
    source: Optional[str] = Field(
        max_length=50,
        nullable=True,
        description="Alert source this template applies to (e.g., wazuh, velociraptor). NULL = any source.",
    )
    is_default: bool = Field(
        default=False,
        nullable=False,
        description="Default template for its (customer_code, source) scope. Used as the final fallback in selection.",
    )
    created_by: str = Field(max_length=100, nullable=False, description="User who created this template")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    tasks: List["CaseTemplateTask"] = Relationship(back_populates="template")


class CaseTemplateTask(SQLModel, table=True):
    """A predefined task on a CaseTemplate. Definition only — instances live in CaseTask."""

    __tablename__ = "incident_management_case_template_task"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="incident_management_case_template.id", nullable=False)
    title: str = Field(max_length=500, nullable=False)
    description: Optional[str] = Field(sa_column=Text, nullable=True)
    guidelines: Optional[str] = Field(
        sa_column=Text,
        nullable=True,
        description="Best practices / steps the analyst should follow when executing this task",
    )
    mandatory: bool = Field(
        default=False,
        nullable=False,
        description="If true, NOT_NECESSARY status is rejected and closing the case with this task incomplete triggers a soft warning.",
    )
    order_index: int = Field(default=0, nullable=False, description="Display order; lower = first")

    template: "CaseTemplate" = Relationship(back_populates="tasks")


class CaseTask(SQLModel, table=True):
    """
    Instance of a task attached to a real Case.

    Rows are snapshots created by copying CaseTemplateTask fields when a
    template is applied. ``template_task_id`` is an informational soft link
    only — editing the source template does NOT mutate existing CaseTask rows.
    Custom tasks added by analysts during investigation have ``template_task_id``
    set to NULL.
    """

    __tablename__ = "incident_management_case_task"

    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="incident_management_case.id", nullable=False)
    template_task_id: Optional[int] = Field(
        default=None,
        foreign_key="incident_management_case_template_task.id",
        nullable=True,
        description="Soft link back to the source template task. NULL for custom-added tasks.",
    )

    # Snapshot of template task definition at the time of application.
    title: str = Field(max_length=500, nullable=False)
    description: Optional[str] = Field(sa_column=Text, nullable=True)
    guidelines: Optional[str] = Field(sa_column=Text, nullable=True)
    mandatory: bool = Field(default=False, nullable=False)
    order_index: int = Field(default=0, nullable=False)

    # Lifecycle.
    status: str = Field(
        default="TODO",
        max_length=50,
        nullable=False,
        description="One of TODO, DONE, NOT_NECESSARY (NOT_NECESSARY only valid when mandatory=False).",
    )
    evidence_comment: Optional[str] = Field(
        sa_column=Text,
        nullable=True,
        description="Free-form notes / evidence (logs, command output) attached when status changes.",
    )
    completed_by: Optional[str] = Field(max_length=100, nullable=True)
    completed_at: Optional[datetime] = Field(default=None, nullable=True)

    created_by: str = Field(max_length=100, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CaseEvent(SQLModel, table=True):
    """
    Append-only audit log of mutations against a Case.

    Every case-level mutation (status change, alert link/unlink, assignment,
    template application, task add/status change/comment) emits one row.
    Used to power the case timeline view.
    """

    __tablename__ = "incident_management_case_event"

    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="incident_management_case.id", nullable=False, index=True)
    event_type: str = Field(
        max_length=64,
        nullable=False,
        index=True,
        description=(
            "One of: case_created, case_status_changed, case_assigned, case_escalated, "
            "alert_linked, alert_unlinked, comment_added, template_applied, "
            "task_added, task_status_changed, task_commented"
        ),
    )
    actor: str = Field(max_length=100, nullable=False, description="user_name that performed the action")
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    payload: Optional[Dict] = Field(
        sa_column=Column(JSON),
        nullable=True,
        description="Event-type-specific JSON payload (e.g., from_status/to_status, alert_id, task_id).",
    )


class TagAccessSettings(SQLModel, table=True):
    """Global settings for tag-based access control."""

    __tablename__ = "incident_management_tag_access_settings"
    id: Optional[int] = Field(default=None, primary_key=True)

    # Whether tag-based RBAC is enabled (False = current behavior, no filtering)
    enabled: bool = Field(default=False)

    # How to handle untagged alerts: "admin_only", "visible_to_all", "default_tag"
    untagged_alert_behavior: str = Field(default="visible_to_all", max_length=50)

    # If untagged_alert_behavior is "default_tag", which tag to use
    default_tag_id: Optional[int] = Field(
        foreign_key="incident_management_alerttag.id",
        nullable=True,
    )

    # Last modified
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = Field(max_length=100, nullable=True)
