"""Request/response shapes for per-customer Customer Portal branding overrides.

The validators mirror the global portal-settings ones (``schema/settings.py``) so
an override cannot carry a payload the global settings would have rejected.
"""
import base64
import re
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

ALLOWED_LOGO_MIME_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/svg+xml", "image/webp"]
MAX_LOGO_BASE64_BYTES = 5 * 1024 * 1024  # 5MB base64 == ~3.75MB original


def _validate_brand_color(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if not v:
        return None
    if not re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", v):
        raise HTTPException(
            status_code=400,
            detail="Invalid brand_color. Expected a hex color like #RGB or #RRGGBB",
        )
    return v.lower()


def _validate_logo_base64(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v

    # Accept a full data URL and keep only the payload.
    if v.startswith("data:"):
        v = v.split(",", 1)[1] if "," in v else v

    if not v:
        return None

    if len(v) > MAX_LOGO_BASE64_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Logo file too large. Maximum size is {MAX_LOGO_BASE64_BYTES // (1024 * 1024)}MB (base64-encoded)",
        )

    if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", v):
        raise HTTPException(status_code=400, detail="Invalid base64 encoded string for logo_base64")

    try:
        base64.b64decode(v)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 data - cannot decode")

    return v


def _validate_mime_type(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if not v:
        return None
    if v not in ALLOWED_LOGO_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid MIME type. Allowed types are: {', '.join(ALLOWED_LOGO_MIME_TYPES)}")
    return v


class UpdateCustomerBrandingRequest(BaseModel):
    """Upsert a customer's branding override.

    ``enabled=false`` keeps the stored values but makes the customer inherit the
    global defaults, so an operator can toggle an override off and back on
    without re-uploading the logo. Any field left null while ``enabled`` is true
    falls back to the global default for that field.
    """

    enabled: bool = Field(True, description="False makes the customer inherit the global portal settings.")
    title: Optional[str] = Field(None, max_length=255, description="Custom portal title. Null/empty inherits the global title.")
    logo_base64: Optional[str] = Field(None, description="Base64 encoded logo. Null/empty inherits the global logo.")
    logo_mime_type: Optional[str] = Field(None, max_length=50, description="MIME type of the logo.")
    brand_color: Optional[str] = Field(None, max_length=9, description="Hex brand color (e.g. #RRGGBB). Null inherits the global color.")

    @field_validator("brand_color")
    @classmethod
    def validate_brand_color(cls, v):
        return _validate_brand_color(v)

    @field_validator("logo_base64")
    @classmethod
    def validate_logo_base64(cls, v):
        return _validate_logo_base64(v)

    @field_validator("logo_mime_type")
    @classmethod
    def validate_logo_mime_type(cls, v):
        return _validate_mime_type(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "enabled": True,
                "title": "Acme Security Portal",
                "logo_base64": "iVBORw0KGgoAAAANS...",
                "logo_mime_type": "image/png",
                "brand_color": "#215ac8",
            },
        },
    )


class CustomerBrandingOverride(BaseModel):
    """The stored override row, exactly as configured (no global fallback applied)."""

    id: int
    customer_code: str
    enabled: bool
    title: Optional[str] = None
    logo_base64: Optional[str] = None
    logo_mime_type: Optional[str] = None
    brand_color: Optional[str] = None
    updated_at: str
    updated_by: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class EffectiveBranding(BaseModel):
    """The branding a portal user should actually see, after resolution.

    ``source`` is ``"custom"`` when at least one field came from a per-customer
    override, otherwise ``"global"``. ``customer_code`` is the customer the
    override was resolved for (null when the global defaults were used).
    """

    title: str
    logo_base64: Optional[str] = None
    logo_mime_type: Optional[str] = None
    brand_color: Optional[str] = None
    source: str = "global"
    customer_code: Optional[str] = None


class CustomerBrandingResponse(BaseModel):
    success: bool
    message: str
    override: Optional[CustomerBrandingOverride] = None
    effective: Optional[EffectiveBranding] = None


class CustomerBrandingListItem(BaseModel):
    customer_code: str
    enabled: bool
    title: Optional[str] = None
    has_logo: bool = False
    brand_color: Optional[str] = None
    updated_at: str


class CustomerBrandingListResponse(BaseModel):
    success: bool
    message: str
    overrides: List[CustomerBrandingListItem] = []


class EffectiveBrandingResponse(BaseModel):
    success: bool
    message: str
    settings: Optional[EffectiveBranding] = None
