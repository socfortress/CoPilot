from fastapi import APIRouter

from app.integrations.sap_siem.routes.provision import (
    integration_sap_siem_provision_scheduler_router,
)
from app.integrations.sap_siem.routes.sap_siem import integration_sap_siem_router

# Instantiate the APIRouter
router = APIRouter()

# Include the SAP SIEM related routes
router.include_router(
    integration_sap_siem_router,
    prefix="/sap_siem",
    tags=["sap_siem"],
)

# Include the SAP SIEM provisioning related routes
router.include_router(
    integration_sap_siem_provision_scheduler_router,
    prefix="/sap_siem",
    tags=["sap_siem"],
)
