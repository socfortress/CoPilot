from fastapi import APIRouter

from app.connectors.cortex.routes.analyzers import cortex_analyzer_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Cortex related routes
router.include_router(
    cortex_analyzer_router,
    prefix="/analyzers",
    tags=["cortex-analyzers"],
)
