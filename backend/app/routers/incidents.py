from fastapi import APIRouter

from app.incidents.routes.db_operations import incidents_db_operations_router

# Instantiate the APIRouter
router = APIRouter()

router.include_router(incidents_db_operations_router, prefix="/incidents/db_operations", tags=["incidents"])
