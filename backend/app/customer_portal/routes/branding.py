"""Per-customer Customer Portal branding endpoints.

Split across two audiences:

* CoPilot operators (admin/analyst) manage overrides per customer under
  ``/customer_portal/branding``.
* The Customer Portal itself calls ``GET /customer_portal/settings/effective``
  once the user is authenticated to learn which branding to render. The public
  ``GET /customer_portal/settings`` (see ``routes/settings.py``) keeps serving the
  global defaults for the login page, where no customer is known yet.
"""
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from fastapi import status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.schema.branding import CustomerBrandingListItem
from app.customer_portal.schema.branding import CustomerBrandingListResponse
from app.customer_portal.schema.branding import CustomerBrandingOverride
from app.customer_portal.schema.branding import CustomerBrandingResponse
from app.customer_portal.schema.branding import EffectiveBrandingResponse
from app.customer_portal.schema.branding import UpdateCustomerBrandingRequest
from app.customer_portal.services.branding import delete_branding_override
from app.customer_portal.services.branding import get_branding_override
from app.customer_portal.services.branding import list_branding_overrides
from app.customer_portal.services.branding import resolve_branding_for_user
from app.customer_portal.services.branding import resolve_effective_branding
from app.customer_portal.services.branding import upsert_branding_override
from app.db.db_session import get_db
from app.db.universal_models import Customers

customer_portal_branding_router = APIRouter()


def _to_override_schema(override) -> CustomerBrandingOverride:
    return CustomerBrandingOverride(
        id=override.id,
        customer_code=override.customer_code,
        enabled=override.enabled,
        title=override.title,
        logo_base64=override.logo_base64,
        logo_mime_type=override.logo_mime_type,
        brand_color=override.brand_color,
        updated_at=override.updated_at.isoformat(),
        updated_by=override.updated_by,
    )


async def _ensure_customer_exists(session: AsyncSession, customer_code: str) -> None:
    result = await session.execute(select(Customers).where(Customers.customer_code == customer_code))
    if result.scalars().first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer {customer_code} not found")


@customer_portal_branding_router.get(
    "/settings/effective",
    response_model=EffectiveBrandingResponse,
    description="Get the portal branding for the authenticated user (per-customer override if set, otherwise the global defaults).",
)
async def get_effective_portal_settings(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EffectiveBrandingResponse:
    """Resolve branding for the logged-in portal user.

    Never fails the portal over branding: on any unexpected error we log and let
    the caller keep whatever it already had (``settings=None``).
    """
    try:
        effective = await resolve_branding_for_user(session, current_user)
        return EffectiveBrandingResponse(
            success=True,
            message="Portal branding resolved successfully",
            settings=effective,
        )
    except Exception as e:
        logger.error(f"Failed to resolve effective portal branding for user {current_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve portal branding: {str(e)}",
        )


# NOTE: the static ``/branding`` list route must stay above ``/branding/{customer_code}``
# or the wildcard swallows it (see CLAUDE.md, FastAPI route ordering).
@customer_portal_branding_router.get(
    "/branding",
    response_model=CustomerBrandingListResponse,
    description="List every customer that has a branding override configured.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_customer_branding(
    session: AsyncSession = Depends(get_db),
) -> CustomerBrandingListResponse:
    try:
        overrides = await list_branding_overrides(session)
        return CustomerBrandingListResponse(
            success=True,
            message="Customer branding overrides retrieved successfully",
            overrides=[
                CustomerBrandingListItem(
                    customer_code=item.customer_code,
                    enabled=item.enabled,
                    title=item.title,
                    has_logo=bool(item.logo_base64),
                    brand_color=item.brand_color,
                    updated_at=item.updated_at.isoformat(),
                )
                for item in overrides
            ],
        )
    except Exception as e:
        logger.error(f"Failed to list customer branding overrides: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list customer branding overrides: {str(e)}",
        )


@customer_portal_branding_router.get(
    "/branding/{customer_code}",
    response_model=CustomerBrandingResponse,
    description="Get a customer's branding override (if any) plus the branding that currently resolves for it.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_branding(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> CustomerBrandingResponse:
    try:
        override = await get_branding_override(session, customer_code)
        effective = await resolve_effective_branding(session, customer_code)

        return CustomerBrandingResponse(
            success=True,
            message="Customer branding retrieved successfully",
            override=_to_override_schema(override) if override else None,
            effective=effective,
        )
    except Exception as e:
        logger.error(f"Failed to get branding for customer {customer_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get customer branding: {str(e)}",
        )


@customer_portal_branding_router.put(
    "/branding/{customer_code}",
    response_model=CustomerBrandingResponse,
    description="Create or update a customer's branding override. Fields left null inherit the global portal settings.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def set_customer_branding(
    customer_code: str,
    request: UpdateCustomerBrandingRequest,
    session: AsyncSession = Depends(get_db),
    auth_handler: AuthHandler = Depends(AuthHandler().get_current_user),
) -> CustomerBrandingResponse:
    await _ensure_customer_exists(session, customer_code)

    try:
        override = await upsert_branding_override(
            session,
            customer_code=customer_code,
            enabled=request.enabled,
            title=request.title,
            logo_base64=request.logo_base64,
            logo_mime_type=request.logo_mime_type,
            brand_color=request.brand_color,
            user_id=getattr(auth_handler, "user_id", None),
        )
        await session.commit()
        await session.refresh(override)

        effective = await resolve_effective_branding(session, customer_code)
        logger.info(f"Customer portal branding override saved for customer {customer_code} (enabled={request.enabled})")

        return CustomerBrandingResponse(
            success=True,
            message="Customer branding override saved successfully",
            override=_to_override_schema(override),
            effective=effective,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save branding for customer {customer_code}: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save customer branding: {str(e)}",
        )


@customer_portal_branding_router.delete(
    "/branding/{customer_code}",
    response_model=CustomerBrandingResponse,
    description="Remove a customer's branding override so it inherits the global portal settings.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def remove_customer_branding(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> CustomerBrandingResponse:
    try:
        deleted = await delete_branding_override(session, customer_code)
        if deleted:
            await session.commit()

        effective = await resolve_effective_branding(session, customer_code)

        return CustomerBrandingResponse(
            success=True,
            message="Customer branding override removed - inheriting global portal settings"
            if deleted
            else "No branding override configured - already inheriting global portal settings",
            override=None,
            effective=effective,
        )
    except Exception as e:
        logger.error(f"Failed to delete branding for customer {customer_code}: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete customer branding: {str(e)}",
        )
