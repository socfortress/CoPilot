"""Branding resolution for the Customer Portal.

Two layers exist:

1. ``customer_portal_settings`` — the **global default** (a singleton row). This is
   what every customer sees unless overridden, and what the *login* page shows
   (no customer is known before authentication).
2. ``customer_portal_branding`` — an optional **per-customer override** managed
   from CoPilot (one row per customer, ``enabled`` toggles it without discarding
   the stored values).

Resolution is per *field*, not all-or-nothing: an override that only sets a title
still inherits the global logo and brand color. That makes "clear the field ->
fall back to global" the natural behaviour for every field, and deleting the row
(or disabling it) reverts the customer completely.

Every consumer — the portal API, the report theming in
``app.incidents.services.customer_report_branding`` — must go through
``resolve_effective_branding`` / ``resolve_branding_for_user`` rather than reading
either table directly, so the fallback rules stay in one place.
"""
from datetime import datetime
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.customer_portal.schema.branding import EffectiveBranding
from app.db.universal_models import CustomerPortalBranding
from app.db.universal_models import CustomerPortalSettings
from app.middleware.customer_access import customer_access_handler


async def get_global_settings(session: AsyncSession) -> Optional[CustomerPortalSettings]:
    """Return the global portal settings row, or None when it has never been saved."""
    result = await session.execute(select(CustomerPortalSettings).limit(1))
    return result.scalars().first()


async def get_branding_override(session: AsyncSession, customer_code: str) -> Optional[CustomerPortalBranding]:
    """Return the raw override row for a customer (regardless of ``enabled``), or None."""
    result = await session.execute(select(CustomerPortalBranding).where(CustomerPortalBranding.customer_code == customer_code))
    return result.scalars().first()


async def list_branding_overrides(session: AsyncSession) -> List[CustomerPortalBranding]:
    result = await session.execute(select(CustomerPortalBranding).order_by(CustomerPortalBranding.customer_code))
    return list(result.scalars().all())


def _normalize(value: Optional[str]) -> Optional[str]:
    """Treat empty/whitespace-only strings as "not set" so they fall back to global."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def build_effective_branding(
    global_settings: Optional[CustomerPortalSettings],
    override: Optional[CustomerPortalBranding],
    customer_code: Optional[str] = None,
) -> EffectiveBranding:
    """Merge an override over the global defaults, field by field.

    A disabled (or missing) override contributes nothing. The logo is merged as a
    *pair* — taking a custom ``logo_base64`` without its ``logo_mime_type`` would
    render a broken image — so either both come from the override or both come
    from the global settings.
    """
    global_title = _normalize(global_settings.title if global_settings else None) or "CoPilot"
    global_logo = _normalize(global_settings.logo_base64 if global_settings else None)
    global_mime = _normalize(global_settings.logo_mime_type if global_settings else None)
    global_color = _normalize(global_settings.brand_color if global_settings else None)

    if not override or not override.enabled:
        return EffectiveBranding(
            title=global_title,
            logo_base64=global_logo,
            logo_mime_type=global_mime,
            brand_color=global_color,
            source="global",
            customer_code=None,
        )

    custom_title = _normalize(override.title)
    custom_logo = _normalize(override.logo_base64)
    custom_mime = _normalize(override.logo_mime_type)
    custom_color = _normalize(override.brand_color)

    used_custom = any([custom_title, custom_logo, custom_color])

    return EffectiveBranding(
        title=custom_title or global_title,
        logo_base64=custom_logo or global_logo,
        # Keep the mime type paired with whichever logo won.
        logo_mime_type=(custom_mime or "image/png") if custom_logo else global_mime,
        brand_color=custom_color or global_color,
        source="custom" if used_custom else "global",
        customer_code=customer_code if used_custom else None,
    )


async def resolve_effective_branding(session: AsyncSession, customer_code: Optional[str]) -> EffectiveBranding:
    """Resolve the branding for one customer (or the global defaults when None)."""
    global_settings = await get_global_settings(session)
    override = await get_branding_override(session, customer_code) if customer_code else None
    return build_effective_branding(global_settings, override, customer_code)


async def resolve_branding_for_user(session: AsyncSession, user: User) -> EffectiveBranding:
    """Resolve the branding a logged-in portal user should see.

    A portal user can be scoped to several customers (``user_customer_access``),
    and admins/analysts get the wildcard ``"*"``. A per-customer override is only
    unambiguous when the user is scoped to exactly one customer — with more than
    one (or with wildcard access) we deliberately fall back to the global
    defaults rather than picking a winner, so the branding a user sees never
    depends on ordering or on the portal's customer *filter* (which is a view
    control, not an identity).
    """
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)

    if len(accessible) == 1 and accessible[0] != "*":
        return await resolve_effective_branding(session, accessible[0])

    return await resolve_effective_branding(session, None)


async def upsert_branding_override(
    session: AsyncSession,
    customer_code: str,
    enabled: bool,
    title: Optional[str],
    logo_base64: Optional[str],
    logo_mime_type: Optional[str],
    brand_color: Optional[str],
    user_id: Optional[int] = None,
) -> CustomerPortalBranding:
    """Create or update a customer's override row and return it (caller commits)."""
    override = await get_branding_override(session, customer_code)

    if override is None:
        override = CustomerPortalBranding(customer_code=customer_code)
        session.add(override)

    override.enabled = enabled
    override.title = _normalize(title)
    override.logo_base64 = _normalize(logo_base64)
    override.logo_mime_type = _normalize(logo_mime_type) if _normalize(logo_base64) else None
    override.brand_color = _normalize(brand_color)
    override.updated_by = user_id
    override.updated_at = datetime.utcnow()

    return override


async def delete_branding_override(session: AsyncSession, customer_code: str) -> bool:
    """Drop a customer's override so it inherits the global defaults. Caller commits."""
    override = await get_branding_override(session, customer_code)
    if override is None:
        return False

    await session.delete(override)
    logger.info(f"Deleted customer portal branding override for customer {customer_code}")
    return True
