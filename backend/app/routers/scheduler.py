from app.schedulers.routes.scheduler import scheduler_router
from fastapi import APIRouter

# Instantiate the APIRouter
router = APIRouter()

# Include the Office365 related routes
router.include_router(scheduler_router, prefix="/scheduler", tags=["Scheduler"])
