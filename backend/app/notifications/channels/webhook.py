"""Direct HTTP webhook delivery.

Ported verbatim from the ``if/elif`` branch in ``dispatch()``. The structured
JSON payload below is an **external contract** — customers' automation platforms
consume these exact field names — so the shape, the key order and the
``None``-vs-empty-string distinctions are reproduced exactly.

Fire-and-record: POST/PUT to the route's URL, treat any 2xx/3xx as sent.
"""

from __future__ import annotations

import json
from typing import Any
from typing import Dict
from typing import Optional

from pydantic import field_validator

from app.notifications.channels.base import ChannelConfig
from app.notifications.channels.base import ChannelProvider
from app.notifications.channels.base import DispatchContext
from app.notifications.channels.base import RenderedMessage
from app.notifications.channels.base import SendResult
from app.notifications.schema.events import EntityType
from app.notifications.schema.events import NotificationEvent
from app.notifications.services.ai_report_context import named_report_id
from app.notifications.services.ai_report_context import select_report
from app.notifications.services.dispatchers import dispatch_webhook
from app.notifications.services.payload_v1 import SCHEMA_V1
from app.notifications.services.payload_v1 import ai_report_v1_for_route
from app.notifications.services.payload_v1 import report_permitted_for_route


async def build_full_report(
    alert_id: int,
    session,
    customer_code: Optional[str] = None,
    *,
    report_id: Optional[int] = None,
    entity_type: str = EntityType.ALERT,
) -> Optional[Dict[str, Any]]:
    """Fetch the notification's AI report's *extra* fields as a flat dict.

    Returns only the fields NOT already present at the top level of the webhook
    payload — it deliberately omits ``summary`` and the severity to avoid
    duplicating them. Returns None when there is no report to carry, so a webhook
    never fails just because the report write-back hasn't landed.

    The shape (names, values, nulls, order) is the pre-v1 external contract and is
    pinned by ``tests/test_notification_payload_v1.py``. The report is the one
    ``select_report`` picks for the v1 block and ``context.ai_report`` too: the
    reviewed one on a review event, else the alert's newest by ``created_at`` then
    ``id``; nothing for a case or task, or another customer's report. So
    ``report_id`` here is always the block's ``report_id``. ``iocs`` keep their
    pre-v1 meaning: every IOC recorded for the **alert**, across its reports,
    newest first, read through the ai_analyst service layer.

    Callers check the route may receive the report first (``full_report_for_route``).
    """
    from app.ai_analyst.services.ai_analyst import list_iocs_by_alert

    report = await select_report(alert_id, session, report_id=report_id, customer_code=customer_code, entity_type=entity_type)
    if report is None:
        return None
    iocs = await list_iocs_by_alert(alert_id, session)
    return {
        "report_id": report.id,
        "recommended_actions": report.recommended_actions,
        "report_markdown": report.report_markdown,
        "report_created_at": report.created_at.isoformat() if report.created_at else None,
        "iocs": [
            {
                "ioc_value": i.ioc_value,
                "ioc_type": i.ioc_type,
                "vt_verdict": i.vt_verdict,
                "vt_score": i.vt_score,
                "details": i.details,
            }
            for i in iocs
        ],
    }


async def full_report_for_route(
    route_scope: Optional[str],
    event: NotificationEvent,
    ctx: DispatchContext,
) -> Optional[Dict[str, Any]]:
    """The flat report fields one route may receive, or None: the ``include_full_report`` merge
    and the ``{{report}}`` token, in a webhook and in a rendered template alike.

    None when the route may not receive the report (``report_permitted_for_route``: a customer
    whose AI report setting is off, on any trigger; a manual send without the report) — the
    payload is then exactly the "no report yet" one, a shape receivers already handle. Internal
    routes are not gated. Memoized per dispatch call and report, so several routes on one alert
    share a single read.
    """
    if not await report_permitted_for_route(route_scope, event, ctx.session, ctx):
        return None
    report_id = named_report_id(event.context)
    return await ctx.memoize(
        f"full_report:{event.entity_type}:{event.entity_id}:{report_id}",
        lambda: build_full_report(
            event.entity_id,
            ctx.session,
            event.customer_code,
            report_id=report_id,
            entity_type=event.entity_type,
        ),
    )


class WebhookConfig(ChannelConfig):
    """`customer_notification_route.config` when channel='webhook'.

    `headers` is a real dict here, unlike the legacy `webhook_headers` column,
    which stored a JSON *string* inside a Text column and needed hand-decoding
    on every read.
    """

    url: Optional[str] = None
    method: str = "POST"
    headers: Optional[Dict[str, str]] = None
    include_full_report: bool = False

    @field_validator("method")
    @classmethod
    def _method_supported(cls, v: str) -> str:
        upper = (v or "POST").upper()
        if upper not in {"POST", "PUT"}:
            raise ValueError("method must be POST or PUT")
        return upper


class WebhookChannel(ChannelProvider):
    key = "webhook"
    display_name = "Webhook"
    config_schema = WebhookConfig
    # A webhook targets a fixed URL, so it cannot deliver to a resolved
    # assignee — that needs an addressable channel like email.
    supports_recipient_modes = {"static"}
    # Authorization / X-API-Key and friends live here; encrypted in #1020.
    secret_fields = {"headers"}

    async def send(
        self,
        *,
        route: Any,
        event: NotificationEvent,
        message: RenderedMessage,
        ctx: DispatchContext,
    ) -> SendResult:
        # Read every attribute before the first await — an expired ORM object
        # would otherwise trigger a synchronous refresh and MissingGreenlet.
        has_template = message.is_custom
        route_scope = getattr(route, "scope", None)
        try:
            cfg = self.parse_config(route)
        except ValueError as e:
            # A malformed config is a data-integrity problem on one route; log
            # it against that route rather than failing the whole batch.
            return SendResult.failed(f"Invalid webhook config: {e}")

        url = cfg.url
        method = cfg.method
        headers = cfg.headers
        include_full_report = cfg.include_full_report

        if not url:
            return SendResult.failed("Route config has no url (data integrity issue)")

        # Structured default payload — automation platforms consume these fields
        # directly, so the names and null-vs-empty semantics are load-bearing.
        structured_payload: Dict[str, Any] = {
            "customer_code": event.customer_code,
            "alert_id": event.entity_id,
            "alert_name": event.context.get("alert_name"),
            "severity": event.severity.value,
            "summary": event.summary,
            "report_url": event.link_url,
            "text": message.body,
            # Added with v1, after the original keys so their order is unchanged.
            "schema": SCHEMA_V1,
        }

        # Two mutually-exclusive body modes (enforced in the UI, guarded here):
        #   1. include_full_report → merge the report's extra fields flat into
        #      the structured payload (the pre-v1 shape, kept byte for byte for
        #      existing receivers), and add the same report as the nested,
        #      bounded `ai_report` block (`services/payload_v1.py`). The key is
        #      always present with the option on: null when there is no report,
        #      or when this route may not receive one. Template ignored.
        #   2. custom template → that rendered string is the body. If it
        #      contains the {{report}} token, inject the same report fields as
        #      a JSON object at that spot.
        rendered_template: Optional[str] = None
        if include_full_report:
            report_fields = await self._report(route_scope, event, ctx)
            if report_fields is not None:
                structured_payload.update(report_fields)
            structured_payload["ai_report"] = await ai_report_v1_for_route(route_scope, event, ctx.session, ctx)
        elif has_template:
            rendered_template = message.body
            if "{{report}}" in rendered_template:
                report_fields = await self._report(route_scope, event, ctx)
                rendered_template = rendered_template.replace(
                    "{{report}}",
                    json.dumps(report_fields) if report_fields is not None else "null",
                )

        status, error_message, latency_ms, _ = await dispatch_webhook(
            url=url,
            method=method or "POST",
            headers=headers,
            structured_payload=structured_payload,
            rendered_template=rendered_template,
        )
        return SendResult(status=status, error_message=error_message, latency_ms=latency_ms)

    async def _report(self, route_scope: Optional[str], event: NotificationEvent, ctx: DispatchContext) -> Optional[Dict[str, Any]]:
        return await full_report_for_route(route_scope, event, ctx)
