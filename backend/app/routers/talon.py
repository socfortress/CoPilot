from fastapi import APIRouter

from app.connectors.talon.routes.talon import talon_router
from app.connectors.talon.routes.talon_v2 import talon_v2_proxy_router
from app.connectors.talon.routes.talon_v2 import talon_v2_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Talon related routes
router.include_router(talon_router, prefix="/talon", tags=["talon"])
# Talon v2 (talon-analyst M5): the setting, then the thread and chat proxy behind it.
router.include_router(talon_v2_router, prefix="/talon/v2", tags=["talon-v2"])
router.include_router(talon_v2_proxy_router, prefix="/talon/v2", tags=["talon-v2"])
