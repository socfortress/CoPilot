"""Microsoft Teams delivery via an incoming webhook.

Teams is NOT the generic `webhook` channel with a different URL. It requires an
Adaptive Card wrapped in a `{"type": "message", "attachments": [...]}` envelope;
posting a bare JSON body produces a 200 and no visible message, which is the
worst possible failure mode.

**Which webhook.** Microsoft retired the Office 365 connector webhooks
(`*.webhook.office.com`) during 2026 in favour of Power Automate **Workflows**,
whose URLs live on `*.powerautomate.com`, `*.powerplatform.com` and
`flow.microsoft.com`. Workflows accept both Adaptive Card and the legacy
MessageCard format; we send Adaptive Cards. The host is deliberately NOT
validated beyond https — a deployment may still have a working legacy connector,
and Microsoft has changed these hosts before.

**Constraints that shaped this, both from Microsoft's docs rather than
guesswork:** messages over 28 KB are rejected outright, and Teams throttles
above roughly four requests per second with a 429.

Configuration is a single URL, so this channel needs no bespoke form block —
the route form renders it from the schema below. That was the point of #1029.
"""

from __future__ import annotations

import json
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import field_validator

from app.notifications.channels.base import ChannelConfig
from app.notifications.channels.base import ChannelProvider
from app.notifications.channels.base import DispatchContext
from app.notifications.channels.base import SendResult
from app.notifications.schema.events import NotificationEvent
from app.notifications.services.dispatchers import TEAMS_MAX_PAYLOAD_BYTES
from app.notifications.services.dispatchers import dispatch_teams

#: Adaptive Card container styles by severity. Teams renders these as a coloured
#: band, which is what makes a channel of alerts scannable.
_SEVERITY_STYLE = {
    "Critical": "attention",
    "High": "attention",
    "Medium": "warning",
    "Low": "good",
    "Informational": "default",
}

#: Pinned rather than "latest": Teams renders a card at the version declared,
#: and a newer schema silently degrades on older clients.
_ADAPTIVE_CARD_VERSION = "1.4"


class TeamsConfig(ChannelConfig):
    """`customer_notification_route.config` when channel='teams'.

    One field, which is the point — a channel this simple should need no
    frontend work, and the generic renderer handles it.
    """

    webhook_url: Optional[str] = None

    @field_validator("webhook_url")
    @classmethod
    def _must_be_https(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.strip()
        if cleaned and not cleaned.lower().startswith("https://"):
            raise ValueError("webhook_url must start with https://")
        return cleaned


class TeamsChannel(ChannelProvider):
    key = "teams"
    display_name = "Microsoft Teams"
    config_schema = TeamsConfig
    # A webhook targets a fixed channel, so it cannot deliver to a resolved
    # person — same constraint as the generic webhook channel.
    supports_recipient_modes = {"static"}
    # The URL is the credential: anyone holding it can post to the channel.
    secret_fields = {"webhook_url"}

    async def send(
        self,
        *,
        route: Any,
        event: NotificationEvent,
        rendered_body: str,
        ctx: DispatchContext,
    ) -> SendResult:
        # Read attributes before the first await — an expired ORM object would
        # otherwise trigger a synchronous refresh and MissingGreenlet.
        has_template = bool(route.format_template)
        try:
            cfg = self.parse_config(route)
        except ValueError as e:
            return SendResult.failed(f"Invalid teams config: {e}")

        if not cfg.webhook_url:
            return SendResult.failed("Route config has no webhook_url (data integrity issue)")

        card = self._build_card(event, rendered_body, raw_body=has_template)
        card = self._fit_within_size_limit(card, event, rendered_body)

        status, error_message, latency_ms, _ = await dispatch_teams(webhook_url=cfg.webhook_url, card=card)
        return SendResult(status=status, error_message=error_message, latency_ms=latency_ms)

    # -- card construction --------------------------------------------------

    def _build_card(self, event: NotificationEvent, body: str, *, raw_body: bool) -> Dict[str, Any]:
        """Wrap the rendered body in an Adaptive Card envelope.

        When the route sets a `format_template` the operator has chosen their
        own wording, so the body is shown verbatim under a minimal header rather
        than being decomposed into facts they didn't ask for.
        """
        style = _SEVERITY_STYLE.get(event.severity.value, "default")

        elements: List[Dict[str, Any]] = [
            {
                "type": "Container",
                "style": style,
                "bleed": True,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"{event.severity.value} · {event.subject}",
                        "weight": "Bolder",
                        "size": "Medium",
                        "wrap": True,
                    },
                ],
            },
        ]

        if not raw_body:
            facts = [{"title": "Trigger", "value": event.trigger.value.replace("_", " ")}]
            if event.customer_code:
                facts.append({"title": "Customer", "value": event.customer_code})
            facts.append({"title": "Entity", "value": f"{event.entity_type} #{event.entity_id}"})
            if event.assignee_username:
                facts.append({"title": "Assignee", "value": event.assignee_username})
            if event.actor_username:
                facts.append({"title": "By", "value": event.actor_username})
            elements.append({"type": "FactSet", "facts": facts})

        elements.append({"type": "TextBlock", "text": body, "wrap": True})

        card_content: Dict[str, Any] = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": _ADAPTIVE_CARD_VERSION,
            "body": elements,
        }

        if event.link_url:
            # Both an action AND a text line. Microsoft's own docs are ambiguous
            # about whether button rendering survives in Workflows, and a deep
            # link that silently vanishes is worse than a slightly redundant one.
            card_content["actions"] = [
                {"type": "Action.OpenUrl", "title": "Open in CoPilot", "url": event.link_url},
            ]
            elements.append(
                {
                    "type": "TextBlock",
                    "text": f"[Open in CoPilot]({event.link_url})",
                    "wrap": True,
                    "isSubtle": True,
                },
            )

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": card_content,
                },
            ],
        }

    def _fit_within_size_limit(self, card: Dict[str, Any], event: NotificationEvent, body: str) -> Dict[str, Any]:
        """Truncate the body until the card fits Teams' 28 KB ceiling.

        Teams rejects an oversized message outright, and an AI report with a full
        markdown write-up and IOC list can exceed it. A truncated notification
        that arrives beats a complete one that doesn't — the deep link is
        preserved so the full detail is always one click away.
        """
        if len(json.dumps(card).encode("utf-8")) <= TEAMS_MAX_PAYLOAD_BYTES:
            return card

        # Binary-search the longest body that fits, rather than guessing a
        # character count: the overhead depends on how many facts were rendered.
        low, high = 0, len(body)
        best = ""
        while low <= high:
            mid = (low + high) // 2
            candidate = body[:mid]
            trial = self._build_card(event, candidate + "\n\n…truncated by CoPilot to fit Teams' 28 KB limit.", raw_body=True)
            if len(json.dumps(trial).encode("utf-8")) <= TEAMS_MAX_PAYLOAD_BYTES:
                best = candidate
                low = mid + 1
            else:
                high = mid - 1

        return self._build_card(event, best + "\n\n…truncated by CoPilot to fit Teams' 28 KB limit.", raw_body=True)
