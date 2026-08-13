"""Jinja rendering for notification message bodies.

Replaces `str.replace()` token substitution. Three things this file exists to
hold, in order of how badly they'd hurt:

1. **The sandbox holds.** These templates are operator-authored and stored in
   the database — untrusted input by definition. Plain `jinja2.Environment`
   allows attribute traversal that reaches Python internals and, from there,
   code execution (GHSA-7q83-228r-wfh5).
2. **Existing templates still render identically.** Anything written against the
   old substitution renderer must keep working byte-for-byte.
3. **A broken template never costs a notification.** It degrades to the channel
   default and says why.

Run with: cd backend && python -m pytest tests/test_notification_template_rendering.py
"""

import os

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from jinja2 import TemplateError  # noqa: E402

from app.notifications.schema.events import NotificationEvent  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services import rendering  # noqa: E402

CUSTOMER = "TENANT_A"


def _event(**over):
    base = dict(
        customer_code=CUSTOMER,
        trigger=NotificationTrigger.INVESTIGATION_COMPLETE,
        severity=NotificationSeverity.CRITICAL,
        subject="Mimikatz signature",
        summary="Credential dumping observed on WKSTN-04.",
        entity_type="alert",
        entity_id=42,
        dedupe_key="alert:42:investigation_complete",
        link_url="https://copilot.invalid/alerts/42",
        context={"alert_name": "Mimikatz signature", "iocs": ["1.2.3.4", "evil.example"]},
    )
    base.update(over)
    return NotificationEvent(**base)


def _render(tpl, event=None, **kw):
    return rendering.render(tpl, event or _event(), **kw)


# ── the sandbox ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "attack",
    [
        "{{ ''.__class__ }}",
        "{{ ''.__class__.__mro__ }}",
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
        "{{ event.__class__.__init__.__globals__ }}",
        "{{ self.__init__.__globals__ }}",
        "{{ ''.__class__.__base__.__subclasses__() }}",
        "{{ cycler.__init__.__globals__.os }}",
    ],
    ids=lambda a: a[:34],
)
def test_sandbox_blocks_attribute_traversal_to_internals(attack):
    """Each of these is a documented route from a template to arbitrary code
    execution in an unsandboxed Jinja environment."""
    with pytest.raises(Exception) as exc:
        _render(attack)
    # Either the sandbox refuses the attribute, or the name doesn't exist.
    assert exc.type is not AssertionError


def test_a_template_cannot_reach_os():
    with pytest.raises(Exception):
        _render("{{ ''.__class__.__mro__[1].__subclasses__()[0].__init__.__globals__['os'].system('id') }}")


# ── backward compatibility ────────────────────────────────────────────────


def test_every_original_token_still_resolves():
    """These are the six the string-substitution renderer supported. A stored
    template using them must keep working."""
    tpl = "{{customer_code}}|{{alert_id}}|{{alert_name}}|{{severity}}|{{summary}}|{{report_url}}"
    out = _render(tpl)
    assert out == ("TENANT_A|42|Mimikatz signature|Critical|Credential dumping observed on WKSTN-04.|https://copilot.invalid/alerts/42")


def test_tokens_added_with_the_envelope_resolve():
    out = _render("{{assignee}}|{{actor}}|{{entity_type}}|{{entity_id}}", _event(assignee_username="bob", actor_username="alice"))
    assert out == "bob|alice|alert|42"


def test_absent_optional_values_render_empty_not_none():
    """The old renderer substituted "" for a missing value. Rendering the string
    "None" into a customer's Slack message would be a visible regression."""
    out = _render("[{{assignee}}][{{report_url}}]", _event(assignee_username=None, link_url=None))
    assert out == "[][]"


# ── what Jinja adds ───────────────────────────────────────────────────────


def test_conditionals_work():
    tpl = "{% if severity == 'Critical' %}PAGE{% else %}queue{% endif %}"
    assert _render(tpl) == "PAGE"
    assert _render(tpl, _event(severity=NotificationSeverity.LOW)) == "queue"


def test_loops_over_the_event_context_work():
    """The motivating case: listing an alert's IOCs, impossible before."""
    out = _render("{% for i in event.context.iocs %}- {{ i }}\n{% endfor %}")
    assert out == "- 1.2.3.4\n- evil.example\n"


def test_filters_work():
    assert _render("{{ severity | upper }}") == "CRITICAL"


def test_the_whole_envelope_is_reachable():
    assert _render("{{ event.trigger.value }}") == "investigation_complete"


# ── failure handling ──────────────────────────────────────────────────────


def test_compile_rejects_malformed_syntax():
    with pytest.raises(TemplateError):
        rendering.compile_template("{% for x in y %}{{ x }}")


def test_compile_accepts_a_valid_template():
    rendering.compile_template("{% if severity %}{{ summary }}{% endif %}")


def test_render_body_returns_the_output_and_no_error_on_success():
    body, err = rendering.render_body("{{severity}}", _event(), "FALLBACK")
    assert (body, err) == ("Critical", None)


def test_render_body_falls_back_when_the_template_raises():
    """A broken template must never cost a notification."""
    body, err = rendering.render_body("{{ nonexistent_variable }}", _event(), "FALLBACK")

    assert body == "FALLBACK"
    assert err and "render failed" in err


def test_render_body_uses_the_fallback_when_no_template_is_set():
    body, err = rendering.render_body(None, _event(), "FALLBACK")
    assert (body, err) == ("FALLBACK", None)


def test_an_unknown_token_is_now_loud_rather_than_literal():
    """BEHAVIOUR CHANGE from string substitution.

    `{{foo}}` used to survive into the output as a literal. Under
    StrictUndefined it raises, and the route sends the channel default with the
    reason recorded. Louder, and deliberately so — a message containing a raw
    `{{foo}}` was already broken, just silently.
    """
    body, err = rendering.render_body("Hello {{foo}}", _event(), "FALLBACK")
    assert body == "FALLBACK"
    assert err is not None


# ── the size cap ──────────────────────────────────────────────────────────


#: Under the sandbox's own MAX_RANGE (100_000), but 20 bytes per iteration puts
#: the output at ~2 MB — well past the 64 KB cap.
_RUNAWAY = "{% for i in range(99000) %}xxxxxxxxxxxxxxxxxxxx{% endfor %}"


def test_a_runaway_loop_is_rejected_rather_than_sent():
    with pytest.raises(rendering.TemplateTooLargeError):
        _render(_RUNAWAY)


def test_an_oversized_template_falls_back_rather_than_raising():
    body, err = rendering.render_body(_RUNAWAY, _event(), "FALLBACK")
    assert body == "FALLBACK"
    assert err and "TemplateTooLarge" in err


def test_the_sandbox_caps_range_before_we_even_get_there():
    """Defence in depth: Jinja's sandbox refuses range() above 100_000 itself,
    so the most obvious runaway never allocates at all. Our cap catches the
    cases it doesn't — nested loops, huge string multiplication.

    OverflowError is not a TemplateError, so this also exercises render_body's
    catch-all: an operator still gets a notification.
    """
    body, err = rendering.render_body("{% for i in range(500000) %}x{% endfor %}", _event(), "FALLBACK")
    assert body == "FALLBACK"
    assert err and "OverflowError" in err


def test_a_normal_body_is_unaffected_by_the_cap():
    body, err = rendering.render_body("{{summary}}", _event(), "FALLBACK")
    assert err is None


# ── escaping ──────────────────────────────────────────────────────────────


def test_autoescape_is_off_by_default():
    """A notification body is plain text or markdown far more often than HTML;
    escaping would turn every & into &amp; in a Slack message."""
    out = _render("{{ summary }}", _event(summary="a & b < c"))
    assert out == "a & b < c"


def test_autoescape_can_be_turned_on_for_html():
    out = _render("{{ summary }}", _event(summary="a & b < c"), autoescape=True)
    assert "&amp;" in out and "&lt;" in out


def test_render_json_rejects_output_that_is_not_valid_json():
    """Catches the common mistake of an unquoted substitution."""
    with pytest.raises(TemplateError):
        rendering.render_json('{"text": {{ summary }}}', _event())


def test_render_json_accepts_a_correctly_quoted_template():
    out = rendering.render_json('{"text": {{ summary | tojson }}}', _event())
    assert '"text"' in out
