from fastapi import APIRouter

from app.integrations.microsoft_patch_tuesday.routes.microsoft_patch_tuesday import (
    microsoft_patch_tuesday_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the Microsoft Patch Tuesday related routes
router.include_router(
    microsoft_patch_tuesday_router,
    prefix="/patch-tuesday",
    tags=["Microsoft Patch Tuesday"],
)
