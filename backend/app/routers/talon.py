from fastapi import APIRouter

from app.connectors.talon.routes.talon import talon_router
from app.connectors.talon.routes.talon_actions import talon_actions_router
from app.connectors.talon.routes.talon_collections import talon_collect_start_router
from app.connectors.talon.routes.talon_collections import (
    talon_collection_settings_router,
)
from app.connectors.talon.routes.talon_v2 import talon_v2_proxy_router
from app.connectors.talon.routes.talon_v2 import talon_v2_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Talon related routes
router.include_router(talon_router, prefix="/talon", tags=["talon"])
# Talon v2 (talon-analyst M5): the setting, then the thread and chat proxy behind it.
router.include_router(talon_v2_router, prefix="/talon/v2", tags=["talon-v2"])
router.include_router(talon_v2_proxy_router, prefix="/talon/v2", tags=["talon-v2"])
# Talon v2 action proposals: approve, deny, withdraw (talon-analyst M5-11), behind the same setting.
router.include_router(talon_actions_router, prefix="/talon/actions", tags=["talon-v2"])
# The collection start route for talon-analyst's investigations (EA-4b), behind the same setting,
# beside /artifacts/collect; and the admin's setting for the Talon service account's allowlist.
router.include_router(talon_collect_start_router, prefix="/artifacts", tags=["talon-v2"])
router.include_router(talon_collection_settings_router, prefix="/talon/v2", tags=["talon-v2"])
