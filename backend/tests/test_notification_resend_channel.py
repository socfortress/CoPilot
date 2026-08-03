"""The Resend email channel.

Two things make this channel different from the two before it, and both are what
these tests are mostly about:

1. It can address a **person**. `recipient_mode='assignee'` resolves the event's
   assignee to their email at dispatch time — the first channel that can, and
   what makes "notify whoever this was assigned to" (#1006) expressible.

2. Its quota is a **shared, finite deployment resource**. The free tier is 1,000
   emails/month across every customer, because the API key is deployment-wide.
   One noisy route can exhaust it for everyone, so the throttle matters.

Every failure path must produce a logged outcome rather than an exception: a
route pointed at a departed user should record why it didn't send, not take down
the dispatch batch.

Unit tests with mocked sessions and stubbed HTTP — no DB, no network.

Run with: cd backend && python -m pytest tests/test_notification_resend_channel.py
"""

import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.notifications.channels.resend as resend_mod  # noqa: E402
from app.notifications.channels import CHANNEL_REGISTRY  # noqa: E402
from app.notifications.channels.base import DispatchContext  # noqa: E402
from app.notifications.channels.base import RenderedMessage  # noqa: E402
from app.notifications.channels.resend import ResendConfig  # noqa: E402
from app.notifications.schema.events import NotificationEvent  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402

CUSTOMER = "TENANT_A"
CREDS = ("https://api.resend.com", "re_key", "alerts@socfortress.co")


def _event(assignee=None, subject="Mimikatz signature", severity=NotificationSeverity.CRITICAL):
    return NotificationEvent(
        customer_code=CUSTOMER,
        trigger=NotificationTrigger.INVESTIGATION_COMPLETE,
        severity=severity,
        subject=subject,
        summary="Credential dumping observed on WKSTN-04.",
        entity_type="alert",
        entity_id=42,
        dedupe_key="alert:42:investigation_complete",
        assignee_username=assignee,
    )


def _route(config=None, recipient_mode="static", **over):
    cfg = {"to": ["soc@acme.example"]}
    cfg.update(config or {})
    base = dict(id=1, name="SOC email", channel="resend", recipient_mode=recipient_mode, config=json.dumps(cfg))
    base.update(over)
    return SimpleNamespace(**base)


def _send(route, event=None, creds=CREDS, recent_sends=0, user=...):
    """Invoke the provider with HTTP, connector and DB lookups stubbed.

    Returns (result, kwargs-the-dispatcher-was-called-with-or-None).
    """
    ev = event or _event()
    sent = AsyncMock(return_value=("sent", None, 12, "msg-1"))
    creds_mock = AsyncMock(side_effect=creds) if isinstance(creds, Exception) else AsyncMock(return_value=creds)

    patches = [
        patch.object(resend_mod, "dispatch_resend", sent),
        patch.object(resend_mod, "get_resend_connector", creds_mock),
        patch("app.notifications.services.resend_quota.sends_in_last_hour", AsyncMock(return_value=recent_sends)),
    ]
    if user is not ...:
        patches.append(patch("app.auth.services.universal.find_user", AsyncMock(return_value=user)))

    for p in patches:
        p.start()
    try:
        result = asyncio.run(
            CHANNEL_REGISTRY["resend"].send(
                route=route,
                event=ev,
                message=RenderedMessage(body="RENDERED BODY"),
                ctx=DispatchContext(session=AsyncMock(), event=ev),
            ),
        )
    finally:
        for p in patches:
            p.stop()
    return result, (sent.await_args.kwargs if sent.await_args else None)


# ── the provider contract ─────────────────────────────────────────────────


def test_resend_is_the_first_channel_that_can_address_a_person():
    provider = CHANNEL_REGISTRY["resend"]
    assert "assignee" in provider.supports_recipient_modes
    assert "static" in provider.supports_recipient_modes


def test_api_key_is_not_route_config_so_nothing_here_needs_encrypting():
    """The key lives on the deployment's connector row. If that ever changes,
    #1020's encryption has to cover it."""
    assert CHANNEL_REGISTRY["resend"].secret_fields == set()


# ── static delivery ───────────────────────────────────────────────────────


def test_static_mode_sends_to_the_configured_addresses():
    _result, kwargs = _send(_route(config={"to": ["a@x.example", "b@x.example"]}))
    assert kwargs["to"] == ["a@x.example", "b@x.example"]


def test_from_address_falls_back_to_the_connector_default():
    _result, kwargs = _send(_route())
    assert kwargs["from_address"] == "alerts@socfortress.co"


def test_route_can_override_the_from_address():
    _result, kwargs = _send(_route(config={"from_address": "ir@acme.example"}))
    assert kwargs["from_address"] == "ir@acme.example"


def test_missing_from_address_everywhere_is_a_clear_failure():
    """Neither the connector nor the route supplies one — Resend would reject
    the send, so fail with something actionable instead."""
    result, kwargs = _send(_route(), creds=("https://api.resend.com", "re_key", None))

    assert result.status == "failed"
    assert "From address" in result.error_message
    assert kwargs is None


def test_subject_carries_severity_for_scanability():
    _result, kwargs = _send(_route())
    assert kwargs["subject"] == "[CoPilot] Critical: Mimikatz signature"


def test_subject_prefix_is_configurable_and_optional():
    _result, kwargs = _send(_route(config={"subject_prefix": ""}))
    assert kwargs["subject"] == "Critical: Mimikatz signature"


def test_message_id_becomes_the_provider_reference():
    result, _kwargs = _send(_route())
    assert result.status == "sent"
    assert result.provider_reference == "msg-1"


# ── assignee resolution: the point of the channel ─────────────────────────


def test_assignee_mode_resolves_the_users_email():
    user = SimpleNamespace(username="analyst_one", email="analyst_one@socfortress.co")
    _result, kwargs = _send(
        _route(recipient_mode="assignee", config={"to": []}),
        event=_event(assignee="analyst_one"),
        user=user,
    )
    assert kwargs["to"] == ["analyst_one@socfortress.co"]


def test_assignee_mode_ignores_the_static_recipient_list():
    """`to` is not a fallback in assignee mode — treating it as one would mail
    the SOC list every time a lookup failed."""
    user = SimpleNamespace(username="analyst_one", email="analyst_one@socfortress.co")
    _result, kwargs = _send(
        _route(recipient_mode="assignee", config={"to": ["everyone@acme.example"]}),
        event=_event(assignee="analyst_one"),
        user=user,
    )
    assert kwargs["to"] == ["analyst_one@socfortress.co"]


def test_event_without_an_assignee_is_skipped_not_failed():
    """An investigation_complete event reaching an assignee-mode route isn't a
    misconfiguration — there is simply nobody to address."""
    result, kwargs = _send(_route(recipient_mode="assignee", config={"to": []}), event=_event(assignee=None))

    assert result.status == "skipped"
    assert "no assignee" in result.error_message
    assert kwargs is None


def test_unknown_assignee_fails_with_the_username():
    result, kwargs = _send(
        _route(recipient_mode="assignee", config={"to": []}),
        event=_event(assignee="departed_user"),
        user=None,
    )
    assert result.status == "failed"
    assert "departed_user" in result.error_message
    assert kwargs is None


def test_assignee_without_an_email_fails_clearly():
    user = SimpleNamespace(username="analyst_one", email=None)
    result, kwargs = _send(
        _route(recipient_mode="assignee", config={"to": []}),
        event=_event(assignee="analyst_one"),
        user=user,
    )
    assert result.status == "failed"
    assert "no email address" in result.error_message
    assert kwargs is None


# ── the shared quota ──────────────────────────────────────────────────────


def test_throttle_skips_before_reaching_the_provider():
    """A throttled send must cost nothing. The quota is a shared deployment
    resource, so the check happens before the network call, not after."""
    result, kwargs = _send(_route(config={"max_per_hour": 5}), recent_sends=5)

    assert result.status == "skipped"
    assert "Rate limit" in result.error_message
    assert kwargs is None, "throttled send must not hit Resend"


def test_under_the_throttle_still_sends():
    result, kwargs = _send(_route(config={"max_per_hour": 5}), recent_sends=4)
    assert result.status == "sent"
    assert kwargs is not None


def test_throttle_can_be_disabled_with_null():
    result, _kwargs = _send(_route(config={"max_per_hour": None}), recent_sends=9999)
    assert result.status == "sent"


def test_throttle_must_be_a_positive_number():
    with pytest.raises(ValueError):
        ResendConfig(to=["a@b.c"], max_per_hour=0)


# ── config shape ──────────────────────────────────────────────────────────


def test_a_bare_string_recipient_is_accepted_as_one_address():
    """The form sends a list, but hand-written config and API callers commonly
    send a single address; rejecting that is needless friction."""
    cfg = ResendConfig.model_validate({"to": "one@x.example"})
    assert cfg.to == ["one@x.example"]


def test_unknown_config_key_is_rejected():
    with pytest.raises(ValueError):
        ResendConfig.model_validate({"to": ["a@b.c"], "subjectprefix": "oops"})


def test_defaults_are_sane_for_a_shared_quota():
    cfg = ResendConfig()
    assert cfg.max_per_hour == 20, "an unthrottled default would let one route drain the tier"
    assert cfg.subject_prefix == "[CoPilot]"


# ── connector failures ────────────────────────────────────────────────────


def test_unconfigured_connector_surfaces_its_own_message():
    """The operator needs "no API key set", not a generic dispatcher error."""
    exc = HTTPException(status_code=503, detail="Resend connector is configured but has no API key set.")
    result, kwargs = _send(_route(), creds=exc)

    assert result.status == "failed"
    assert result.error_message == "Resend connector is configured but has no API key set."
    assert kwargs is None


def test_malformed_config_fails_only_this_route():
    broken = _route()
    broken.config = "{not json"
    result, kwargs = _send(broken)

    assert result.status == "failed"
    assert "Invalid resend config" in result.error_message
    assert kwargs is None
