"""Delivering the AI investigation report through a notification (#1048).

Before this, an investigation's 6–8 KB report was written by Talon, stored,
displayed in CoPilot and exposed to the customer portal — and no delivery
channel could see any of it. Routes sent the 400-character `summary`. Separately,
the manual-send dialog offered an "Include the AI investigation report" checkbox
that was wired only as a permission gate: ticking it could refuse a send, never
add content.

What these tests protect, in rough order of how expensive the regression would
be:

**The lazy guard.** Loading a report is the largest single read the dispatch
loop can perform, and investigations are a minority of alerts. A template that
never mentions `ai_report` must cost zero extra queries — `alert_created` is on
the ingest hot path. `test_a_template_that_never_mentions_the_report_does_not_load_one`
is the one that stops a well-meaning refactor from making every alert pay for a
report nobody asked for.

**Escaping.** Report markdown is LLM-written and reaches an HTML email. The
`html=False` option is not the markdown-it default — both the commonmark and
gfm-like presets ship `html: True` — so an upgrade or a preset change could
silently start passing raw HTML through.

**Tables.** They are not part of CommonMark. Under the wrong preset a GFM table
renders as a run-on paragraph with visible pipes, which looks like working
output. This is the single easiest thing here to get silently wrong, and it is
also the entire reason the feature exists.

**Degradation.** An alert with no report, a report over the render cap, a case
rather than an alert — each must produce a sensible notification or a clear
refusal, never a dropped Critical alert.

Unit tests with fake sessions — no DB.

Run with: cd backend && python -m pytest tests/test_notification_ai_report_delivery.py
"""

import asyncio
import json
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from markupsafe import Markup  # noqa: E402

import app.notifications.services.manual_send as ms  # noqa: E402
import app.notifications.services.notifications as svc  # noqa: E402
from app.notifications.channels.base import DispatchContext  # noqa: E402
from app.notifications.schema.events import EntityType  # noqa: E402
from app.notifications.schema.events import NotificationEvent  # noqa: E402
from app.notifications.schema.notifications import DISPATCH_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.rendering import MAX_RENDERED_BYTES  # noqa: E402
from app.notifications.services.rendering import render_body  # noqa: E402
from app.notifications.services.template_seeds import BUILTIN_TEMPLATES  # noqa: E402
from app.notifications.utils.markdown_html import markdown_to_html  # noqa: E402

CUSTOMER = "ACME"

#: A miniature of a real report: a heading, a GFM table, and inline emphasis.
#: Real ones run 6–8 KB with five or more tables.
REPORT_MD = """# Investigation Report — Alert #14

## Alert Summary
- **Severity:** Medium

| Field | Value | Level |
|---|---|---:|
| Event ID | 4732 | 12 |
| Group | Administrators | 5 |

Confirmed automated red team simulation activity.
"""


def _report(**over):
    base = dict(
        markdown=REPORT_MD,
        html=markdown_to_html(REPORT_MD),
        summary="A local admin was added on agent 025.",
        recommended_actions="Create a suppression rule.",
        severity="Medium",
        created_at=datetime(2026, 8, 3, 21, 37, 15),
        report_id=3,
        iocs=[{"value": "simadmin", "type": "user", "vt_verdict": "suspicious", "vt_score": "", "details": ""}],
        ioc_count=1,
        iocs_truncated=False,
    )
    base.update(over)
    return base


def _event(with_report=False, **over):
    context = {"alert_name": "Administrators Group Changed", "asset_name": "test"}
    if with_report:
        context["ai_report"] = _report()
    base = dict(
        customer_code=CUSTOMER,
        trigger=NotificationTrigger.INVESTIGATION_COMPLETE,
        severity=NotificationSeverity.CRITICAL,
        subject="Administrators Group Changed",
        summary="An AI investigation completed for this alert.",
        entity_type=EntityType.ALERT,
        entity_id=14,
        dedupe_key="alert:14:investigation_complete",
        link_url="https://copilot.invalid/alerts/14",
        context=context,
    )
    base.update(over)
    return NotificationEvent(**base)


def _route(**over):
    base = dict(
        id=1,
        name="Customer email",
        channel="resend",
        scope="customer",
        customer_code=CUSTOMER,
        enabled=True,
        trigger="investigation_complete",
        min_severity="Informational",
        destination="",
        format_template=None,
        template_id=None,
        config=json.dumps({"to": ["soc@acme.example"]}),
        shuffle_integration_id=None,
        notify_on_self_assign=False,
        recipient_mode="static",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _template(**over):
    base = dict(
        id=7,
        name="AI report",
        description=None,
        trigger="investigation_complete",
        format="html",
        subject_template=None,
        body_template="{{ context.ai_report.html }}",
        customer_code=None,
        is_default=False,
        created_by="admin",
        updated_at=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _session(template=None):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = template
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    return session


def _render(route, event, session, ctx=None, loader=None):
    """Render, with the report loader stubbed so no DB is involved.

    Returns (message, template_error, loader_mock).
    """
    loader = loader or AsyncMock(return_value=_report())
    with patch.object(svc, "safe_load_ai_report_context", loader):
        message, err = asyncio.run(svc._render_body(route, event, session, ctx=ctx))
    return message, err, loader


# ── the markdown renderer ─────────────────────────────────────────────────


def test_a_gfm_table_becomes_a_real_html_table():
    """Tables are not in CommonMark. Under the default preset this renders as a
    paragraph full of visible pipes — output that looks like it worked."""
    html = markdown_to_html(REPORT_MD)

    assert "<table" in html
    assert "<th" in html and "<td" in html
    assert "| Field |" not in html, "pipes left in the output mean the table extension is off"


def test_column_alignment_survives():
    """A right-aligned numeric column silently left-aligning is the kind of
    regression a custom render rule introduces."""
    html = markdown_to_html("| n |\n|---:|\n| 12 |")
    assert "text-align:right" in html


def test_raw_html_in_markdown_is_escaped():
    """`html=False` is NOT the markdown-it default — both the commonmark and
    gfm-like presets ship `html: True`. Report markdown is LLM-written and lands
    in an email, so this option is load-bearing rather than defensive."""
    html = markdown_to_html("Normal text <script>alert(1)</script> more")

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_styling_is_inline_because_mail_clients_drop_stylesheets():
    html = markdown_to_html(REPORT_MD)

    assert "<style" not in html, "a stylesheet would be stripped by many clients"
    assert 'style="' in html


def test_the_result_is_markup_so_autoescape_leaves_it_alone():
    """`_render_body` turns autoescape ON for html templates. A plain str would
    reach the recipient as visible &lt;table&gt; tags."""
    assert isinstance(markdown_to_html("# x"), Markup)


def test_empty_markdown_gives_empty_output_not_an_empty_wrapper():
    """So `{% if context.ai_report.html %}` behaves as an author expects."""
    assert markdown_to_html("") == ""
    assert markdown_to_html("   \n  ") == ""


# ── the lazy guard ────────────────────────────────────────────────────────


def test_a_template_that_never_mentions_the_report_does_not_load_one():
    """The hot-path guarantee. `alert_created` fires on every ingested alert and
    almost none of them have an investigation; loading a report speculatively
    would put the largest read in the engine on the busiest path."""
    session = _session(template=_template(body_template="Alert: {{ alert_name }}", format="text"))
    _message, _err, loader = _render(_route(template_id=7), _event(), session)

    assert loader.await_count == 0


def test_a_template_that_mentions_the_report_gets_one():
    session = _session(template=_template())
    message, err, loader = _render(_route(template_id=7), _event(), session)

    assert err is None
    assert loader.await_count == 1
    assert "<table" in message.body


def test_the_subject_template_also_triggers_the_load():
    """The guard reads body and subject together — a report referenced only in
    the subject must still resolve."""
    session = _session(
        template=_template(
            body_template="Static body",
            subject_template="{{ context.ai_report.severity }} finding",
        ),
    )
    message, _err, loader = _render(_route(template_id=7), _event(), session)

    assert loader.await_count == 1
    assert message.subject == "Medium finding"


def test_an_inline_template_can_reach_the_report_too():
    """`include_ai_report` must not depend on which template style a route uses."""
    session = _session()
    message, err, loader = _render(
        _route(format_template="Report: {{ context.ai_report.summary }}"),
        _event(),
        session,
    )

    assert err is None
    assert loader.await_count == 1
    assert "A local admin was added" in message.body


def test_a_case_never_loads_a_report():
    """Investigations belong to alerts. A case-assigned event reaching a
    report-shaped template must not query for one."""
    session = _session(template=_template(body_template="{{ context.ai_report }}", format="text"))
    _message, _err, loader = _render(
        _route(template_id=7),
        _event(entity_type=EntityType.CASE, trigger=NotificationTrigger.CASE_ASSIGNED),
        session,
    )

    assert loader.await_count == 0


def test_an_already_attached_report_is_not_reloaded():
    """Manual send pre-populates the key. Re-querying would be wasted work and
    could disagree with what the preview showed."""
    session = _session(template=_template())
    _message, _err, loader = _render(_route(template_id=7), _event(with_report=True), session)

    assert loader.await_count == 0


def test_two_routes_in_one_dispatch_share_a_single_load():
    """The memo lives on DispatchContext so a customer with an email route and a
    chat route pays for the report once."""
    event = _event()
    ctx = DispatchContext(session=AsyncMock(), event=event)
    loader = AsyncMock(return_value=_report())

    for route_id in (1, 2):
        _render(_route(id=route_id, template_id=7), event, _session(template=_template()), ctx=ctx, loader=loader)

    assert loader.await_count == 1


def test_a_missing_report_renders_without_raising():
    """Most alerts have no investigation. Under StrictUndefined an unguarded
    reference would drop the message to the channel default, so the guard has to
    survive a None."""
    session = _session(template=_template(body_template="{% if context.ai_report %}R{% else %}none{% endif %}", format="text"))
    message, err, _loader = _render(
        _route(template_id=7),
        _event(),
        session,
        loader=AsyncMock(return_value=None),
    )

    assert err is None
    assert message.body == "none"


# ── the channel default body ──────────────────────────────────────────────


def test_the_default_body_is_untouched_without_a_report():
    """Every existing route must render byte-for-byte what it rendered before."""
    session = _session()
    message, err, _loader = _render(_route(), _event(), session)

    assert err is None
    # The strongest available statement: identical to the pre-#1048 formatter,
    # which is still in the tree as `_format_default_body_core`.
    assert message.body == svc._format_default_body_core(_event())
    assert message.format == "text"


def test_the_default_body_carries_the_report_when_one_is_attached():
    """So ticking the checkbox works on a route with no template at all — which
    is exactly the case where an operator most needs it to."""
    session = _session()
    message, _err, _loader = _render(_route(), _event(with_report=True), session)

    assert "Investigation Report" in message.body
    assert "assessed severity: *Medium*" in message.body


def test_a_default_body_with_a_report_is_flagged_markdown():
    """Otherwise the email channel ships the report's tables as pipes. `text`
    stays `text` when there is no report, so nothing else changes."""
    session = _session()
    with_report, _e1, _l1 = _render(_route(), _event(with_report=True), session)
    without, _e2, _l2 = _render(_route(), _event(), _session())

    assert with_report.format == "markdown"
    assert without.format == "text"


# ── the seeded built-in ───────────────────────────────────────────────────


def _full_report_seed():
    return next(t for t in BUILTIN_TEMPLATES if t["name"] == "AI investigation — full report (HTML email)")


def test_the_full_report_builtin_exists_and_is_html():
    seed = _full_report_seed()

    assert seed["format"] == "html"
    assert seed["trigger"] == "investigation_complete"


def test_the_full_report_builtin_renders_the_report():
    seed = _full_report_seed()
    body, err = render_body(
        seed["body_template"],
        _event(with_report=True),
        "FALLBACK",
        autoescape=True,
        extra_context={"branding": {"logo": None, "accent": "#111", "accent_strong": "#222", "accent_text": "#fff", "title": "T"}},
    )

    assert err is None
    assert "<table" in body, "the report's tables must survive Jinja autoescaping"
    assert "&lt;table" not in body, "Markup was lost somewhere and the HTML got escaped"


def test_the_full_report_builtin_falls_back_to_the_summary():
    """An investigation_complete route can fire for an alert whose report row is
    missing. Dropping to the channel default on a customer-facing route would be
    the worse outcome, so the template degrades instead."""
    seed = _full_report_seed()
    body, err = render_body(
        seed["body_template"],
        _event(),
        "FALLBACK",
        autoescape=True,
        extra_context={"branding": {"logo": None, "accent": "#111", "accent_strong": "#222", "accent_text": "#fff", "title": "T"}},
    )

    assert err is None
    assert body != "FALLBACK"
    assert "An AI investigation completed" in body


def test_every_builtin_still_renders_against_an_event_with_a_report():
    """Attaching a report adds a key to `context`; no existing built-in may
    change behaviour or start failing because of it.

    Restricted to built-ins the dispatch loop actually renders. #999 reuses this
    table as a second event source — the temporary-password built-in is scoped
    to a trigger nothing dispatches and reads variables its own sender supplies,
    so rendering it against an alert event proves nothing about report
    attachment. Its coverage is tests/test_temp_password_email.py.
    """
    branding = {"logo": None, "accent": "#111", "accent_strong": "#222", "accent_text": "#fff", "title": "T"}
    dispatchable = [s for s in BUILTIN_TEMPLATES if s["trigger"] is None or s["trigger"] in {t.value for t in DISPATCH_TRIGGERS}]
    for seed in dispatchable:
        body, err = render_body(
            seed["body_template"],
            _event(with_report=True, trigger=NotificationTrigger.ALERT_CREATED),
            "FALLBACK",
            autoescape=seed["format"] == "html",
            extra_context={"branding": branding},
        )
        assert err is None, f"{seed['name']} failed: {err}"
        assert body != "FALLBACK", f"{seed['name']} fell back to the channel default"


# ── size, the one hard limit ──────────────────────────────────────────────


def test_an_oversized_report_degrades_instead_of_disappearing():
    """A pathological report must cost the recipient the report section, not the
    notification. The cap is checked after rendering, so this is the path that
    proves the fallback still engages."""
    huge = "x" * (MAX_RENDERED_BYTES + 1)
    session = _session(template=_template(body_template="{{ context.ai_report.markdown }}", format="text"))
    message, err, _loader = _render(
        _route(template_id=7),
        _event(),
        session,
        loader=AsyncMock(return_value=_report(markdown=huge, html=Markup(""))),
    )

    assert err is not None and "limit" in err
    assert message.body.startswith("*AI investigation complete*"), "the channel default should have gone out"


# ── manual send ───────────────────────────────────────────────────────────


def _attach(entity_type="alert", include=True, report=None):
    event = _event()
    with patch.object(ms, "safe_load_ai_report_context", AsyncMock(return_value=report)):
        asyncio.run(ms._attach_ai_report(event, entity_type, include, AsyncMock()))
    return event


def test_ticking_the_box_attaches_the_report():
    """The whole point: before #1048 this flag reached one permission check and
    was then discarded, so the checkbox could only ever refuse a send."""
    event = _attach(report=_report())

    assert event.context["ai_report"]["markdown"] == REPORT_MD


def test_leaving_the_box_unticked_loads_nothing():
    event = _attach(include=False, report=_report())

    assert "ai_report" not in event.context


def test_asking_for_a_report_that_does_not_exist_is_refused():
    """Silently sending without it would leave the operator believing the
    customer received findings they never got."""
    with pytest.raises(HTTPException) as exc:
        _attach(report=None)

    assert exc.value.status_code == 400
    assert "no AI investigation report" in exc.value.detail


def test_asking_for_a_report_on_a_case_is_refused():
    """Cases have no investigations; the UI should not offer this, and the
    server does not trust that it didn't."""
    with pytest.raises(HTTPException) as exc:
        _attach(entity_type="case", report=None)

    assert exc.value.status_code == 400
    assert "Only an alert" in exc.value.detail
