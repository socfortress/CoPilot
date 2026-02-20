from fastapi import APIRouter

from app.integrations.copilot_searches.routes.copilot_searches import copilot_searches_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Copilot Searches related routes
router.include_router(
    copilot_searches_router,
    prefix="/copilot_searches",
    tags=["Copilot Searches"],
)
