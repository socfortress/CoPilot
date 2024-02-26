from fastapi import APIRouter

from app.integrations.huntress.routes.huntress import integration_huntress_router


# Instantiate the APIRouter
router = APIRouter()

# Include the Huntress APIRouter
router.include_router(
    integration_huntress_router,
    prefix="/huntress",
    tags=["huntress"],
)
