"""Per-customer Customer Portal branding endpoints.

Split across two audiences:

* CoPilot operators (admin/analyst) manage overrides per customer under
  ``/customer_portal/branding``.
* The Customer Portal itself calls ``GET /customer_portal/settings/effective``
  once the user is authenticated to learn which branding to render. The public
  ``GET /customer_portal/settings`` (see ``routes/settings.py``) keeps serving the
  global defaults for the login page, where no customer is known yet.
"""
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import Response
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.routes.settings import logo_response
from app.customer_portal.schema.branding import CustomerBrandingListItem
from app.customer_portal.schema.branding import CustomerBrandingListResponse
from app.customer_portal.schema.branding import CustomerBrandingOverride
from app.customer_portal.schema.branding import CustomerBrandingResponse
from app.customer_portal.schema.branding import EffectiveBrandingResponse
from app.customer_portal.schema.branding import UpdateCustomerBrandingRequest
from app.customer_portal.services import branding_cache
from app.customer_portal.services.branding import delete_branding_override
from app.customer_portal.services.branding import get_branding_override
from app.customer_portal.services.branding import get_effective_logo_for_user
from app.customer_portal.services.branding import list_branding_overrides
from app.customer_portal.services.branding import resolve_branding_for_user
from app.customer_portal.services.branding import resolve_effective_branding
from app.customer_portal.services.branding import to_portal_branding
from app.customer_portal.services.branding import upsert_branding_override
from app.customer_portal.services.customers import ensure_customer_exists
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access

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

    A failure is a generic 500; the portal keeps the branding it already shows.
    """
    async with internal_errors("resolve portal branding"):
        effective = await resolve_branding_for_user(session, current_user)
        return EffectiveBrandingResponse(
            success=True,
            message="Portal branding resolved successfully",
            settings=to_portal_branding(effective),
        )


@customer_portal_branding_router.get(
    "/settings/effective/logo",
    response_class=Response,
    responses={200: {"content": {"image/*": {}}}, 304: {"description": "Not modified"}, 404: {"description": "No logo configured"}},
    description="Get the logo of the authenticated user's portal branding as an image (cacheable per user).",
)
async def get_effective_portal_logo(
    if_none_match: Optional[str] = Header(None),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return logo_response(await get_effective_logo_for_user(session, current_user), if_none_match, cache_scope="private")


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
    async with internal_errors("list customer branding overrides"):
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


@customer_portal_branding_router.get(
    "/branding/{customer_code}",
    response_model=CustomerBrandingResponse,
    description="Get a customer's branding override (if any) plus the branding that currently resolves for it.",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def get_customer_branding(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> CustomerBrandingResponse:
    async with internal_errors("get customer branding"):
        override = await get_branding_override(session, customer_code)
        effective = await resolve_effective_branding(session, customer_code)

        return CustomerBrandingResponse(
            success=True,
            message="Customer branding retrieved successfully",
            override=_to_override_schema(override) if override else None,
            effective=effective,
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
    current_user: User = Depends(AuthHandler().get_current_user),
) -> CustomerBrandingResponse:
    await ensure_customer_exists(session, customer_code)

    async with internal_errors("save customer branding", session):
        override = await upsert_branding_override(
            session,
            customer_code=customer_code,
            enabled=request.enabled,
            title=request.title,
            logo_base64=request.logo_base64,
            logo_mime_type=request.logo_mime_type,
            brand_color=request.brand_color,
            user_id=current_user.id,
        )
        await session.commit()
        branding_cache.invalidate_all()
        await session.refresh(override)

        effective = await resolve_effective_branding(session, customer_code)
        logger.info(f"Customer portal branding override saved for customer {customer_code} (enabled={request.enabled})")

        return CustomerBrandingResponse(
            success=True,
            message="Customer branding override saved successfully",
            override=_to_override_schema(override),
            effective=effective,
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
    async with internal_errors("delete customer branding", session):
        deleted = await delete_branding_override(session, customer_code)
        if deleted:
            await session.commit()
            branding_cache.invalidate_all()

        effective = await resolve_effective_branding(session, customer_code)

        return CustomerBrandingResponse(
            success=True,
            message="Customer branding override removed - inheriting global portal settings"
            if deleted
            else "No branding override configured - already inheriting global portal settings",
            override=None,
            effective=effective,
        )
