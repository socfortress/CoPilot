from fastapi import APIRouter

from app.status.routes.context import context_router

router = APIRouter()

router.include_router(
    context_router,
    prefix="/status",
    tags=["Status"],
)
