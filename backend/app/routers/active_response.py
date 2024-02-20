from fastapi import APIRouter

from app.active_response.routes.active_response import active_response_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Stack Provisioning related routes
router.include_router(
    active_response_router,
    prefix="/active_response",
    tags=["Active Response"],
)
