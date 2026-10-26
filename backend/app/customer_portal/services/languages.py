"""The Customer Portal's languages (#1310).

A customer's languages are set in CoPilot by an admin; English is always one of them and is the
default. A portal user may pick any language enabled for at least one of their customers (the
union), and the pick is stored on their account, so it follows them to any device. The portal
shows English whenever the pick is not, or no longer, available to them; the stored pick is kept,
so re-enabling the language brings it back.
"""

from typing import List
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.customer_portal.utils.locales import DEFAULT_LOCALE
from app.customer_portal.utils.locales import SUPPORTED_LOCALES
from app.customer_portal.utils.locales import effective_locale
from app.customer_portal.utils.locales import ordered
from app.db.universal_models import CustomerPortalLanguageSettings
from app.middleware.customer_access import customer_access_handler
from app.time_utils import now_utc

NOT_AVAILABLE = "This language is not enabled for your customers"


async def get_settings(customer_code: str, session: AsyncSession) -> Optional[CustomerPortalLanguageSettings]:
    result = await session.execute(
        select(CustomerPortalLanguageSettings).where(CustomerPortalLanguageSettings.customer_code == customer_code),
    )
    return result.scalars().first()


def languages_of(settings: Optional[CustomerPortalLanguageSettings]) -> List[str]:
    """A customer's languages as stored, cleaned: no row, English only; never without English."""
    return ordered(settings.languages if settings and settings.languages else [DEFAULT_LOCALE])


async def upsert_settings(
    customer_code: str,
    languages: List[str],
    session: AsyncSession,
    user_id: Optional[int] = None,
) -> CustomerPortalLanguageSettings:
    """Create or replace a customer's languages (already checked). Caller commits."""
    settings = await get_settings(customer_code, session)
    if settings is None:
        settings = CustomerPortalLanguageSettings(customer_code=customer_code)
        session.add(settings)
    settings.languages = ordered(languages)
    settings.updated_at = now_utc()
    settings.updated_by = user_id
    return settings


async def available_for_user(user: User, session: AsyncSession) -> List[str]:
    """The languages ``user`` may pick: English, plus any enabled for at least one of their customers."""
    codes = [code for code in await customer_access_handler.get_user_accessible_customers(user, session) if code != "*"]
    if not codes:
        return [DEFAULT_LOCALE]
    rows = (
        (
            await session.execute(
                select(CustomerPortalLanguageSettings.languages).where(CustomerPortalLanguageSettings.customer_code.in_(codes)),
            )
        )
        .scalars()
        .all()
    )
    return ordered(code for languages in rows for code in (languages or []))


async def portal_locale(user: User, session: AsyncSession) -> tuple[str, List[str]]:
    """The language the portal shows ``user`` and the ones they may pick."""
    available = await available_for_user(user, session)
    return effective_locale(getattr(user, "locale", None), available), available


async def set_my_locale(user: User, locale: str, session: AsyncSession) -> tuple[str, List[str]]:
    """Store ``user``'s pick; only a language enabled for one of their customers (400 otherwise)."""
    if locale not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=400, detail=NOT_AVAILABLE)
    available = await available_for_user(user, session)
    if locale not in available:
        raise HTTPException(status_code=400, detail=NOT_AVAILABLE)
    row = await session.get(User, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    row.locale = locale
    await session.commit()
    return locale, available
