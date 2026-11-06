from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class SwitchState(BaseModel):
    """A section that is a per-customer switch: on or off."""

    on: bool


class ListState(BaseModel):
    """A section that holds a list: how many entries this customer has."""

    count: int = Field(..., ge=0)


class LanguagesState(BaseModel):
    """The portal languages: on when the customer offers more than English."""

    on: bool
    count: int = Field(..., ge=1, description="Languages offered, English included")


class CustomerSectionStatus(BaseModel):
    """What each section of a customer's page holds, for the navigation's status lights (#1325).

    Only what an analyst can already read in the section itself; nothing that needs an upstream call.
    """

    integrations: ListState
    network_connectors: ListState
    event_sources: ListState
    waf: ListState
    knowledge: ListState
    ai_triggers: SwitchState
    notification_workflows: ListState
    notification_routes: ListState
    portal_branding: SwitchState
    portal_languages: LanguagesState
    portal_sla: SwitchState
    portal_activity: SwitchState
    portal_exposure: SwitchState
    portal_audit: SwitchState
    portal_ai_report: SwitchState
    # The portal's Talon chat (#1326): on only with the AI reports on as well (``talon_chat.py``).
    portal_talon_chat: SwitchState
    portal_ask_soc: SwitchState
    portal_ioc_enrichment: SwitchState
    portal_notifications: SwitchState


class CustomerSectionStatusResponse(BaseModel):
    success: bool
    message: str
    customer_code: str
    sections: Optional[CustomerSectionStatus] = None
