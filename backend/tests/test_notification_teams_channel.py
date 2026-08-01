"""Microsoft Teams delivery.

Teams is not the generic webhook channel with a different URL. It requires an
Adaptive Card inside a `{"type": "message", "attachments": [...]}` envelope, and
posting a bare JSON body returns **200 with no visible message** — the worst
failure mode available, since nothing looks wrong. Most of these tests exist to
pin that envelope.

Two constraints come from Microsoft's documentation rather than guesswork:
messages over 28 KB are rejected outright, and Teams throttles above roughly
four requests per second with a 429.

Unit tests with stubbed HTTP — no network.

Run with: cd backend && python -m pytest tests/test_notification_teams_channel.py
"""

import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.notifications.channels.teams as teams_mod  # noqa: E402
from app.notifications.channels import CHANNEL_REGISTRY  # noqa: E402
from app.notifications.channels.base import DispatchContext  # noqa: E402
from app.notifications.channels.teams import TeamsConfig  # noqa: E402
from app.notifications.schema.events import NotificationEvent  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.dispatchers import TEAMS_MAX_PAYLOAD_BYTES  # noqa: E402

WEBHOOK = "https://prod-11.westus.logic.azure.com:443/workflows/abc/triggers/manual/paths/invoke"


def _event(severity=NotificationSeverity.CRITICAL, link="https://copilot.invalid/alerts/42", assignee=None, summary="Credential dumping."):
    return NotificationEvent(
        customer_code="TENANT_A",
        trigger=NotificationTrigger.INVESTIGATION_COMPLETE,
        severity=severity,
        subject="Mimikatz signature",
        summary=summary,
        entity_type="alert",
        entity_id=42,
        dedupe_key="alert:42:investigation_complete",
        link_url=link,
        assignee_username=assignee,
    )


def _route(config=None, format_template=None):
    cfg = {"webhook_url": WEBHOOK}
    cfg.update(config or {})
    return SimpleNamespace(id=1, name="SOC Teams", channel="teams", format_template=format_template, config=json.dumps(cfg))


def _send(route, event=None, body="RENDERED BODY", result=("sent", None, 12, None)):
    ev = event or _event()
    sent = AsyncMock(return_value=result)
    with patch.object(teams_mod, "dispatch_teams", sent):
        outcome = asyncio.run(
            CHANNEL_REGISTRY["teams"].send(
                route=route,
                event=ev,
                rendered_body=body,
                ctx=DispatchContext(session=AsyncMock(), event=ev),
            ),
        )
    return outcome, (sent.await_args.kwargs if sent.await_args else None)


def _card(kwargs):
    return kwargs["card"]["attachments"][0]["content"]


# ── the envelope: a bare body 200s and shows nothing ──────────────────────


def test_payload_is_wrapped_in_the_message_envelope():
    _outcome, kwargs = _send(_route())
    payload = kwargs["card"]

    assert payload["type"] == "message"
    assert len(payload["attachments"]) == 1
    assert payload["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"


def test_content_is_an_adaptive_card_with_a_pinned_version():
    """Pinned rather than 'latest': Teams renders at the declared version, and a
    newer schema degrades silently on older clients."""
    _outcome, kwargs = _send(_route())
    card = _card(kwargs)

    assert card["type"] == "AdaptiveCard"
    assert card["$schema"] == "http://adaptivecards.io/schemas/adaptive-card.json"
    assert card["version"] == "1.4"


def test_the_rendered_body_reaches_the_card():
    _outcome, kwargs = _send(_route(), body="A very specific body")
    assert any(el.get("text") == "A very specific body" for el in _card(kwargs)["body"])


# ── severity styling ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("severity", "style"),
    [
        (NotificationSeverity.CRITICAL, "attention"),
        (NotificationSeverity.HIGH, "attention"),
        (NotificationSeverity.MEDIUM, "warning"),
        (NotificationSeverity.LOW, "good"),
        (NotificationSeverity.INFORMATIONAL, "default"),
    ],
)
def test_severity_drives_the_header_colour(severity, style):
    """The coloured band is what makes a channel of alerts scannable."""
    _outcome, kwargs = _send(_route(), event=_event(severity=severity))
    header = _card(kwargs)["body"][0]

    assert header["type"] == "Container"
    assert header["style"] == style


def test_header_carries_severity_and_subject():
    _outcome, kwargs = _send(_route())
    text = _card(kwargs)["body"][0]["items"][0]["text"]
    assert "Critical" in text
    assert "Mimikatz signature" in text


# ── the deep link, belt and braces ────────────────────────────────────────


def test_link_appears_as_both_an_action_and_body_text():
    """Microsoft's docs are ambiguous about whether button rendering survives in
    Workflows. A deep link that silently vanishes is worse than a redundant one.
    """
    _outcome, kwargs = _send(_route())
    card = _card(kwargs)

    assert card["actions"][0]["type"] == "Action.OpenUrl"
    assert card["actions"][0]["url"] == "https://copilot.invalid/alerts/42"
    assert any("copilot.invalid/alerts/42" in str(el.get("text", "")) for el in card["body"])


def test_no_link_means_no_actions_block():
    _outcome, kwargs = _send(_route(), event=_event(link=None))
    assert "actions" not in _card(kwargs)


# ── facts vs a custom template ────────────────────────────────────────────


def test_default_body_gets_a_factset():
    _outcome, kwargs = _send(_route())
    factsets = [el for el in _card(kwargs)["body"] if el["type"] == "FactSet"]
    assert len(factsets) == 1
    titles = {f["title"] for f in factsets[0]["facts"]}
    assert {"Trigger", "Customer", "Entity"} <= titles


def test_a_custom_template_is_shown_verbatim_without_facts():
    """The operator chose their own wording; decomposing it into facts they
    didn't ask for would override that choice."""
    _outcome, kwargs = _send(_route(format_template="{{summary}}"), body="My exact wording")
    card = _card(kwargs)

    assert not [el for el in card["body"] if el["type"] == "FactSet"]
    assert any(el.get("text") == "My exact wording" for el in card["body"])


def test_assignee_and_actor_appear_when_present():
    event = _event(assignee="bob")
    event.actor_username = "alice"
    _outcome, kwargs = _send(_route(), event=event)
    facts = [el for el in _card(kwargs)["body"] if el["type"] == "FactSet"][0]["facts"]
    values = {f["title"]: f["value"] for f in facts}

    assert values["Assignee"] == "bob"
    assert values["By"] == "alice"


# ── the 28 KB ceiling ─────────────────────────────────────────────────────


def test_an_oversized_body_is_truncated_to_fit():
    """Teams rejects an oversized message outright. A truncated notification
    that arrives beats a complete one that doesn't."""
    huge = "x" * (TEAMS_MAX_PAYLOAD_BYTES * 2)
    _outcome, kwargs = _send(_route(), body=huge)

    encoded = len(json.dumps(kwargs["card"]).encode("utf-8"))
    assert encoded <= TEAMS_MAX_PAYLOAD_BYTES, f"payload was {encoded} bytes"


def test_truncation_says_so_rather_than_cutting_silently():
    huge = "x" * (TEAMS_MAX_PAYLOAD_BYTES * 2)
    _outcome, kwargs = _send(_route(), body=huge)
    assert any("truncated" in str(el.get("text", "")).lower() for el in _card(kwargs)["body"])


def test_truncation_keeps_the_deep_link_so_full_detail_stays_reachable():
    huge = "x" * (TEAMS_MAX_PAYLOAD_BYTES * 2)
    _outcome, kwargs = _send(_route(), body=huge)
    card = _card(kwargs)
    assert card["actions"][0]["url"] == "https://copilot.invalid/alerts/42"


def test_a_normal_body_is_not_truncated():
    _outcome, kwargs = _send(_route(), body="short body")
    assert not any("truncated" in str(el.get("text", "")).lower() for el in _card(kwargs)["body"])


# ── config ────────────────────────────────────────────────────────────────


def test_missing_webhook_url_fails_without_calling_out():
    outcome, kwargs = _send(_route(config={"webhook_url": None}))
    assert outcome.status == "failed"
    assert "webhook_url" in outcome.error_message
    assert kwargs is None


def test_non_https_url_is_rejected():
    with pytest.raises(ValueError):
        TeamsConfig(webhook_url="http://insecure.invalid/hook")


def test_the_host_is_not_restricted():
    """Deliberately unvalidated beyond https: a deployment may still have a
    working legacy connector, and Microsoft has changed these hosts before."""
    for url in [
        "https://prod-11.westus.logic.azure.com/workflows/x",
        "https://acme.webhook.office.com/webhookb2/x",
        "https://default.api.powerplatform.com/powerautomate/x",
    ]:
        assert TeamsConfig(webhook_url=url).webhook_url == url


def test_unknown_config_key_is_rejected():
    with pytest.raises(ValueError):
        TeamsConfig.model_validate({"webhook_url": WEBHOOK, "cardstyle": "oops"})


def test_malformed_config_fails_only_this_route():
    broken = _route()
    broken.config = "{not json"
    outcome, kwargs = _send(broken)

    assert outcome.status == "failed"
    assert "Invalid teams config" in outcome.error_message
    assert kwargs is None


# ── throttling ────────────────────────────────────────────────────────────


def test_rate_limiting_is_reported_as_retry_later_not_misconfiguration():
    """A bare 429 would send an operator checking their URL. Teams throttles
    above ~4 requests/second, which is a transient condition."""
    outcome, _kwargs = _send(
        _route(),
        result=("failed", "Teams rate-limited this request (429). Teams throttles above ~4 requests/second.", 5, None),
    )
    assert outcome.status == "failed"
    assert "429" in outcome.error_message


# ── the point of #1029 ────────────────────────────────────────────────────


def test_config_is_simple_enough_for_the_generic_form_renderer():
    """One string field, so this channel needed no bespoke frontend block —
    which is what the generic renderer was built for."""
    schema = CHANNEL_REGISTRY["teams"].config_schema.model_json_schema()
    assert list(schema["properties"]) == ["webhook_url"]


def test_the_webhook_url_is_declared_as_a_secret():
    """Anyone holding it can post to the channel."""
    assert CHANNEL_REGISTRY["teams"].secret_fields == {"webhook_url"}
