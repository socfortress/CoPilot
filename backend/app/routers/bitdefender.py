from fastapi import APIRouter

from app.integrations.bitdefender.routes.provision import integration_bitdefender_router

# Instantiate the APIRouter
router = APIRouter()

# Include the BitDefender related routes
router.include_router(
    integration_bitdefender_router,
    prefix="/bitdefender",
    tags=["BitDefender"],
)
