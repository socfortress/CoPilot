"""WebAuthn passkey routes — registration, login, and credential management."""

import os
from datetime import timedelta

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Security
from loguru import logger

from app.auth.models.passkey import PasskeyItemResponse
from app.auth.models.passkey import PasskeyListResponse
from app.auth.models.passkey import PasskeyLoginOptionsRequest
from app.auth.models.passkey import PasskeyLoginResponse
from app.auth.models.passkey import PasskeyRegisterOptionsRequest
from app.auth.models.passkey import PasskeyStatusResponse
from app.auth.models.passkey import PasskeyVerifyRequest
from app.auth.models.users import RoleEnum
from app.auth.routes.totp import _create_temp_token
from app.auth.services.passkey import create_authentication_options
from app.auth.services.passkey import create_registration_options
from app.auth.services.passkey import delete_user_passkey
from app.auth.services.passkey import is_passkey_configured
from app.auth.services.passkey import list_user_passkeys
from app.auth.services.passkey import resolve_request_origin
from app.auth.services.passkey import verify_authentication
from app.auth.services.passkey import verify_registration
from app.auth.services.totp import is_2fa_enabled
from app.auth.services.universal import find_user
from app.auth.services.universal import find_user_by_id
from app.auth.utils import AuthHandler

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

passkey_router = APIRouter()
auth_handler = AuthHandler()


def _request_origin(request: Request) -> str:
    origin = request.headers.get("origin") or request.headers.get("Origin")
    try:
        return resolve_request_origin(origin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _issue_token_or_2fa(user) -> dict:
    if await is_2fa_enabled(user.id):
        temp_token = _create_temp_token(user.username)
        return {"access_token": temp_token, "requires_2fa": True}

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await auth_handler.encode_token(user.username, access_token_expires)
    return {"access_token": access_token, "requires_2fa": False}


# ── Public status ────────────────────────────────────────────────────────────


@passkey_router.get("/passkey/status", response_model=PasskeyStatusResponse)
async def passkey_public_status():
    """Public endpoint — whether passkey login is available on this deployment."""
    configured = is_passkey_configured()
    return PasskeyStatusResponse(enabled=configured, count=0)


# ── Authenticated status / list / delete ─────────────────────────────────────


@passkey_router.get(
    "/passkey/me",
    response_model=PasskeyListResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_my_passkeys(token: str = Depends(AuthHandler().security)):
    username, _ = auth_handler.decode_token(token)
    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    passkeys = await list_user_passkeys(user.id)
    return PasskeyListResponse(
        passkeys=[
            PasskeyItemResponse(
                id=pk.id,
                device_name=pk.device_name,
                created_at=pk.created_at,
                last_used_at=pk.last_used_at,
                transports=pk.transports or [],
            )
            for pk in passkeys
        ],
    )


@passkey_router.get(
    "/passkey/me/status",
    response_model=PasskeyStatusResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def my_passkey_status(token: str = Depends(AuthHandler().security)):
    username, _ = auth_handler.decode_token(token)
    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    passkeys = await list_user_passkeys(user.id)
    return PasskeyStatusResponse(enabled=len(passkeys) > 0, count=len(passkeys))


@passkey_router.delete(
    "/passkey/{passkey_id}",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_passkey(
    passkey_id: int,
    token: str = Depends(AuthHandler().security),
):
    username, _ = auth_handler.decode_token(token)
    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    try:
        await delete_user_passkey(user.id, passkey_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"message": "Passkey removed.", "success": True}


# ── Registration (authenticated) ─────────────────────────────────────────────


@passkey_router.post(
    "/passkey/register/options",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def passkey_register_options(
    body: PasskeyRegisterOptionsRequest,
    request: Request,
    token: str = Depends(AuthHandler().security),
):
    username, _ = auth_handler.decode_token(token)
    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    origin = _request_origin(request)
    device_name = (body.device_name or "Passkey").strip()[:128] or "Passkey"

    try:
        options = await create_registration_options(user.id, user.username, device_name, origin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return options


@passkey_router.post(
    "/passkey/register/verify",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def passkey_register_verify(
    body: PasskeyVerifyRequest,
    request: Request,
    token: str = Depends(AuthHandler().security),
):
    username, _ = auth_handler.decode_token(token)
    user = await find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    origin = _request_origin(request)
    device_name = (body.device_name or "Passkey").strip()[:128] or "Passkey"

    try:
        await verify_registration(
            user_id=user.id,
            username=user.username,
            device_name=device_name,
            challenge_token=body.challenge_token,
            credential=body.credential,
            origin=origin,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Passkey registered successfully.", "success": True}


# ── Login (public) ───────────────────────────────────────────────────────────


@passkey_router.post("/passkey/login/options")
async def passkey_login_options(body: PasskeyLoginOptionsRequest, request: Request):
    origin = _request_origin(request)
    username = body.username.strip() if body.username else None

    try:
        options = await create_authentication_options(username, origin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return options


@passkey_router.post("/passkey/login/verify", response_model=PasskeyLoginResponse)
async def passkey_login_verify(body: PasskeyVerifyRequest, request: Request):
    origin = _request_origin(request)

    try:
        stored = await verify_authentication(
            challenge_token=body.challenge_token,
            credential=body.credential,
            origin=origin,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    user = await find_user_by_id(stored.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.role_id == RoleEnum.customer_user.value:
        logger.warning(f"Customer user {user.username} attempted passkey login to main portal")
        raise HTTPException(
            status_code=403,
            detail="This account is registered for the Customer Portal only. Please log in at the Customer Portal to access your account.",
        )

    result = await _issue_token_or_2fa(user)
    logger.info(f"Passkey login for {user.username}, requires_2fa={result['requires_2fa']}")

    return PasskeyLoginResponse(
        access_token=result["access_token"],
        requires_2fa=result["requires_2fa"],
    )
