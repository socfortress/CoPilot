from fastapi import APIRouter

from app.integrations.log_shipper_test.routes.event_shipper import log_shipper_test_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Log Shipper Test related routes
router.include_router(log_shipper_test_router, prefix="/log_shipper_test", tags=["Log Shipper Test"])
