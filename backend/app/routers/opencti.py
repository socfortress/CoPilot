from fastapi import APIRouter

from app.connectors.opencti.routes.opencti import opencti_router

# Instantiate the APIRouter
router = APIRouter()

# Include the OpenCTI related routes
router.include_router(opencti_router, prefix="/opencti", tags=["opencti"])
