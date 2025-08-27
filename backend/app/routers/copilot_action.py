from fastapi import APIRouter

from app.integrations.copilot_action.routes.copilot_action import copilot_action_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Copilot Action related routes
router.include_router(
    copilot_action_router,
    prefix="/copilot_action",
    tags=["Copilot Action"],
)
