from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

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


ResettableField = Literal["title", "logo", "brand_color"]


class PatchPortalSettingsRequest(BaseModel):
    """Partial update of the global settings: only the fields sent are written.

    Restoring a default is explicit (``reset``), never a null: in ``POST /settings`` a
    missing field and a null both mean "reset", which is why changing only the title
    there means re-sending the whole logo.
    """

    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Portal title.")
    logo_base64: Optional[str] = Field(None, description="Base64 encoded logo image. Send together with logo_mime_type.")
    logo_mime_type: Optional[str] = Field(None, max_length=50, description="MIME type of the logo. Send together with logo_base64.")
    brand_color: Optional[str] = Field(None, max_length=9, description="Brand color as a hex string (e.g. #RRGGBB).")
    reset: List[ResettableField] = Field(
        default_factory=list,
        description="Fields to restore to their default. `logo` resets the logo and its MIME type.",
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

    @model_validator(mode="after")
    def check_consistency(self):
        sent = self.model_fields_set - {"reset"}
        for field in sent:
            if getattr(self, field) is None:
                reset_name = "logo" if field.startswith("logo_") else field
                raise ValueError(f'{field} cannot be empty; to restore its default send reset: ["{reset_name}"]')

        if ("logo_base64" in sent) != ("logo_mime_type" in sent):
            raise ValueError("logo_base64 and logo_mime_type must be sent together")

        touched = {"logo" if field.startswith("logo_") else field for field in sent}
        both = touched & set(self.reset)
        if both:
            raise ValueError(f"Cannot both set and reset: {', '.join(sorted(both))}")

        if not sent and not self.reset:
            raise ValueError("Nothing to update")
        return self

    model_config = ConfigDict(json_schema_extra={"example": {"title": "My Custom Portal", "reset": ["brand_color"]}})


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
