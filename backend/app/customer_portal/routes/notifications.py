from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.notifications import MarkPortalNotificationsReadRequest
from app.customer_portal.schema.notifications import MarkPortalNotificationsReadResponse
from app.customer_portal.schema.notifications import NotificationPreference
from app.customer_portal.schema.notifications import (
    PortalNotificationAvailabilityResponse,
)
from app.customer_portal.schema.notifications import PortalNotificationFeedResponse
from app.customer_portal.schema.notifications import PortalNotificationItem
from app.customer_portal.schema.notifications import (
    PortalNotificationPreferencesResponse,
)
from app.customer_portal.schema.notifications import PortalNotificationSettings
from app.customer_portal.schema.notifications import PortalNotificationSettingsResponse
from app.customer_portal.schema.notifications import PortalNotificationUnreadResponse
from app.customer_portal.schema.notifications import (
    UpdatePortalNotificationPreferencesRequest,
)
from app.customer_portal.schema.notifications import (
    UpdatePortalNotificationSettingsRequest,
)
from app.customer_portal.services import notifications as service
from app.customer_portal.services.customers import ensure_customer_exists
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access

customer_portal_notifications_router = APIRouter()

# Two audiences, like the SLA router:
#
# * CoPilot operators manage the per-customer switch under
#   ``/notifications/settings/{customer_code}`` (admin to write).
# * Portal users read their bell and set their own choices. Everything they touch is
#   their own: the user comes from the token, never the body, and every query is
#   scoped to their id.
#
# Every other path is static and declared before nothing that could swallow it; keep
# ``/notifications/settings/{customer_code}`` the only parameterised one.

PORTAL_USER = Security(AuthHandler().require_any_scope("customer_user"))


def _settings_schema(customer_code: str, settings) -> PortalNotificationSettings:
    if settings is None:
        return PortalNotificationSettings(customer_code=customer_code, enabled=False)
    return PortalNotificationSettings(
        customer_code=settings.customer_code,
        enabled=settings.enabled,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by=settings.updated_by,
    )


def _settings_response(customer_code: str, settings, message: str) -> PortalNotificationSettingsResponse:
    return PortalNotificationSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        email_configured=service.email_configured(),
        digest_hour_utc=service.digest_hour(),
        success=True,
        message=message,
    )


def _preferences(prefs) -> list:
    return [
        NotificationPreference(event=p.event, in_app=p.in_app, email=p.email, min_severity=p.min_severity)
        for p in (prefs[event] for event in service.EVENTS)
    ]


def _item(row) -> PortalNotificationItem:
    return PortalNotificationItem(
        id=row.id,
        customer_code=row.customer_code,
        event=row.event,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        title=row.title,
        body=row.body,
        severity=row.severity,
        created_at=row.created_at.isoformat(),
        read=row.read_at is not None,
    )


# --- Operator-facing switch ---


@customer_portal_notifications_router.get(
    "/notifications/settings/{customer_code}",
    response_model=PortalNotificationSettingsResponse,
    description="Get whether a customer's portal users receive notifications",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def get_customer_notification_settings(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> PortalNotificationSettingsResponse:
    async with internal_errors("read customer notification settings"):
        settings = await service.get_settings(customer_code, session)
    return _settings_response(customer_code, settings, "Customer notification settings retrieved successfully")


@customer_portal_notifications_router.put(
    "/notifications/settings/{customer_code}",
    response_model=PortalNotificationSettingsResponse,
    description="Turn portal user notifications on or off for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def set_customer_notification_settings(
    customer_code: str,
    request: UpdatePortalNotificationSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> PortalNotificationSettingsResponse:
    await ensure_customer_exists(session, customer_code)
    async with internal_errors("save customer notification settings", session):
        settings = await service.upsert_settings(customer_code, request.enabled, session, user_id=getattr(current_user, "id", None))
        await session.commit()
        await session.refresh(settings)
    logger.info(f"Customer portal notifications {'enabled' if request.enabled else 'disabled'} for customer {customer_code}")
    return _settings_response(customer_code, settings, "Customer notification settings saved successfully")


# --- The portal user's own ---


@customer_portal_notifications_router.get(
    "/notifications/availability",
    response_model=PortalNotificationAvailabilityResponse,
    description="Whether the caller's notifications are on, and whether email can reach them",
    dependencies=[PORTAL_USER],
)
async def get_notification_availability(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalNotificationAvailabilityResponse:
    async with internal_errors("resolve notification availability"):
        enabled = bool(await service.enabled_customer_codes(current_user, session))
    problem = service.email_problem(current_user)
    return PortalNotificationAvailabilityResponse(
        enabled=enabled,
        email_available=problem is None,
        email_unavailable_reason=problem,
        digest_hour_utc=service.digest_hour(),
        success=True,
        message="Notifications are on" if enabled else "Notifications are not enabled",
    )


@customer_portal_notifications_router.get(
    "/notifications/preferences",
    response_model=PortalNotificationPreferencesResponse,
    description="The caller's notification choices, defaults included",
    dependencies=[PORTAL_USER],
)
async def get_notification_preferences(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalNotificationPreferencesResponse:
    async with internal_errors("read notification preferences"):
        prefs = (await service.load_preferences([current_user.id], session))[current_user.id]
    return PortalNotificationPreferencesResponse(
        preferences=_preferences(prefs),
        success=True,
        message="Notification preferences retrieved",
    )


@customer_portal_notifications_router.put(
    "/notifications/preferences",
    response_model=PortalNotificationPreferencesResponse,
    description="Save the caller's notification choices; events left out keep theirs",
    dependencies=[PORTAL_USER],
)
async def set_notification_preferences(
    request: UpdatePortalNotificationPreferencesRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalNotificationPreferencesResponse:
    choices = [
        service.Preference(
            event=p.event,
            in_app=p.in_app,
            email=p.email,
            min_severity=(p.min_severity or service.DEFAULT_MIN_SEVERITY) if p.event == service.EVENT_ALERT_CREATED else None,
        )
        for p in request.preferences
    ]
    async with internal_errors("save notification preferences", session):
        prefs = await service.save_preferences(current_user.id, choices, session)
        await session.commit()
    return PortalNotificationPreferencesResponse(preferences=_preferences(prefs), success=True, message="Notification preferences saved")


@customer_portal_notifications_router.get(
    "/notifications/unread-count",
    response_model=PortalNotificationUnreadResponse,
    description="How many of the caller's notifications are unread (the bell's badge)",
    dependencies=[PORTAL_USER],
)
async def get_unread_count(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalNotificationUnreadResponse:
    async with internal_errors("count unread notifications"):
        count = await service.unread_count(current_user, session)
    return PortalNotificationUnreadResponse(unread_count=count, success=True, message="Unread notifications counted")


@customer_portal_notifications_router.post(
    "/notifications/read",
    response_model=MarkPortalNotificationsReadResponse,
    description="Mark some, or all, of the caller's notifications read",
    dependencies=[PORTAL_USER],
)
async def mark_notifications_read(
    request: MarkPortalNotificationsReadRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MarkPortalNotificationsReadResponse:
    async with internal_errors("mark notifications read", session):
        marked = await service.mark_read(current_user, session, None if request.all else request.ids)
        unread = await service.unread_count(current_user, session)
    return MarkPortalNotificationsReadResponse(marked=marked, unread_count=unread, success=True, message=f"Marked {marked} read")


@customer_portal_notifications_router.get(
    "/notifications",
    response_model=PortalNotificationFeedResponse,
    description="A page of the caller's notifications, newest first",
    dependencies=[PORTAL_USER],
)
async def get_notifications(
    limit: int = Query(20, ge=1, le=service.MAX_FEED_PAGE),
    before: Optional[int] = Query(None, ge=1, description="Only notifications older than this id (the next page)"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalNotificationFeedResponse:
    async with internal_errors("list notifications"):
        rows, has_more, unread = await service.list_feed(current_user, session, limit=limit, before_id=before)
    return PortalNotificationFeedResponse(
        notifications=[_item(row) for row in rows],
        has_more=has_more,
        unread_count=unread,
        success=True,
        message="Notifications retrieved",
    )
