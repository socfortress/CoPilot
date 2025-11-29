from typing import Optional
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException
import re


class UpdatePortalSettingsRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Portal title. Set to null to restore default.")
    logo_base64: Optional[str] = Field(None, description="Base64 encoded logo image. Set to null to restore default.")
    logo_mime_type: Optional[str] = Field(None, max_length=50, description="MIME type of the logo. Set to null to restore default.")

    @validator('logo_base64')
    def validate_base64(cls, v):
        # Allow None to pass through for restoring defaults
        if v is None:
            return v

        # Remove data URL prefix if present (e.g., "data:image/png;base64,")
        if v.startswith('data:'):
            v = v.split(',', 1)[1] if ',' in v else v

        # Validate base64 format
        if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', v):
            raise HTTPException(
                status_code=400,
                detail="Invalid base64 encoded string for logo_base64"
            )
        return v

    @validator('logo_mime_type')
    def validate_mime_type(cls, v):
        # Allow None to pass through for restoring defaults
        if v is None:
            return v

        allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/svg+xml', 'image/webp']
        if v not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid MIME type. Allowed types are: {', '.join(allowed_types)}"
            )
        return v


class PortalSettingsData(BaseModel):
    id: int
    title: str
    logo_base64: Optional[str] = None
    logo_mime_type: Optional[str] = None
    updated_at: str

    class Config:
        from_attributes = True


class PortalSettingsResponse(BaseModel):
    success: bool
    message: str
    settings: Optional[PortalSettingsData] = None


class UpdatePortalSettingsResponse(BaseModel):
    success: bool
    message: str
