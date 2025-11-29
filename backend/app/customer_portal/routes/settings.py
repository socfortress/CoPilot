from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from datetime import datetime

from app.customer_portal.schema.settings import (
    UpdatePortalSettingsRequest,
    UpdatePortalSettingsResponse,
    PortalSettingsResponse,
    PortalSettingsData,
)
from app.db.universal_models import CustomerPortalSettings
from app.db.db_session import get_db
from app.auth.utils import AuthHandler

customer_portal_settings_router = APIRouter()


@customer_portal_settings_router.post(
    "/settings",
    response_model=UpdatePortalSettingsResponse,
    description="Update customer portal settings (logo and title). Set fields to null to restore defaults.",
    dependencies=[Depends(AuthHandler().require_any_scope("admin"))],
)
async def update_portal_settings(
    request: UpdatePortalSettingsRequest,
    session: AsyncSession = Depends(get_db),
    auth_handler: AuthHandler = Depends(AuthHandler().get_current_user),
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
            settings.title = defaults['title']
        else:
            settings.title = request.title

        # Handle logo_base64: if explicitly set to null, restore default
        if request.logo_base64 is None:
            settings.logo_base64 = defaults['logo_base64']
        else:
            settings.logo_base64 = request.logo_base64

        # Handle logo_mime_type: if explicitly set to null, restore default
        if request.logo_mime_type is None:
            settings.logo_mime_type = defaults['logo_mime_type']
        else:
            settings.logo_mime_type = request.logo_mime_type

        # Update metadata
        settings.updated_by = auth_handler.user_id if hasattr(auth_handler, 'user_id') else None
        settings.updated_at = datetime.now()

        await session.commit()
        await session.refresh(settings)

        logger.info(f"Portal settings updated successfully by user {auth_handler.user_id if hasattr(auth_handler, 'user_id') else 'unknown'}")

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
    response_model=PortalSettingsResponse,
    description="Get customer portal settings (public endpoint)",
)
async def get_portal_settings(
    session: AsyncSession = Depends(get_db),
) -> PortalSettingsResponse:
    """
    Get customer portal settings including logo and title.
    This is a public endpoint (no authentication required).
    """
    try:
        # Get settings
        result = await session.execute(select(CustomerPortalSettings))
        settings = result.scalars().first()

        if not settings:
            # Create and return default settings
            settings = CustomerPortalSettings.create_default()
            session.add(settings)
            await session.commit()
            await session.refresh(settings)

        settings_data = PortalSettingsData(
            id=settings.id,
            title=settings.title,
            logo_base64=settings.logo_base64,
            logo_mime_type=settings.logo_mime_type,
            updated_at=settings.updated_at.isoformat(),
        )

        return PortalSettingsResponse(
            success=True,
            message="Portal settings retrieved successfully",
            settings=settings_data,
        )

    except Exception as e:
        logger.error(f"Failed to get portal settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get portal settings: {str(e)}",
        )
