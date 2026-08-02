"""Jinja rendering for notification message bodies.

Replaces the `str.replace()` token substitution `_render_body` used to do. That
handled `{{summary}}` but nothing else — no conditionals, no loops over an
alert's IOCs, no filters. Operators asking "only include the asset name when
there is one" had no way to express it.

**The sandbox is mandatory, not defensive.** These templates are authored by
operators and stored in the database, which makes them untrusted input by
definition. Plain `jinja2.Environment` allows attribute traversal that reaches
Python internals and, from there, arbitrary code execution — see
GHSA-7q83-228r-wfh5. The same reasoning already governs `reports_pdf.py` and
`customer_report.py`; this follows their pattern.

Two rails matter as much as the rendering:

**Validate at save time.** `compile_template` is called when a route is written,
so a typo is a 400 the operator sees immediately rather than a notification that
silently stops working and surfaces days later in the dispatch log.

**Fail safe at send time.** If a template raises anyway — a field missing on one
event shape, a filter misused — `render_body` falls back to the channel default
and reports the error. A broken template must never mean a missed critical
alert.
"""

from __future__ import annotations

import json
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

from jinja2 import StrictUndefined
from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment
from loguru import logger

from app.notifications.schema.events import NotificationEvent

#: Rendered bodies feed chat messages and emails. Teams rejects over 28 KB and
#: no channel benefits from more; a runaway loop is the realistic way to exceed
#: it, so this doubles as a blast radius limit.
MAX_RENDERED_BYTES = 64 * 1024

#: Jinja has no execution timeout of its own, and this deliberately does not add
#: one: a wall-clock limit would need a thread per render, which is a poor trade
#: on the ingest hot path.
#:
#: The size cap is therefore checked AFTER rendering, not during. A runaway loop
#: still allocates its output before being rejected — the cap bounds what gets
#: *sent*, not what gets built. That is acceptable because templates are
#: operator-authored and validated at save time, not attacker-supplied. If that
#: assumption ever changes, this needs a streaming limit instead.


class TemplateTooLargeError(TemplateError):
    """Raised when a template's output exceeds MAX_RENDERED_BYTES."""


def _build_environment() -> SandboxedEnvironment:
    """A sandboxed environment with autoescaping off by default.

    Autoescape is deliberately per-format rather than global: a notification
    body is plain text or markdown far more often than HTML, and escaping it
    would turn every `&` into `&amp;` in a Slack message. `render_body` turns it
    on for HTML formats.

    `StrictUndefined` makes a typo'd variable an error rather than an empty
    string — combined with save-time validation, that means a template
    referencing `{{ summry }}` is rejected when written rather than quietly
    producing a message with a hole in it.
    """
    env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)
    env.policies["json.dumps_kwargs"] = {"sort_keys": True}
    return env


_ENV = _build_environment()
_ENV_AUTOESCAPE = SandboxedEnvironment(undefined=StrictUndefined, autoescape=True)


def build_context(event: NotificationEvent) -> Dict[str, Any]:
    """The variables a template can reference.

    The six original token names stay top-level and mean exactly what they did
    before Jinja, so every stored template keeps rendering identically. Anything
    added since is additive.

    `event` is also exposed whole, so a template can reach parts of the envelope
    that have no flat alias — `{{ event.context.iocs }}`, for instance.
    """
    ctx = event.context or {}
    return {
        # Original tokens — unchanged semantics.
        "customer_code": event.customer_code or "",
        "alert_id": event.entity_id,
        "alert_name": ctx.get("alert_name") or event.subject or "",
        "severity": event.severity.value,
        "summary": event.summary,
        "report_url": event.link_url or "",
        # Added with #1006.
        "assignee": event.assignee_username or "",
        "actor": event.actor_username or "",
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        # Added here: the full envelope, for anything without a flat alias.
        "subject": event.subject,
        "trigger": event.trigger.value,
        "link_url": event.link_url or "",
        "context": ctx,
        "event": event,
    }


def compile_template(source: str, *, autoescape: bool = False) -> None:
    """Parse `source`, raising `TemplateError` if it is malformed.

    Called at save time. Compilation catches syntax errors but not undefined
    variables — those depend on the event, and a template legitimately valid for
    one trigger may reference fields another does not carry.
    """
    env = _ENV_AUTOESCAPE if autoescape else _ENV
    env.from_string(source)


def render(source: str, event: NotificationEvent, *, autoescape: bool = False) -> str:
    """Render `source` against `event`. Raises on any failure.

    Callers that must not fail should use `render_body`, which falls back.
    """
    env = _ENV_AUTOESCAPE if autoescape else _ENV
    template = env.from_string(source)
    output = template.render(**build_context(event))

    if len(output.encode("utf-8")) > MAX_RENDERED_BYTES:
        raise TemplateTooLargeError(
            f"Rendered body is {len(output.encode('utf-8'))} bytes, over the {MAX_RENDERED_BYTES} byte limit. "
            f"A loop over an unbounded collection is the usual cause.",
        )
    return output


def render_body(
    source: Optional[str],
    event: NotificationEvent,
    fallback: str,
    *,
    autoescape: bool = False,
) -> Tuple[str, Optional[str]]:
    """Render a template, falling back to `fallback` on any error.

    Returns `(body, error_message)`. The error is non-None only when the
    fallback was used, and is recorded on the dispatch-log row so a broken
    template is visible without having to reproduce it.

    Nothing here raises. A template that fails at 3am must degrade to the
    channel default, not drop a Critical notification.
    """
    if not source:
        return (fallback, None)

    try:
        return (render(source, event, autoescape=autoescape), None)
    except TemplateError as e:
        message = f"Template render failed ({type(e).__name__}: {e}); sent the channel default instead."
        logger.warning(f"{message} trigger={event.trigger.value} entity={event.entity_type}#{event.entity_id}")
        return (fallback, message)
    except Exception as e:  # noqa: BLE001 — a template must never take down a dispatch
        message = f"Template render failed unexpectedly ({type(e).__name__}: {e}); sent the channel default instead."
        logger.exception(message)
        return (fallback, message)


def render_json(source: str, event: NotificationEvent) -> str:
    """Render a template intended to produce JSON.

    `tojson` is the correct escaping for embedding a value inside a JSON
    template — HTML escaping would corrupt it — so autoescape stays off and the
    template is expected to use `{{ value | tojson }}` where needed. Validating
    that the result parses catches the common mistake of an unquoted
    substitution.
    """
    output = render(source, event, autoescape=False)
    try:
        json.loads(output)
    except ValueError as e:
        raise TemplateError(f"Template produced invalid JSON: {e}") from e
    return output
