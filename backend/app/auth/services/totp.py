"""TOTP 2FA business logic — setup, verification, backup codes, brute-force protection."""

import base64

# ── Encryption key for TOTP secrets ──────────────────────────────────────────
import hashlib
import io
import os
import secrets
import string
import time
from typing import Optional

import pyotp
import qrcode
from cryptography.fernet import Fernet
from loguru import logger
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select

from app.auth.models.totp import UserTOTP
from app.auth.utils import AuthHandler
from app.db.db_session import async_engine

# Prefer a dedicated TOTP_ENCRYPTION_KEY (proper Fernet key, separate from JWT).
# Falls back to a key derived from JWT_SECRET so existing deployments that
# haven't set TOTP_ENCRYPTION_KEY continue to decrypt stored TOTP secrets.
_totp_enc_key = os.environ.get("TOTP_ENCRYPTION_KEY")
if _totp_enc_key:
    _fernet_key = _totp_enc_key.encode()
else:
    _fernet_key = base64.urlsafe_b64encode(hashlib.sha256(AuthHandler.secret.encode()).digest())
_fernet = Fernet(_fernet_key)

_pwd_ctx = CryptContext(schemes=["bcrypt"])

# ── Brute-force protection ───────────────────────────────────────────────────
# Per-user: {user_id: (fail_count, first_fail_time)}
_2fa_attempts: dict[int, tuple[int, float]] = {}
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 900  # 15 min


def _check_rate_limit(user_id: int) -> None:
    """Raise ValueError if user has too many recent 2FA failures."""
    entry = _2fa_attempts.get(user_id)
    if entry is None:
        return
    fail_count, first_fail_time = entry
    if time.time() - first_fail_time > _LOCKOUT_SECONDS:
        # Window expired, reset
        _2fa_attempts.pop(user_id, None)
        return
    if fail_count >= _MAX_ATTEMPTS:
        remaining = int(_LOCKOUT_SECONDS - (time.time() - first_fail_time))
        raise ValueError(f"Too many failed 2FA attempts. Try again in {remaining} seconds.")


def _record_failure(user_id: int) -> None:
    entry = _2fa_attempts.get(user_id)
    if entry is None or time.time() - entry[1] > _LOCKOUT_SECONDS:
        _2fa_attempts[user_id] = (1, time.time())
    else:
        _2fa_attempts[user_id] = (entry[0] + 1, entry[1])


def _clear_failures(user_id: int) -> None:
    _2fa_attempts.pop(user_id, None)


# ── Encryption helpers ───────────────────────────────────────────────────────


def _encrypt_secret(secret: str) -> str:
    return _fernet.encrypt(secret.encode()).decode()


def _decrypt_secret(enc: str) -> str:
    return _fernet.decrypt(enc.encode()).decode()


# ── Backup codes ─────────────────────────────────────────────────────────────

_BACKUP_CODE_COUNT = 8
_BACKUP_CODE_LENGTH = 10


def _generate_backup_codes() -> tuple[list[str], list[dict]]:
    """Generate backup codes. Returns (plaintext_list, hashed_list_for_db)."""
    alphabet = string.ascii_uppercase + string.digits
    codes = []
    hashed = []
    for _ in range(_BACKUP_CODE_COUNT):
        code = "".join(secrets.choice(alphabet) for _ in range(_BACKUP_CODE_LENGTH))
        codes.append(code)
        hashed.append({"hash": _pwd_ctx.hash(code), "used": False})
    return codes, hashed


def _verify_backup_code(backup_code: str, stored_codes: list[dict]) -> int:
    """Verify a backup code. Returns the index if valid, -1 otherwise."""
    for i, entry in enumerate(stored_codes):
        if entry.get("used"):
            continue
        if _pwd_ctx.verify(backup_code.upper().strip(), entry["hash"]):
            return i
    return -1


# ── QR code generation ───────────────────────────────────────────────────────


def _generate_qr_data_uri(otpauth_url: str) -> str:
    """Generate a QR code as a base64 data URI."""
    img = qrcode.make(otpauth_url, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


# ── DB operations ────────────────────────────────────────────────────────────


async def get_user_totp(user_id: int) -> Optional[UserTOTP]:
    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(UserTOTP).where(UserTOTP.user_id == user_id))
        return result.scalars().first()


async def is_2fa_enabled(user_id: int) -> bool:
    totp = await get_user_totp(user_id)
    return totp is not None and totp.enabled


async def setup_totp(user_id: int, username: str) -> dict:
    """Generate a new TOTP secret and backup codes. Does NOT activate until verified."""
    secret = pyotp.random_base32()
    enc_secret = _encrypt_secret(secret)
    plaintext_codes, hashed_codes = _generate_backup_codes()

    totp = pyotp.TOTP(secret)
    issuer = "CoPilot"
    otpauth_url = totp.provisioning_uri(name=username, issuer_name=issuer)
    qr_data_uri = _generate_qr_data_uri(otpauth_url)

    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(UserTOTP).where(UserTOTP.user_id == user_id))
        existing = result.scalars().first()
        if existing and existing.enabled:
            raise ValueError("2FA is already enabled. Disable it first to reconfigure.")

        if existing:
            existing.secret_enc = enc_secret
            existing.backup_codes = hashed_codes
            existing.enabled = False
            existing.last_used_at = None
        else:
            entry = UserTOTP(
                user_id=user_id,
                secret_enc=enc_secret,
                enabled=False,
                backup_codes=hashed_codes,
                last_used_at=None,
            )
            session.add(entry)

        await session.commit()

    logger.info(f"2FA setup initiated for user_id={user_id}")
    return {
        "secret": secret,
        "otpauth_url": otpauth_url,
        "qr_data_uri": qr_data_uri,
        "backup_codes": plaintext_codes,
    }


async def verify_setup(user_id: int, code: str) -> bool:
    """Verify a TOTP code to activate 2FA."""
    _check_rate_limit(user_id)

    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(UserTOTP).where(UserTOTP.user_id == user_id))
        entry = result.scalars().first()
        if entry is None:
            raise ValueError("No 2FA setup found. Call setup first.")
        if entry.enabled:
            raise ValueError("2FA is already enabled.")

        secret = _decrypt_secret(entry.secret_enc)
        totp = pyotp.TOTP(secret)

        # valid_window=1 → accept ±1 step (±30s drift tolerance)
        if not totp.verify(code, valid_window=1):
            _record_failure(user_id)
            raise ValueError("Invalid verification code. Check your authenticator app and device clock.")

        entry.enabled = True
        entry.last_used_at = int(time.time()) // 30  # current TOTP counter
        await session.commit()

    _clear_failures(user_id)
    logger.info(f"2FA activated for user_id={user_id}")
    return True


async def validate_totp(user_id: int, code: Optional[str] = None, backup_code: Optional[str] = None) -> bool:
    """Validate a TOTP code or backup code during login."""
    _check_rate_limit(user_id)

    if not code and not backup_code:
        raise ValueError("Provide either a TOTP code or a backup code.")

    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(UserTOTP).where(UserTOTP.user_id == user_id))
        entry = result.scalars().first()
        if entry is None or not entry.enabled:
            raise ValueError("2FA is not enabled for this user.")

        # Try TOTP code first
        if code:
            secret = _decrypt_secret(entry.secret_enc)
            totp = pyotp.TOTP(secret)
            current_counter = int(time.time()) // 30

            if not totp.verify(code, valid_window=1):
                _record_failure(user_id)
                raise ValueError("Invalid authentication code.")

            # Replay prevention: reject if same counter as last use
            if entry.last_used_at is not None and current_counter <= entry.last_used_at:
                _record_failure(user_id)
                raise ValueError("This code has already been used. Wait for a new code.")

            entry.last_used_at = current_counter
            await session.commit()
            _clear_failures(user_id)
            return True

        # Try backup code
        if backup_code:
            codes = list(entry.backup_codes)
            idx = _verify_backup_code(backup_code, codes)
            if idx < 0:
                _record_failure(user_id)
                raise ValueError("Invalid backup code.")

            codes[idx]["used"] = True
            entry.backup_codes = codes
            flag_modified(entry, "backup_codes")
            await session.commit()
            _clear_failures(user_id)
            logger.info(f"2FA backup code used for user_id={user_id} (code index {idx})")
            return True

    raise ValueError("Provide either a TOTP code or a backup code.")


async def disable_totp(user_id: int, code: Optional[str] = None, backup_code: Optional[str] = None) -> bool:
    """Disable 2FA. Requires a valid TOTP code or backup code."""
    # Validate the code first
    await validate_totp(user_id, code=code, backup_code=backup_code)

    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(UserTOTP).where(UserTOTP.user_id == user_id))
        entry = result.scalars().first()
        if entry:
            await session.delete(entry)
            await session.commit()

    logger.info(f"2FA disabled for user_id={user_id}")
    return True


async def regenerate_backup_codes(user_id: int, code: str) -> list[str]:
    """Regenerate backup codes. Requires a valid TOTP code."""
    _check_rate_limit(user_id)

    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(UserTOTP).where(UserTOTP.user_id == user_id))
        entry = result.scalars().first()
        if entry is None or not entry.enabled:
            raise ValueError("2FA is not enabled.")

        # Verify current TOTP code
        secret = _decrypt_secret(entry.secret_enc)
        totp = pyotp.TOTP(secret)
        if not totp.verify(code, valid_window=1):
            _record_failure(user_id)
            raise ValueError("Invalid authentication code.")

        plaintext_codes, hashed_codes = _generate_backup_codes()
        entry.backup_codes = hashed_codes
        await session.commit()

    _clear_failures(user_id)
    logger.info(f"2FA backup codes regenerated for user_id={user_id}")
    return plaintext_codes
