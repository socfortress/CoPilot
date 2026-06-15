"""WebAuthn passkey models and request/response schemas."""

import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import JSON
from sqlmodel import Column
from sqlmodel import Field
from sqlmodel import SQLModel
from sqlmodel import Text


class WebAuthnChallenge(SQLModel, table=True):
    """Short-lived WebAuthn challenge storage for registration and login flows."""

    __tablename__ = "webauthn_challenge"

    token: str = Field(primary_key=True, max_length=64)
    challenge: str = Field(sa_column=Column(Text, nullable=False))
    user_id: Optional[int] = Field(default=None, index=True)
    flow: str = Field(max_length=16)  # register | login
    expires_at: datetime.datetime = Field(index=True)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class UserPasskey(SQLModel, table=True):
    """Registered WebAuthn credential for a user."""

    __tablename__ = "user_passkey"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    credential_id: str = Field(unique=True, index=True, max_length=512)
    public_key: str = Field(sa_column=Column(Text, nullable=False))
    sign_count: int = Field(default=0)
    transports: list = Field(default=[], sa_column=Column(JSON, nullable=False))
    device_name: str = Field(default="Passkey", max_length=128)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    last_used_at: Optional[datetime.datetime] = Field(default=None)


# ── Pydantic request / response schemas ──────────────────────────────────────


class PasskeyRegisterOptionsRequest(BaseModel):
    device_name: str = "Passkey"


class PasskeyLoginOptionsRequest(BaseModel):
    username: Optional[str] = None


class PasskeyVerifyRequest(BaseModel):
    challenge_token: str
    credential: dict
    device_name: Optional[str] = None


class PasskeyItemResponse(BaseModel):
    id: int
    device_name: str
    created_at: datetime.datetime
    last_used_at: Optional[datetime.datetime] = None
    transports: list[str] = []


class PasskeyListResponse(BaseModel):
    passkeys: list[PasskeyItemResponse]
    message: str = "Passkeys retrieved"
    success: bool = True


class PasskeyStatusResponse(BaseModel):
    enabled: bool
    count: int = 0
    message: str = "Passkey status retrieved"
    success: bool = True


class PasskeyLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_2fa: bool = False
