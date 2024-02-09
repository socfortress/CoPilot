from fastapi import APIRouter

from app.integrations.ask_socfortress.routes.ask_socfortress import (
    ask_socfortress_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the Ask SocFortress related routes
router.include_router(
    ask_socfortress_router,
    prefix="/ask_socfortress",
    tags=["Ask SocFortress Integration"],
)
