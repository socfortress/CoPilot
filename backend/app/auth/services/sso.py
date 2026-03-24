"""SSO business logic — Azure Entra ID, Google & Cloudflare Access."""

import datetime
import hashlib
import hmac
import os
import re
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth.models.sso import SSOAllowedEmail
from app.auth.models.sso import SSOConfig
from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import async_engine

# ── HMAC-signed OAuth2 state (stateless, multi-worker safe) ──────────────────
# State format: "<nonce>:<unix_ts>:<hmac_hex>"
# Self-validating — no in-memory or DB store needed. Works across multiple
# uvicorn workers and survives process restarts.
_STATE_TTL_SECONDS = 600
# Use a dedicated SSO_STATE_SECRET if provided; fall back to JWT_SECRET so
# existing deployments that haven't set this variable continue to work.
_STATE_SECRET = os.environ.get("SSO_STATE_SECRET") or AuthHandler().secret

# Allowed pattern for Cloudflare team domains — must end in cloudflareaccess.com
_CF_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9-]+\.cloudflareaccess\.com$")


def _generate_state() -> str:
    """Generate a self-validating HMAC-signed OAuth2 state token."""
    nonce = secrets.token_urlsafe(16)
    ts = str(int(datetime.datetime.utcnow().timestamp()))
    msg = f"{nonce}:{ts}".encode()
    mac = hmac.new(_STATE_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    return f"{nonce}:{ts}:{mac}"


def _validate_state(state: str) -> bool:
    """Validate a self-signed state token. Returns True if valid and not expired."""
    try:
        nonce, ts_str, mac = state.rsplit(":", 2)
        msg = f"{nonce}:{ts_str}".encode()
        expected = hmac.new(_STATE_SECRET.encode(), msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(mac, expected):
            return False
        age = datetime.datetime.utcnow().timestamp() - float(ts_str)
        return 0 <= age <= _STATE_TTL_SECONDS
    except Exception:
        return False


# ── SSO Config CRUD ──────────────────────────────────────────────────────────


async def get_sso_config() -> Optional[SSOConfig]:
    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(SSOConfig).where(SSOConfig.id == 1))
        return result.scalars().first()


async def upsert_sso_config(data: dict) -> SSOConfig:
    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(SSOConfig).where(SSOConfig.id == 1))
        cfg = result.scalars().first()
        if cfg is None:
            cfg = SSOConfig(id=1)
            session.add(cfg)
        for key, value in data.items():
            if not hasattr(cfg, key):
                continue
            # Booleans: always set (False is a valid value)
            # Strings/None: set if key present in payload — allows explicit clearing
            # Skip provider secrets if None (don't overwrite existing secrets)
            if key in ("azure_client_secret", "google_client_secret") and value is None:
                continue
            setattr(cfg, key, value)
        cfg.updated_at = datetime.datetime.utcnow()
        session.add(cfg)
        await session.commit()
        await session.refresh(cfg)
        return cfg


# ── Allowed Emails CRUD ──────────────────────────────────────────────────────


async def list_allowed_emails() -> list[SSOAllowedEmail]:
    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(SSOAllowedEmail).order_by(SSOAllowedEmail.id))
        return list(result.scalars().all())


async def add_allowed_email(email: str, role_id: int = 2) -> SSOAllowedEmail:
    email = email.lower().strip()
    async with AsyncSession(async_engine) as session:
        # Check duplicate
        result = await session.execute(
            select(SSOAllowedEmail).where(SSOAllowedEmail.email == email)
        )
        existing = result.scalars().first()
        if existing:
            raise ValueError(f"Email {email} is already in the allowlist")
        entry = SSOAllowedEmail(email=email, role_id=role_id)
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return entry


async def delete_allowed_email(email_id: int) -> bool:
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(SSOAllowedEmail).where(SSOAllowedEmail.id == email_id)
        )
        entry = result.scalars().first()
        if entry is None:
            return False
        await session.delete(entry)
        await session.commit()
        return True


async def find_allowed_email(email: str) -> Optional[SSOAllowedEmail]:
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(SSOAllowedEmail).where(SSOAllowedEmail.email == email)
        )
        return result.scalars().first()


# ── Auto‑provision SSO user ──────────────────────────────────────────────────


async def get_or_create_sso_user(email: str, role_id: int = 2) -> User:
    """Find existing user by email or create a new SSO‑managed user."""
    from passlib.context import CryptContext

    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if user:
            return user

        # Create a new user with a random unusable password
        pwd_ctx = CryptContext(schemes=["bcrypt"])
        random_pw = secrets.token_urlsafe(64)
        hashed = pwd_ctx.hash(random_pw)

        username = email.split("@")[0]
        # Ensure unique username
        base = username
        counter = 1
        while True:
            result = await session.execute(select(User).where(User.username == username))
            if result.scalars().first() is None:
                break
            username = f"{base}{counter}"
            counter += 1

        user = User(
            username=username,
            password=hashed,
            email=email,
            role_id=role_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"SSO: Auto‑provisioned user '{username}' ({email}) with role_id={role_id}")
        return user


# ── Azure Entra ID helpers ───────────────────────────────────────────────────

_azure_keys_cache: dict[str, tuple[datetime.datetime, list]] = {}


def build_azure_auth_url(cfg: SSOConfig) -> str:
    """Build the Azure OAuth2 authorization URL."""
    state = _generate_state()
    params = {
        "client_id": cfg.azure_client_id,
        "response_type": "code",
        "redirect_uri": cfg.azure_redirect_uri,
        "response_mode": "query",
        "scope": "openid profile email",
        "state": state,
        "nonce": secrets.token_urlsafe(16),
        "prompt": "select_account",
    }
    base = f"https://login.microsoftonline.com/{cfg.azure_tenant_id}/oauth2/v2.0/authorize"
    return f"{base}?{urlencode(params)}"


async def exchange_azure_code(code: str, state: str, cfg: SSOConfig) -> dict:
    """Exchange an authorization code for tokens and return the ID token claims."""
    if not _validate_state(state):
        raise ValueError("Invalid or expired OAuth2 state parameter")

    token_url = f"https://login.microsoftonline.com/{cfg.azure_tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": cfg.azure_client_id,
        "client_secret": cfg.azure_client_secret,
        "code": code,
        "redirect_uri": cfg.azure_redirect_uri,
        "grant_type": "authorization_code",
        "scope": "openid profile email",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(token_url, data=data)
        resp.raise_for_status()
        token_data = resp.json()

    id_token = token_data.get("id_token")
    if not id_token:
        raise ValueError("No id_token in Azure response")

    # Fetch JWKS for signature validation (cached, with retry on key miss)
    jwks_url = f"https://login.microsoftonline.com/{cfg.azure_tenant_id}/discovery/v2.0/keys"
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")

    async def _get_azure_keys() -> list:
        now = datetime.datetime.utcnow()
        cache_key = cfg.azure_tenant_id
        if cache_key in _azure_keys_cache:
            cached_at, keys = _azure_keys_cache[cache_key]
            if (now - cached_at).total_seconds() < 3600:
                return keys
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            jwks = resp.json()
        keys = [{"kid": k.get("kid"), "key": RSAAlgorithm.from_jwk(k)} for k in jwks.get("keys", [])]
        _azure_keys_cache[cache_key] = (now, keys)
        return keys

    public_key = None
    for attempt in range(2):
        for k in await _get_azure_keys():
            if k["kid"] == kid:
                public_key = k["key"]
                break
        if public_key:
            break
        _azure_keys_cache.pop(cfg.azure_tenant_id, None)

    if public_key is None:
        raise ValueError("Unable to find matching signing key in Azure JWKS")

    claims = jwt.decode(
        id_token,
        key=public_key,
        algorithms=["RS256"],
        audience=cfg.azure_client_id,
        issuer=f"https://login.microsoftonline.com/{cfg.azure_tenant_id}/v2.0",
        options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
    )

    return claims


# ── Google OAuth2 / OIDC helpers ────────────────────────────────────────────

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUER = "https://accounts.google.com"

# Cache for Google public keys (same pattern as Cloudflare)
_google_keys_cache: dict[str, tuple[datetime.datetime, list]] = {}


def build_google_auth_url(cfg: SSOConfig) -> str:
    """Build the Google OAuth2 authorization URL."""
    state = _generate_state()
    params = {
        "client_id": cfg.google_client_id,
        "response_type": "code",
        "redirect_uri": cfg.google_redirect_uri,
        "scope": "openid email",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"


async def _get_google_public_keys() -> list:
    """Fetch and cache Google's public JWKS keys (TTL 1 hour)."""
    now = datetime.datetime.utcnow()
    if "google" in _google_keys_cache:
        cached_at, keys = _google_keys_cache["google"]
        if (now - cached_at).total_seconds() < 3600:
            return keys

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_GOOGLE_JWKS_URL)
        resp.raise_for_status()
        data = resp.json()

    keys = []
    for jwk in data.get("keys", []):
        public_key = RSAAlgorithm.from_jwk(jwk)
        keys.append({"kid": jwk.get("kid"), "key": public_key})

    _google_keys_cache["google"] = (now, keys)
    return keys


async def exchange_google_code(code: str, state: str, cfg: SSOConfig) -> dict:
    """Exchange a Google authorization code for tokens and return ID token claims."""
    if not _validate_state(state):
        raise ValueError("Invalid or expired OAuth2 state parameter")

    data = {
        "client_id": cfg.google_client_id,
        "client_secret": cfg.google_client_secret,
        "code": code,
        "redirect_uri": cfg.google_redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(_GOOGLE_TOKEN_URL, data=data)
        resp.raise_for_status()
        token_data = resp.json()

    id_token = token_data.get("id_token")
    if not id_token:
        raise ValueError("No id_token in Google response")

    # Fetch JWKS and find matching key; retry once on miss (handles key rotation)
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")

    for attempt in range(2):
        keys = await _get_google_public_keys()
        for k in keys:
            if k["kid"] == kid:
                claims = jwt.decode(
                    id_token,
                    key=k["key"],
                    algorithms=["RS256"],
                    audience=cfg.google_client_id,
                    issuer=_GOOGLE_ISSUER,
                    options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
                )
                return claims
        # Key not found — bust the cache and retry once
        _google_keys_cache.pop("google", None)

    raise ValueError("Unable to find matching signing key in Google JWKS")


# ── Cloudflare Access helpers ────────────────────────────────────────────────

# Cache for Cloudflare public keys
_cf_keys_cache: dict[str, tuple[datetime.datetime, list]] = {}


async def _get_cf_public_keys(team_domain: str) -> list:
    """Fetch and cache Cloudflare Access public keys."""
    cache_key = team_domain
    now = datetime.datetime.utcnow()
    if cache_key in _cf_keys_cache:
        cached_at, keys = _cf_keys_cache[cache_key]
        if (now - cached_at).total_seconds() < 3600:  # cache for 1 hour
            return keys

    certs_url = f"https://{team_domain}/cdn-cgi/access/certs"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(certs_url)
        resp.raise_for_status()
        data = resp.json()

    keys = []
    for jwk in data.get("keys", []):
        public_key = RSAAlgorithm.from_jwk(jwk)
        keys.append({"kid": jwk.get("kid"), "key": public_key})

    _cf_keys_cache[cache_key] = (now, keys)
    return keys


async def validate_cf_jwt(token: str, cfg: SSOConfig) -> dict:
    """Validate a Cloudflare Access JWT assertion and return its claims."""
    if not cfg.cf_team_domain or not _CF_DOMAIN_RE.match(cfg.cf_team_domain):
        raise ValueError(
            f"Invalid Cloudflare team domain '{cfg.cf_team_domain}'. "
            "Must match *.cloudflareaccess.com"
        )

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    keys = await _get_cf_public_keys(cfg.cf_team_domain)

    expected_issuer = f"https://{cfg.cf_team_domain}"

    for k in keys:
        if k["kid"] == kid:
            claims = jwt.decode(
                token,
                key=k["key"],
                algorithms=["RS256"],
                audience=cfg.cf_audience,
                issuer=expected_issuer,
                options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
            )
            return claims

    raise ValueError("Unable to find matching signing key in Cloudflare JWKS")
