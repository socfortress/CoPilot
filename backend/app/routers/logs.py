from app.utils import logs_router
from fastapi import APIRouter

# Instantiate the APIRouter
router = APIRouter()

# Include the Logs related routes
router.include_router(logs_router, prefix="/logs", tags=["logs"])
