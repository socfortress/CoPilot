from app.agents.routes.agents import agents_router
from fastapi import APIRouter

# Instantiate the APIRouter
router = APIRouter()

# Include the Wazuh Manager related routes
router.include_router(agents_router, prefix="/agents", tags=["agents"])
