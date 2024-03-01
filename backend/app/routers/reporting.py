from fastapi import APIRouter

from app.reporting.testing import reporting_router

# Instantiate the APIRouter
router = APIRouter()

# Include the reporting related routes
router.include_router(
    reporting_router,
    prefix="/reporting",
    tags=["Reporting"],
)
