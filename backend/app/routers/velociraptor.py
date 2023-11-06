from fastapi import APIRouter

from app.connectors.velociraptor.routes.artifacts import velociraptor_artifacts_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Velociraptor related routes
router.include_router(velociraptor_artifacts_router, prefix="/artifacts", tags=["velociraptor-artifacts"])
