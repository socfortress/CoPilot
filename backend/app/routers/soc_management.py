from fastapi import APIRouter

from app.soc_management.routes.soc_management import soc_management_router

# Instantiate the APIRouter
router = APIRouter()

# SOC Management & SLA (#1187)
router.include_router(soc_management_router, prefix="/soc_management", tags=["soc-management"])
