import base64
import re
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


class UpdatePortalSettingsRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Portal title. Set to null to restore default.")
    logo_base64: Optional[str] = Field(None, description="Base64 encoded logo image. Set to null to restore default.")
    logo_mime_type: Optional[str] = Field(None, max_length=50, description="MIME type of the logo. Set to null to restore default.")
    brand_color: Optional[str] = Field(
        None,
        max_length=9,
        description="Brand color as a hex string (e.g. #RRGGBB), used to theme customer-branded reports. Set to null to restore default.",
    )

    @field_validator("brand_color")
    @classmethod
    def validate_brand_color(cls, v):
        if v is None:
            return v

        v = v.strip()
        if not re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", v):
            raise HTTPException(
                status_code=400,
                detail="Invalid brand_color. Expected a hex color like #RGB or #RRGGBB",
            )
        return v.lower()

    @field_validator("logo_base64")
    @classmethod
    def validate_base64(cls, v):
        if v is None:
            return v

        # Remove data URL prefix if present
        if v.startswith("data:"):
            v = v.split(",", 1)[1] if "," in v else v

        # Check size (limit to 5MB base64 = ~3.75MB original)
        max_size = 5 * 1024 * 1024  # 5MB
        if len(v) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Logo file too large. Maximum size is {max_size // (1024 * 1024)}MB (base64-encoded)",
            )

        # Validate base64 format
        if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", v):
            raise HTTPException(status_code=400, detail="Invalid base64 encoded string for logo_base64")

        # Optional: Try to decode to verify it's valid base64
        try:
            base64.b64decode(v)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 data - cannot decode")

        return v

    @field_validator("logo_mime_type")
    @classmethod
    def validate_mime_type(cls, v):
        if v is None:
            return v

        allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/svg+xml", "image/webp"]
        if v not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Invalid MIME type. Allowed types are: {', '.join(allowed_types)}")
        return v

    model_config = ConfigDict(
        json_schema_extra={"example": {"title": "My Custom Portal", "logo_base64": "iVBORw0KGgoAAAANS...", "logo_mime_type": "image/png"}},
    )


class PortalSettingsData(BaseModel):
    id: int
    title: str
    logo_base64: Optional[str] = None
    logo_mime_type: Optional[str] = None
    brand_color: Optional[str] = None
    updated_at: str
    model_config = ConfigDict(from_attributes=True)


class PortalSettingsResponse(BaseModel):
    success: bool
    message: str
    settings: Optional[PortalSettingsData] = None


class UpdatePortalSettingsResponse(BaseModel):
    success: bool
    message: str
