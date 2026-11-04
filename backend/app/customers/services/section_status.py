"""What each section of a customer's page holds, for the navigation's status lights (#1325).

One statement: every figure is a scalar subquery of the same SELECT, so the page pays one round
trip however many sections it shows. The rules stay where they live: a missing settings row is
off (the portal switches, the AI trigger), the portal languages and the portal chat are read
through their own services' helpers.
"""

from typing import Any
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.customer_portal.services.languages import languages_of
from app.customer_portal.services.talon_chat import chat_switched_on
from app.customers.schema.section_status import CustomerSectionStatus
from app.customers.schema.section_status import LanguagesState
from app.customers.schema.section_status import ListState
from app.customers.schema.section_status import SwitchState
from app.db.universal_models import CustomerNotificationRoute
from app.db.universal_models import CustomerPortalActivitySettings
from app.db.universal_models import CustomerPortalAiReportSettings
from app.db.universal_models import CustomerPortalAuditSettings
from app.db.universal_models import CustomerPortalBranding
from app.db.universal_models import CustomerPortalChatSettings
from app.db.universal_models import CustomerPortalExposureSettings
from app.db.universal_models import CustomerPortalIocEnrichmentSettings
from app.db.universal_models import CustomerPortalLanguageSettings
from app.db.universal_models import CustomerPortalNotificationSettings
from app.db.universal_models import CustomerPortalSlaSettings
from app.db.universal_models import CustomerPortalSocRequestSettings
from app.db.universal_models import Customers
from app.db.universal_models import CustomerWafInstance
from app.db.universal_models import EventSources
from app.incidents.models import AIAnalystTriggerEnabled
from app.incidents.models import Notification
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.network_connectors.models.network_connectors import CustomerNetworkConnectors

CUSTOMER_NOT_FOUND = "Customer not found"

# The per-customer switches whose row holds an ``enabled`` column; no row reads as off.
SWITCHES = {
    "ai_triggers": AIAnalystTriggerEnabled,
    "portal_sla": CustomerPortalSlaSettings,
    "portal_activity": CustomerPortalActivitySettings,
    "portal_exposure": CustomerPortalExposureSettings,
    "portal_audit": CustomerPortalAuditSettings,
    "portal_ai_report": CustomerPortalAiReportSettings,
    "portal_ask_soc": CustomerPortalSocRequestSettings,
    "portal_ioc_enrichment": CustomerPortalIocEnrichmentSettings,
    "portal_notifications": CustomerPortalNotificationSettings,
    # A customer's own branding: an override row that is switched on. Only ``enabled`` is read
    # (the row also carries the logo, up to 5 MB); what the branding resolves to is
    # ``customer_portal/services/branding.py``'s.
    "portal_branding": CustomerPortalBranding,
}

# The sections that hold a list, and the column naming the customer in each.
LISTS = {
    "integrations": CustomerIntegrations.customer_code,
    "network_connectors": CustomerNetworkConnectors.customer_code,
    "event_sources": EventSources.customer_code,
    "waf": CustomerWafInstance.customer_code,
    "notification_workflows": Notification.customer_code,
    "notification_routes": CustomerNotificationRoute.customer_code,
}


def _first(column: Any, owner: Any, customer_code: str):
    return select(column).where(owner == customer_code).limit(1).scalar_subquery()


def _count(owner: Any, customer_code: str):
    return select(func.count()).select_from(owner.class_).where(owner == customer_code).scalar_subquery()


def section_status_query(customer_code: str):
    columns = [_count(Customers.customer_code, customer_code).label("customer")]
    columns += [_first(model.enabled, model.customer_code, customer_code).label(key) for key, model in SWITCHES.items()]
    columns += [_count(owner, customer_code).label(key) for key, owner in LISTS.items()]
    language = CustomerPortalLanguageSettings
    columns += [
        _first(language.id, language.customer_code, customer_code).label("languages_row"),
        _first(language.languages, language.customer_code, customer_code).label("languages"),
    ]
    chat = CustomerPortalChatSettings
    columns += [
        _first(chat.id, chat.customer_code, customer_code).label("chat_row"),
        _first(chat.portal_chat_enabled, chat.customer_code, customer_code).label("chat_enabled"),
        _first(chat.daily_message_limit, chat.customer_code, customer_code).label("chat_daily_limit"),
    ]
    return select(*columns)


def _switch(value: Optional[bool]) -> SwitchState:
    return SwitchState(on=bool(value))


def build_status(row: Any) -> CustomerSectionStatus:
    languages = languages_of(
        CustomerPortalLanguageSettings(languages=row.languages) if row.languages_row is not None else None,
    )
    chat_row = (
        CustomerPortalChatSettings(portal_chat_enabled=bool(row.chat_enabled), daily_message_limit=row.chat_daily_limit)
        if row.chat_row is not None
        else None
    )
    return CustomerSectionStatus(
        **{key: _switch(getattr(row, key)) for key in SWITCHES},
        **{key: ListState(count=int(getattr(row, key) or 0)) for key in LISTS},
        portal_languages=LanguagesState(on=len(languages) > 1, count=len(languages)),
        # The chat needs the AI reports on as well (``talon_chat.py``): off without them.
        portal_talon_chat=_switch(bool(row.portal_ai_report) and chat_switched_on(chat_row)),
    )


async def get_section_status(customer_code: str, session: AsyncSession) -> CustomerSectionStatus:
    row = (await session.execute(section_status_query(customer_code))).one()
    if not row.customer:
        raise HTTPException(status_code=404, detail=CUSTOMER_NOT_FOUND)
    return build_status(row)
