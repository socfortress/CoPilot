"""WebAuthn passkey business logic — registration, authentication, credential management."""

import datetime
import json
import os
import uuid
from typing import Optional
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete
from sqlmodel import select
from webauthn import generate_authentication_options
from webauthn import generate_registration_options
from webauthn import options_to_json
from webauthn import verify_authentication_response
from webauthn import verify_registration_response
from webauthn.helpers import base64url_to_bytes
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse
from webauthn.helpers.exceptions import InvalidRegistrationResponse
from webauthn.helpers.structs import AuthenticatorSelectionCriteria
from webauthn.helpers.structs import AuthenticatorTransport
from webauthn.helpers.structs import PublicKeyCredentialDescriptor
from webauthn.helpers.structs import ResidentKeyRequirement
from webauthn.helpers.structs import UserVerificationRequirement

from app.auth.models.passkey import UserPasskey
from app.auth.models.passkey import WebAuthnChallenge
from app.db.db_session import async_engine

CHALLENGE_TTL_SECONDS = 300


def _credential_descriptor(credential_id_b64: str, transports: list | None) -> PublicKeyCredentialDescriptor:
    """Build a descriptor from DB values (transports are stored as plain strings)."""
    normalized_transports = None
    if transports:
        parsed: list[AuthenticatorTransport] = []
        for transport in transports:
            if isinstance(transport, AuthenticatorTransport):
                parsed.append(transport)
            elif isinstance(transport, str):
                try:
                    parsed.append(AuthenticatorTransport(transport))
                except ValueError:
                    logger.debug(f"Ignoring unknown WebAuthn transport: {transport}")
        normalized_transports = parsed or None

    return PublicKeyCredentialDescriptor(
        id=base64url_to_bytes(credential_id_b64),
        transports=normalized_transports,
    )


def _parse_origins() -> list[str]:
    raw = os.environ.get("WEBAUTHN_ORIGINS", os.environ.get("WEBAUTHN_ORIGIN", ""))
    if not raw:
        return []
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


def _get_rp_id() -> str:
    """Static RP ID fallback for status checks. Prefer _get_rp_id_for_origin() in flows."""
    explicit = os.environ.get("WEBAUTHN_RP_ID", "").strip()
    if explicit:
        return explicit

    origins = _parse_origins()
    if origins:
        return urlparse(origins[0]).hostname or "localhost"

    return "localhost"


def _get_rp_id_for_origin(origin: str) -> str:
    """RP ID must match the page origin. Loopback always uses localhost (not 127.0.0.1)."""
    hostname = urlparse(origin).hostname or "localhost"
    explicit = os.environ.get("WEBAUTHN_RP_ID", "").strip()

    if hostname in {"localhost", "127.0.0.1"}:
        return "localhost"

    if explicit and (hostname == explicit or hostname.endswith(f".{explicit}")):
        return explicit

    return explicit or hostname


def _ensure_passkey_origin(origin: str) -> None:
    """Browsers reject WebAuthn on literal 127.0.0.1 — only the localhost hostname works."""
    hostname = urlparse(origin).hostname or ""
    if hostname != "127.0.0.1":
        return

    parsed = urlparse(origin)
    port_suffix = f":{parsed.port}" if parsed.port else ""
    scheme = parsed.scheme or "http"
    raise ValueError(
        f"Passkeys do not work on 127.0.0.1. Open {scheme}://localhost{port_suffix} in your browser instead.",
    )


def _get_rp_name() -> str:
    return os.environ.get("WEBAUTHN_RP_NAME", "SOCFortress CoPilot").strip()


def is_passkey_configured() -> bool:
    """True when RP ID and at least one allowed origin are configured."""
    return bool(_get_rp_id() and _parse_origins())


def resolve_request_origin(request_origin: Optional[str]) -> str:
    """Pick the matching allowed origin for the incoming request."""
    allowed = _parse_origins()
    if not allowed:
        raise ValueError("WebAuthn is not configured. Set WEBAUTHN_ORIGINS and WEBAUTHN_RP_ID.")

    if request_origin:
        normalized = request_origin.rstrip("/")
        if normalized in allowed:
            return normalized

        # Dev convenience: localhost and 127.0.0.1 are interchangeable when the allowed
        # list already contains a loopback origin on the same port/scheme.
        parsed = urlparse(normalized)
        if parsed.hostname in {"localhost", "127.0.0.1"}:
            port_suffix = f":{parsed.port}" if parsed.port else ""
            scheme = parsed.scheme or "http"
            for candidate_host in ("localhost", "127.0.0.1"):
                alias = f"{scheme}://{candidate_host}{port_suffix}"
                if alias in allowed:
                    return normalized

    if len(allowed) == 1:
        return allowed[0]

    raise ValueError("Request origin is not allowed for WebAuthn.")


async def _store_challenge(
    *,
    challenge_bytes: bytes,
    flow: str,
    user_id: Optional[int] = None,
) -> str:
    token = str(uuid.uuid4())
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=CHALLENGE_TTL_SECONDS)

    async with AsyncSession(async_engine) as session:
        await session.execute(delete(WebAuthnChallenge).where(WebAuthnChallenge.expires_at < datetime.datetime.utcnow()))
        session.add(
            WebAuthnChallenge(
                token=token,
                challenge=bytes_to_base64url(challenge_bytes),
                user_id=user_id,
                flow=flow,
                expires_at=expires_at,
            ),
        )
        await session.commit()

    return token


async def _consume_challenge(token: str, flow: str, user_id: Optional[int] = None) -> bytes:
    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(WebAuthnChallenge).where(WebAuthnChallenge.token == token))
        entry = result.scalars().first()

        if entry is None:
            raise ValueError("Challenge not found or already used.")

        if entry.flow != flow:
            raise ValueError("Invalid challenge flow.")

        if entry.expires_at < datetime.datetime.utcnow():
            await session.delete(entry)
            await session.commit()
            raise ValueError("Challenge has expired. Please try again.")

        if user_id is not None and entry.user_id != user_id:
            raise ValueError("Challenge does not match the authenticated user.")

        challenge = base64url_to_bytes(entry.challenge)
        await session.delete(entry)
        await session.commit()
        return challenge


async def list_user_passkeys(user_id: int) -> list[UserPasskey]:
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(UserPasskey).where(UserPasskey.user_id == user_id).order_by(UserPasskey.created_at.desc()),
        )
        return list(result.scalars().all())


async def count_user_passkeys(user_id: int) -> int:
    passkeys = await list_user_passkeys(user_id)
    return len(passkeys)


async def get_passkey_by_credential_id(credential_id_b64: str) -> Optional[UserPasskey]:
    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(UserPasskey).where(UserPasskey.credential_id == credential_id_b64))
        return result.scalars().first()


async def delete_user_passkey(user_id: int, passkey_id: int) -> None:
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(UserPasskey).where(UserPasskey.id == passkey_id, UserPasskey.user_id == user_id),
        )
        entry = result.scalars().first()
        if entry is None:
            raise ValueError("Passkey not found.")
        await session.delete(entry)
        await session.commit()


async def create_registration_options(user_id: int, username: str, device_name: str, origin: str) -> dict:
    if not is_passkey_configured():
        raise ValueError("WebAuthn is not configured on this server.")

    _ensure_passkey_origin(origin)
    rp_id = _get_rp_id_for_origin(origin)

    existing = await list_user_passkeys(user_id)
    exclude_credentials = [_credential_descriptor(pk.credential_id, pk.transports) for pk in existing]

    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=_get_rp_name(),
        user_id=str(user_id).encode(),
        user_name=username,
        user_display_name=username,
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )

    challenge_token = await _store_challenge(
        challenge_bytes=options.challenge,
        flow="register",
        user_id=user_id,
    )

    payload = json.loads(options_to_json(options))
    payload["challengeToken"] = challenge_token
    payload["deviceName"] = device_name
    return payload


async def verify_registration(
    *,
    user_id: int,
    username: str,
    device_name: str,
    challenge_token: str,
    credential: dict,
    origin: str,
) -> UserPasskey:
    _ensure_passkey_origin(origin)
    rp_id = _get_rp_id_for_origin(origin)
    expected_challenge = await _consume_challenge(challenge_token, flow="register", user_id=user_id)

    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            require_user_verification=False,
        )
    except InvalidRegistrationResponse as e:
        raise ValueError(str(e)) from e

    credential_id = bytes_to_base64url(verification.credential_id)
    public_key = bytes_to_base64url(verification.credential_public_key)
    transports = list(credential.get("response", {}).get("transports") or [])

    async with AsyncSession(async_engine) as session:
        existing = await session.execute(select(UserPasskey).where(UserPasskey.credential_id == credential_id))
        if existing.scalars().first():
            raise ValueError("This passkey is already registered.")

        entry = UserPasskey(
            user_id=user_id,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=verification.sign_count,
            transports=transports,
            device_name=device_name or "Passkey",
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)

    logger.info(f"Passkey registered for user {username} (id={user_id})")
    return entry


async def create_authentication_options(username: Optional[str], origin: str) -> dict:
    if not is_passkey_configured():
        raise ValueError("WebAuthn is not configured on this server.")

    _ensure_passkey_origin(origin)
    rp_id = _get_rp_id_for_origin(origin)

    allow_credentials = None
    user_id = None

    if username:
        from app.auth.services.universal import find_user

        user = await find_user(username)
        if user is None:
            raise ValueError("User not found.")

        passkeys = await list_user_passkeys(user.id)
        if not passkeys:
            raise ValueError("No passkeys registered for this user.")

        allow_credentials = [_credential_descriptor(pk.credential_id, pk.transports) for pk in passkeys]
        user_id = user.id

    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    challenge_token = await _store_challenge(
        challenge_bytes=options.challenge,
        flow="login",
        user_id=user_id,
    )

    payload = json.loads(options_to_json(options))
    payload["challengeToken"] = challenge_token
    return payload


async def verify_authentication(
    *,
    challenge_token: str,
    credential: dict,
    origin: str,
) -> UserPasskey:
    _ensure_passkey_origin(origin)
    rp_id = _get_rp_id_for_origin(origin)
    expected_challenge = await _consume_challenge(challenge_token, flow="login")

    credential_id = credential.get("id")
    if not credential_id:
        raise ValueError("Missing credential id.")

    stored = await get_passkey_by_credential_id(credential_id)
    if stored is None:
        raise ValueError("Unknown passkey.")

    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=base64url_to_bytes(stored.public_key),
            credential_current_sign_count=stored.sign_count,
            require_user_verification=False,
        )
    except InvalidAuthenticationResponse as e:
        raise ValueError(str(e)) from e

    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(UserPasskey).where(UserPasskey.id == stored.id))
        entry = result.scalars().first()
        if entry is None:
            raise ValueError("Passkey no longer exists.")

        entry.sign_count = verification.new_sign_count
        entry.last_used_at = datetime.datetime.utcnow()
        session.add(entry)
        await session.commit()
        await session.refresh(entry)

    return entry
