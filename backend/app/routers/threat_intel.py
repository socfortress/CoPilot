from fastapi import APIRouter

from app.threat_intel.routes.epss import threat_intel_epss_router
from app.threat_intel.routes.socfortress import threat_intel_socfortress_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Threat Intel related routes
router.include_router(
    threat_intel_socfortress_router,
    prefix="/threat_intel",
    tags=["Threat Intel"],
)

router.include_router(
    threat_intel_epss_router,
    prefix="/threat_intel",
    tags=["Threat Intel"],
)
