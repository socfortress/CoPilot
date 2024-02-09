from fastapi import APIRouter

from app.connectors.wazuh_manager.routes.rules import wazuh_manager_rules_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Wazuh Manager related routes
router.include_router(
    wazuh_manager_rules_router,
    prefix="/wazuh_manager",
    tags=["wazuh-manager"],
)
