"""SSO routes — settings management + Azure, Google & Cloudflare login flows."""

import os
from datetime import timedelta
from urllib.parse import quote

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fastapi import Security
from fastapi.responses import RedirectResponse
from loguru import logger

from app.auth.models.sso import SSOAllowedEmailInput
from app.auth.models.sso import SSOAllowedEmailListResponse
from app.auth.models.sso import SSOAllowedEmailOut
from app.auth.models.sso import SSOConfigResponse
from app.auth.models.sso import SSOConfigUpdate
from app.auth.models.sso import SSOPublicStatusResponse
from app.auth.routes.totp import _create_temp_token
from app.auth.services.sso import add_allowed_email
from app.auth.services.sso import build_azure_auth_url
from app.auth.services.sso import build_google_auth_url
from app.auth.services.sso import delete_allowed_email
from app.auth.services.sso import exchange_azure_code
from app.auth.services.sso import exchange_google_code
from app.auth.services.sso import find_allowed_email
from app.auth.services.sso import find_user_by_email
from app.auth.services.sso import get_or_create_sso_user
from app.auth.services.sso import get_sso_config
from app.auth.services.sso import list_allowed_emails
from app.auth.services.sso import upsert_sso_config
from app.auth.services.sso import validate_cf_jwt
from app.auth.services.totp import is_2fa_enabled
from app.auth.utils import AuthHandler

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

sso_router = APIRouter()
auth_handler = AuthHandler()


def _error_redirect(detail: str) -> RedirectResponse:
    """Redirect to the login page with an error message in the query string."""
    return RedirectResponse(url=f"/login?error_message={quote(detail)}")


async def _resolve_sso_user(email: str):
    """
    Resolve an SSO login to a user account.
    - Existing users log in directly (no allowlist check).
    - New users require an allowlist entry for auto-provisioning.
    """
    user = await find_user_by_email(email)
    if user:
        return user

    # New user — require allowlist entry for provisioning
    allowed = await find_allowed_email(email)
    if allowed is None:
        raise ValueError(
            f"Email {email} is not authorized for SSO access. Contact your administrator.",
        )

    return await get_or_create_sso_user(email, role_id=allowed.role_id)


async def _issue_token_or_2fa(user, auth_handler) -> dict:
    """
    Issue a full CoPilot JWT, or — if the user has 2FA enabled — a short-lived
    temp token that the frontend must exchange via /auth/2fa/validate first.
    Returns a dict with at minimum {token, is_2fa}.
    """
    if await is_2fa_enabled(user.id):
        temp_token = _create_temp_token(user.username)
        return {"token": temp_token, "is_2fa": True}

    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = await auth_handler.encode_token(user.username, expires)
    return {"token": token, "is_2fa": False}


# ── Public: SSO status (used by login page) ──────────────────────────────────


@sso_router.get("/sso/status", response_model=SSOPublicStatusResponse)
async def sso_public_status():
    """
    Public endpoint — returns which SSO providers are active.
    The login page uses this to decide whether to show SSO buttons.
    """
    cfg = await get_sso_config()
    if cfg is None or not cfg.sso_enabled:
        return SSOPublicStatusResponse(
            sso_enabled=False,
            azure_enabled=False,
            cf_enabled=False,
        )

    return SSOPublicStatusResponse(
        sso_enabled=True,
        azure_enabled=cfg.azure_enabled,
        google_enabled=cfg.google_enabled,
        cf_enabled=cfg.cf_enabled,
    )


# ── Admin: SSO settings CRUD ─────────────────────────────────────────────────


@sso_router.get(
    "/sso/settings",
    response_model=SSOConfigResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_sso_settings():
    """Retrieve current SSO configuration. Admin only."""
    cfg = await get_sso_config()
    if cfg is None:
        return SSOConfigResponse(
            sso_enabled=False,
            azure_enabled=False,
            google_enabled=False,
            cf_enabled=False,
            message="No SSO configuration found",
        )
    return SSOConfigResponse(
        sso_enabled=cfg.sso_enabled,
        azure_enabled=cfg.azure_enabled,
        azure_tenant_id=cfg.azure_tenant_id,
        azure_client_id=cfg.azure_client_id,
        azure_client_secret_set=bool(cfg.azure_client_secret),
        azure_redirect_uri=cfg.azure_redirect_uri,
        google_enabled=cfg.google_enabled,
        google_client_id=cfg.google_client_id,
        google_client_secret_set=bool(cfg.google_client_secret),
        google_redirect_uri=cfg.google_redirect_uri,
        cf_enabled=cfg.cf_enabled,
        cf_team_domain=cfg.cf_team_domain,
        cf_audience=cfg.cf_audience,
    )


@sso_router.put(
    "/sso/settings",
    response_model=SSOConfigResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def update_sso_settings(body: SSOConfigUpdate):
    """Update SSO configuration. Admin only."""
    data = body.dict(exclude_none=False)

    # Don't overwrite secrets if empty/None
    if not data.get("azure_client_secret"):
        data.pop("azure_client_secret", None)
    if not data.get("google_client_secret"):
        data.pop("google_client_secret", None)

    cfg = await upsert_sso_config(data)
    logger.info(
        f"SSO config updated: sso_enabled={cfg.sso_enabled}, "
        f"azure={cfg.azure_enabled}, google={cfg.google_enabled}, cf={cfg.cf_enabled}",
    )

    return SSOConfigResponse(
        sso_enabled=cfg.sso_enabled,
        azure_enabled=cfg.azure_enabled,
        azure_tenant_id=cfg.azure_tenant_id,
        azure_client_id=cfg.azure_client_id,
        azure_client_secret_set=bool(cfg.azure_client_secret),
        azure_redirect_uri=cfg.azure_redirect_uri,
        google_enabled=cfg.google_enabled,
        google_client_id=cfg.google_client_id,
        google_client_secret_set=bool(cfg.google_client_secret),
        google_redirect_uri=cfg.google_redirect_uri,
        cf_enabled=cfg.cf_enabled,
        cf_team_domain=cfg.cf_team_domain,
        cf_audience=cfg.cf_audience,
        message="SSO configuration updated successfully",
    )


# ── Admin: Allowed emails CRUD ───────────────────────────────────────────────


@sso_router.get(
    "/sso/allowed-emails",
    response_model=SSOAllowedEmailListResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_allowed_emails():
    """List all SSO-allowed emails. Admin only."""
    emails = await list_allowed_emails()
    return SSOAllowedEmailListResponse(
        emails=[
            SSOAllowedEmailOut(
                id=e.id,
                email=e.email,
                role_id=e.role_id,
                created_at=e.created_at,
            )
            for e in emails
        ],
    )


@sso_router.post(
    "/sso/allowed-emails",
    status_code=201,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def create_allowed_email(body: SSOAllowedEmailInput):
    """Add an email to the SSO allowlist. Admin only."""
    try:
        entry = await add_allowed_email(body.email, body.role_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "message": f"Email {body.email} added to SSO allowlist",
        "success": True,
        "id": entry.id,
    }


@sso_router.delete(
    "/sso/allowed-emails/{email_id}",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def remove_allowed_email(email_id: int):
    """Remove an email from the SSO allowlist. Admin only."""
    ok = await delete_allowed_email(email_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Email entry not found")
    return {"message": "Email removed from SSO allowlist", "success": True}


# ── Azure Entra ID: OAuth2 flow ──────────────────────────────────────────────


@sso_router.get("/sso/azure/login")
async def azure_login():
    """Redirect user to Azure Entra ID authorization page."""
    cfg = await get_sso_config()
    if cfg is None or not cfg.sso_enabled or not cfg.azure_enabled:
        raise HTTPException(status_code=400, detail="Azure SSO is not enabled")
    url = build_azure_auth_url(cfg)
    return RedirectResponse(url=url)


@sso_router.get("/sso/azure/callback")
async def azure_callback(code: str = None, state: str = None, error: str = None):
    """
    Azure Entra ID OAuth2 callback.
    Exchanges the authorization code for tokens, validates the ID token,
    checks the email allowlist, and returns a CoPilot JWT.
    """
    if error:
        return _error_redirect(f"Azure auth error: {error}")
    if not code or not state:
        return _error_redirect("Missing code or state parameter")

    cfg = await get_sso_config()
    if cfg is None or not cfg.sso_enabled or not cfg.azure_enabled:
        return _error_redirect("Azure SSO is not enabled")

    try:
        claims = await exchange_azure_code(code, state, cfg)
    except ValueError as e:
        return _error_redirect(str(e))
    except Exception as e:
        logger.error(f"Azure SSO error: {e}")
        return _error_redirect("Azure authentication failed")

    email = claims.get("email") or claims.get("preferred_username")
    if not email:
        return _error_redirect("No email claim in Azure ID token")

    if not claims.get("email_verified", True):
        return _error_redirect("Azure account email is not verified")

    # Existing users log in directly; new users require allowlist entry
    try:
        user = await _resolve_sso_user(email.lower())
    except ValueError as e:
        return _error_redirect(str(e))

    # Issue token (full or 2FA-pending)
    result = await _issue_token_or_2fa(user, auth_handler)
    logger.info(f"SSO Azure login: {user.username} ({email}), 2fa={result['is_2fa']}")

    redirect_url = f"/sso-callback#token={result['token']}"
    if result["is_2fa"]:
        redirect_url += "&requires_2fa=true"
    return RedirectResponse(url=redirect_url)


# ── Google OAuth2: authorization code flow ───────────────────────────────────


@sso_router.get("/sso/google/login")
async def google_login():
    """Redirect user to Google authorization page."""
    cfg = await get_sso_config()
    if cfg is None or not cfg.sso_enabled or not cfg.google_enabled:
        raise HTTPException(status_code=400, detail="Google SSO is not enabled")
    url = build_google_auth_url(cfg)
    return RedirectResponse(url=url)


@sso_router.get("/sso/google/callback")
async def google_callback(code: str = None, state: str = None, error: str = None):
    """
    Google OAuth2 callback.
    Exchanges the authorization code for tokens, validates the ID token,
    checks the email allowlist, and returns a CoPilot JWT.
    """
    if error:
        return _error_redirect(f"Google auth error: {error}")
    if not code or not state:
        return _error_redirect("Missing code or state parameter")

    cfg = await get_sso_config()
    if cfg is None or not cfg.sso_enabled or not cfg.google_enabled:
        return _error_redirect("Google SSO is not enabled")

    try:
        claims = await exchange_google_code(code, state, cfg)
    except ValueError as e:
        return _error_redirect(str(e))
    except Exception as e:
        logger.error(f"Google SSO error: {e}")
        return _error_redirect("Google authentication failed")

    email = claims.get("email")
    if not email:
        return _error_redirect("No email claim in Google ID token")

    if not claims.get("email_verified", False):
        return _error_redirect("Google account email is not verified")

    # Existing users log in directly; new users require allowlist entry
    try:
        user = await _resolve_sso_user(email.lower())
    except ValueError as e:
        return _error_redirect(str(e))

    # Issue token (full or 2FA-pending)
    result = await _issue_token_or_2fa(user, auth_handler)
    logger.info(f"SSO Google login: {user.username} ({email}), 2fa={result['is_2fa']}")

    redirect_url = f"/sso-callback#token={result['token']}"
    if result["is_2fa"]:
        redirect_url += "&requires_2fa=true"
    return RedirectResponse(url=redirect_url)


# ── Cloudflare Access: JWT validation flow ───────────────────────────────────


@sso_router.post("/sso/cloudflare/verify")
async def cloudflare_verify(request: Request):
    """
    Validate the Cf-Access-Jwt-Assertion header from Cloudflare Access.
    Returns a CoPilot JWT if the email is in the allowlist.
    """
    cfg = await get_sso_config()
    if cfg is None or not cfg.sso_enabled or not cfg.cf_enabled:
        raise HTTPException(status_code=400, detail="Cloudflare Access SSO is not enabled")

    # Extract JWT from header (preferred) or cookie
    cf_token = request.headers.get("Cf-Access-Jwt-Assertion")
    if not cf_token:
        cf_token = request.cookies.get("CF_Authorization")
    if not cf_token:
        raise HTTPException(
            status_code=401,
            detail="No Cloudflare Access JWT found in request headers or cookies",
        )

    try:
        claims = await validate_cf_jwt(cf_token, cfg)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Cloudflare Access SSO error: {e}")
        raise HTTPException(status_code=500, detail="Cloudflare authentication failed")

    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No email claim in Cloudflare JWT")

    # Existing users log in directly; new users require allowlist entry
    try:
        user = await _resolve_sso_user(email.lower())
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Issue token (full or 2FA-pending)
    result = await _issue_token_or_2fa(user, auth_handler)
    logger.info(f"SSO Cloudflare login: {user.username} ({email}), 2fa={result['is_2fa']}")

    response = {
        "access_token": result["token"],
        "token_type": "bearer",
        "message": "Cloudflare Access authentication successful",
        "success": True,
    }
    if result["is_2fa"]:
        response["requires_2fa"] = True
    return response
