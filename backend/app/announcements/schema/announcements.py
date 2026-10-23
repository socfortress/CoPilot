"""SOCFortress announcements: the published feed's shape and what the console is sent.

The feed is a JSON document SOCFortress publishes (by default from the public
``socfortress/copilot-announcements`` repository). Every item is validated on its own:
one malformed item is dropped and logged, never the whole feed. Links and images must
be https, and every string is bounded, since the feed is fetched from the internet and
rendered to every analyst.
"""
import re
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import List
from typing import Optional
from urllib.parse import urlsplit

from packaging.version import InvalidVersion
from packaging.version import Version
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

ANNOUNCEMENT_ID = r"^[a-z0-9][a-z0-9._-]{0,79}$"
MAX_URL_LENGTH = 2048
AUDIENCE_ROLES = ("admin", "analyst", "responder")

_UNSAFE_URL_CHARS = re.compile(r"[\s\x00-\x1f\x7f\\]")


class AnnouncementCategory(str, Enum):
    PRODUCT = "product"
    RELEASE = "release"
    ADVISORY = "advisory"
    EVENT = "event"
    PROMOTION = "promotion"


def https_url(value: str) -> str:
    """An absolute https URL with a host, no credentials and nothing a browser would reinterpret."""
    if not isinstance(value, str) or not value or len(value) > MAX_URL_LENGTH:
        raise ValueError("must be an https URL of at most 2048 characters")
    if _UNSAFE_URL_CHARS.search(value):
        raise ValueError("must not contain whitespace, control characters or backslashes")
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("must be an https URL")
    if parts.username is not None or parts.password is not None:
        raise ValueError("must not carry credentials")
    return value


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    """A naive time in the feed is UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class AnnouncementCta(BaseModel):
    label: str = Field(..., min_length=1, max_length=40)
    url: str

    model_config = ConfigDict(extra="ignore")

    @field_validator("url")
    @classmethod
    def _url(cls, value: str) -> str:
        return https_url(value)


class FeedAnnouncement(BaseModel):
    """One item as published. Unknown fields are ignored so the feed can grow."""

    id: str = Field(..., pattern=ANNOUNCEMENT_ID)
    category: AnnouncementCategory
    title: str = Field(..., min_length=1, max_length=120)
    summary: str = Field("", max_length=300)
    body_markdown: str = Field("", max_length=20000)
    image_url: Optional[str] = None
    image_alt: str = Field("", max_length=200)
    cta: Optional[AnnouncementCta] = None
    published_at: datetime
    expires_at: Optional[datetime] = None
    popup: bool = False
    audience: List[str] = Field(default_factory=lambda: list(AUDIENCE_ROLES), max_length=len(AUDIENCE_ROLES))
    min_version: Optional[str] = None
    max_version: Optional[str] = None

    model_config = ConfigDict(extra="ignore")

    @field_validator("image_url")
    @classmethod
    def _image_url(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else https_url(value)

    @field_validator("published_at", "expires_at")
    @classmethod
    def _utc(cls, value: Optional[datetime]) -> Optional[datetime]:
        return _aware(value)

    @field_validator("audience")
    @classmethod
    def _audience(cls, value: List[str]) -> List[str]:
        unknown = [role for role in value if role not in AUDIENCE_ROLES]
        if unknown or not value:
            raise ValueError(f"audience must be a non-empty list of {', '.join(AUDIENCE_ROLES)}")
        return value

    @field_validator("min_version", "max_version")
    @classmethod
    def _version(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            Version(value)
        except InvalidVersion as e:
            raise ValueError("must be a version such as 0.1.99") from e
        return value

    @model_validator(mode="after")
    def _window(self) -> "FeedAnnouncement":
        if self.expires_at is not None and self.expires_at <= self.published_at:
            raise ValueError("expires_at must be after published_at")
        return self


class AnnouncementOut(BaseModel):
    """What the console renders: the targeting fields (audience, versions) stay on the server."""

    id: str
    category: AnnouncementCategory
    title: str
    summary: str
    body_markdown: str
    image_url: Optional[str] = None
    image_alt: str = ""
    cta: Optional[AnnouncementCta] = None
    published_at: datetime
    expires_at: Optional[datetime] = None
    popup: bool


class AnnouncementsResponse(BaseModel):
    success: bool
    message: str
    # False when the deployment turned announcements off (ANNOUNCEMENTS_ENABLED=false):
    # the console then shows no "What's new" entry at all.
    enabled: bool
    announcements: List[AnnouncementOut] = Field(default_factory=list)
