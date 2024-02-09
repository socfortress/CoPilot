from app.auth.routes.auth import auth_router
from fastapi import APIRouter

# Instantiate the APIRouter
router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
