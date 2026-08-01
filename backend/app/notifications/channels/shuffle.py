"""Shuffle hosted-MCP delivery.

Ported verbatim from the ``if/elif`` branch in ``dispatch()``. Every status,
error string and latency value below is reproduced exactly — the pre-refactor
behaviour is the spec, and the dispatch log is a customer-visible surface.

Fire-and-record: we POST to ``/api/v1/apps/{app_id}/mcp`` with the deployment's
admin Bearer plus the customer's Org-Id, capture the execution id, and treat
HTTP 200 as sent. We do not poll for the downstream app's terminal state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import update

from app.connectors.utils import get_connector_info_from_db
from app.db.universal_models import CustomerShuffleIntegration
from app.notifications.channels.base import ChannelProvider
from app.notifications.channels.base import DispatchContext
from app.notifications.channels.base import SendResult
from app.notifications.schema.events import NotificationEvent
from app.notifications.services.dispatchers import dispatch_shuffle

_CREDS_MEMO_KEY = "shuffle_creds"

SHUFFLE_CONNECTOR_NAME = "Shuffle"


async def get_shuffle_connector(session) -> Tuple[str, str]:
    """Fetch (base_url, api_key) for the Shuffle connector. Raises
    HTTPException if the connector row is missing or unconfigured —
    surfaces a clear 4xx in the dispatch endpoint instead of a generic
    500 when an admin forgets to configure Shuffle.

    Lives here rather than in the service module so the provider owns its own
    credential lookup; the service's app/org/verify helpers import it from here.
    """
    info = await get_connector_info_from_db(SHUFFLE_CONNECTOR_NAME, session)
    if not info:
        raise HTTPException(
            status_code=503,
            detail=(
                "Shuffle connector is not configured in CoPilot. "
                "Add the Shuffle connector with a valid API key before "
                "creating Shuffle-channel notification routes."
            ),
        )
    api_key = info.get("connector_api_key") or ""
    base_url = info.get("connector_url") or "https://shuffler.io"
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Shuffle connector is configured but has no API key set.",
        )
    return (base_url, api_key)


class ShuffleChannel(ChannelProvider):
    key = "shuffle"
    display_name = "Shuffle"

    async def send(
        self,
        *,
        route: Any,
        event: NotificationEvent,
        rendered_body: str,
        ctx: DispatchContext,
    ) -> SendResult:
        # Read every attribute before the first await — an expired ORM object
        # would otherwise trigger a synchronous refresh and MissingGreenlet.
        app_id = route.shuffle_app_id
        integration_id = route.shuffle_integration_id
        destination = route.destination

        # Memoized per dispatch call: several Shuffle routes for one customer
        # share a single connector read, matching the pre-refactor behaviour.
        creds: Optional[Tuple[str, str]] = None
        try:
            creds = await ctx.memoize(_CREDS_MEMO_KEY, lambda: get_shuffle_connector(ctx.session))
        except HTTPException as e:
            # Caught here rather than in the dispatch loop so the operator sees
            # the connector's own detail string instead of a generic
            # "Dispatcher exception".
            logger.warning(f"Shuffle connector unavailable: {e.detail}")
            return SendResult.failed(str(e.detail) or "Shuffle connector unavailable")

        if creds is None:
            return SendResult.failed("Shuffle connector unavailable")
        if not app_id:
            return SendResult.failed("Route has no shuffle_app_id (data integrity issue)")

        integration = await ctx.session.get(CustomerShuffleIntegration, integration_id)
        if not integration or integration.customer_code != event.customer_code:
            # Defense in depth: tenant isolation is enforced at create/update
            # time, but a hand-edited row could still slip through. Refusing at
            # dispatch time prevents cross-tenant leaks.
            return SendResult.failed(
                "Route's shuffle_integration is missing or belongs to a different customer; refusing to dispatch.",
            )
        if not integration.enabled:
            return SendResult.skipped("Shuffle integration is disabled")

        base_url, api_key = creds
        org_id = integration.shuffle_org_id

        # Shuffle's input_text is natural language. We prepend a
        # "send to {destination}" hint so the app agent knows where to deliver.
        input_text = f"Send to {destination}: {rendered_body}" if destination else rendered_body

        status, error_message, latency_ms, execution_id = await dispatch_shuffle(
            base_url=base_url,
            api_key=api_key,
            org_id=org_id,
            app_id=app_id,
            input_text=input_text,
        )
        return SendResult(
            status=status,
            error_message=error_message,
            latency_ms=latency_ms,
            provider_reference=execution_id,
        )

    async def after_send(self, *, route: Any, result: SendResult, ctx: DispatchContext) -> None:
        """Stamp the integration's ``last_used_at``.

        Gives the integration list a "fired 2h ago" signal without joining the
        dispatch log on every render.
        """
        integration_id = route.shuffle_integration_id
        if not integration_id:
            return

        await ctx.session.execute(
            update(CustomerShuffleIntegration)
            .where(CustomerShuffleIntegration.id == integration_id)
            .values(last_used_at=datetime.utcnow()),
        )
