"""TOTP 2FA routes — setup, verify, validate at login, disable, regenerate backup codes."""

import os
from datetime import datetime
from datetime import timedelta

import jwt
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.models.totp import TOTPBackupCodesResponse
from app.auth.models.totp import TOTPDisableRequest
from app.auth.models.totp import TOTPSetupResponse
from app.auth.models.totp import TOTPStatusResponse
from app.auth.models.totp import TOTPValidateRequest
from app.auth.models.totp import TOTPVerifyRequest
from app.auth.services.totp import disable_totp
from app.auth.services.totp import is_2fa_enabled
from app.auth.services.totp import regenerate_backup_codes
from app.auth.services.totp import setup_totp
from app.auth.services.totp import validate_totp
from app.auth.services.totp import verify_setup
from app.auth.services.universal import find_user
from app.auth.utils import AuthHandler

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

totp_router = APIRouter()
auth_handler = AuthHandler()

_jwt_secret = auth_handler.secret


# ── Helper: temp token for 2FA pending state ─────────────────────────────────


def _create_temp_token(username: str) -> str:
    """Create a short-lived JWT for 2FA verification step (5 min)."""
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(minutes=5),
        "iat": datetime.utcnow(),
        "type": "2fa_pending",
    }
    return jwt.encode(payload, _jwt_secret, algorithm="HS256")


def _decode_temp_token(token: str) -> str:
    """Decode a 2FA temp token and return the username. Raises ValueError on failure."""
    try:
        payload = jwt.decode(token, _jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "2fa_pending":
            raise ValueError("Invalid token type")
        username = payload.get("sub")
        if not username:
            raise ValueError("No username in token")
        return username
    except jwt.ExpiredSignatureError:
        raise ValueError("2FA verification token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid 2FA verification token.")


# ── Status ───────────────────────────────────────────────────────────────────


@totp_router.get(
    "/2fa/status",
    response_model=TOTPStatusResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_2fa_status(
    token: str = Depends(AuthHandler().security),
):
    """Check if 2FA is enabled for the current user."""
    username, _ = auth_handler.decode_token(token)
    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    enabled = await is_2fa_enabled(user.id)
    return TOTPStatusResponse(enabled=enabled)


# ── Setup ────────────────────────────────────────────────────────────────────


@totp_router.post(
    "/2fa/setup",
    response_model=TOTPSetupResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def start_2fa_setup(
    token: str = Depends(AuthHandler().security),
):
    """Generate a new TOTP secret, QR code, and backup codes. Does NOT activate until verified."""
    username, _ = auth_handler.decode_token(token)
    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    try:
        result = await setup_totp(user.id, user.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TOTPSetupResponse(**result)


# ── Verify setup (activate) ─────────────────────────────────────────────────


@totp_router.post(
    "/2fa/verify-setup",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def verify_2fa_setup(
    body: TOTPVerifyRequest,
    token: str = Depends(AuthHandler().security),
):
    """Verify a TOTP code to activate 2FA."""
    username, _ = auth_handler.decode_token(token)
    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    try:
        await verify_setup(user.id, body.code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Two-factor authentication is now enabled.", "success": True}


# ── Disable ──────────────────────────────────────────────────────────────────


@totp_router.delete(
    "/2fa/disable",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def disable_2fa(
    body: TOTPDisableRequest,
    token: str = Depends(AuthHandler().security),
):
    """Disable 2FA. Requires a valid TOTP code or backup code."""
    username, _ = auth_handler.decode_token(token)
    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not body.code and not body.backup_code:
        raise HTTPException(status_code=400, detail="Provide a TOTP code or backup code.")

    try:
        await disable_totp(user.id, code=body.code, backup_code=body.backup_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Two-factor authentication has been disabled.", "success": True}


# ── Validate at login ────────────────────────────────────────────────────────


@totp_router.post("/2fa/validate")
async def validate_2fa_login(body: TOTPValidateRequest):
    """
    Validate a TOTP code or backup code during login.
    Accepts the temp_token issued by /auth/token when 2FA is required.
    Returns a full access token on success.
    """
    try:
        username = _decode_temp_token(body.temp_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not body.code and not body.backup_code:
        raise HTTPException(status_code=400, detail="Provide a TOTP code or backup code.")

    try:
        await validate_totp(user.id, code=body.code, backup_code=body.backup_code)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Issue full access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await auth_handler.encode_token(user.username, access_token_expires)
    logger.info(f"2FA login completed for {user.username}")

    return {"access_token": access_token, "token_type": "bearer"}


# ── Regenerate backup codes ──────────────────────────────────────────────────


@totp_router.post(
    "/2fa/backup-codes/regenerate",
    response_model=TOTPBackupCodesResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def regenerate_2fa_backup_codes(
    body: TOTPVerifyRequest,
    token: str = Depends(AuthHandler().security),
):
    """Regenerate backup codes. Requires a valid TOTP code. Old codes are invalidated."""
    username, _ = auth_handler.decode_token(token)
    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    try:
        codes = await regenerate_backup_codes(user.id, body.code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TOTPBackupCodesResponse(backup_codes=codes)
