from fastapi import APIRouter

from app.customers.routes.customers import customers_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Customers related routes
router.include_router(customers_router, prefix="/customers", tags=["customers"])
