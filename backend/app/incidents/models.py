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


class Case(SQLModel, table=True):
    __tablename__ = "incident_management_case"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_name: str = Field(max_length=10000, nullable=False)
    case_description: str = Field(sa_column=Text)
    case_creation_time: datetime = Field(default_factory=datetime.utcnow)
    case_status: str = Field(max_length=50, nullable=False)
    assigned_to: Optional[str] = Field(max_length=50, nullable=True)
    customer_code: Optional[str] = Field(max_length=50, nullable=True)
    notification_invoked_number: Optional[int] = Field(default=0, nullable=True)

    alerts: List["CaseAlertLink"] = Relationship(back_populates="case")
    data_store: List["CaseDataStore"] = Relationship(back_populates="case")


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
