"""The Customer Portal's languages (#1310): a customer's set, and the portal user's own pick."""

from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from app.customer_portal.utils.locales import SUPPORTED_LOCALES
from app.customer_portal.utils.locales import check_languages


class PortalLanguageSettings(BaseModel):
    customer_code: str
    # English first, then the others in the portal's order.
    languages: List[str]
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None


class PortalLanguageSettingsResponse(BaseModel):
    settings: PortalLanguageSettings
    # Every language the portal ships, for the editor's list.
    supported: List[str] = Field(default_factory=lambda: list(SUPPORTED_LOCALES))
    success: bool
    message: str


class UpdatePortalLanguageSettingsRequest(BaseModel):
    """The whole set, English included: an admin can't leave English out."""

    languages: List[str] = Field(..., max_length=len(SUPPORTED_LOCALES) * 2)

    @field_validator("languages")
    @classmethod
    def _check(cls, value: List[str]) -> List[str]:
        return check_languages(value)


class PortalLanguagesResponse(BaseModel):
    """The portal user's language and the ones they may pick (the union of their customers')."""

    locale: str
    available: List[str]
    success: bool
    message: str


class UpdateMyLocaleRequest(BaseModel):
    locale: str = Field(..., min_length=2, max_length=8)
