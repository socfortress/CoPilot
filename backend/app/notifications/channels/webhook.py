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

from loguru import logger
from pydantic import field_validator

from app.notifications.channels.base import ChannelConfig
from app.notifications.channels.base import ChannelProvider
from app.notifications.channels.base import DispatchContext
from app.notifications.channels.base import SendResult
from app.notifications.schema.events import NotificationEvent
from app.notifications.services.dispatchers import dispatch_webhook


def decode_webhook_headers(raw: Optional[str]) -> Optional[Dict[str, str]]:
    """Deserialize the route's JSON-string ``webhook_headers`` column.

    Returns a flat str→str dict, or None when unset/blank/malformed. Failing
    closed (None) rather than raising keeps a bad row from aborting the whole
    dispatch — the request just goes out with the dispatcher's default headers.
    """
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        logger.warning(f"Malformed webhook_headers JSON, ignoring: {raw[:120]!r}")
        return None
    if not isinstance(parsed, dict):
        return None
    return {str(k): str(v) for k, v in parsed.items()}


async def build_full_report(alert_id: int, session) -> Optional[Dict[str, Any]]:
    """Fetch the alert's latest AI report's *extra* fields as a flat dict.

    Returns only the fields NOT already present at the top level of the webhook
    payload — it deliberately omits ``summary`` and the severity to avoid
    duplicating them. Returns None when no report exists yet, so a webhook never
    fails just because the report write-back hasn't landed.

    Reuses the ai_analyst service layer (the canonical read path) so the shape
    stays in sync with the AI Analyst API. ``list_reports_by_alert`` returns
    newest-first, so element 0 is the report this dispatch is about.
    """
    from app.ai_analyst.services.ai_analyst import list_iocs_by_alert
    from app.ai_analyst.services.ai_analyst import list_reports_by_alert

    reports = await list_reports_by_alert(alert_id, session)
    if not reports:
        return None
    report = reports[0]
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
        rendered_body: str,
        ctx: DispatchContext,
    ) -> SendResult:
        # Read every attribute before the first await — an expired ORM object
        # would otherwise trigger a synchronous refresh and MissingGreenlet.
        has_template = bool(route.format_template)
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
            "text": rendered_body,
        }

        # Two mutually-exclusive body modes (enforced in the UI, guarded here):
        #   1. include_full_report → merge the report's extra fields flat into
        #      the structured payload. Template ignored.
        #   2. custom template → that rendered string is the body. If it
        #      contains the {{report}} token, inject the same report fields as
        #      a JSON object at that spot.
        rendered_template: Optional[str] = None
        if include_full_report:
            report_fields = await self._report(event, ctx)
            if report_fields is not None:
                structured_payload.update(report_fields)
        elif has_template:
            rendered_template = rendered_body
            if "{{report}}" in rendered_template:
                report_fields = await self._report(event, ctx)
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

    async def _report(self, event: NotificationEvent, ctx: DispatchContext) -> Optional[Dict[str, Any]]:
        """Memoized per dispatch call — several webhook routes on one alert
        share a single report read."""
        return await ctx.memoize(
            f"full_report:{event.entity_id}",
            lambda: build_full_report(event.entity_id, ctx.session),
        )
