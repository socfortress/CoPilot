"""TOTP two-factor authentication models and schemas."""

import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import JSON
from sqlmodel import Column
from sqlmodel import Field
from sqlmodel import SQLModel
from sqlmodel import Text


class UserTOTP(SQLModel, table=True):
    """Stores per-user TOTP 2FA configuration."""

    __tablename__ = "user_totp"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(unique=True, index=True)

    # Fernet-encrypted TOTP secret
    secret_enc: str = Field(sa_column=Column(Text, nullable=False))

    # Not enabled until user verifies with a valid code
    enabled: bool = Field(default=False)

    # List of {hash: str, used: bool} — bcrypt hashed backup codes
    backup_codes: list = Field(default=[], sa_column=Column(JSON, nullable=False))

    # Last TOTP counter used — prevents replay of same code
    last_used_at: Optional[int] = Field(default=None)

    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# ── Pydantic request / response schemas ──────────────────────────────────────


class TOTPSetupResponse(BaseModel):
    """Returned on setup — contains secret, QR data, and one-time backup codes."""

    secret: str
    otpauth_url: str
    qr_data_uri: str
    backup_codes: list[str]
    message: str = "Scan the QR code with your authenticator app, then verify with a code."


class TOTPVerifyRequest(BaseModel):
    code: str


class TOTPDisableRequest(BaseModel):
    code: Optional[str] = None
    backup_code: Optional[str] = None


class TOTPValidateRequest(BaseModel):
    """Used during login — temp_token + TOTP code or backup code."""

    temp_token: str
    code: Optional[str] = None
    backup_code: Optional[str] = None


class TOTPStatusResponse(BaseModel):
    enabled: bool
    message: str = "2FA status retrieved"
    success: bool = True


class TOTPBackupCodesResponse(BaseModel):
    backup_codes: list[str]
    message: str = "New backup codes generated. Save them — they are shown only once."
    success: bool = True
