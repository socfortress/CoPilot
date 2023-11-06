from fastapi import APIRouter

from app.integrations.dnstwist.routes.analyze import dnstwist_router

# Instantiate the APIRouter
router = APIRouter()

# Include the DNS Twist related routes
router.include_router(dnstwist_router, prefix="/dnstwist", tags=["dnstwist"])
