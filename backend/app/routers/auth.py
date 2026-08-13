from fastapi import APIRouter

from app.auth.routes.auth import auth_router
from app.auth.routes.customer_users import customer_users_router
from app.auth.routes.passkey import passkey_router
from app.auth.routes.security_admin import security_admin_router
from app.auth.routes.sso import sso_router
from app.auth.routes.totp import totp_router

# Instantiate the APIRouter
router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(customer_users_router, prefix="/auth", tags=["customer_users"])
router.include_router(sso_router, prefix="/auth", tags=["sso"])
router.include_router(totp_router, prefix="/auth", tags=["2fa"])
router.include_router(passkey_router, prefix="/auth", tags=["passkey"])
router.include_router(security_admin_router, prefix="/auth", tags=["security-admin"])
