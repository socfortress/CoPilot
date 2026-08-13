"""Operator-authored templates for the temporary-password email (#999).

The Security tab's "Email temp password" action used to send one hardcoded
English plaintext body. Organisations needed their own wording, their own
language, their branding, and their support contact — none of which was
reachable without editing `security_admin.build_temp_password_email` and
rebuilding the image.

**No new table.** `notification_template` already stores named, scoped,
sandboxed-Jinja templates with a CRUD API and an editor, and its model comment
names this issue as the reason `trigger` is nullable and free-form. A template
scoped to the `temp_password_issued` trigger is a temporary-password email; the
same rows, the same editor, the same `SandboxedEnvironment`.

**But it is not a notification route.** Nothing emits this trigger into
`dispatch()` — delivery is the admin pressing Send, over SMTP, synchronously,
with the plaintext password in hand. So the *template* machinery is shared and
the *delivery* machinery is not, which is why this module lives under `auth`
next to its only caller rather than under `notifications`.

## Which template a given send uses

Resolution is by scope, most specific first, and every step is a query the
operator can predict from the template list:

1. a template scoped to this customer (`customer_code == <the customer>`)
2. a shared operator-authored template (`customer_code IS NULL`)
3. the seeded built-in (`is_default=True`)
4. no template at all — `build_temp_password_email`'s plaintext, unchanged

Ties inside a step are broken by most-recently-updated, and the send dialog
always shows which template won with a picker to override it for that one send.
That is what makes "select globally or per customer" a matter of *where you
create the template* rather than a second piece of selection state.

**Trigger-agnostic templates are deliberately excluded.** `list_templates` in
the notifications service treats a NULL trigger as "usable anywhere", which is
right for routes: an assignment template renders fine on three assignment
triggers. Here it would silently offer "Alert — concise" as someone's password
email, rendering `{{ alert_name }}` empty and `{{ severity }}` as a lie. This
path requires an exact trigger match, both for resolution and for the picker.

## The password never appears in a preview

`preview_for_user` renders against `PREVIEW_PASSWORD`, a constant. Previewing
must not rotate anyone's credentials, and a preview that showed the real value
would put it in a response body, a browser cache and probably a screenshot. The
send path is the only thing that ever sees a real password, and it holds it in
memory for exactly one SMTP conversation.
"""

from __future__ import annotations

import os
import re
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.db.universal_models import Customers
from app.db.universal_models import NotificationTemplate
from app.notifications.schema.events import EntityType
from app.notifications.schema.events import NotificationEvent
from app.notifications.schema.notifications import NotificationSeverity
from app.notifications.schema.notifications import NotificationTrigger

#: The template `trigger` value that marks a row as a temporary-password email.
TEMPLATE_TRIGGER = NotificationTrigger.TEMP_PASSWORD_ISSUED.value

#: Stands in for the real password everywhere a preview is rendered. Shaped like
#: a real one so the layout is honest, and obviously fake so nobody tries it.
PREVIEW_PASSWORD = "PREVIEW-Not-A-Real-Password"  # noqa: S105 — a placeholder, by design

#: Used when a template has no subject of its own, and by the plaintext
#: fallback. Kept identical to what the route sent before #999 so an operator
#: who authors no template sees no change whatsoever.
DEFAULT_SUBJECT = "CoPilot — temporary password"

#: Formats this sender can put in an email. `markdown` is accepted but sent as
#: text — no mail client renders it — and `json` is meaningless here.
SUPPORTED_FORMATS = ("text", "markdown", "html")


def login_url() -> str:
    """The sign-in URL to offer in the email, or "" when CoPilot has no base URL.

    Same `COPILOT_URL` the notification deep links use, so a deployment that has
    already configured one gets a working button here for free. Empty rather
    than a guess: a template guards it with `{% if login_url %}`, and a wrong
    URL in a credentials email is worse than no URL.
    """
    base = (os.getenv("COPILOT_URL") or "").strip().rstrip("/")
    return f"{base}/login" if base else ""


def build_extra_context(
    *,
    username: str,
    email: str,
    temp_password: str,
    customer_code: Optional[str],
    customer_name: Optional[str],
) -> Dict[str, Any]:
    """The variables specific to this email, on top of the shared event ones.

    These are passed as `extra_context` rather than stuffed into the event's
    `context` bag so they are top-level: `{{ temp_password }}`, not
    `{{ context.temp_password }}`. `render` merges extras *under* the event
    context, so none of these can shadow `severity` or `summary` and change what
    an existing template means — and none of these names collides with one.

    Mirrored by `TEMP_PASSWORD_VARIABLES` in the frontend's
    `templateVariables.ts`. A list that is wrong is worse than no list, because
    the operator finds out when a real password email renders with a hole in it.
    """
    return {
        "user_name": username,
        "user_email": email,
        "temp_password": temp_password,
        "login_url": login_url(),
        "customer_name": customer_name or customer_code or "",
        "organization_name": customer_name or customer_code or "",
    }


def build_event(
    *,
    username: str,
    customer_code: Optional[str],
    user_id: int = 0,
) -> NotificationEvent:
    """A `NotificationEvent` describing "an admin issued a temporary password".

    The envelope is required by `render`, which is shared with the dispatch
    path. Severity is `Informational` because this is not a finding, and
    `summary`/`subject` are populated so a trigger-agnostic template dragged
    here by hand still renders something readable rather than raising under
    `StrictUndefined`.
    """
    return NotificationEvent(
        customer_code=customer_code,
        trigger=NotificationTrigger.TEMP_PASSWORD_ISSUED,
        severity=NotificationSeverity.INFORMATIONAL,
        subject=DEFAULT_SUBJECT,
        summary="An administrator has issued a temporary password for your CoPilot account. Sign in with it and change it immediately.",
        entity_type=EntityType.USER,
        entity_id=user_id,
        # Carried because the envelope requires it. Nothing dedupes this path —
        # re-sending is a deliberate admin action and must always go out.
        dedupe_key=f"{EntityType.USER}:{user_id}:{TEMPLATE_TRIGGER}",
        link_url=login_url() or None,
        context={"username": username},
    )


# ── Template resolution ───────────────────────────────────────────────────────


async def list_available_templates(
    session: AsyncSession,
    customer_code: Optional[str],
) -> List[NotificationTemplate]:
    """Templates that can serve this customer, best match first.

    Ordered exactly as `resolve_template` resolves, so the picker's first entry
    is always the one that would be used anyway — the operator never has to
    reconcile two different orderings.
    """
    stmt = select(NotificationTemplate).where(NotificationTemplate.trigger == TEMPLATE_TRIGGER)
    result = await session.execute(stmt.order_by(desc(NotificationTemplate.updated_at), desc(NotificationTemplate.created_at)))
    templates = list(result.scalars().all())

    def rank(t: NotificationTemplate) -> int:
        if customer_code and t.customer_code == customer_code:
            return 0
        if t.customer_code is None:
            return 1 if not t.is_default else 2
        return 3  # another customer's — listed last, and never auto-resolved

    return sorted([t for t in templates if rank(t) < 3], key=rank)


async def resolve_template(
    session: AsyncSession,
    customer_code: Optional[str],
    template_id: Optional[int] = None,
) -> Optional[NotificationTemplate]:
    """The template a send should use, or None to fall back to plaintext.

    An explicit `template_id` wins — that is the send dialog's per-send override
    — but it is still checked against this customer, so an admin cannot email
    one tenant's branded template to another tenant's user by passing an id.
    """
    if template_id is not None:
        template = (await session.execute(select(NotificationTemplate).where(NotificationTemplate.id == template_id))).scalars().first()
        if template is None:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        if template.trigger != TEMPLATE_TRIGGER:
            raise HTTPException(
                status_code=400,
                detail=(
                    "That template is not a temporary-password email template. Set its trigger to "
                    "'Temporary password issued' to use it here."
                ),
            )
        if template.customer_code and template.customer_code != customer_code:
            raise HTTPException(
                status_code=400,
                detail=f"That template belongs to customer {template.customer_code!r}, not {customer_code!r}.",
            )
        if template.format not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"A {template.format!r} template cannot be sent as an email (supported: {list(SUPPORTED_FORMATS)}).",
            )
        return template

    available = await list_available_templates(session, customer_code)
    return available[0] if available else None


async def resolve_customer_code(
    session: AsyncSession,
    user: User,
    requested: Optional[str] = None,
) -> Optional[str]:
    """Which customer's template and branding this user's email should use.

    The Security tab is rendered per customer and passes the code it is showing,
    which is the right answer whenever a user is scoped to several. It is still
    verified against `user_customer_access`: the route is admin-only, but an
    unchecked code would let a wrong (or hand-crafted) request render one
    tenant's branding and support contact into another tenant's user's email.

    With nothing requested, a user scoped to exactly one customer resolves to it
    — that is the common case and asking would be noise. A user scoped to
    several stays unresolved rather than picking a winner, matching how portal
    branding refuses to guess for a multi-customer user; they get the shared
    template.
    """
    from app.auth.models.users import UserCustomerAccess

    result = await session.execute(select(UserCustomerAccess.customer_code).where(UserCustomerAccess.user_id == user.id))
    codes = [c for c in result.scalars().all()]

    if requested:
        if requested not in codes:
            raise HTTPException(
                status_code=400,
                detail=f"User {user.username!r} does not have access to customer {requested!r}.",
            )
        return requested

    return codes[0] if len(codes) == 1 else None


async def customer_name_for(session: AsyncSession, customer_code: Optional[str]) -> Optional[str]:
    """Display name for the customer, or None. Never raises — it is decoration."""
    if not customer_code:
        return None
    result = await session.execute(select(Customers.customer_name).where(Customers.customer_code == customer_code))
    return result.scalars().first()


# ── Rendering ─────────────────────────────────────────────────────────────────


def html_to_text(html: str) -> str:
    """A readable plaintext alternative for an HTML body.

    Every HTML email is sent multipart. A recipient on a text-only client — or a
    gateway that strips HTML, which some corporate mail filters do to messages
    containing credentials — must still be able to read their password.

    Deliberately crude: this is a fallback part, not a rendering engine. It drops
    script/style wholesale, turns block boundaries into newlines and unescapes
    the five named entities that matter. Anything fancier would be a dependency
    for a part most recipients never see.
    """
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|li|h[1-6]|table)\s*>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    for entity, char in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(entity, char)
    # Collapse the run of blank lines the tag-stripping leaves behind, but keep
    # paragraph separation — a wall of text is unreadable.
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


async def render_email(
    session: AsyncSession,
    *,
    template: Optional[NotificationTemplate],
    username: str,
    email: str,
    temp_password: str,
    customer_code: Optional[str],
    customer_name: Optional[str] = None,
    user_id: int = 0,
) -> Tuple[str, str, Optional[str]]:
    """Render the email. Returns `(subject, text_body, html_body_or_None)`.

    Raises on a template failure rather than falling back silently. The dispatch
    path falls back because a broken template must not cost a Critical alert;
    here the operator is standing at the dialog watching, the password has not
    been rotated yet (the route renders *before* it commits one), and a silent
    fallback to English plaintext is exactly the outcome #999 exists to stop.
    """
    if template is None:
        from app.auth.services.security_admin import build_temp_password_email

        return (DEFAULT_SUBJECT, build_temp_password_email(username, temp_password), None)

    from app.notifications.services.rendering import render
    from app.notifications.services.templates import build_branding_context

    event = build_event(username=username, customer_code=customer_code, user_id=user_id)
    extra = build_extra_context(
        username=username,
        email=email,
        temp_password=temp_password,
        customer_code=customer_code,
        customer_name=customer_name,
    )

    # Resolved only when referenced, matching the notification preview: it is a
    # DB round trip plus a logo read, and most templates never touch it.
    source = f"{template.body_template}{template.subject_template or ''}"
    if "branding" in source:
        extra["branding"] = await build_branding_context(customer_code, session)

    is_html = template.format == "html"
    body = render(template.body_template, event, autoescape=is_html, extra_context=extra)

    subject = DEFAULT_SUBJECT
    if template.subject_template:
        # A subject with a newline in it is a header-injection vector, and mail
        # servers reject or truncate it. Whitespace-collapsing is the same thing
        # the notification preview does to a rendered subject.
        subject = " ".join(render(template.subject_template, event, autoescape=is_html, extra_context=extra).split())
        if not subject:
            subject = DEFAULT_SUBJECT

    if is_html:
        return (subject, html_to_text(body), body)
    return (subject, body, None)


async def preview_for_user(
    session: AsyncSession,
    *,
    template: Optional[NotificationTemplate],
    user: User,
    customer_code: Optional[str],
) -> Dict[str, Any]:
    """Render what this user would receive, with a placeholder password.

    Errors are returned rather than raised, for the same reason the template
    editor's preview returns them: the admin needs to see the failure next to
    the template that caused it, and a 400 that closes the dialog tells them
    less.
    """
    customer_name = await customer_name_for(session, customer_code)
    try:
        subject, text_body, html_body = await render_email(
            session,
            template=template,
            username=user.username,
            email=user.email,
            temp_password=PREVIEW_PASSWORD,
            customer_code=customer_code,
            customer_name=customer_name,
            user_id=user.id,
        )
    except Exception as e:  # noqa: BLE001 — the message IS the useful output here
        logger.warning(f"Temp-password preview failed for template {getattr(template, 'id', None)}: {type(e).__name__}: {e}")
        return {"subject": None, "body": "", "format": "text", "error": f"{type(e).__name__}: {e}"}

    return {
        "subject": subject,
        "body": html_body if html_body is not None else text_body,
        "format": "html" if html_body is not None else "text",
        "error": None,
    }
