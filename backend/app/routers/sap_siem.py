from fastapi import APIRouter

from app.integrations.sap_siem.routes.sap_siem import integration_sap_siem_router

# Instantiate the APIRouter
router = APIRouter()

# Include the SAP SIEM related routes
router.include_router(
    integration_sap_siem_router,
    prefix="/sap_siem",
    tags=["sap_siem"],
)

