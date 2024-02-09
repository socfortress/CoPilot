import datetime
from typing import List
from typing import Optional

from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class FlaggedRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    rule_id: str
    name: str
    severity: Optional[str] = Field(
        None,
        description="Severity level of the flagged rule",
    )
    tags: str
    sublime_alert_id: int = Field(foreign_key="sublimealerts.id")

    # Relationship attribute
    sublime_alert: "SublimeAlerts" = Relationship(back_populates="flagged_rules")


class Mailbox(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: Optional[str] = Field(
        None,
        description="External identifier for the mailbox",
    )
    mailbox_id: str
    sublime_alert_id: int = Field(foreign_key="sublimealerts.id")

    # Relationship attribute
    sublime_alert: "SublimeAlerts" = Relationship(back_populates="mailbox")


class TriggeredAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    action_id: str
    name: str
    type: str
    sublime_alert_id: int = Field(foreign_key="sublimealerts.id")

    # Relationship attribute
    sublime_alert: "SublimeAlerts" = Relationship(back_populates="triggered_actions")


class Sender(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    name: Optional[str] = Field(None, description="Name of the sender")
    sublime_alert_id: int = Field(foreign_key="sublimealerts.id")

    # Relationship attribute
    sublime_alert: "SublimeAlerts" = Relationship(back_populates="sender")


class Recipient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    name: Optional[str] = Field(None, description="Name of the recipient")
    sublime_alert_id: int = Field(foreign_key="sublimealerts.id")

    # Relationship attribute
    sublime_alert: "SublimeAlerts" = Relationship(back_populates="recipients")


class SublimeAlerts(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    api_version: str
    created_at: str
    event_id: str
    type: str
    message_id: str
    canonical_id: str
    external_id: str
    message_source_id: str
    timestamp: datetime.datetime = datetime.datetime.now()

    flagged_rules: List[FlaggedRule] = Relationship(back_populates="sublime_alert")
    mailbox: List[Mailbox] = Relationship(back_populates="sublime_alert")
    triggered_actions: List[TriggeredAction] = Relationship(
        back_populates="sublime_alert",
    )
    sender: List[Sender] = Relationship(back_populates="sublime_alert")
    recipients: List[Recipient] = Relationship(back_populates="sublime_alert")
