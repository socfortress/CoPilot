from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.languages import PortalLanguageSettings
from app.customer_portal.schema.languages import PortalLanguageSettingsResponse
from app.customer_portal.schema.languages import PortalLanguagesResponse
from app.customer_portal.schema.languages import UpdateMyLocaleRequest
from app.customer_portal.schema.languages import UpdatePortalLanguageSettingsRequest
from app.customer_portal.services import languages as service
from app.customer_portal.services.customers import ensure_customer_exists
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access

customer_portal_languages_router = APIRouter()

# Two audiences (#1310):
#
# * CoPilot operators set a customer's languages under ``/languages/settings/{code}`` (admin to write).
# * Portal users read their language and the ones they may pick, and store their own pick.
#
# Static paths before the one with a parameter (``/languages/me`` and ``/languages`` never collide
# with ``/languages/settings/{code}``, but keep new ones in that order).

PORTAL_USER = Security(AuthHandler().require_any_scope("customer_user"))


def _settings_schema(customer_code: str, settings) -> PortalLanguageSettings:
    return PortalLanguageSettings(
        customer_code=customer_code,
        languages=service.languages_of(settings),
        updated_at=settings.updated_at.isoformat() if settings and settings.updated_at else None,
        updated_by=settings.updated_by if settings else None,
    )


@customer_portal_languages_router.get(
    "/languages",
    response_model=PortalLanguagesResponse,
    description="The portal user's language and the languages they may pick",
    dependencies=[PORTAL_USER],
)
async def get_my_languages(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalLanguagesResponse:
    async with internal_errors("read the portal languages"):
        locale, available = await service.portal_locale(current_user, session)
    return PortalLanguagesResponse(locale=locale, available=available, success=True, message="Languages retrieved successfully")


@customer_portal_languages_router.put(
    "/languages/me",
    response_model=PortalLanguagesResponse,
    description="Store the portal user's language: one enabled for at least one of their customers",
    dependencies=[PORTAL_USER],
)
async def set_my_language(
    request: UpdateMyLocaleRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalLanguagesResponse:
    async with internal_errors("save the portal language", session):
        locale, available = await service.set_my_locale(current_user, request.locale, session)
    return PortalLanguagesResponse(locale=locale, available=available, success=True, message="Language saved")


@customer_portal_languages_router.get(
    "/languages/settings/{customer_code}",
    response_model=PortalLanguageSettingsResponse,
    description="The languages a customer's portal users may pick",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def get_customer_languages(customer_code: str, session: AsyncSession = Depends(get_db)) -> PortalLanguageSettingsResponse:
    async with internal_errors("read the customer's portal languages"):
        settings = await service.get_settings(customer_code, session)
    return PortalLanguageSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer portal languages retrieved successfully",
    )


@customer_portal_languages_router.put(
    "/languages/settings/{customer_code}",
    response_model=PortalLanguageSettingsResponse,
    description="Set the languages a customer's portal users may pick (English always included)",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def set_customer_languages(
    customer_code: str,
    request: UpdatePortalLanguageSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> PortalLanguageSettingsResponse:
    await ensure_customer_exists(session, customer_code)
    async with internal_errors("save the customer's portal languages", session):
        before = service.languages_of(await service.get_settings(customer_code, session))
        settings = await service.upsert_settings(customer_code, request.languages, session, user_id=getattr(current_user, "id", None))
        await session.commit()
        await session.refresh(settings)

    after = service.languages_of(settings)
    logger.info(f"Customer portal languages for {customer_code}: {', '.join(after)}")
    if before != after:
        await record_audit_event(
            action=AuditAction.PORTAL_LANGUAGES_SETTINGS_UPDATE,
            actor_user_id=getattr(current_user, "id", None),
            actor_username=getattr(current_user, "username", None),
            customer_code=customer_code,
            entity_type="customer_portal_language_settings",
            entity_id=customer_code,
            old_value={"languages": before},
            new_value={"languages": after},
        )
    return PortalLanguageSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer portal languages saved successfully",
    )
