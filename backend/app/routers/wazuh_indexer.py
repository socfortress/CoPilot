from fastapi import APIRouter

from app.connectors.wazuh_indexer.routes.alerts import wazuh_indexer_alerts_router
from app.connectors.wazuh_indexer.routes.monitoring import wazuh_indexer_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Wazuh Indexer related routes
router.include_router(
    wazuh_indexer_alerts_router,
    prefix="/alerts",
    tags=["wazuh-indexer-alerts"],
)
router.include_router(
    wazuh_indexer_router,
    prefix="/wazuh_indexer",
    tags=["wazuh-indexer-monitoring"],
)
