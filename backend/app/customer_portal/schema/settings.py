from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from app.customer_portal.utils.validators import validate_brand_color
from app.customer_portal.utils.validators import validate_logo_base64
from app.customer_portal.utils.validators import validate_logo_mime_type


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
        return validate_brand_color(v)

    @field_validator("logo_base64")
    @classmethod
    def validate_base64(cls, v):
        return validate_logo_base64(v)

    @field_validator("logo_mime_type")
    @classmethod
    def validate_mime_type(cls, v):
        return validate_logo_mime_type(v)

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


class PublicPortalSettingsData(BaseModel):
    """The global settings as the anonymous login page sees them: no inline logo."""

    id: int
    title: str
    logo_url: Optional[str] = Field(
        None,
        description="Versioned path of the logo, relative to the API root (e.g. /customer_portal/settings/logo?v=…). Null when no logo is set.",
    )
    logo_mime_type: Optional[str] = None
    brand_color: Optional[str] = None
    updated_at: Optional[str] = None


class PublicPortalSettingsResponse(BaseModel):
    success: bool
    message: str
    settings: Optional[PublicPortalSettingsData] = None


class UpdatePortalSettingsResponse(BaseModel):
    success: bool
    message: str
