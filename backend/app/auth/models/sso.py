"""SSO configuration and allowed email models."""

import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import EmailStr
from sqlmodel import Field
from sqlmodel import SQLModel


class SSOConfig(SQLModel, table=True):
    """Stores SSO provider configuration. Only one row should exist (id=1)."""

    __tablename__ = "sso_config"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Global toggle
    sso_enabled: bool = Field(default=False)

    # --- Azure Entra ID (OAuth2 / OIDC) ---
    azure_enabled: bool = Field(default=False)
    azure_tenant_id: Optional[str] = Field(default=None, max_length=256)
    azure_client_id: Optional[str] = Field(default=None, max_length=256)
    azure_client_secret: Optional[str] = Field(default=None, max_length=512)
    azure_redirect_uri: Optional[str] = Field(default=None, max_length=512)

    # --- Google OAuth2 / OIDC ---
    google_enabled: bool = Field(default=False)
    google_client_id: Optional[str] = Field(default=None, max_length=256)
    google_client_secret: Optional[str] = Field(default=None, max_length=512)
    google_redirect_uri: Optional[str] = Field(default=None, max_length=512)

    # --- Cloudflare Access (JWT assertion) ---
    cf_enabled: bool = Field(default=False)
    cf_team_domain: Optional[str] = Field(default=None, max_length=256)
    cf_audience: Optional[str] = Field(default=None, max_length=512)

    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class SSOAllowedEmail(SQLModel, table=True):
    """Allowlist of emails permitted to authenticate via SSO."""

    __tablename__ = "sso_allowed_email"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(max_length=256, index=True)
    role_id: int = Field(default=2)  # default to analyst
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# ── Pydantic request / response schemas ──────────────────────────────────────


class SSOConfigUpdate(BaseModel):
    """Request body for updating SSO settings."""

    sso_enabled: bool = False

    azure_enabled: bool = False
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_redirect_uri: Optional[str] = None

    google_enabled: bool = False
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: Optional[str] = None

    cf_enabled: bool = False
    cf_team_domain: Optional[str] = None
    cf_audience: Optional[str] = None


class SSOConfigResponse(BaseModel):
    """Response body — never exposes the client_secret in full."""

    sso_enabled: bool
    azure_enabled: bool
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret_set: bool = False  # True if a secret is stored
    azure_redirect_uri: Optional[str] = None
    google_enabled: bool = False
    google_client_id: Optional[str] = None
    google_client_secret_set: bool = False  # True if a secret is stored
    google_redirect_uri: Optional[str] = None
    cf_enabled: bool
    cf_team_domain: Optional[str] = None
    cf_audience: Optional[str] = None
    message: str = "SSO configuration retrieved"
    success: bool = True


class SSOAllowedEmailInput(BaseModel):
    email: EmailStr
    role_id: int = 2  # analyst by default


class SSOAllowedEmailOut(BaseModel):
    id: int
    email: str
    role_id: int
    created_at: datetime.datetime


class SSOAllowedEmailListResponse(BaseModel):
    emails: list
    message: str = "Allowed emails retrieved"
    success: bool = True


class SSOPublicStatusResponse(BaseModel):
    """Public endpoint — tells the login page which SSO providers are active."""

    sso_enabled: bool
    azure_enabled: bool
    google_enabled: bool = False
    cf_enabled: bool
    azure_authorization_url: Optional[str] = None
    google_authorization_url: Optional[str] = None
