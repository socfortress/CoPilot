from fastapi import APIRouter

from app.integrations.scoutsuite.routes.scoutsuite import integration_scoutsuite_router

# Instantiate the APIRouter
router = APIRouter()

# Include the ScoutSuite related routes
router.include_router(
    integration_scoutsuite_router,
    prefix="/scoutsuite",
    tags=["ScoutSuite"],
)
