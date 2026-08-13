"""Named, reusable message templates (#1038).

What's actually at risk here isn't the CRUD — it's the three places this feature
can quietly change what a customer receives:

1. **Precedence.** Inline `format_template` → named template → channel default.
   Every route that existed before #1038 has no `template_id`, so it must render
   byte-for-byte what it rendered yesterday. A precedence bug is invisible in
   tests that only exercise the new path.

2. **Detachment on delete.** The FK has no cascade on purpose. Deleting a
   template must strand the routes' reference, not the routes — losing a
   template is an inconvenience, losing a route is an outage.

3. **`context.*` under StrictUndefined.** The preview renders against a fully
   populated sample event; a real alert often carries a sparse `context`. Under
   strict lookup a template that previews perfectly falls back to the channel
   default in production, which is the worst failure mode available. The
   regression test for that is `test_a_missing_context_key_renders_empty`.

Unit tests with fake sessions — no DB.

Run with: cd backend && python -m pytest tests/test_notification_templates.py
"""

import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.notifications.services.notifications as svc  # noqa: E402
import app.notifications.services.templates as templates_svc  # noqa: E402
from app.notifications.schema.events import EntityType  # noqa: E402
from app.notifications.schema.events import NotificationEvent  # noqa: E402
from app.notifications.schema.notifications import DISPATCH_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import (  # noqa: E402
    NotificationTemplateUpdate,
)
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.rendering import render  # noqa: E402
from app.notifications.services.template_seeds import BUILTIN_TEMPLATES  # noqa: E402
from app.notifications.services.templates import _FALLBACK_BRANDING  # noqa: E402
from app.notifications.services.templates import sample_event  # noqa: E402

CUSTOMER = "ACME"


def _event(**over):
    base = dict(
        customer_code=CUSTOMER,
        trigger=NotificationTrigger.ALERT_CREATED,
        severity=NotificationSeverity.HIGH,
        subject="Mimikatz signature",
        summary="Credential dumping detected.",
        entity_type=EntityType.ALERT,
        entity_id=42,
        dedupe_key="k",
        link_url="https://copilot.invalid/42",
        assignee_username=None,
        actor_username=None,
        context={"alert_name": "Mimikatz signature", "asset_name": "SRV-01"},
    )
    base.update(over)
    return NotificationEvent(**base)


def _route(channel="webhook", **over):
    base = dict(
        id=1,
        name="a route",
        channel=channel,
        scope="customer",
        customer_code=CUSTOMER,
        enabled=True,
        trigger="alert_created",
        min_severity="Informational",
        destination="",
        format_template=None,
        template_id=None,
        config=json.dumps({"url": "https://example.invalid/hook"}),
        shuffle_integration_id=None,
        notify_on_self_assign=False,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _template(**over):
    base = dict(
        id=7,
        name="Shared",
        description=None,
        trigger=None,
        format="text",
        subject_template=None,
        body_template="named: {{ alert_name }}",
        customer_code=None,
        is_default=False,
        created_by="admin",
        updated_at=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _session(first=None, all_=None):
    """A session whose every execute() returns the same scalars result."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = first
    result.scalars.return_value.all.return_value = all_ or []
    result.rowcount = len(all_ or [])
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def _render(route, event, session):
    return asyncio.run(svc._render_body(route, event, session))


# ── precedence ────────────────────────────────────────────────────────────


def test_no_template_at_all_gives_the_channel_default():
    """The pre-#1038 route shape. Must be untouched."""
    session = _session()
    message, err = _render(_route(), _event(), session)

    assert err is None
    assert message.body.startswith("*New alert*")
    assert message.is_custom is False, "the channel default is not operator-authored"
    assert session.execute.await_count == 0, "a route with no template_id must not hit the DB"


def test_an_inline_template_wins_over_the_named_one():
    """The inline field stays a per-route override so one route can deviate
    without forking the shared template."""
    session = _session(first=_template(body_template="NAMED"))
    route = _route(format_template="INLINE {{ alert_name }}", template_id=7)

    message, err = _render(route, _event(), session)

    assert err is None
    assert message.body == "INLINE Mimikatz signature"
    assert session.execute.await_count == 0, "the named template must not even be fetched"


def test_a_named_template_is_used_when_there_is_no_inline_one():
    session = _session(first=_template())
    message, err = _render(_route(template_id=7), _event(), session)

    assert err is None
    assert message.body == "named: Mimikatz signature"
    assert message.is_custom is True


def test_a_dangling_template_reference_falls_back_rather_than_failing():
    """A template deleted out from under a route (or a stale id) must not stop
    the notification."""
    session = _session(first=None)
    message, err = _render(_route(template_id=999), _event(), session)

    assert err is None
    assert message.body.startswith("*New alert*")


def test_a_broken_named_template_degrades_to_the_default_and_says_so():
    session = _session(first=_template(body_template="{{ nope }}"))
    message, err = _render(_route(template_id=7), _event(), session)

    assert message.body.startswith("*New alert*"), "a broken template must not drop the notification"
    assert err is not None and "nope" in err
    assert message.is_custom is False


# ── subject and format ────────────────────────────────────────────────────


def test_a_template_subject_reaches_the_message():
    session = _session(first=_template(subject_template="{{ severity }} — {{ alert_name }}"))
    message, _err = _render(_route(template_id=7), _event(), session)

    assert message.subject == "High — Mimikatz signature"


def test_a_multiline_subject_is_collapsed_to_one_line():
    """A newline in a subject would produce a header-shaped string."""
    session = _session(first=_template(subject_template="line one\nline two"))
    message, _err = _render(_route(template_id=7), _event(), session)

    assert message.subject == "line one line two"


def test_no_subject_template_leaves_the_provider_to_compose_one():
    session = _session(first=_template())
    message, _err = _render(_route(template_id=7), _event(), session)

    assert message.subject is None


def test_the_declared_format_travels_with_the_message():
    session = _session(first=_template(format="html", body_template="<p>{{ alert_name }}</p>"))
    message, _err = _render(_route(channel="resend", template_id=7), _event(), session)

    assert message.format == "html"


def test_html_templates_autoescape():
    """Only the HTML format escapes — doing it globally would turn every `&` in
    a Slack message into `&amp;`."""
    session = _session(first=_template(format="html", body_template="<p>{{ alert_name }}</p>"))
    event = _event(context={"alert_name": "<script>x</script>"})
    message, err = _render(_route(channel="resend", template_id=7), event, session)

    assert err is None
    assert "<script>" not in message.body
    assert "&lt;script&gt;" in message.body


def test_text_templates_do_not_escape():
    session = _session(first=_template(body_template="{{ alert_name }}"))
    event = _event(context={"alert_name": "A & B"})
    message, _err = _render(_route(template_id=7), event, session)

    assert message.body == "A & B"


# ── branding ──────────────────────────────────────────────────────────────


def test_branding_is_not_resolved_unless_the_template_asks_for_it():
    """The lookup is a DB read on the ingest hot path; skipping it for the
    common plain-text template is the whole point of the substring check."""
    session = _session(first=_template(body_template="plain body, no theming"))
    calls = []

    async def _spy(customer_code, sess):
        calls.append(customer_code)
        return dict(_FALLBACK_BRANDING)

    original = svc.build_branding_context
    svc.build_branding_context = _spy
    try:
        _render(_route(template_id=7), _event(), session)
    finally:
        svc.build_branding_context = original

    assert calls == []


def test_branding_is_resolved_when_the_template_references_it():
    session = _session(first=_template(body_template="{{ branding.title }}"))
    calls = []

    async def _spy(customer_code, sess):
        calls.append(customer_code)
        return {**_FALLBACK_BRANDING, "title": "Acme Security"}

    original = svc.build_branding_context
    svc.build_branding_context = _spy
    try:
        message, err = _render(_route(template_id=7), _event(), session)
    finally:
        svc.build_branding_context = original

    assert err is None
    assert calls == [CUSTOMER]
    assert message.body == "Acme Security"


def test_branding_never_shadows_an_event_variable():
    """A branding key colliding with `severity` must not change what an existing
    template means."""

    async def _spy(customer_code, sess):
        # A full theme plus a key that collides with an event variable.
        return {**_FALLBACK_BRANDING, "severity": "Informational"}

    # `branding` appears in the source, so the lookup runs.
    session = _session(first=_template(body_template="{{ severity }}{{ branding.title }}"))
    original = svc.build_branding_context
    svc.build_branding_context = _spy
    try:
        message, _err = _render(_route(template_id=7), _event(), session)
    finally:
        svc.build_branding_context = original

    assert message.body.startswith("High")


# ── the StrictUndefined trap ──────────────────────────────────────────────


def test_a_missing_context_key_renders_empty():
    """The regression this feature would otherwise have shipped.

    `context` is a free-form per-event bag: `asset_name` is present on one alert
    and absent on the next. Under strict lookup a template guarding on it renders
    fine against the fully-populated preview event and then falls back to the
    channel default on a sparse real one — passing preview while silently
    degrading in production.
    """
    sparse = _event(context={})
    out = render("[{% if context.asset_name %}{{ context.asset_name }}{% endif %}]", sparse)
    assert out == "[]"


def test_a_missing_top_level_variable_still_raises():
    """Strictness stays where it belongs: the top-level names are a fixed
    contract, and a typo in one is a bug worth failing on."""
    with pytest.raises(Exception) as exc:
        render("{{ summry }}", _event())
    assert "summry" in str(exc.value)


def test_rendering_does_not_mutate_the_event_context():
    """The defaultdict inserts on read; it must be a copy."""
    event = _event(context={"alert_name": "x"})
    render("{{ context.nothing_here }}", event)
    assert event.context == {"alert_name": "x"}


# ── built-in seeds ────────────────────────────────────────────────────────

#: Built-ins that the dispatch loop can actually render.
#:
#: #999 reuses this table as a second event source: the temporary-password
#: built-in is scoped to a trigger nothing dispatches, and its variables
#: (`user_name`, `temp_password`) are extras its own sender supplies, not fields
#: on a `NotificationEvent`. Rendering it against an alert event would fail
#: under StrictUndefined and prove nothing — it has its own coverage in
#: tests/test_temp_password_email.py. Filtering by DISPATCH_TRIGGERS rather than
#: by name means a future non-dispatch built-in is excluded automatically.
DISPATCHABLE_BUILTINS = [s for s in BUILTIN_TEMPLATES if s["trigger"] is None or s["trigger"] in {t.value for t in DISPATCH_TRIGGERS}]


@pytest.mark.parametrize("spec", DISPATCHABLE_BUILTINS, ids=lambda s: s["name"])
def test_every_builtin_renders_against_a_populated_event(spec):
    event = sample_event(spec["trigger"] or "alert_created", CUSTOMER)
    extra = {"branding": dict(_FALLBACK_BRANDING)}
    for field in ("body_template", "subject_template"):
        if spec[field]:
            render(spec[field], event, autoescape=spec["format"] == "html", extra_context=extra)


@pytest.mark.parametrize("spec", DISPATCHABLE_BUILTINS, ids=lambda s: s["name"])
def test_every_builtin_renders_against_a_bare_event(spec):
    """The case the sample event hides: empty context, no link, no assignee."""
    bare = _event(
        subject="",
        summary="",
        link_url=None,
        context={},
        trigger=NotificationTrigger(spec["trigger"]) if spec["trigger"] else NotificationTrigger.ALERT_CREATED,
    )
    extra = {"branding": dict(_FALLBACK_BRANDING)}
    for field in ("body_template", "subject_template"):
        if spec[field]:
            render(spec[field], bare, autoescape=spec["format"] == "html", extra_context=extra)


def test_builtin_names_are_unique():
    """Seeding is idempotent by name; duplicates would insert forever."""
    names = [s["name"] for s in BUILTIN_TEMPLATES]
    assert len(names) == len(set(names))


def test_html_builtins_are_only_offered_to_channels_that_render_html():
    from app.notifications.channels import CHANNEL_REGISTRY

    for spec in BUILTIN_TEMPLATES:
        if spec["format"] != "html":
            continue
        accepting = [k for k, p in CHANNEL_REGISTRY.items() if "html" in p.template_formats]
        assert accepting == ["resend"], "a chat card would show the markup"


# ── compatibility rules ───────────────────────────────────────────────────


def _assert_usable(template, **route_props):
    props = dict(channel="webhook", trigger="alert_created", customer_code=CUSTOMER)
    props.update(route_props)
    return asyncio.run(
        templates_svc.assert_template_usable(template.id, session=_session(first=template), **props),
    )


def test_a_shared_template_works_anywhere():
    _assert_usable(_template())


def test_a_customer_scoped_template_is_refused_on_another_customers_route():
    with pytest.raises(HTTPException) as exc:
        _assert_usable(_template(customer_code="OTHER"))
    assert exc.value.status_code == 400
    assert "OTHER" in exc.value.detail


def test_a_customer_scoped_template_is_refused_on_an_internal_route():
    """It would render one customer's branding into a message going to the SOC."""
    with pytest.raises(HTTPException) as exc:
        _assert_usable(_template(customer_code="OTHER"), customer_code=None)
    assert exc.value.status_code == 400
    assert "internal route" in exc.value.detail


def test_a_trigger_scoped_template_is_refused_on_a_different_trigger():
    with pytest.raises(HTTPException) as exc:
        _assert_usable(_template(trigger="alert_assigned"))
    assert exc.value.status_code == 400
    assert "alert_assigned" in exc.value.detail


def test_an_html_template_is_refused_on_a_chat_channel():
    with pytest.raises(HTTPException) as exc:
        _assert_usable(_template(format="html"), channel="teams")
    assert exc.value.status_code == 400


def test_an_html_template_is_accepted_on_email():
    _assert_usable(_template(format="html"), channel="resend")


# ── lifecycle ─────────────────────────────────────────────────────────────


def test_deleting_a_template_detaches_routes_rather_than_deleting_them():
    """The FK has no cascade on purpose: losing a template is an inconvenience,
    losing a route is an outage."""
    session = _session(first=_template())
    session.execute.return_value.rowcount = 3

    detached = asyncio.run(templates_svc.delete_template(7, session))

    assert detached == 3
    session.delete.assert_awaited_once()
    # The UPDATE that clears the reference, not a DELETE against routes.
    statements = [str(c.args[0]) for c in session.execute.await_args_list]
    assert any("UPDATE customer_notification_route" in s for s in statements)
    assert not any("DELETE FROM customer_notification_route" in s for s in statements)


def test_builtin_templates_cannot_be_deleted():
    session = _session(first=_template(is_default=True))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(templates_svc.delete_template(7, session))
    assert exc.value.status_code == 400
    session.delete.assert_not_awaited()


def test_builtin_templates_cannot_be_edited():
    """The next startup would recreate them anyway; the UI offers Duplicate."""
    session = _session(first=_template(is_default=True))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(templates_svc.update_template(7, NotificationTemplateUpdate(name="mine"), session))
    assert exc.value.status_code == 400
    assert "Duplicate" in exc.value.detail


def test_malformed_jinja_is_rejected_at_save_time():
    session = _session(first=_template())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(templates_svc.update_template(7, NotificationTemplateUpdate(body_template="{% if %}"), session))
    assert exc.value.status_code == 400
    assert "not valid Jinja" in exc.value.detail


def test_an_edit_that_would_break_an_attached_route_is_refused():
    """Otherwise the attach-time compatibility check only holds until the first
    edit."""
    template = _template()
    attached = _route(channel="teams", name="Teams SOC")
    session = _session(first=template, all_=[attached])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(templates_svc.update_template(7, NotificationTemplateUpdate(format="html"), session))

    assert exc.value.status_code == 400
    assert "Teams SOC" in exc.value.detail
    session.commit.assert_not_awaited()


def test_an_edit_that_breaks_nothing_goes_through():
    session = _session(first=_template(), all_=[_route()])
    asyncio.run(templates_svc.update_template(7, NotificationTemplateUpdate(name="Renamed"), session))
    session.commit.assert_awaited()


# ── preview ───────────────────────────────────────────────────────────────


def _preview(**over):
    from app.notifications.schema.notifications import TemplatePreviewRequest

    base = dict(body_template="{{ alert_name }}", customer_code=CUSTOMER)
    base.update(over)
    return asyncio.run(templates_svc.preview(TemplatePreviewRequest(**base), _session()))


def test_preview_renders_against_a_populated_sample():
    assert _preview()["body"] == "Suspicious PowerShell execution on WKSTN-014"


def test_preview_returns_errors_rather_than_raising():
    """The editor shows the error beside the template being written; a 400 would
    clear the form."""
    result = _preview(body_template="{{ nope }}")
    assert result["error"] is not None
    assert result["body"] == ""


def test_preview_renders_the_subject_too():
    result = _preview(subject_template="{{ severity }}!")
    assert result["subject"] == "High!"


def test_preview_populates_assignment_variables_for_any_trigger():
    """So a half-written template referencing {{assignee}} previews instead of
    looking broken."""
    assert _preview(body_template="{{ assignee }}")["body"] == "jdoe"
