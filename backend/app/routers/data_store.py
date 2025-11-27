from fastapi import APIRouter

from app.data_store.data_store_routes import agent_data_store_router

# Instantiate the APIRouter
router = APIRouter()

# Include the customer portal settings routes
router.include_router(
    agent_data_store_router,
    prefix="/agent_data_store",
    tags=["Agent Data Store"],
)
