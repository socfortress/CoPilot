from fastapi import APIRouter

from app.connectors.routes import connector_router

router = APIRouter()

router.include_router(connector_router, prefix="/connectors", tags=["connectors"])
