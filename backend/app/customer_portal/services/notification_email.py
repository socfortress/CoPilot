"""The emails a portal user's notifications send (#1282).

**Operator-authored, like the temporary-password email (#999).** Each email is a
``notification_template`` scoped to its own ``portal_*`` trigger, so the SOC writes
its wording, language and branding in the Message Templates editor it already uses.
Resolution is by scope, most specific first: this customer's template, a shared one,
the seeded built-in, and finally the plaintext below — a deployment with no template
still sends something readable.

**A broken template never costs the email.** These are sent by CoPilot on its own, with
nobody watching a dialog, so a render failure is logged and the plaintext goes out
instead (the dispatch loop's rule, not the password email's).

Links point into the portal through ``CUSTOMER_PORTAL_URL``; unset, the emails carry no
link rather than a guessed one.
"""

from __future__ import annotations

import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

from loguru import logger
from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.db.universal_models import CustomerPortalNotification
from app.db.universal_models import Customers
from app.db.universal_models import NotificationTemplate
from app.notifications.schema.events import NotificationEvent
from app.notifications.schema.notifications import NotificationSeverity
from app.notifications.schema.notifications import NotificationTrigger

#: The template trigger for each notification event, and for the digest.
TRIGGER_FOR_EVENT: Dict[str, NotificationTrigger] = {
    "alert_created": NotificationTrigger.PORTAL_ALERT_CREATED,
    "waiting_on_you": NotificationTrigger.PORTAL_WAITING_ON_YOU,
    "case_closed": NotificationTrigger.PORTAL_CASE_CLOSED,
    "report_ready": NotificationTrigger.PORTAL_REPORT_READY,
}
DIGEST_TRIGGER = NotificationTrigger.PORTAL_DIGEST

#: Formats an email can carry; `markdown` goes out as text, as for the password email.
SUPPORTED_FORMATS = ("text", "markdown", "html")

#: What each event is called in a plaintext email and a digest's sections.
EVENT_HEADINGS: Dict[str, str] = {
    "alert_created": "New alerts",
    "waiting_on_you": "Waiting on you",
    "case_closed": "Closed cases",
    "report_ready": "Reports ready",
}


def portal_url() -> str:
    """The Customer Portal's base URL (``CUSTOMER_PORTAL_URL``), or "" when unset."""
    return (os.getenv("CUSTOMER_PORTAL_URL") or "").strip().rstrip("/")


def item_url(entity_type: str, entity_id: int) -> str:
    """Where a notification's item lives in the portal, or "" without a base URL."""
    base = portal_url()
    if not base:
        return ""
    if entity_type == "alert":
        return f"{base}/alerts/{entity_id}"
    if entity_type == "case":
        return f"{base}/cases/{entity_id}"
    if entity_type == "report":
        return f"{base}/reports"
    return base


def item_view(row: CustomerPortalNotification) -> Dict[str, Any]:
    """One notification as a template sees it (``items`` in the digest)."""
    return {
        "event": row.event,
        "title": row.title,
        "body": row.body or "",
        "severity": row.severity or "",
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "url": item_url(row.entity_type, row.entity_id),
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M UTC") if row.created_at else "",
    }


async def resolve_template(
    session: AsyncSession,
    trigger: NotificationTrigger,
    customer_code: Optional[str],
) -> Optional[NotificationTemplate]:
    """The template for this email: the customer's, a shared one, the built-in — or None.

    An exact trigger match only: a trigger-agnostic template is written for alert
    routes and would render ``{{ alert_name }}`` empty here. Another customer's
    template is never used.
    """
    result = await session.execute(
        select(NotificationTemplate)
        .where(NotificationTemplate.trigger == trigger.value, NotificationTemplate.format.in_(SUPPORTED_FORMATS))
        .order_by(desc(NotificationTemplate.updated_at), desc(NotificationTemplate.created_at)),
    )

    def rank(template: NotificationTemplate) -> int:
        if customer_code and template.customer_code == customer_code:
            return 0
        if template.customer_code is None:
            return 1 if not template.is_default else 2
        return 3

    candidates = sorted((t for t in result.scalars().all() if rank(t) < 3), key=rank)
    return candidates[0] if candidates else None


async def customer_name_for(session: AsyncSession, customer_code: Optional[str]) -> str:
    if not customer_code:
        return ""
    result = await session.execute(select(Customers.customer_name).where(Customers.customer_code == customer_code))
    return result.scalars().first() or customer_code


def build_event(
    trigger: NotificationTrigger,
    *,
    customer_code: Optional[str],
    title: str,
    body: Optional[str],
    severity: Optional[str],
    entity_type: str,
    entity_id: int,
    link: str,
) -> NotificationEvent:
    """The envelope `render` needs. Severity falls back to Informational (a closed case has none)."""
    try:
        parsed = NotificationSeverity(severity) if severity else NotificationSeverity.INFORMATIONAL
    except ValueError:
        parsed = NotificationSeverity.INFORMATIONAL
    return NotificationEvent(
        customer_code=customer_code,
        trigger=trigger,
        severity=parsed,
        subject=title,
        summary=body or title,
        entity_type=entity_type,
        entity_id=entity_id,
        dedupe_key=f"{trigger.value}:{entity_type}:{entity_id}",
        link_url=link or None,
        context={"title": title},
    )


def build_extra_context(
    *,
    user_name: str,
    customer_code: Optional[str],
    customer_name: str,
    event: Optional[str] = None,
    items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """The variables these emails add on top of the event's (merged under them by `render`).

    Mirrored by `PORTAL_VARIABLES` in the frontend's `templateVariables.ts`.
    """
    return {
        "user_name": user_name,
        "customer_name": customer_name,
        "organization_name": customer_name,
        "portal_url": portal_url(),
        "event_name": event or "",
        "event_heading": EVENT_HEADINGS.get(event or "", ""),
        "items": items or [],
        "item_count": len(items or []),
    }


async def render_with(
    session: AsyncSession,
    *,
    template: Optional[NotificationTemplate],
    event: NotificationEvent,
    extra: Dict[str, Any],
    fallback: Tuple[str, str],
) -> Tuple[str, str, Optional[str]]:
    """Render ``template`` (or the plaintext ``fallback``). Returns (subject, text, html)."""
    if template is None:
        return (fallback[0], fallback[1], None)

    from app.auth.services.temp_password_email import html_to_text
    from app.notifications.services.rendering import render
    from app.notifications.services.templates import build_branding_context

    source = f"{template.body_template}{template.subject_template or ''}"
    if "branding" in source:
        extra = {**extra, "branding": await build_branding_context(event.customer_code, session)}
    is_html = template.format == "html"
    try:
        body = render(template.body_template, event, autoescape=is_html, extra_context=extra)
        subject = fallback[0]
        if template.subject_template:
            # One line: a newline in a subject is a header-injection vector.
            subject = " ".join(render(template.subject_template, event, autoescape=is_html, extra_context=extra).split()) or fallback[0]
    except Exception as e:  # noqa: BLE001 — a broken template must not cost the email
        logger.warning(
            f"Portal notification template {template.id} ({template.name!r}) failed to render "
            f"({type(e).__name__}: {e}); sending the plaintext instead.",
        )
        return (fallback[0], fallback[1], None)
    if is_html:
        return (subject, html_to_text(body), body)
    return (subject, body, None)


def plaintext(user: User, customer_name: str, rows: Sequence[CustomerPortalNotification]) -> str:
    """The email without a template: a greeting, each notification, a link back."""
    lines = [f"Hello {user.username},", ""]
    if len(rows) == 1:
        row = rows[0]
        lines.append(row.title)
        if row.body:
            lines += ["", row.body]
        url = item_url(row.entity_type, row.entity_id)
        if url:
            lines += ["", f"Open it in the portal: {url}"]
    else:
        lines.append(f"Here is what happened{f' at {customer_name}' if customer_name else ''} since your last summary:")
        for event, heading in EVENT_HEADINGS.items():
            section = [row for row in rows if row.event == event]
            if not section:
                continue
            lines += ["", heading]
            for row in section:
                url = item_url(row.entity_type, row.entity_id)
                lines.append(f"- {row.title}{f' ({url})' if url else ''}")
        if portal_url():
            lines += ["", f"Open the portal: {portal_url()}"]
    settings = f"{portal_url()}/profile?tab=notifications" if portal_url() else "Profile → Notifications"
    lines += ["", f"You receive this because of your notification settings in the portal: {settings}"]
    return "\n".join(lines)


async def render_notification_email(
    row: CustomerPortalNotification,
    user: User,
    session: AsyncSession,
) -> Tuple[str, str, Optional[str]]:
    """One notification as an email: (subject, text, html or None)."""
    trigger = TRIGGER_FOR_EVENT[row.event]
    customer_name = await customer_name_for(session, row.customer_code)
    link = item_url(row.entity_type, row.entity_id)
    event = build_event(
        trigger,
        customer_code=row.customer_code,
        title=row.title,
        body=row.body,
        severity=row.severity,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        link=link,
    )
    extra = build_extra_context(
        user_name=user.username,
        customer_code=row.customer_code,
        customer_name=customer_name,
        event=row.event,
        items=[item_view(row)],
    )
    template = await resolve_template(session, trigger, row.customer_code)
    return await render_with(
        session,
        template=template,
        event=event,
        extra=extra,
        fallback=(row.title, plaintext(user, customer_name, [row])),
    )


async def render_digest_email(
    rows: Sequence[CustomerPortalNotification],
    user: User,
    session: AsyncSession,
) -> Tuple[str, str, Optional[str]]:
    """A day's notifications as one email.

    Branded and resolved for the customer when every row is one customer's, else with
    the shared template and no customer: a user of several customers gets one digest.
    """
    codes = {row.customer_code for row in rows}
    customer_code = next(iter(codes)) if len(codes) == 1 else None
    customer_name = await customer_name_for(session, customer_code)
    count = len(rows)
    title = f"Your daily summary: {count} notification{'s' if count != 1 else ''}"
    event = build_event(
        DIGEST_TRIGGER,
        customer_code=customer_code,
        title=title,
        body=title,
        severity=None,
        entity_type="user",
        entity_id=user.id,
        link=portal_url(),
    )
    extra = build_extra_context(
        user_name=user.username,
        customer_code=customer_code,
        customer_name=customer_name,
        items=[item_view(row) for row in rows],
    )
    template = await resolve_template(session, DIGEST_TRIGGER, customer_code)
    return await render_with(session, template=template, event=event, extra=extra, fallback=(title, plaintext(user, customer_name, rows)))


# ── The template editor's preview ─────────────────────────────────────────────

_PREVIEW_ITEMS: Dict[str, Dict[str, Any]] = {
    "alert_created": {
        "title": "New High alert: Suspicious PowerShell execution on WKSTN-014",
        "body": "An encoded PowerShell command was run by a non-administrative user.",
        "severity": "High",
        "entity_type": "alert",
        "entity_id": 4821,
    },
    "waiting_on_you": {
        "title": "The SOC is waiting on your reply: Suspicious PowerShell execution on WKSTN-014",
        "body": "Their response clock for this alert is paused until you answer. Reply in its comments to hand it back.",
        "severity": "High",
        "entity_type": "alert",
        "entity_id": 4821,
    },
    "case_closed": {
        "title": "Case closed: Phishing campaign against the finance team",
        "body": "Twelve messages quarantined; two credentials reset.",
        "severity": None,
        "entity_type": "case",
        "entity_id": 312,
    },
    "report_ready": {
        "title": "Report ready: Monthly security report",
        "body": "It covers 2026-09-01 to 2026-09-30.",
        "severity": None,
        "entity_type": "report",
        "entity_id": 57,
    },
}

_TRIGGER_EVENTS = {trigger.value: event for event, trigger in TRIGGER_FOR_EVENT.items()}


def is_portal_trigger(trigger: Optional[str]) -> bool:
    return trigger in _TRIGGER_EVENTS or trigger == DIGEST_TRIGGER.value


def preview_event(trigger: str, customer_code: Optional[str]) -> NotificationEvent:
    """A sample envelope for a ``portal_*`` template being edited."""
    if trigger == DIGEST_TRIGGER.value:
        return build_event(
            DIGEST_TRIGGER,
            customer_code=customer_code,
            title="Your daily summary: 3 notifications",
            body=None,
            severity=None,
            entity_type="user",
            entity_id=0,
            link=portal_url() or "https://portal.example.com",
        )
    item = _PREVIEW_ITEMS[_TRIGGER_EVENTS[trigger]]
    return build_event(
        NotificationTrigger(trigger),
        customer_code=customer_code,
        title=item["title"],
        body=item["body"],
        severity=item["severity"],
        entity_type=item["entity_type"],
        entity_id=item["entity_id"],
        link=item_url(item["entity_type"], item["entity_id"]) or "https://portal.example.com",
    )


def preview_extra_context(trigger: str, customer_name: str) -> Dict[str, Any]:
    """The extras a ``portal_*`` template sees, with sample values."""
    events = list(_PREVIEW_ITEMS) if trigger == DIGEST_TRIGGER.value else [_TRIGGER_EVENTS[trigger]]
    items = [
        {
            **_PREVIEW_ITEMS[event],
            "body": _PREVIEW_ITEMS[event]["body"] or "",
            "severity": _PREVIEW_ITEMS[event]["severity"] or "",
            "event": event,
            "url": "https://portal.example.com",
            "created_at": "2026-10-01 08:15 UTC",
        }
        for event in events[:3]
    ]
    return build_extra_context(
        user_name="jdoe",
        customer_code=None,
        customer_name=customer_name or "Acme Corp",
        event=None if trigger == DIGEST_TRIGGER.value else _TRIGGER_EVENTS[trigger],
        items=items,
    )
