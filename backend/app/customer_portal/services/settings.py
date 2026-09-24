"""Global Customer Portal settings as served to anonymous callers.

``GET /customer_portal/settings`` is public: the login page calls it before anyone
is authenticated. Two rules follow from that:

* **It never writes.** The default row is created once at startup
  (``ensure_default_portal_settings``) or by the first admin save; a missing row
  simply reads as the defaults.
* **It never inlines the logo.** The logo can be up to 5MB of base64, so the
  settings carry only a versioned ``logo_url`` and the bytes are served by
  ``GET /customer_portal/settings/logo`` with ``ETag`` + ``Cache-Control``.
"""
import base64
import binascii
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.customer_portal.schema.settings import PublicPortalSettingsData
from app.db.universal_models import CustomerPortalSettings

# Relative to the API root, like every path the portal's HTTP client calls.
LOGO_PATH = "/customer_portal/settings/logo"
EFFECTIVE_LOGO_PATH = "/customer_portal/settings/effective/logo"


@dataclass
class PortalLogo:
    content: bytes
    mime_type: str
    etag: str


def _logo_version(updated_at: Optional[datetime]) -> str:
    """Version token for the logo: any save moves ``updated_at``, which busts the cached URL."""
    return str(int(updated_at.timestamp() * 1000)) if updated_at else "0"


def logo_content_version(logo_base64: str) -> str:
    """Version token derived from the logo itself, for logos with no single ``updated_at`` (merged branding)."""
    return hashlib.sha256(logo_base64.encode()).hexdigest()[:16]


def decode_logo(logo_base64: Optional[str], mime_type: Optional[str], version: str) -> Optional[PortalLogo]:
    """Decode a stored base64 logo; None when there is none or it cannot be decoded."""
    if not logo_base64:
        return None
    try:
        content = base64.b64decode(logo_base64, validate=True)
    except (binascii.Error, ValueError):
        logger.error("Stored customer portal logo is not valid base64")
        return None
    return PortalLogo(content=content, mime_type=mime_type or "image/png", etag=f'"{version}"')


async def ensure_default_portal_settings(async_engine) -> None:
    """Create the global settings row if it is missing. Idempotent, never raises."""
    try:
        async with AsyncSession(async_engine) as session:
            result = await session.execute(select(CustomerPortalSettings.id).limit(1))
            if result.scalars().first() is None:
                session.add(CustomerPortalSettings.create_default())
                await session.commit()
                logger.info("Created default customer portal settings")
    except Exception as e:
        # The public endpoint reads a missing row as the defaults, so this is not fatal.
        logger.error(f"Failed to ensure default customer portal settings: {e}")


async def get_public_portal_settings(session: AsyncSession) -> PublicPortalSettingsData:
    """The global settings without the logo bytes (which are not even loaded)."""
    result = await session.execute(
        select(
            CustomerPortalSettings.id,
            CustomerPortalSettings.title,
            CustomerPortalSettings.logo_mime_type,
            CustomerPortalSettings.brand_color,
            CustomerPortalSettings.updated_at,
            func.coalesce(func.length(CustomerPortalSettings.logo_base64), 0).label("logo_length"),
        ).limit(1),
    )
    row = result.first()

    if row is None:
        defaults = CustomerPortalSettings.get_default_values()
        return PublicPortalSettingsData(
            id=0,
            title=defaults["title"],
            logo_url=None,
            logo_mime_type=defaults["logo_mime_type"],
            brand_color=defaults["brand_color"],
            updated_at=None,
        )

    return PublicPortalSettingsData(
        id=row.id,
        title=row.title,
        logo_url=f"{LOGO_PATH}?v={_logo_version(row.updated_at)}" if row.logo_length else None,
        logo_mime_type=row.logo_mime_type,
        brand_color=row.brand_color,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


async def get_portal_logo(session: AsyncSession) -> Optional[PortalLogo]:
    """The decoded global logo, or None when none is configured (or it cannot be decoded)."""
    result = await session.execute(select(CustomerPortalSettings).limit(1))
    settings = result.scalars().first()
    if settings is None:
        return None
    return decode_logo(settings.logo_base64, settings.logo_mime_type, _logo_version(settings.updated_at))
