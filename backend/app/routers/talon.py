from fastapi import APIRouter

from app.connectors.talon.routes.talon import talon_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Talon related routes
router.include_router(talon_router, prefix="/talon", tags=["talon"])
