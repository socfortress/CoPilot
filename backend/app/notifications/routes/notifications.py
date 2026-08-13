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
from app.middleware.customer_access import customer_access_handler
from app.middleware.customer_access import verify_customer_code_access
from app.middleware.customer_access import verify_optional_customer_code_access
from app.notifications.channels import CHANNEL_REGISTRY
from app.notifications.schema.notifications import ChannelDescriptor
from app.notifications.schema.notifications import ChannelListResponse
from app.notifications.schema.notifications import DispatchLogListResponse
from app.notifications.schema.notifications import DispatchOutcome
from app.notifications.schema.notifications import DispatchRequest
from app.notifications.schema.notifications import DispatchResponse
from app.notifications.schema.notifications import ManualSendRequest
from app.notifications.schema.notifications import NotificationRouteCreate
from app.notifications.schema.notifications import NotificationRouteListResponse
from app.notifications.schema.notifications import NotificationRouteRead
from app.notifications.schema.notifications import NotificationRouteResponse
from app.notifications.schema.notifications import NotificationRouteUpdate
from app.notifications.schema.notifications import NotificationTemplateCreate
from app.notifications.schema.notifications import NotificationTemplateListResponse
from app.notifications.schema.notifications import NotificationTemplateRead
from app.notifications.schema.notifications import NotificationTemplateResponse
from app.notifications.schema.notifications import NotificationTemplateUpdate
from app.notifications.schema.notifications import ResendQuotaResponse
from app.notifications.schema.notifications import ShuffleAppListResponse
from app.notifications.schema.notifications import ShuffleIntegrationCreate
from app.notifications.schema.notifications import ShuffleIntegrationListResponse
from app.notifications.schema.notifications import ShuffleIntegrationRead
from app.notifications.schema.notifications import ShuffleIntegrationResponse
from app.notifications.schema.notifications import ShuffleIntegrationUpdate
from app.notifications.schema.notifications import ShuffleOrgListResponse
from app.notifications.schema.notifications import ShuffleVerifyResponse
from app.notifications.schema.notifications import TemplatePreviewRequest
from app.notifications.schema.notifications import TemplatePreviewResponse
from app.notifications.services import notifications as svc
from app.notifications.services import templates as templates_svc

notifications_router = APIRouter()


# ---------------------------------------------------------------------------
# Per-customer route CRUD
# ---------------------------------------------------------------------------


@notifications_router.get(
    "/customers/{customer_code}/notification_routes",
    response_model=NotificationRouteListResponse,
    description="List notification routes for a customer.",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def delete_route_route(
    customer_code: str,
    route_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict:
    await svc.delete_route(route_id, customer_code, session)
    return {"success": True, "message": "Route deleted"}


@notifications_router.post(
    "/customers/{customer_code}/notification_routes/{route_id}/test",
    response_model=DispatchOutcome,
    description=(
        "Send a real test notification through this route. Consumes provider quota and is "
        "recorded in the dispatch log, exactly like a live notification."
    ),
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def test_route(
    customer_code: str,
    route_id: int,
    session: AsyncSession = Depends(get_db),
) -> DispatchOutcome:
    route = await svc.get_route(route_id, customer_code, session)
    return await svc.send_test_notification(route, session)


@notifications_router.post(
    "/internal_notification_routes/{route_id}/test",
    response_model=DispatchOutcome,
    description="Send a real test notification through this internal route.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def test_internal_route(route_id: int, session: AsyncSession = Depends(get_db)) -> DispatchOutcome:
    route = await svc.get_internal_route(route_id, session)
    return await svc.send_test_notification(route, session)


# ---------------------------------------------------------------------------
# Manual send
# ---------------------------------------------------------------------------
#
# A data egress control point rather than a convenience endpoint: it pushes a
# specific customer's data outward on demand, bypassing the trigger and severity
# filters that govern automatic notifications.
#
# The scope dependency below is intentionally the permissive one. Real
# enforcement lives in the service — customer-facing targets need admin,
# portal users are refused outright, the route is re-validated against the
# item's tenant, and the caller must be able to see the item at all. Putting it
# there rather than in a route dependency keeps every check in one auditable
# place and applies to any future caller.


@notifications_router.post(
    "/notifications/send",
    response_model=DispatchOutcome,
    description=(
        "Send a specific alert or case to a configured notification route. Sends a real "
        "notification: it consumes provider quota and is recorded in the dispatch log. "
        "Customer-facing routes require admin."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def manual_send_route(
    payload: ManualSendRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DispatchOutcome:
    from app.notifications.services.manual_send import send_manual

    return await send_manual(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        route_id=payload.route_id,
        user=current_user,
        session=session,
        include_ai_report=payload.include_ai_report,
    )


@notifications_router.post(
    "/notifications/send/preview",
    description=(
        "Render what a manual send would deliver, without sending it. Runs the same "
        "authorization as the send itself, so a preview cannot reveal an item the caller "
        "may not see."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def manual_send_preview_route(
    payload: ManualSendRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    from app.notifications.services.manual_send import preview_manual

    rendered = await preview_manual(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        route_id=payload.route_id,
        user=current_user,
        session=session,
        include_ai_report=payload.include_ai_report,
    )
    return {
        "success": True,
        "message": "Preview rendered",
        "body": rendered.body,
        # Null unless a named template set one; the provider composes its own
        # in that case, which this preview deliberately does not guess at.
        "subject": rendered.subject,
    }


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


@notifications_router.get(
    "/internal_notification_routes/{route_id}",
    response_model=NotificationRouteResponse,
    description="A single internal-scope notification route. Backs the route's own detail page, which is reachable by deep link.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_internal_route_route(route_id: int, session: AsyncSession = Depends(get_db)) -> NotificationRouteResponse:
    # The service scopes the lookup to scope='internal', so a customer route's
    # id cannot be read through this endpoint.
    route = await svc.get_internal_route(route_id, session)
    return NotificationRouteResponse(
        success=True,
        message="Internal route retrieved",
        route=NotificationRouteRead.from_orm(route),
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
            supports_internal_scope=provider.supports_internal_scope,
            secret_fields=sorted(provider.secret_fields),
            template_formats=sorted(provider.template_formats),
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_optional_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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


# ---------------------------------------------------------------------------
# Named message templates (#1038)
# ---------------------------------------------------------------------------
#
# Deployment-level rather than nested under /customers/{code}: a template with a
# null customer_code is shared with every tenant, so there is no one customer it
# belongs under. The optional `customer_code` query param filters the list to
# one customer's own templates plus the shared ones.


@notifications_router.get(
    "/notifications/templates",
    response_model=NotificationTemplateListResponse,
    description=(
        "List reusable message templates. Filter to a customer (returns their own plus the shared ones) "
        "and/or to a trigger (returns templates scoped to it plus the trigger-agnostic ones)."
    ),
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_optional_customer_code_access),
    ],
)
async def list_templates_route(
    customer_code: Optional[str] = None,
    trigger: Optional[str] = None,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationTemplateListResponse:
    accessible = await customer_access_handler.get_user_accessible_customers(current_user, session)
    templates = await templates_svc.list_templates(
        session,
        customer_code=customer_code,
        trigger=trigger,
        accessible_customers=accessible,
    )
    return NotificationTemplateListResponse(
        success=True,
        message=f"{len(templates)} template(s) retrieved",
        templates=[NotificationTemplateRead.model_validate(t) for t in templates],
    )


@notifications_router.post(
    "/notifications/templates/preview",
    response_model=TemplatePreviewResponse,
    description=(
        "Render template source against a sample event without saving it. Takes the source inline so the "
        "editor can preview unsaved edits. A render failure is returned in `error`, not raised."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def preview_template_route(
    payload: TemplatePreviewRequest,
    session: AsyncSession = Depends(get_db),
) -> TemplatePreviewResponse:
    result = await templates_svc.preview(payload, session)
    return TemplatePreviewResponse(
        success=result["error"] is None,
        message="Rendered" if result["error"] is None else "Template failed to render",
        **result,
    )


# Static paths above, wildcards below — a `/{template_id}` declared first would
# swallow `/preview` and 422 on parsing it as an int. See CLAUDE.md.


@notifications_router.get(
    "/notifications/templates/{template_id}",
    response_model=NotificationTemplateResponse,
    description="Fetch one template.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_template_route(
    template_id: int,
    session: AsyncSession = Depends(get_db),
) -> NotificationTemplateResponse:
    template = await templates_svc.get_template(template_id, session)
    return NotificationTemplateResponse(
        success=True,
        message="Template retrieved",
        template=NotificationTemplateRead.model_validate(template),
    )


@notifications_router.post(
    "/notifications/templates",
    response_model=NotificationTemplateResponse,
    description="Create a reusable message template. Leave customer_code empty to share it with every customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def create_template_route(
    payload: NotificationTemplateCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> NotificationTemplateResponse:
    created_by = getattr(current_user, "username", None) or str(current_user.id)
    logger.info(f"User {created_by} creating notification template {payload.name!r}")
    template = await templates_svc.create_template(payload, created_by, session)
    return NotificationTemplateResponse(
        success=True,
        message="Template created",
        template=NotificationTemplateRead.model_validate(template),
    )


@notifications_router.patch(
    "/notifications/templates/{template_id}",
    response_model=NotificationTemplateResponse,
    description=(
        "Update a template. Rejected if the change would break a route already using it, and built-in "
        "templates cannot be edited — duplicate one instead."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def update_template_route(
    template_id: int,
    payload: NotificationTemplateUpdate,
    session: AsyncSession = Depends(get_db),
) -> NotificationTemplateResponse:
    template = await templates_svc.update_template(template_id, payload, session)
    return NotificationTemplateResponse(
        success=True,
        message="Template updated",
        template=NotificationTemplateRead.model_validate(template),
    )


@notifications_router.delete(
    "/notifications/templates/{template_id}",
    response_model=NotificationTemplateResponse,
    description=(
        "Delete a template. Routes using it are detached rather than deleted — they fall back to their "
        "inline template or the channel default, so notifications keep flowing."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def delete_template_route(
    template_id: int,
    session: AsyncSession = Depends(get_db),
) -> NotificationTemplateResponse:
    template = await templates_svc.get_template(template_id, session)
    # Snapshot before deletion: the ORM row is unusable for a response once the
    # session has expunged it.
    read = NotificationTemplateRead.model_validate(template)
    detached = await templates_svc.delete_template(template_id, session)
    return NotificationTemplateResponse(
        success=True,
        message=("Template deleted" + (f"; {detached} route(s) fell back to their channel default" if detached else "")),
        template=read,
    )
