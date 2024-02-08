from app.healthchecks.agents.routes.agents import healtcheck_agents_router
from fastapi import APIRouter

# Instantiate the APIRouter
router = APIRouter()

# Include the Healthcheck related routes
router.include_router(
    healtcheck_agents_router, prefix="/healthcheck", tags=["healthcheck agents"],
)
