from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.mysql import JSON
from typing import Optional, List
from datetime import datetime
from uuid import uuid4
import enum


class AlertStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    work_in_progress = "work_in_progress"


class Alert(SQLModel, table=True):
    __tablename__ = "incident_management_alert"
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_name: str
    alert_description: str  # markdown content
    status: AlertStatus
    alert_creation_time: datetime
    customer_code: str
    time_closed: Optional[datetime] = Field(default=None)
    source: str  # added field to specify the alert source

    comments: List["Comment"] = Relationship(back_populates="alert")
    assets: List["Asset"] = Relationship(back_populates="alert")
    cases: List["CaseAlertLink"] = Relationship(back_populates="alert")


class Comment(SQLModel, table=True):
    __tablename__ = "incident_management_comment"
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_id: int = Field(foreign_key="incident_management_alert.id")
    comment: str
    user_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    alert: Alert = Relationship(back_populates="comments")


class Asset(SQLModel, table=True):
    __tablename__ = "incident_management_asset"
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_linked: int = Field(foreign_key="incident_management_alert.id")
    asset_name: str
    alert_context: dict = Field(sa_column=Column(JSON))  # JSON field mapped to a dict in Pydantic
    agent_id: Optional[str] = Field(default=None)
    velociraptor_id: Optional[str] = Field(default=None)
    customer_code: str
    index_name: str
    index_id: str

    alert: Alert = Relationship(back_populates="assets")


class AlertContext(SQLModel, table=True):
    __tablename__ = "incident_management_alertcontext"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    field_names: List["FieldName"] = Relationship(back_populates="alert_context")
    asset_field_names: List["AssetFieldName"] = Relationship(back_populates="alert_context")


class FieldName(SQLModel, table=True):
    __tablename__ = "incident_management_fieldname"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    field_name: str
    alert_context_id: int = Field(foreign_key="incident_management_alertcontext.id")

    alert_context: AlertContext = Relationship(back_populates="field_names")


class AssetFieldName(SQLModel, table=True):
    __tablename__ = "incident_management_assetfieldname"
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    field_name: str
    alert_context_id: int = Field(foreign_key="incident_management_alertcontext.id")

    alert_context: AlertContext = Relationship(back_populates="asset_field_names")


class Case(SQLModel, table=True):
    __tablename__ = "incident_management_case"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_name: str
    case_description: str

    alerts: List["CaseAlertLink"] = Relationship(back_populates="case")


class CaseAlertLink(SQLModel, table=True):
    __tablename__ = "incident_management_casealertlink"
    case_id: Optional[int] = Field(default=None, primary_key=True)
    alert_id: Optional[int] = Field(default=None, primary_key=True)

    case: Case = Relationship(back_populates="alerts")
    alert: Alert = Relationship(back_populates="cases")
