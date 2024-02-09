from fastapi import APIRouter

from app.utils import logs_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Logs related routes
router.include_router(logs_router, prefix="/logs", tags=["logs"])
