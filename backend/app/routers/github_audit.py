from fastapi import APIRouter

from app.integrations.github_audit.routes.github_audit import (
    github_audit_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the GitHub Audit related routes
router.include_router(
    github_audit_router,
    prefix="/github-audit",
    tags=["GitHub Audit"],
)
