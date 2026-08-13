"""Custom HTML templates for the temporary-password email (#999).

The CRUD is not what's at risk here — the templates are ordinary
`notification_template` rows that #1038 already covers. What this feature can
get wrong is narrower and much worse:

1. **Resolution order.** Customer-scoped beats shared beats built-in, and
   another tenant's template must never be reachable. Selection is not stored
   anywhere, so if the ordering drifts an operator's customer-specific template
   silently stops being used and nobody finds out — the email still sends.

2. **Trigger isolation.** `list_templates` treats a NULL trigger as "usable
   anywhere", which is right for routes and catastrophic here: it would offer
   "Alert — concise" as someone's password email. This path requires an exact
   trigger match, in both directions.

3. **No password in a preview.** Previewing must not rotate a credential, and
   the rendered body must never carry a real one.

4. **The plaintext part.** HTML emails go out multipart because some corporate
   gateways strip HTML from mail carrying credentials. If the text alternative
   loses the password, those recipients get an unusable email.

5. **Render-before-rotate.** A template that fails to render must leave the
   user's existing password working — the ordering in the route is the whole
   guarantee, and it is easy to "tidy" back into rotate-then-render.

Unit tests with fake sessions — no DB.

Run with: cd backend && python -m pytest tests/test_temp_password_email.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.auth.services.temp_password_email as tpe  # noqa: E402
from app.notifications.schema.notifications import DISPATCH_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import NotificationRouteUpdate  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.rendering import render  # noqa: E402
from app.notifications.services.template_seeds import BUILTIN_TEMPLATES  # noqa: E402

CUSTOMER = "ACME"
OTHER = "GLOBEX"


def _template(id, *, customer_code=None, is_default=False, trigger=tpe.TEMPLATE_TRIGGER, fmt="html", **over):
    base = dict(
        id=id,
        name=f"template-{id}",
        description=None,
        trigger=trigger,
        format=fmt,
        subject_template="Password for {{ user_name }}",
        body_template="<p>{{ user_name }}: {{ temp_password }}</p>",
        customer_code=customer_code,
        is_default=is_default,
        updated_at=None,
        created_at=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _session(all_=None, first=None):
    """A session whose every execute() returns the same scalars result."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = all_ or []
    result.scalars.return_value.first.return_value = first
    session.execute = AsyncMock(return_value=result)
    return session


def _run(coro):
    # `asyncio.run`, not `get_event_loop().run_until_complete`: the latter picks
    # up whatever loop the rest of the suite left behind and fails once these
    # tests run alongside the others rather than on their own.
    return asyncio.run(coro)


# ── Resolution order ─────────────────────────────────────────────────────────


def test_customer_scoped_template_beats_shared_and_builtin():
    """The whole selection model is this ordering. There is no stored default."""
    rows = [_template(1, is_default=True), _template(2), _template(3, customer_code=CUSTOMER)]
    resolved = _run(tpe.resolve_template(_session(all_=rows), CUSTOMER))
    assert resolved.id == 3


def test_operator_shared_template_beats_the_builtin():
    """A deployment that wrote its own shared wording must not keep getting ours."""
    rows = [_template(1, is_default=True), _template(2)]
    resolved = _run(tpe.resolve_template(_session(all_=rows), CUSTOMER))
    assert resolved.id == 2


def test_builtin_is_used_when_nothing_else_exists():
    rows = [_template(1, is_default=True)]
    assert _run(tpe.resolve_template(_session(all_=rows), CUSTOMER)).id == 1


def test_no_templates_resolves_to_none_not_an_error():
    """None means the pre-#999 plaintext body, which must stay a working path."""
    assert _run(tpe.resolve_template(_session(all_=[]), CUSTOMER)) is None


def test_another_customers_template_is_never_offered_or_resolved():
    """A cross-tenant leak here would put GLOBEX's branding and support contact
    in an ACME user's credentials email."""
    rows = [_template(9, customer_code=OTHER)]
    assert _run(tpe.list_available_templates(_session(all_=rows), CUSTOMER)) == []
    assert _run(tpe.resolve_template(_session(all_=rows), CUSTOMER)) is None


def test_the_picker_order_matches_what_resolution_would_pick():
    """The dialog preselects `resolved_template_id` and shows this list. If the
    two orderings ever disagreed, the admin would see one default and get
    another."""
    rows = [_template(1, is_default=True), _template(2), _template(3, customer_code=CUSTOMER)]
    listed = _run(tpe.list_available_templates(_session(all_=rows), CUSTOMER))
    resolved = _run(tpe.resolve_template(_session(all_=rows), CUSTOMER))
    assert listed[0].id == resolved.id


# ── Trigger and scope isolation on an explicit override ──────────────────────


def test_an_alert_template_cannot_be_forced_by_id():
    """`list_templates` would happily return a NULL-trigger template here. This
    path must not."""
    row = _template(5, trigger="alert_created")
    with pytest.raises(HTTPException) as e:
        _run(tpe.resolve_template(_session(first=row), CUSTOMER, template_id=5))
    assert e.value.status_code == 400
    assert "not a temporary-password email template" in e.value.detail


def test_a_trigger_agnostic_template_cannot_be_forced_by_id():
    row = _template(5, trigger=None)
    with pytest.raises(HTTPException):
        _run(tpe.resolve_template(_session(first=row), CUSTOMER, template_id=5))


def test_another_customers_template_cannot_be_forced_by_id():
    row = _template(5, customer_code=OTHER)
    with pytest.raises(HTTPException) as e:
        _run(tpe.resolve_template(_session(first=row), CUSTOMER, template_id=5))
    assert "GLOBEX" in e.value.detail


def test_a_json_template_cannot_be_forced_by_id():
    """`json` is a legal template format but cannot be an email body."""
    row = _template(5, fmt="json")
    with pytest.raises(HTTPException) as e:
        _run(tpe.resolve_template(_session(first=row), CUSTOMER, template_id=5))
    assert e.value.status_code == 400


def test_an_explicit_id_overrides_the_resolved_default():
    """The per-send override is the other half of the selection model."""
    row = _template(7, customer_code=CUSTOMER)
    assert _run(tpe.resolve_template(_session(first=row), CUSTOMER, template_id=7)).id == 7


# ── Customer scoping of the send ─────────────────────────────────────────────


def test_a_customer_the_user_has_no_access_to_is_refused():
    session = _session(all_=[CUSTOMER])
    user = SimpleNamespace(id=1, username="jdoe", email="j@e.com")
    with pytest.raises(HTTPException) as e:
        _run(tpe.resolve_customer_code(session, user, OTHER))
    assert e.value.status_code == 400


def test_a_single_customer_user_resolves_without_being_asked():
    session = _session(all_=[CUSTOMER])
    user = SimpleNamespace(id=1, username="jdoe", email="j@e.com")
    assert _run(tpe.resolve_customer_code(session, user, None)) == CUSTOMER


def test_a_multi_customer_user_resolves_to_none_rather_than_guessing():
    """Picking a winner would render one tenant's branding at a user who belongs
    to both. The shared template is the honest answer."""
    session = _session(all_=[CUSTOMER, OTHER])
    user = SimpleNamespace(id=1, username="jdoe", email="j@e.com")
    assert _run(tpe.resolve_customer_code(session, user, None)) is None


# ── The seeded built-in ──────────────────────────────────────────────────────


def _builtin():
    return next(t for t in BUILTIN_TEMPLATES if t["trigger"] == tpe.TEMPLATE_TRIGGER)


def test_exactly_one_builtin_is_seeded_for_this_trigger():
    """Two would make "the built-in" step of resolution depend on insertion
    order, which is not something an operator can predict or see."""
    seeded = [t for t in BUILTIN_TEMPLATES if t["trigger"] == tpe.TEMPLATE_TRIGGER]
    assert len(seeded) == 1


def test_the_builtin_renders_and_carries_the_password():
    spec = _builtin()
    event = tpe.build_event(username="jdoe", customer_code=CUSTOMER)
    extra = tpe.build_extra_context(
        username="jdoe",
        email="jdoe@example.com",
        temp_password="S3cr3t-Pass",
        customer_code=CUSTOMER,
        customer_name="Acme Corp",
    )
    from app.notifications.services.templates import _FALLBACK_BRANDING

    extra["branding"] = dict(_FALLBACK_BRANDING)

    body = render(spec["body_template"], event, autoescape=True, extra_context=extra)
    subject = render(spec["subject_template"], event, autoescape=True, extra_context=extra)

    assert "S3cr3t-Pass" in body
    assert "jdoe" in body
    assert "Acme Corp" in subject


def test_the_builtin_omits_the_sign_in_button_when_copilot_url_is_unset():
    """COPILOT_URL is optional. An unguarded link would render `href=""`, which
    in a credentials email reads as a broken or spoofed message."""
    spec = _builtin()
    event = tpe.build_event(username="jdoe", customer_code=CUSTOMER)
    from app.notifications.services.templates import _FALLBACK_BRANDING

    extra = tpe.build_extra_context(
        username="jdoe",
        email="jdoe@example.com",
        temp_password="pw",
        customer_code=CUSTOMER,
        customer_name="Acme Corp",
    )
    extra["branding"] = dict(_FALLBACK_BRANDING)
    extra["login_url"] = ""

    body = render(spec["body_template"], event, autoescape=True, extra_context=extra)
    assert "Sign in" not in body


# ── The plaintext alternative ────────────────────────────────────────────────


def test_html_to_text_keeps_the_password():
    """Some corporate gateways strip HTML from mail carrying credentials. If the
    text part loses the password those recipients get an unusable email."""
    html = '<div><p>Hello jdoe,</p><p style="font-family:monospace">S3cr3t-Pass</p></div>'
    assert "S3cr3t-Pass" in tpe.html_to_text(html)


def test_html_to_text_unescapes_entities_a_password_can_contain():
    """Autoescaping turns `&` into `&amp;` in the HTML part. The text part must
    show the character the user actually has to type."""
    html = "<p>pass&amp;word&lt;1&gt;</p>"
    assert tpe.html_to_text(html) == "pass&word<1>"


def test_html_to_text_drops_script_and_style_bodies():
    html = "<style>p{color:red}</style><p>Hello</p><script>alert(1)</script>"
    text = tpe.html_to_text(html)
    assert text == "Hello"


def test_html_to_text_separates_blocks_rather_than_running_them_together():
    assert tpe.html_to_text("<p>one</p><p>two</p>") == "one\ntwo"


# ── Preview safety ───────────────────────────────────────────────────────────


def test_the_preview_password_is_obviously_not_real():
    assert "PREVIEW" in tpe.PREVIEW_PASSWORD


def test_preview_renders_the_placeholder_and_never_a_real_password():
    session = _session()
    user = SimpleNamespace(id=1, username="jdoe", email="jdoe@example.com")
    template = _template(1, body_template="<p>{{ temp_password }}</p>", subject_template=None)

    result = _run(tpe.preview_for_user(session, template=template, user=user, customer_code=CUSTOMER))

    assert result["error"] is None
    assert tpe.PREVIEW_PASSWORD in result["body"]
    assert result["format"] == "html"


def test_preview_returns_a_render_error_instead_of_raising():
    """The admin needs the failure next to the template that caused it; a 400
    that closes the dialog tells them less."""
    session = _session()
    user = SimpleNamespace(id=1, username="jdoe", email="jdoe@example.com")
    template = _template(1, body_template="{{ nope_undefined_variable }}", subject_template=None)

    result = _run(tpe.preview_for_user(session, template=template, user=user, customer_code=CUSTOMER))

    assert result["error"] is not None
    assert result["body"] == ""


def test_preview_with_no_template_shows_the_builtin_plaintext_body():
    """The fallback path has to be inspectable too — it is what a deployment
    with no templates actually sends."""
    session = _session()
    user = SimpleNamespace(id=1, username="jdoe", email="jdoe@example.com")

    result = _run(tpe.preview_for_user(session, template=None, user=user, customer_code=CUSTOMER))

    assert result["format"] == "text"
    assert tpe.PREVIEW_PASSWORD in result["body"]
    assert result["subject"] == tpe.DEFAULT_SUBJECT


# ── Rendering the real email ─────────────────────────────────────────────────


def test_render_email_returns_both_parts_for_an_html_template():
    session = _session()
    subject, text, html = _run(
        tpe.render_email(
            session,
            template=_template(1, body_template="<p>{{ temp_password }}</p>"),
            username="jdoe",
            email="jdoe@example.com",
            temp_password="S3cr3t",
            customer_code=CUSTOMER,
            customer_name="Acme Corp",
        ),
    )
    assert html is not None and "S3cr3t" in html
    assert "S3cr3t" in text
    assert subject == "Password for jdoe"


def test_render_email_sends_no_html_part_for_a_text_template():
    session = _session()
    _, text, html = _run(
        tpe.render_email(
            session,
            template=_template(1, fmt="text", body_template="Password: {{ temp_password }}", subject_template=None),
            username="jdoe",
            email="jdoe@example.com",
            temp_password="S3cr3t",
            customer_code=CUSTOMER,
        ),
    )
    assert html is None
    assert text == "Password: S3cr3t"


def test_a_subject_cannot_smuggle_a_newline_into_the_headers():
    """A rendered value containing CRLF is a header-injection vector and mail
    servers reject or truncate it."""
    session = _session()
    subject, _, _ = _run(
        tpe.render_email(
            session,
            template=_template(1, subject_template="Reset for\n{{ user_name }}\r\nX-Injected: 1"),
            username="jdoe",
            email="jdoe@example.com",
            temp_password="S3cr3t",
            customer_code=CUSTOMER,
        ),
    )
    assert "\n" not in subject and "\r" not in subject


def test_render_email_raises_rather_than_silently_using_the_default_body():
    """The dispatch path falls back so a broken template can't cost a Critical
    alert. Here a silent fallback to English plaintext is the exact outcome a
    customised template exists to prevent — and the caller uses this raise to
    abort BEFORE rotating the password."""
    session = _session()
    with pytest.raises(Exception):
        _run(
            tpe.render_email(
                session,
                template=_template(1, body_template="{{ undefined_thing }}"),
                username="jdoe",
                email="jdoe@example.com",
                temp_password="S3cr3t",
                customer_code=CUSTOMER,
            ),
        )


def test_no_template_renders_the_unchanged_pre_999_body():
    """An operator who authors nothing must see no change at all."""
    from app.auth.services.security_admin import build_temp_password_email

    session = _session()
    subject, text, html = _run(
        tpe.render_email(
            session,
            template=None,
            username="jdoe",
            email="jdoe@example.com",
            temp_password="S3cr3t",
            customer_code=CUSTOMER,
        ),
    )
    assert html is None
    assert text == build_temp_password_email("jdoe", "S3cr3t")
    assert subject == tpe.DEFAULT_SUBJECT


# ── The trigger is a template scope, not a route trigger ─────────────────────


def test_the_temp_password_trigger_is_not_dispatchable():
    assert NotificationTrigger.TEMP_PASSWORD_ISSUED not in DISPATCH_TRIGGERS


def test_a_route_cannot_be_bound_to_the_temp_password_trigger():
    """Nothing emits it into dispatch(), so such a route would be config that
    silently never fires."""
    with pytest.raises(Exception):
        NotificationRouteUpdate(trigger="temp_password_issued")


def test_real_triggers_are_still_accepted_on_a_route():
    assert NotificationRouteUpdate(trigger="alert_created").trigger == NotificationTrigger.ALERT_CREATED


# ── The editor's preview knows this trigger ──────────────────────────────────


def test_the_sample_event_for_this_trigger_is_not_alert_shaped():
    """Previewing a password email against "Suspicious PowerShell execution"
    would be actively misleading."""
    from app.notifications.services.templates import sample_event

    event = sample_event(tpe.TEMPLATE_TRIGGER, CUSTOMER)
    assert event.trigger == NotificationTrigger.TEMP_PASSWORD_ISSUED
    assert event.entity_type == "user"
    assert "PowerShell" not in event.summary
