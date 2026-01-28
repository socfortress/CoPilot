from fastapi import APIRouter

from app.connectors.wazuh_indexer.routes.alerts import wazuh_indexer_alerts_router
from app.connectors.wazuh_indexer.routes.monitoring import wazuh_indexer_router
from app.connectors.wazuh_indexer.routes.sigma import wazuh_indexer_sigma_router
from app.connectors.wazuh_indexer.routes.snapshot_and_restore import wazuh_indexer_snapshots_router

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
router.include_router(
    wazuh_indexer_sigma_router,
    prefix="/sigma",
    tags=["wazuh-indexer-sigma"],
)
router.include_router(
    wazuh_indexer_snapshots_router,
    prefix="/snapshots",
    tags=["wazuh-indexer-snapshots"],
)
