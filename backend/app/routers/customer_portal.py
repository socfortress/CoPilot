from fastapi import APIRouter

from app.customer_portal.routes.settings import customer_portal_settings_router

# Instantiate the APIRouter
router = APIRouter()

# Include the customer portal settings routes
router.include_router(
    customer_portal_settings_router,
    prefix="/customer_portal",
    tags=["Customer Portal Settings"],
)
