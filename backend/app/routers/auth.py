from fastapi import APIRouter

from app.auth.routes.auth import auth_router
from app.auth.routes.customer_users import customer_users_router

# Instantiate the APIRouter
router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(customer_users_router, prefix="/auth", tags=["customer_users"])
