"""Resend email delivery.

The first channel that can address a *person* rather than a fixed endpoint: a
webhook targets a URL and Shuffle targets an app, but email can resolve the
event's assignee at dispatch time. That's what makes "notify whoever this alert
was assigned to" expressible (#1006).

Credentials are deployment-wide, following the Shuffle precedent — one Resend
account in the `connectors` table, with the per-customer differentiator being
the to/from addresses on each route.

**Quota is the operational constraint here.** Resend's free tier is 1,000
emails/month across the whole deployment — roughly 33/day for every customer
combined. `max_per_hour` on the route and the monthly counter in
`services/resend_quota.py` exist so that ceiling is visible and enforceable
rather than something you discover when delivery stops.
"""

from __future__ import annotations

from typing import Any
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from loguru import logger
from pydantic import field_validator

from app.connectors.utils import get_connector_info_from_db
from app.notifications.channels.base import ChannelConfig
from app.notifications.channels.base import ChannelProvider
from app.notifications.channels.base import DispatchContext
from app.notifications.channels.base import RenderedMessage
from app.notifications.channels.base import SendResult
from app.notifications.schema.events import NotificationEvent
from app.notifications.services.dispatchers import dispatch_resend

_CREDS_MEMO_KEY = "resend_creds"

RESEND_CONNECTOR_NAME = "Resend"

#: Resend's free tier, for the UI's quota indicator. Not enforced here — Resend
#: itself rejects over-quota sends, and a paid plan raises it.
FREE_TIER_MONTHLY_LIMIT = 1000


async def get_resend_connector(session) -> Tuple[str, str, Optional[str]]:
    """Fetch (base_url, api_key, default_from) for the Resend connector.

    Raises HTTPException when unconfigured, which the provider converts into a
    per-route failure rather than letting it abort a whole dispatch batch.
    """
    info = await get_connector_info_from_db(RESEND_CONNECTOR_NAME, session)
    if not info:
        raise HTTPException(
            status_code=503,
            detail=(
                "Resend connector is not configured in CoPilot. Add the Resend connector "
                "with a valid API key before creating email notification routes."
            ),
        )
    api_key = info.get("connector_api_key") or ""
    base_url = info.get("connector_url") or "https://api.resend.com"
    default_from = info.get("connector_extra_data") or None
    if not api_key:
        raise HTTPException(status_code=503, detail="Resend connector is configured but has no API key set.")
    return (base_url, api_key, default_from)


class ResendConfig(ChannelConfig):
    """`customer_notification_route.config` when channel='resend'.

    `to` is required for recipient_mode='static' and ignored for 'assignee',
    where the address is resolved from the event instead. Enforced at save time
    in the route schema, which knows the mode.

    No secret_fields: the API key lives on the deployment's connector row, not
    in per-route config, so nothing here needs encrypting in #1020.
    """

    to: List[str] = []
    cc: List[str] = []
    #: Overrides the connector's RESEND_FROM_ADDRESS. Must be on a domain
    #: verified in Resend or the send is rejected.
    from_address: Optional[str] = None
    reply_to: Optional[str] = None
    subject_prefix: str = "[CoPilot]"
    #: Per-route throttle, checked before the provider call. Guards the shared
    #: monthly quota from one noisy route — an alert_created route on a busy
    #: customer could exhaust the free tier for everyone in a morning.
    max_per_hour: Optional[int] = 20

    @field_validator("to", "cc", mode="before")
    @classmethod
    def _coerce_single_address(cls, v):
        """Accept a bare string as a one-element list.

        The form sends a list, but hand-written config and API callers commonly
        send a single address; rejecting that is needless friction.
        """
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v

    @field_validator("max_per_hour")
    @classmethod
    def _positive_limit(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("max_per_hour must be at least 1, or null to disable the throttle")
        return v


class ResendChannel(ChannelProvider):
    key = "resend"
    display_name = "Email (Resend)"
    config_schema = ResendConfig
    # The first channel that can resolve a person. `assignee` looks up the
    # event's assignee and mails them directly.
    supports_recipient_modes = {"static", "assignee"}
    # Empty: the API key is on the connector row, not in route config.
    secret_fields = set()
    # The only channel that renders HTML: an `html` template is posted as both
    # the `html` and `text` parts, so it arrives formatted and still degrades to
    # readable text. A chat card would show the markup instead.
    template_formats = {"text", "markdown", "html"}

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
        route_id = route.id
        recipient_mode = route.recipient_mode
        try:
            cfg = self.parse_config(route)
        except ValueError as e:
            return SendResult.failed(f"Invalid resend config: {e}")

        try:
            creds = await ctx.memoize(_CREDS_MEMO_KEY, lambda: get_resend_connector(ctx.session))
        except HTTPException as e:
            logger.warning(f"Resend connector unavailable: {e.detail}")
            return SendResult.failed(str(e.detail) or "Resend connector unavailable")

        base_url, api_key, default_from = creds

        from_address = cfg.from_address or default_from
        if not from_address:
            return SendResult.failed(
                "No From address: set RESEND_FROM_ADDRESS on the connector or from_address on the route.",
            )

        recipients, problem = await self._resolve_recipients(recipient_mode, cfg, event)
        if problem is not None:
            return problem
        if not recipients:
            return SendResult.failed("No recipients resolved for this route.")

        # Throttle before the provider call, so a skipped send costs nothing and
        # is visible in the dispatch log rather than silently dropped.
        if cfg.max_per_hour:
            from app.notifications.services.resend_quota import sends_in_last_hour

            recent = await sends_in_last_hour(route_id, ctx.session)
            if recent >= cfg.max_per_hour:
                return SendResult.skipped(
                    f"Rate limit reached for this route ({recent}/{cfg.max_per_hour} in the last hour).",
                )

        # A named template's subject line wins over the composed one — an
        # operator who wrote a subject meant it. `subject_prefix` still applies,
        # so deployment-wide inbox filtering on "[CoPilot]" keeps working.
        subject = self._subject(cfg, event, override=message.subject)

        # Email is the only channel that can render HTML, so an `html` template
        # is sent as the HTML part with the same source as the text fallback.
        # Clients that refuse HTML still get something readable.
        is_html = message.format == "html"

        status, error_message, latency_ms, message_id = await dispatch_resend(
            base_url=base_url,
            api_key=api_key,
            from_address=from_address,
            to=recipients,
            cc=cfg.cc or None,
            reply_to=cfg.reply_to,
            subject=subject,
            text_body=message.body,
            html_body=message.body if is_html else None,
        )
        return SendResult(
            status=status,
            error_message=error_message,
            latency_ms=latency_ms,
            provider_reference=message_id,
        )

    async def _resolve_recipients(
        self,
        recipient_mode: str,
        cfg: ResendConfig,
        event: NotificationEvent,
    ) -> Tuple[List[str], Optional[SendResult]]:
        """Return (addresses, failure). Exactly one is meaningful.

        Every failure path is a logged outcome rather than an exception: a route
        pointed at a departed user should record why it didn't send, not take
        down the batch.
        """
        if recipient_mode != "assignee":
            return (list(cfg.to), None)

        username = event.assignee_username
        if not username:
            # e.g. an investigation_complete event reaching an assignee-mode
            # route. Skipped rather than failed: nothing is misconfigured, this
            # event simply has no one to address.
            return ([], SendResult.skipped("Route delivers to the assignee, but this event has no assignee."))

        from app.auth.services.universal import find_user

        user = await find_user(username)
        if user is None:
            return ([], SendResult.failed(f"Assignee '{username}' not found; cannot resolve an email address."))
        email = getattr(user, "email", None)
        if not email:
            return ([], SendResult.failed(f"Assignee '{username}' has no email address on their account."))
        return ([str(email)], None)

    def _subject(self, cfg: ResendConfig, event: NotificationEvent, *, override: Optional[str] = None) -> str:
        """Prefix + the event's one-line subject, with severity for scanability.

        Kept here rather than in the body renderer because a subject line is an
        email-specific concern — no other channel has one.

        `override` is a named template's rendered `subject_template`. It replaces
        the composed core but keeps the prefix: the prefix is a deployment-wide
        inbox-filtering convention, and letting a per-customer template drop it
        would silently break those filters.
        """
        prefix = (cfg.subject_prefix or "").strip()
        core = (override or f"{event.severity.value}: {event.subject}").strip()
        return f"{prefix} {core}".strip() if prefix else core
