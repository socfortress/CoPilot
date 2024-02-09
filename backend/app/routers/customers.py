from app.customers.routes.customers import customers_router
from fastapi import APIRouter

# Instantiate the APIRouter
router = APIRouter()

# Include the Customers related routes
router.include_router(customers_router, prefix="/customers", tags=["customers"])
