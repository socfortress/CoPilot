"""
REST routes for the notification routing module.

Two surfaces:

  /customers/{customer_code}/notification_routes
  /customers/{customer_code}/notification_dispatch_log
        admin/analyst CRUD + read-only audit view, used by the CoPilot
        frontend's per-customer Notifications tab.

  /notifications/dispatch
        called by Talon (NanoClaw) after every successful investigation.
        Walks the customer's routes, fires each match, logs each
        outcome, returns a per-route result list. Best-effort — Talon
        does not retry, and a failure here MUST NOT fail the upstream
        investigation.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.notifications.channels import CHANNEL_REGISTRY
from app.notifications.schema.notifications import ChannelDescriptor
from app.notifications.schema.notifications import ChannelListResponse
from app.notifications.schema.notifications import DispatchLogListResponse
from app.notifications.schema.notifications import DispatchRequest
from app.notifications.schema.notifications import DispatchResponse
from app.notifications.schema.notifications import NotificationRouteCreate
from app.notifications.schema.notifications import NotificationRouteListResponse
from app.notifications.schema.notifications import NotificationRouteRead
from app.notifications.schema.notifications import NotificationRouteResponse
from app.notifications.schema.notifications import NotificationRouteUpdate
from app.notifications.schema.notifications import ResendQuotaResponse
from app.notifications.schema.notifications import ShuffleAppListResponse
from app.notifications.schema.notifications import ShuffleIntegrationCreate
from app.notifications.schema.notifications import ShuffleIntegrationListResponse
from app.notifications.schema.notifications import ShuffleIntegrationRead
from app.notifications.schema.notifications import ShuffleIntegrationResponse
from app.notifications.schema.notifications import ShuffleIntegrationUpdate
from app.notifications.schema.notifications import ShuffleOrgListResponse
from app.notifications.schema.notifications import ShuffleVerifyResponse
from app.notifications.services import notifications as svc

notifications_router = APIRouter()


# ---------------------------------------------------------------------------
# Per-customer route CRUD
# ---------------------------------------------------------------------------


@notifications_router.get(
    "/customers/{customer_code}/notification_routes",
    response_model=NotificationRouteListResponse,
    description="List notification routes for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_routes_route(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> NotificationRouteListResponse:
    routes = await svc.list_routes(customer_code, session)
    return NotificationRouteListResponse(
        success=True,
        message=f"{len(routes)} route(s) retrieved",
        routes=[NotificationRouteRead.from_orm(r) for r in routes],
    )


@notifications_router.post(
    "/customers/{customer_code}/notification_routes",
    response_model=NotificationRouteResponse,
    description="Create a new notification route for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_route_route(
    customer_code: str,
    payload: NotificationRouteCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> NotificationRouteResponse:
    logger.info(f"User {current_user.id} creating notification route " f"for customer {customer_code}")
    route = await svc.create_route(
        customer_code=customer_code,
        payload=payload,
        created_by=getattr(current_user, "username", None) or str(current_user.id),
        session=session,
    )
    return NotificationRouteResponse(
        success=True,
        message="Route created",
        route=NotificationRouteRead.from_orm(route),
    )


@notifications_router.patch(
    "/customers/{customer_code}/notification_routes/{route_id}",
    response_model=NotificationRouteResponse,
    description="Update an existing notification route. Only fields included in the body are modified.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_route_route(
    customer_code: str,
    route_id: int,
    payload: NotificationRouteUpdate,
    session: AsyncSession = Depends(get_db),
) -> NotificationRouteResponse:
    route = await svc.update_route(route_id, customer_code, payload, session)
    return NotificationRouteResponse(
        success=True,
        message="Route updated",
        route=NotificationRouteRead.from_orm(route),
    )


@notifications_router.delete(
    "/customers/{customer_code}/notification_routes/{route_id}",
    description="Delete a notification route. Dispatch log entries for the route are retained.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_route_route(
    customer_code: str,
    route_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict:
    await svc.delete_route(route_id, customer_code, session)
    return {"success": True, "message": "Route deleted"}


# ---------------------------------------------------------------------------
# Internal-scope routes (deployment-wide, no tenant)
# ---------------------------------------------------------------------------
#
# Separate from the /customers/{code}/... CRUD because these routes belong to no
# customer: there is no code to put in the path. They are where assignment
# notifications land, so analyst chatter never reaches a customer's channel.
#
# Admin-only. A customer-scoped route configures what one tenant receives; an
# internal route configures where the SOC's own traffic goes, which is
# deployment-wide configuration.


@notifications_router.get(
    "/internal_notification_routes",
    response_model=NotificationRouteListResponse,
    description="Internal-scope notification routes. These belong to no customer and receive assignment events.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def list_internal_routes_route(session: AsyncSession = Depends(get_db)) -> NotificationRouteListResponse:
    routes = await svc.list_internal_routes(session)
    return NotificationRouteListResponse(
        success=True,
        message=f"{len(routes)} internal route(s) retrieved",
        routes=routes,
    )


@notifications_router.post(
    "/internal_notification_routes",
    response_model=NotificationRouteResponse,
    description="Create an internal-scope notification route. Shuffle is unavailable — its integrations are per-customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def create_internal_route_route(
    payload: NotificationRouteCreate,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationRouteResponse:
    route = await svc.create_internal_route(payload, current_user.username, session)
    return NotificationRouteResponse(success=True, message="Internal route created", route=route)


@notifications_router.patch(
    "/internal_notification_routes/{route_id}",
    response_model=NotificationRouteResponse,
    description="Update an internal-scope notification route.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def update_internal_route_route(
    route_id: int,
    payload: NotificationRouteUpdate,
    session: AsyncSession = Depends(get_db),
) -> NotificationRouteResponse:
    route = await svc.update_internal_route(route_id, payload, session)
    return NotificationRouteResponse(success=True, message="Internal route updated", route=route)


@notifications_router.delete(
    "/internal_notification_routes/{route_id}",
    description="Delete an internal-scope notification route. Dispatch log entries are retained.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def delete_internal_route_route(route_id: int, session: AsyncSession = Depends(get_db)):
    await svc.delete_internal_route(route_id, session)
    return {"success": True, "message": "Internal route deleted"}


# ---------------------------------------------------------------------------
# Channel catalog
# ---------------------------------------------------------------------------


@notifications_router.get(
    "/notification_channels",
    response_model=ChannelListResponse,
    description=(
        "Delivery channels this deployment supports, with each one's config JSON Schema. "
        "The route form renders generic inputs from the schema for channels without a "
        "bespoke block, so adding a channel needs no frontend change."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_channels_route() -> ChannelListResponse:
    channels = [
        ChannelDescriptor(
            key=provider.key,
            display_name=provider.display_name,
            config_schema=provider.config_schema.model_json_schema(),
            supports_recipient_modes=sorted(provider.supports_recipient_modes),
            secret_fields=sorted(provider.secret_fields),
        )
        for provider in CHANNEL_REGISTRY.values()
    ]
    return ChannelListResponse(success=True, message=f"{len(channels)} channel(s) retrieved", channels=channels)


@notifications_router.get(
    "/notification_channels/resend/quota",
    response_model=ResendQuotaResponse,
    description=(
        "Resend emails sent this calendar month against the plan limit. Deployment-wide — "
        "the API key is shared, so every customer's routes draw from one allowance. "
        "Pass customer_code for a display-only breakdown."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def resend_quota_route(
    customer_code: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
) -> ResendQuotaResponse:
    from app.notifications.channels.resend import FREE_TIER_MONTHLY_LIMIT
    from app.notifications.channels.resend import get_resend_connector
    from app.notifications.services.resend_quota import sends_this_month

    total = await sends_this_month(session)
    scoped = await sends_this_month(session, customer_code) if customer_code else None

    # "Is Resend usable at all" drives whether the UI offers the channel; an
    # unconfigured connector is a normal state, not an error.
    try:
        await get_resend_connector(session)
        configured = True
    except HTTPException:
        configured = False

    return ResendQuotaResponse(
        success=True,
        message=f"{total} email(s) sent this month",
        sent_this_month=total,
        limit=FREE_TIER_MONTHLY_LIMIT,
        customer_sent=scoped,
        configured=configured,
    )


# ---------------------------------------------------------------------------
# Dispatch log (read-only audit)
# ---------------------------------------------------------------------------


@notifications_router.get(
    "/customers/{customer_code}/notification_dispatch_log",
    response_model=DispatchLogListResponse,
    description="Recent notification dispatch attempts for a customer (newest first, capped at 100).",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_dispatch_log_route(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> DispatchLogListResponse:
    entries = await svc.list_dispatch_log(customer_code, session, limit=100)
    return DispatchLogListResponse(
        success=True,
        message=f"{len(entries)} entry/entries retrieved",
        entries=entries,
    )


# ---------------------------------------------------------------------------
# Deployment-scoped Shuffle helpers (Phase 3)
# ---------------------------------------------------------------------------


@notifications_router.get(
    "/notifications/shuffle/orgs",
    response_model=ShuffleOrgListResponse,
    description=(
        "List every Shuffle org the deployment's admin Bearer key can see. "
        "Used by the integration form's org picker so admins choose from a "
        "dropdown instead of pasting Org-Ids. Not customer-scoped — each "
        "org is later attached to a specific customer via a "
        "customer_shuffle_integration row."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_shuffle_orgs_route(
    session: AsyncSession = Depends(get_db),
) -> ShuffleOrgListResponse:
    orgs = await svc.list_orgs(session)
    return ShuffleOrgListResponse(
        success=True,
        message=f"{len(orgs)} org(s) retrieved",
        orgs=orgs,
    )


# ---------------------------------------------------------------------------
# Per-customer Shuffle integrations (Phase 2)
# ---------------------------------------------------------------------------


@notifications_router.get(
    "/customers/{customer_code}/shuffle_integrations",
    response_model=ShuffleIntegrationListResponse,
    description="List Shuffle integrations (per-customer Org-Id rows) for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_shuffle_integrations_route(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> ShuffleIntegrationListResponse:
    integrations = await svc.list_shuffle_integrations(customer_code, session)
    return ShuffleIntegrationListResponse(
        success=True,
        message=f"{len(integrations)} integration(s) retrieved",
        integrations=[ShuffleIntegrationRead.from_orm(i) for i in integrations],
    )


@notifications_router.post(
    "/customers/{customer_code}/shuffle_integrations",
    response_model=ShuffleIntegrationResponse,
    description="Create a new Shuffle integration for a customer (records the customer's Shuffle Org-Id).",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_shuffle_integration_route(
    customer_code: str,
    payload: ShuffleIntegrationCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> ShuffleIntegrationResponse:
    logger.info(f"User {current_user.id} adding Shuffle integration " f"({payload.display_name}) for customer {customer_code}")
    integration = await svc.create_shuffle_integration(
        customer_code=customer_code,
        payload=payload,
        created_by=getattr(current_user, "username", None) or str(current_user.id),
        session=session,
    )
    return ShuffleIntegrationResponse(
        success=True,
        message="Integration created",
        integration=ShuffleIntegrationRead.from_orm(integration),
    )


@notifications_router.patch(
    "/customers/{customer_code}/shuffle_integrations/{integration_id}",
    response_model=ShuffleIntegrationResponse,
    description="Update an existing Shuffle integration. Only fields included in the body are modified.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_shuffle_integration_route(
    customer_code: str,
    integration_id: int,
    payload: ShuffleIntegrationUpdate,
    session: AsyncSession = Depends(get_db),
) -> ShuffleIntegrationResponse:
    integration = await svc.update_shuffle_integration(integration_id, customer_code, payload, session)
    return ShuffleIntegrationResponse(
        success=True,
        message="Integration updated",
        integration=ShuffleIntegrationRead.from_orm(integration),
    )


@notifications_router.delete(
    "/customers/{customer_code}/shuffle_integrations/{integration_id}",
    description="Delete a Shuffle integration. Refused if any notification routes reference it.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_shuffle_integration_route(
    customer_code: str,
    integration_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict:
    await svc.delete_shuffle_integration(integration_id, customer_code, session)
    return {"success": True, "message": "Integration deleted"}


@notifications_router.get(
    "/customers/{customer_code}/shuffle_integrations/{integration_id}/apps",
    response_model=ShuffleAppListResponse,
    description=(
        "Fetch the Shuffle app catalog scoped to this customer's org. Used "
        "by the route form's app picker so admins can pick from a list "
        "instead of hand-typing UUIDs."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_shuffle_apps_route(
    customer_code: str,
    integration_id: int,
    session: AsyncSession = Depends(get_db),
) -> ShuffleAppListResponse:
    apps = await svc.list_apps_for_integration(integration_id, customer_code, session)
    return ShuffleAppListResponse(
        success=True,
        message=f"{len(apps)} app(s) retrieved",
        apps=apps,
    )


@notifications_router.get(
    "/customers/{customer_code}/shuffle_integrations/{integration_id}/verify",
    response_model=ShuffleVerifyResponse,
    description="Probe Shuffle with the integration's Org-Id to confirm the connector is reachable and the org is valid.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def verify_shuffle_integration_route(
    customer_code: str,
    integration_id: int,
    session: AsyncSession = Depends(get_db),
) -> ShuffleVerifyResponse:
    result = await svc.verify_integration(integration_id, customer_code, session)
    return ShuffleVerifyResponse(**result)


# ---------------------------------------------------------------------------
# Dispatch — called by Talon after each investigation
# ---------------------------------------------------------------------------


@notifications_router.post(
    "/notifications/dispatch",
    response_model=DispatchResponse,
    description=(
        "Walk the customer's notification routes for the given trigger and "
        "severity, dispatch each match, and log each outcome. Idempotent — "
        "re-dispatching the same (customer, alert, route, trigger) is a no-op. "
        "Talon calls this after writing back an investigation report."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def dispatch_route(
    payload: DispatchRequest,
    session: AsyncSession = Depends(get_db),
) -> DispatchResponse:
    logger.info(
        f"Notification dispatch requested for customer {payload.customer_code} "
        f"alert {payload.alert_id} trigger {payload.trigger.value} "
        f"severity {payload.severity_assessment.value}",
    )
    return await svc.dispatch(payload, session)
