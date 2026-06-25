from fastapi import APIRouter

from app.audit.routes.audit import audit_router

# Instantiate the APIRouter
router = APIRouter()

# Include the audit log read routes
router.include_router(audit_router, prefix="/audit", tags=["audit"])
