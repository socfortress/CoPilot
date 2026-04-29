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

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.notifications.schema.notifications import (
    DispatchLogListResponse,
    DispatchRequest,
    DispatchResponse,
    NotificationRouteCreate,
    NotificationRouteListResponse,
    NotificationRouteRead,
    NotificationRouteResponse,
    NotificationRouteUpdate,
    ShuffleAppListResponse,
    ShuffleIntegrationCreate,
    ShuffleIntegrationListResponse,
    ShuffleIntegrationRead,
    ShuffleIntegrationResponse,
    ShuffleIntegrationUpdate,
    ShuffleVerifyResponse,
)
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
    logger.info(
        f"User {current_user.id} creating notification route "
        f"for customer {customer_code}"
    )
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
    logger.info(
        f"User {current_user.id} adding Shuffle integration "
        f"({payload.display_name}) for customer {customer_code}"
    )
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
    integration = await svc.update_shuffle_integration(
        integration_id, customer_code, payload, session
    )
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
        f"severity {payload.severity_assessment.value}"
    )
    return await svc.dispatch(payload, session)
