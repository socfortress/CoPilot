from fastapi import APIRouter

from app.reporting.routes.reporting import report_generation_router

# Instantiate the APIRouter
router = APIRouter()

# Include the reporting related routes
router.include_router(
    report_generation_router,
    prefix="/reporting",
    tags=["Reporting"],
)
