from fastapi import APIRouter

from app.customer_portal.routes.branding import customer_portal_branding_router
from app.customer_portal.routes.dashboard import customer_portal_dashboard_router
from app.customer_portal.routes.settings import customer_portal_settings_router

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
