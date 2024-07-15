from sqlmodel import SQLModel, Field, Relationship, Column, JSON, Text
from typing import Optional, List, Dict
from datetime import datetime
from uuid import uuid4
from sqlalchemy import PrimaryKeyConstraint, ForeignKey


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
    assigned_to: str = Field(max_length=50, nullable=True)

    comments: List["Comment"] = Relationship(back_populates="alert")
    assets: List["Asset"] = Relationship(back_populates="alert")
    cases: List["CaseAlertLink"] = Relationship(back_populates="alert")
    tags: List["AlertToTag"] = Relationship(back_populates="alert")

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


class Case(SQLModel, table=True):
    __tablename__ = "incident_management_case"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_name: str = Field(max_length=10000, nullable=False)
    case_description: str = Field(sa_column=Text)
    case_creation_time: datetime = Field(default_factory=datetime.utcnow)
    case_status: str = Field(max_length=50, nullable=False)
    assigned_to: str = Field(max_length=50, nullable=True)

    alerts: List["CaseAlertLink"] = Relationship(back_populates="case")


class CaseAlertLink(SQLModel, table=True):
    __tablename__ = "incident_management_casealertlink"
    case_id: Optional[int] = Field(default=None, foreign_key="incident_management_case.id")
    alert_id: Optional[int] = Field(default=None, foreign_key="incident_management_alert.id")

    case: Case = Relationship(back_populates="alerts")
    alert: Alert = Relationship(back_populates="cases")

    __table_args__ = (
        PrimaryKeyConstraint('case_id', 'alert_id'),
    )
