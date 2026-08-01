"""Channel provider registry, and byte-level equivalence with the old dispatcher.

The `if/elif` on `route.channel` inside `dispatch()` became a provider registry.
That refactor is only safe if what actually goes out over the wire is unchanged:
the webhook payload's field names are an external contract (customers' automation
platforms read them), and every status/error string lands in the dispatch log,
which operators read.

So the assertions below are deliberately literal — exact payload dicts, exact
error strings — rather than "something webhook-shaped was sent". They are the
regression bar for #1017.

Unit tests with mocked sessions and stubbed HTTP — no DB, no network.

Run with: cd backend && python -m pytest tests/test_notification_channel_registry.py
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

import app.notifications.channels.shuffle as shuffle_mod  # noqa: E402
import app.notifications.channels.webhook as webhook_mod  # noqa: E402
from app.notifications.channels import CHANNEL_REGISTRY  # noqa: E402
from app.notifications.channels import channel_keys  # noqa: E402
from app.notifications.channels import get_channel  # noqa: E402
from app.notifications.channels.base import ChannelProvider  # noqa: E402
from app.notifications.channels.base import DispatchContext  # noqa: E402
from app.notifications.schema.events import event_from_dispatch_request  # noqa: E402
from app.notifications.schema.notifications import DispatchRequest  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402

CUSTOMER = "TENANT_A"


def _request(alert_name="Mimikatz signature", report_url="https://copilot.invalid/alerts/42"):
    return DispatchRequest(
        customer_code=CUSTOMER,
        alert_id=42,
        trigger=NotificationTrigger.INVESTIGATION_COMPLETE,
        severity_assessment=NotificationSeverity.CRITICAL,
        summary="Credential dumping observed on WKSTN-04.",
        report_url=report_url,
        alert_name=alert_name,
    )


def _ctx(event, session=None):
    return DispatchContext(session=session or AsyncMock(), event=event)


def _webhook_route(config=None, **over):
    """A webhook route. Channel settings now live in the JSON `config` column
    rather than a column per setting."""
    cfg = {"url": "https://example.invalid/hook", "method": "POST", "include_full_report": False}
    cfg.update(config or {})
    base = dict(
        id=1,
        name="SOC webhook",
        channel="webhook",
        destination="",
        format_template=None,
        config=json.dumps(cfg),
        shuffle_integration_id=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _shuffle_route(config=None, **over):
    cfg = {"app_id": "app-uuid", "app_name": "Slack"}
    cfg.update(config or {})
    base = dict(
        id=2,
        name="SOC slack",
        channel="shuffle",
        destination="#soc-alerts",
        format_template=None,
        config=json.dumps(cfg),
        shuffle_integration_id=7,
    )
    base.update(over)
    return SimpleNamespace(**base)


# ── registry ──────────────────────────────────────────────────────────────


def test_registry_contains_the_shipped_channels():
    assert sorted(channel_keys()) == ["resend", "shuffle", "webhook"]


@pytest.mark.parametrize("key", ["resend", "shuffle", "webhook"])
def test_every_provider_declares_the_required_classvars(key):
    provider = CHANNEL_REGISTRY[key]
    assert isinstance(provider, ChannelProvider)
    assert provider.key == key
    assert provider.display_name


def test_registry_key_matches_provider_key():
    """A mismatch would make a route dispatch through the wrong provider."""
    for key, provider in CHANNEL_REGISTRY.items():
        assert key == provider.key


def test_unknown_channel_returns_none_rather_than_raising():
    """The dispatch loop records an unsupported channel as a per-route failure;
    raising here would abort the whole batch instead."""
    assert get_channel("carrier-pigeon") is None


# ── webhook: the payload is an external contract ──────────────────────────


def _run_webhook(route, req=None, report=None):
    """Invoke the webhook provider with the HTTP dispatcher stubbed, returning
    the kwargs it was called with."""
    event = event_from_dispatch_request(req or _request())
    sent = AsyncMock(return_value=("sent", None, 12, None))
    with (
        patch.object(webhook_mod, "dispatch_webhook", sent),
        patch.object(webhook_mod, "build_full_report", AsyncMock(return_value=report)),
    ):
        result = asyncio.run(
            CHANNEL_REGISTRY["webhook"].send(
                route=route,
                event=event,
                rendered_body="RENDERED BODY",
                ctx=_ctx(event),
            ),
        )
    return result, (sent.await_args.kwargs if sent.await_args else None)


def test_webhook_structured_payload_is_unchanged():
    """Exact field set and values — customers' automation reads these names."""
    _result, kwargs = _run_webhook(_webhook_route())

    assert kwargs["structured_payload"] == {
        "customer_code": CUSTOMER,
        "alert_id": 42,
        "alert_name": "Mimikatz signature",
        "severity": "Critical",
        "summary": "Credential dumping observed on WKSTN-04.",
        "report_url": "https://copilot.invalid/alerts/42",
        "text": "RENDERED BODY",
    }


def test_webhook_preserves_none_for_absent_optional_fields():
    """`alert_name` and `report_url` must stay None in the payload, not "".

    Template substitution renders them as empty strings; the JSON payload keeps
    them null. Collapsing the two would change what downstream automation sees.
    """
    _result, kwargs = _run_webhook(_webhook_route(), req=_request(alert_name=None, report_url=None))

    assert kwargs["structured_payload"]["alert_name"] is None
    assert kwargs["structured_payload"]["report_url"] is None


def test_webhook_defaults_method_to_post():
    _result, kwargs = _run_webhook(_webhook_route(config={"method": "POST"}))
    assert kwargs["method"] == "POST"


def test_webhook_missing_url_fails_with_the_original_message():
    result, kwargs = _run_webhook(_webhook_route(config={"url": None}))
    assert result.status == "failed"
    assert result.error_message == "Route config has no url (data integrity issue)"
    assert kwargs is None, "must not attempt delivery"


def test_webhook_include_full_report_merges_flat_and_ignores_template():
    report = {"report_id": 9, "recommended_actions": "isolate", "iocs": []}
    _result, kwargs = _run_webhook(
        _webhook_route(config={"include_full_report": True}, format_template="ignored {{summary}}"),
        report=report,
    )

    assert kwargs["structured_payload"]["report_id"] == 9
    assert kwargs["structured_payload"]["recommended_actions"] == "isolate"
    assert kwargs["rendered_template"] is None, "include_full_report takes precedence over a template"


def test_webhook_missing_report_still_sends_base_payload():
    """A dispatch must not fail just because report write-back hasn't landed."""
    _result, kwargs = _run_webhook(_webhook_route(config={"include_full_report": True}), report=None)

    assert "report_id" not in kwargs["structured_payload"]
    assert kwargs["structured_payload"]["summary"] == "Credential dumping observed on WKSTN-04."


def test_webhook_template_body_passes_through_untouched_without_the_token():
    """The provider only rewrites the {{report}} token; everything else in the
    already-rendered body is left alone."""
    _result, kwargs = _run_webhook(
        _webhook_route(format_template="see something"),
        report={"report_id": 9, "iocs": []},
    )
    assert kwargs["rendered_template"] == "RENDERED BODY"


def test_webhook_template_report_token_substitutes_when_present_in_body():
    report = {"report_id": 9, "iocs": []}
    event = event_from_dispatch_request(_request())
    sent = AsyncMock(return_value=("sent", None, 12, None))
    with (
        patch.object(webhook_mod, "dispatch_webhook", sent),
        patch.object(webhook_mod, "build_full_report", AsyncMock(return_value=report)),
    ):
        asyncio.run(
            CHANNEL_REGISTRY["webhook"].send(
                route=_webhook_route(format_template="x"),
                event=event,
                rendered_body="prefix {{report}} suffix",
                ctx=_ctx(event),
            ),
        )
    assert sent.await_args.kwargs["rendered_template"] == f"prefix {json.dumps(report)} suffix"


def test_webhook_headers_come_through_as_a_dict():
    """Headers are a real dict in config, where the legacy column stored a JSON
    string that needed hand-decoding on every read."""
    _result, kwargs = _run_webhook(_webhook_route(config={"headers": {"Authorization": "Bearer x"}}))
    assert kwargs["headers"] == {"Authorization": "Bearer x"}


def test_webhook_absent_headers_are_none():
    _result, kwargs = _run_webhook(_webhook_route())
    assert kwargs["headers"] is None


def test_malformed_config_fails_the_route_rather_than_the_batch():
    """BEHAVIOUR CHANGE from the per-column scheme.

    Malformed `webhook_headers` used to be swallowed — headers became None and
    the dispatch went out anyway. `config` carries the whole channel setup, so
    an unparseable one means we don't know the URL either; sending a
    half-configured request is worse than recording a failure. Config is
    validated at save time now, so reaching this needs a hand-edited row.

    It must still fail only THIS route, not raise into the dispatch loop.
    """
    result, kwargs = _run_webhook(
        _webhook_route(),
    )
    # sanity: the well-formed case succeeds
    assert result.status == "sent"

    broken = _webhook_route()
    broken.config = "{not json"
    result, kwargs = _run_webhook(broken)

    assert result.status == "failed"
    assert "Invalid webhook config" in result.error_message
    assert kwargs is None, "must not attempt delivery on a config we cannot read"


def test_config_with_unknown_key_is_rejected():
    """extra='forbid' — a typo'd key should surface, not silently do nothing."""
    broken = _webhook_route()
    broken.config = json.dumps({"url": "https://x.invalid", "heders": {"a": "b"}})
    result, kwargs = _run_webhook(broken)

    assert result.status == "failed"
    assert kwargs is None


# ── shuffle: statuses and tenancy ─────────────────────────────────────────


def _run_shuffle(route, integration, creds=("https://shuffler.io", "key")):
    event = event_from_dispatch_request(_request())
    session = AsyncMock()
    session.get = AsyncMock(return_value=integration)
    sent = AsyncMock(return_value=("sent", None, 12, "exec-1"))

    creds_mock = AsyncMock(return_value=creds) if not isinstance(creds, Exception) else AsyncMock(side_effect=creds)
    with (
        patch.object(shuffle_mod, "dispatch_shuffle", sent),
        patch.object(shuffle_mod, "get_shuffle_connector", creds_mock),
    ):
        result = asyncio.run(
            CHANNEL_REGISTRY["shuffle"].send(
                route=route,
                event=event,
                rendered_body="RENDERED BODY",
                ctx=_ctx(event, session),
            ),
        )
    return result, (sent.await_args.kwargs if sent.await_args else None)


def _integration(customer_code=CUSTOMER, enabled=True, org_id="org-1"):
    return SimpleNamespace(id=7, customer_code=customer_code, enabled=enabled, shuffle_org_id=org_id)


def test_shuffle_prepends_the_destination_hint():
    """Shuffle's input_text is natural language; the hint tells its app agent
    where to deliver."""
    _result, kwargs = _run_shuffle(_shuffle_route(), _integration())
    assert kwargs["input_text"] == "Send to #soc-alerts: RENDERED BODY"


def test_shuffle_without_destination_sends_the_bare_body():
    _result, kwargs = _run_shuffle(_shuffle_route(destination=""), _integration())
    assert kwargs["input_text"] == "RENDERED BODY"


def test_shuffle_returns_the_execution_id_as_provider_reference():
    result, _kwargs = _run_shuffle(_shuffle_route(), _integration())
    assert result.status == "sent"
    assert result.provider_reference == "exec-1"


def test_shuffle_cross_tenant_integration_is_refused():
    """Defense in depth against a hand-edited row — this is a tenant leak."""
    result, kwargs = _run_shuffle(_shuffle_route(), _integration(customer_code="OTHER_TENANT"))

    assert result.status == "failed"
    assert "belongs to a different customer" in result.error_message
    assert kwargs is None, "must not attempt delivery"


def test_shuffle_missing_integration_is_refused():
    result, kwargs = _run_shuffle(_shuffle_route(), None)
    assert result.status == "failed"
    assert kwargs is None


def test_shuffle_disabled_integration_is_skipped_not_failed():
    """Disabled is an operator choice, not an error — the distinction shows up
    in the dispatch log."""
    result, kwargs = _run_shuffle(_shuffle_route(), _integration(enabled=False))

    assert result.status == "skipped"
    assert result.error_message == "Shuffle integration is disabled"
    assert kwargs is None


def test_shuffle_missing_app_id_fails_with_the_original_message():
    result, _kwargs = _run_shuffle(_shuffle_route(config={"app_id": None}), _integration())
    assert result.status == "failed"
    assert result.error_message == "Route config has no app_id (data integrity issue)"


def test_shuffle_connector_error_surfaces_the_connector_detail():
    """The operator needs the connector's own message, not a generic
    "Dispatcher exception" from the loop's catch-all."""
    exc = HTTPException(status_code=503, detail="Shuffle connector is configured but has no API key set.")
    result, kwargs = _run_shuffle(_shuffle_route(), _integration(), creds=exc)

    assert result.status == "failed"
    assert result.error_message == "Shuffle connector is configured but has no API key set."
    assert kwargs is None


# ── per-dispatch memoization ──────────────────────────────────────────────


def test_connector_is_read_once_across_routes_in_one_dispatch():
    """The pre-refactor loop prefetched Shuffle credentials once per dispatch
    call. DispatchContext.memoize replaces that prefetch — this pins that a
    batch of Shuffle routes still causes exactly one connector read.
    """
    event = event_from_dispatch_request(_request())
    session = AsyncMock()
    session.get = AsyncMock(return_value=_integration())
    creds = AsyncMock(return_value=("https://shuffler.io", "key"))
    ctx = _ctx(event, session)

    with (
        patch.object(shuffle_mod, "dispatch_shuffle", AsyncMock(return_value=("sent", None, 12, "e"))),
        patch.object(shuffle_mod, "get_shuffle_connector", creds),
    ):
        for _ in range(3):
            asyncio.run(
                CHANNEL_REGISTRY["shuffle"].send(
                    route=_shuffle_route(),
                    event=event,
                    rendered_body="B",
                    ctx=ctx,
                ),
            )

    assert creds.await_count == 1


def test_report_is_read_once_across_routes_in_one_dispatch():
    """Several webhook routes on one alert share a single AI-report read."""
    event = event_from_dispatch_request(_request())
    ctx = _ctx(event)
    build = AsyncMock(return_value={"report_id": 9, "iocs": []})

    with (
        patch.object(webhook_mod, "dispatch_webhook", AsyncMock(return_value=("sent", None, 12, None))),
        patch.object(webhook_mod, "build_full_report", build),
    ):
        for _ in range(3):
            asyncio.run(
                CHANNEL_REGISTRY["webhook"].send(
                    route=_webhook_route(config={"include_full_report": True}),
                    event=event,
                    rendered_body="B",
                    ctx=ctx,
                ),
            )

    assert build.await_count == 1


# ── the envelope ──────────────────────────────────────────────────────────


def test_envelope_maps_every_dispatch_request_field():
    event = event_from_dispatch_request(_request())

    assert event.customer_code == CUSTOMER
    assert event.entity_type == "alert"
    assert event.entity_id == 42
    assert event.alert_id == 42
    assert event.severity == NotificationSeverity.CRITICAL
    assert event.summary == "Credential dumping observed on WKSTN-04."
    assert event.link_url == "https://copilot.invalid/alerts/42"
    assert event.context["alert_name"] == "Mimikatz signature"


def test_envelope_dedupe_key_reproduces_the_existing_idempotency_tuple():
    """#1019 moves idempotency onto this key; it must mean the same thing as
    the current (alert_id, trigger) pair for existing rows."""
    event = event_from_dispatch_request(_request())
    assert event.dedupe_key == "alert:42:investigation_complete"


def test_envelope_keeps_alert_name_none_rather_than_empty():
    event = event_from_dispatch_request(_request(alert_name=None))
    assert event.context["alert_name"] is None
