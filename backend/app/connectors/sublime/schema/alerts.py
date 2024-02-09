import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class FlaggedRule(BaseModel):
    id: str = Field(..., description="Unique identifier for the flagged rule")
    name: str = Field(..., description="Name of the flagged rule")
    severity: Optional[str] = Field(
        None,
        description="Severity level of the flagged rule",
    )
    tags: List[str] = Field(
        ...,
        description="List of tags associated with the flagged rule",
    )


class Mailbox(BaseModel):
    external_id: Optional[str] = Field(
        None,
        description="External identifier for the mailbox",
    )
    id: str = Field(..., description="Unique identifier for the mailbox")


class Message(BaseModel):
    canonical_id: str = Field(..., description="Canonical identifier for the message")
    external_id: Optional[str] = Field(
        None,
        description="External identifier for the mailbox",
    )
    id: str = Field(..., description="Unique identifier for the message")
    mailbox: Mailbox = Field(..., description="Mailbox details")
    message_source_id: str = Field(..., description="Source identifier for the message")


class TriggeredAction(BaseModel):
    id: str = Field(..., description="Unique identifier for the triggered action")
    name: str = Field(..., description="Name of the triggered action")
    type: str = Field(..., description="Type of the triggered action")


class Data(BaseModel):
    flagged_rules: List[FlaggedRule] = Field(..., description="List of flagged rules")
    message: Message = Field(..., description="Message details")
    triggered_actions: List[TriggeredAction] = Field(
        ...,
        description="List of triggered actions",
    )


class AlertRequestBody(BaseModel):
    api_version: str = Field(..., description="API version", alias="api_version")
    created_at: str = Field(
        ...,
        description="Creation timestamp in ISO 8601 format",
        alias="created_at",
    )
    data: Data = Field(..., description="Nested data object")
    id: str = Field(..., description="Unique identifier for the request body")
    type: str = Field(..., description="Type of event, e.g., message.flagged")


class AlertResponseBody(BaseModel):
    success: bool = Field(..., description="Success status of the request")
    message: str = Field(
        ...,
        description="Message describing the result of the request",
    )


### SQLModel Schema
class FlaggedRuleSchema(BaseModel):
    rule_id: str
    name: str
    severity: Optional[str] = Field(
        None,
        description="Severity level of the flagged rule",
    )
    tags: str

    class Config:
        orm_mode = True


class MailboxSchema(BaseModel):
    external_id: Optional[str] = Field(
        None,
        description="External identifier for the mailbox",
    )
    mailbox_id: str

    class Config:
        orm_mode = True


class TriggeredActionSchema(BaseModel):
    action_id: str
    name: str
    type: str

    class Config:
        orm_mode = True


class SenderSchema(BaseModel):
    email: str
    name: str

    class Config:
        orm_mode = True


class RecipientSchema(BaseModel):
    email: str
    name: str

    class Config:
        orm_mode = True


class SublimeAlertsSchema(BaseModel):
    api_version: str
    created_at: str
    event_id: str
    type: str
    message_id: str
    canonical_id: str
    external_id: str
    message_source_id: str
    timestamp: datetime.datetime
    flagged_rules: List[FlaggedRuleSchema]
    mailbox: List[MailboxSchema]
    triggered_actions: List[TriggeredActionSchema]
    sender: List[SenderSchema]
    recipients: List[RecipientSchema]

    class Config:
        orm_mode = True


class SublimeAlertsResponse(BaseModel):
    sublime_alerts: List[SublimeAlertsSchema]
    success: bool
    message: str
