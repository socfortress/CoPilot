from fastapi import APIRouter

from app.connectors.shuffle.routes.workflows import shuffle_workflows_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Shuffle related routes
router.include_router(
    shuffle_workflows_router,
    prefix="/workflows",
    tags=["shuffle-workflows"],
)
