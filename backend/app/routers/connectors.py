from app.connectors.routes import connector_router
from fastapi import APIRouter

router = APIRouter()

router.include_router(connector_router, prefix="/connectors", tags=["connectors"])
