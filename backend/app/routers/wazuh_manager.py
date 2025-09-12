from fastapi import APIRouter

from app.connectors.wazuh_manager.routes.groups import wazuh_manager_groups_router
from app.connectors.wazuh_manager.routes.management import (
    wazuh_manager_management_router,
)
from app.connectors.wazuh_manager.routes.mitre import wazuh_manager_mitre_router
from app.connectors.wazuh_manager.routes.rules import wazuh_manager_rules_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Wazuh Manager related routes
router.include_router(
    wazuh_manager_rules_router,
    prefix="/wazuh_manager",
    tags=["wazuh-manager"],
)

router.include_router(
    wazuh_manager_groups_router,
    prefix="/wazuh_manager",
    tags=["wazuh-manager"],
)

router.include_router(
    wazuh_manager_mitre_router,
    prefix="/wazuh_manager/mitre",
    tags=["wazuh-manager"],
)

router.include_router(
    wazuh_manager_management_router,
    prefix="/wazuh_manager/management",
    tags=["wazuh-manager"],
)
