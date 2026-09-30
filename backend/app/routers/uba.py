from fastapi import APIRouter

from app.connectors.uba.routes.uba import uba_router

# Instantiate the APIRouter
router = APIRouter()

# Include the SOCFortress UBA related routes
router.include_router(uba_router, prefix="/uba", tags=["uba"])
