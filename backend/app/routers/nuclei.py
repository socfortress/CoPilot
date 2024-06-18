from fastapi import APIRouter

from app.integrations.nuclei.routes.nuclei import integration_nuclei_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Nuclei related routes
router.include_router(
    integration_nuclei_router,
    prefix="/nuclei",
    tags=["Nuclei"],
)
