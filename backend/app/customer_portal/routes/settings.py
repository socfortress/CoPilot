from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Response
from fastapi import Security
from fastapi import status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.schema.settings import PortalSettingsData
from app.customer_portal.schema.settings import PortalSettingsResponse
from app.customer_portal.schema.settings import PublicPortalSettingsResponse
from app.customer_portal.schema.settings import UpdatePortalSettingsRequest
from app.customer_portal.schema.settings import UpdatePortalSettingsResponse
from app.customer_portal.services.branding import get_global_settings
from app.customer_portal.services.settings import PortalLogo
from app.customer_portal.services.settings import get_portal_logo
from app.customer_portal.services.settings import get_public_portal_settings
from app.db.db_session import get_db
from app.db.universal_models import CustomerPortalSettings

customer_portal_settings_router = APIRouter()

LOGO_MAX_AGE_SECONDS = 3600


@customer_portal_settings_router.post(
    "/settings",
    response_model=UpdatePortalSettingsResponse,
    description="Update customer portal settings (logo and title). Set fields to null to restore defaults.",
    dependencies=[Depends(AuthHandler().require_any_scope("admin"))],
)
async def update_portal_settings(
    request: UpdatePortalSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> UpdatePortalSettingsResponse:
    """
    Update customer portal settings including logo and title.
    Set any field to null to restore its default value.
    Requires authentication.
    """
    try:
        # Check if settings exist
        result = await session.execute(select(CustomerPortalSettings))
        settings = result.scalars().first()

        if not settings:
            # Create default settings if none exist
            settings = CustomerPortalSettings.create_default()
            session.add(settings)

        # Get default values
        defaults = CustomerPortalSettings.get_default_values()

        # Handle title: if explicitly set to null, restore default
        if request.title is None:
            settings.title = defaults["title"]
        else:
            settings.title = request.title

        # Handle logo_base64: if explicitly set to null, restore default
        if request.logo_base64 is None:
            settings.logo_base64 = defaults["logo_base64"]
        else:
            settings.logo_base64 = request.logo_base64

        # Handle logo_mime_type: if explicitly set to null, restore default
        if request.logo_mime_type is None:
            settings.logo_mime_type = defaults["logo_mime_type"]
        else:
            settings.logo_mime_type = request.logo_mime_type

        # Handle brand_color: if explicitly set to null, restore default
        if request.brand_color is None:
            settings.brand_color = defaults["brand_color"]
        else:
            settings.brand_color = request.brand_color

        # Update metadata. UTC, like the column default and every other portal
        # timestamp — datetime.now() would stamp the server's local time and make
        # this row inconsistent with the rest of the schema.
        settings.updated_by = current_user.id
        settings.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(settings)

        logger.info(f"Portal settings updated successfully by user {current_user.username} (id={current_user.id})")

        return UpdatePortalSettingsResponse(
            success=True,
            message="Portal settings updated successfully",
        )

    except Exception as e:
        logger.error(f"Failed to update portal settings: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update portal settings: {str(e)}",
        )


@customer_portal_settings_router.get(
    "/settings",
    response_model=PublicPortalSettingsResponse,
    description="Get the global customer portal settings (public endpoint). The logo is not inlined: fetch it from `logo_url`.",
)
async def get_portal_settings(
    session: AsyncSession = Depends(get_db),
) -> PublicPortalSettingsResponse:
    """
    Global title, brand color and logo URL for the login page.
    Public (no authentication) and read-only: a missing row reads as the defaults.
    """
    try:
        settings = await get_public_portal_settings(session)
        return PublicPortalSettingsResponse(
            success=True,
            message="Portal settings retrieved successfully",
            settings=settings,
        )
    except Exception as e:
        logger.error(f"Failed to get portal settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get portal settings",
        )


def logo_response(logo: Optional[PortalLogo], if_none_match: Optional[str], *, cache_scope: str) -> Response:
    """Serve a portal logo as bytes with ETag revalidation; 404 when there is none.

    ``cache_scope`` is ``public`` for the anonymous global logo and ``private`` for a
    logo resolved per user, which shared caches must not hand to anyone else.
    """
    if logo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No portal logo configured")

    headers = {
        "ETag": logo.etag,
        # The portal requests a versioned URL (?v=…), so a stale copy is only ever
        # served for the unversioned path, and then for an hour at most.
        "Cache-Control": f"{cache_scope}, max-age={LOGO_MAX_AGE_SECONDS}",
        "X-Content-Type-Options": "nosniff",
        # The logo may be an admin-uploaded SVG: opened directly, it must not run script.
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
    }

    if if_none_match and logo.etag in [tag.strip() for tag in if_none_match.split(",")]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    return Response(content=logo.content, media_type=logo.mime_type, headers=headers)


@customer_portal_settings_router.get(
    "/settings/logo",
    response_class=Response,
    responses={200: {"content": {"image/*": {}}}, 304: {"description": "Not modified"}, 404: {"description": "No logo configured"}},
    description="Get the global customer portal logo as an image (public endpoint, cacheable).",
)
async def get_portal_logo_image(
    if_none_match: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return logo_response(await get_portal_logo(session), if_none_match, cache_scope="public")


@customer_portal_settings_router.get(
    "/settings/global",
    response_model=PortalSettingsResponse,
    description="Get the global customer portal settings including the inline logo, for the CoPilot settings editor.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_global_portal_settings(
    session: AsyncSession = Depends(get_db),
) -> PortalSettingsResponse:
    try:
        settings = await get_global_settings(session)
        if settings is None:
            settings = CustomerPortalSettings.create_default()
            settings.id = 0

        return PortalSettingsResponse(
            success=True,
            message="Portal settings retrieved successfully",
            settings=PortalSettingsData(
                id=settings.id,
                title=settings.title,
                logo_base64=settings.logo_base64,
                logo_mime_type=settings.logo_mime_type,
                brand_color=settings.brand_color,
                updated_at=settings.updated_at.isoformat(),
            ),
        )
    except Exception as e:
        logger.error(f"Failed to get portal settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get portal settings",
        )
