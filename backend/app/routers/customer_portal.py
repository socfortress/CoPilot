from fastapi import APIRouter

from app.customer_portal.routes.activity import customer_portal_activity_router
from app.customer_portal.routes.agents import customer_portal_agents_router
from app.customer_portal.routes.ai_reports import customer_portal_ai_reports_router
from app.customer_portal.routes.audit import customer_portal_audit_router
from app.customer_portal.routes.branding import customer_portal_branding_router
from app.customer_portal.routes.dashboard import customer_portal_dashboard_router
from app.customer_portal.routes.exposure import customer_portal_exposure_router
from app.customer_portal.routes.ioc_enrichment import (
    customer_portal_ioc_enrichment_router,
)
from app.customer_portal.routes.languages import customer_portal_languages_router
from app.customer_portal.routes.me import customer_portal_me_router
from app.customer_portal.routes.notifications import (
    customer_portal_notifications_router,
)
from app.customer_portal.routes.settings import customer_portal_settings_router
from app.customer_portal.routes.sla import customer_portal_sla_router
from app.customer_portal.routes.soc_requests import customer_portal_soc_requests_router
from app.customer_portal.routes.talon_chat import customer_portal_talon_chat_router
from app.customer_portal.routes.tenant_users import customer_portal_tenant_users_router

# Instantiate the APIRouter
router = APIRouter()

# Include the customer portal settings routes
router.include_router(
    customer_portal_settings_router,
    prefix="/customer_portal",
    tags=["Customer Portal Settings"],
)
# Per-customer branding overrides + the authenticated "which branding do I render?" lookup
router.include_router(
    customer_portal_branding_router,
    prefix="/customer_portal",
    tags=["Customer Portal Branding"],
)
router.include_router(
    customer_portal_dashboard_router,
    prefix="/customer_portal",
    tags=["Customer Portal Dashboard"],
)
# Read-only AI Analyst findings surfaced to end customers
router.include_router(
    customer_portal_ai_reports_router,
    prefix="/customer_portal",
    tags=["Customer Portal AI Reports"],
)
# Paginated agents list, with its cards and filter options, computed server-side
router.include_router(
    customer_portal_agents_router,
    prefix="/customer_portal",
    tags=["Customer Portal Agents"],
)
# The SOC's SLA for the caller's customers (#1187) — opt-in per customer, read-only
router.include_router(
    customer_portal_sla_router,
    prefix="/customer_portal",
    tags=["Customer Portal SLA"],
)
# What the SOC handled for the caller's customers, broken down (#1284) — opt-in per customer
router.include_router(
    customer_portal_activity_router,
    prefix="/customer_portal",
    tags=["Customer Portal Activity"],
)
# Vulnerabilities and compliance across the caller's agents, live from Wazuh (#1289) — opt-in per customer
router.include_router(
    customer_portal_exposure_router,
    prefix="/customer_portal",
    tags=["Customer Portal Exposure"],
)
# The portal's languages: a customer's set (CoPilot) and the portal user's own pick (#1310)
router.include_router(
    customer_portal_languages_router,
    prefix="/customer_portal",
    tags=["Customer Portal Languages"],
)
# The portal user and their customers, with names (the token carries only codes)
router.include_router(
    customer_portal_me_router,
    prefix="/customer_portal",
    tags=["Customer Portal Profile"],
)
# Portal users' email and in-app notifications (#1282) — opt-in per customer, each user's own choices
router.include_router(
    customer_portal_notifications_router,
    prefix="/customer_portal",
    tags=["Customer Portal Notifications"],
)
# A customer admin manages their customers' portal users (#1296)
router.include_router(
    customer_portal_tenant_users_router,
    prefix="/customer_portal",
    tags=["Customer Portal Users"],
)
# Who did what in the caller's customers, for customer admins (#1298) — opt-in per customer
router.include_router(
    customer_portal_audit_router,
    prefix="/customer_portal",
    tags=["Customer Portal Audit Log"],
)
# "Ask the SOC" about an alert or a case (#1305) — opt-in per customer; the SOC's list and its switch
router.include_router(
    customer_portal_soc_requests_router,
    prefix="/customer_portal",
    tags=["Customer Portal Ask the SOC"],
)
# Threat Intel enrichment of the caller's alerts' IOCs (#1318) — opt-in per customer, cached per customer
router.include_router(
    customer_portal_ioc_enrichment_router,
    prefix="/customer_portal",
    tags=["Customer Portal IOC Enrichment"],
)
# Talon chat for portal users (talon-analyst D97) — opt-in per customer, admin-set; the portal proxy
router.include_router(
    customer_portal_talon_chat_router,
    prefix="/customer_portal",
    tags=["Customer Portal Talon Chat"],
)
