from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Response
from fastapi import Security
from fastapi import status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.settings import PatchPortalSettingsRequest
from app.customer_portal.schema.settings import PortalSettingsData
from app.customer_portal.schema.settings import PortalSettingsResponse
from app.customer_portal.schema.settings import PublicPortalSettingsResponse
from app.customer_portal.schema.settings import UpdatePortalSettingsRequest
from app.customer_portal.schema.settings import UpdatePortalSettingsResponse
from app.customer_portal.services import branding_cache
from app.customer_portal.services.settings import PortalLogo
from app.customer_portal.services.settings import get_global_settings_or_default
from app.customer_portal.services.settings import get_portal_logo
from app.customer_portal.services.settings import get_public_portal_settings
from app.customer_portal.services.settings import patch_global_settings
from app.customer_portal.services.settings import replace_global_settings
from app.db.db_session import get_db

customer_portal_settings_router = APIRouter()

LOGO_MAX_AGE_SECONDS = 3600


@customer_portal_settings_router.post(
    "/settings",
    response_model=UpdatePortalSettingsResponse,
    description=(
        "Replace the customer portal settings: every field is written, and a null or missing one restores its default. "
        "Prefer PATCH, which changes only the fields sent."
    ),
    dependencies=[Depends(AuthHandler().require_any_scope("admin"))],
)
async def update_portal_settings(
    request: UpdatePortalSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> UpdatePortalSettingsResponse:
    """Replace the global settings: every field is written, and a null one restores its default."""
    async with internal_errors("update portal settings", session):
        await replace_global_settings(session, request, current_user.id)
        await session.commit()
        branding_cache.invalidate_all()

        logger.info(f"Portal settings updated successfully by user {current_user.username} (id={current_user.id})")

        return UpdatePortalSettingsResponse(
            success=True,
            message="Portal settings updated successfully",
        )


@customer_portal_settings_router.patch(
    "/settings",
    response_model=UpdatePortalSettingsResponse,
    description="Change only the customer portal settings sent; restore defaults explicitly with `reset`.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def patch_portal_settings(
    request: PatchPortalSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> UpdatePortalSettingsResponse:
    async with internal_errors("update portal settings", session):
        await patch_global_settings(session, request, current_user.id)
        await session.commit()
        branding_cache.invalidate_all()

    logger.info(f"Portal settings patched by user {current_user.username} (id={current_user.id})")
    return UpdatePortalSettingsResponse(success=True, message="Portal settings updated successfully")


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
    async with internal_errors("get portal settings"):
        settings = await get_public_portal_settings(session)
        return PublicPortalSettingsResponse(
            success=True,
            message="Portal settings retrieved successfully",
            settings=settings,
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
    async with internal_errors("get portal settings"):
        settings = await get_global_settings_or_default(session)

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
