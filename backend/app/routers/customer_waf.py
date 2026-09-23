from fastapi import APIRouter

from app.customer_waf.routes.customer_waf import customer_waf_router

# Instantiate the APIRouter
router = APIRouter()

# Include the customer WAF related routes
router.include_router(customer_waf_router, prefix="/customer_waf", tags=["customer-waf"])
