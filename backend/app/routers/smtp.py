from fastapi import APIRouter

from app.smtp.routes.configure import smtp_configure_router
from app.smtp.routes.reports import smtp_reports_router

# Instantiate the APIRouter
router = APIRouter()

# Include the SMTP related routes
router.include_router(smtp_configure_router, prefix="/smtp", tags=["smtp"])
router.include_router(smtp_reports_router, prefix="/smtp", tags=["smtp"])
