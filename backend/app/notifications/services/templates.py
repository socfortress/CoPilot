"""Named, reusable message templates.

#1037 made `route.format_template` real Jinja. This makes templates shareable:
write one, attach it to many routes, edit it once.

**Precedence at render time is inline → named → channel default.** The inline
field survives deliberately as a per-route override, so a single route can
deviate without forking the shared copy — and so nothing that worked before this
existed changes behaviour.

Two decisions worth knowing:

**Deleting a template does not delete the routes using it.** The FK has no
cascade; `delete_template` clears the reference and reports how many routes were
affected. Those routes fall back to their inline template or the channel
default, so notifications keep flowing rather than silently stopping.

**Compatibility is checked when a template is attached, not when it fires.** A
template scoped to `alert_assigned` references `{{assignee}}`, which is empty on
`alert_created`; a template in `html` cannot render as a Teams card. Catching
that at attach time is a 400 the operator sees, rather than a route that
degrades to the channel default forever.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from jinja2 import TemplateError
from loguru import logger
from sqlalchemy import desc
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import CustomerNotificationRoute
from app.db.universal_models import NotificationTemplate
from app.notifications.schema.events import NotificationEvent
from app.notifications.services.rendering import compile_template

#: Formats a template can declare. `html` autoescapes; `json` is validated to
#: parse after rendering; `text` and `markdown` pass through.
TEMPLATE_FORMATS = ("text", "markdown", "html", "json")

_HTML_FORMATS = {"html"}


async def list_templates(
    session: AsyncSession,
    *,
    customer_code: Optional[str] = None,
    trigger: Optional[str] = None,
    accessible_customers: Optional[List[str]] = None,
) -> List[NotificationTemplate]:
    """Templates available to a customer: their own plus the shared ones.

    A NULL `customer_code` means shared, so the filter is deliberately an OR
    rather than an equality — omitting the shared ones would hide every built-in
    default from every customer.

    ``accessible_customers`` is the caller's tenant scope (``["*"]`` for
    deployment-wide). It bounds the listing when no single ``customer_code`` was
    asked for, so a scoped analyst browsing "all templates" sees only their own
    tenants' — plus the shared ones, which are shared with them too.
    """
    stmt = select(NotificationTemplate)
    if customer_code:
        stmt = stmt.where(
            or_(
                NotificationTemplate.customer_code == customer_code,
                NotificationTemplate.customer_code.is_(None),
            ),
        )
    elif accessible_customers is not None and "*" not in accessible_customers:
        stmt = stmt.where(
            or_(
                NotificationTemplate.customer_code.in_(accessible_customers),
                NotificationTemplate.customer_code.is_(None),
            ),
        )
    if trigger:
        # A trigger-agnostic template (NULL) is usable everywhere.
        stmt = stmt.where(
            or_(NotificationTemplate.trigger == trigger, NotificationTemplate.trigger.is_(None)),
        )
    result = await session.execute(stmt.order_by(desc(NotificationTemplate.created_at)))
    return result.scalars().all()


async def get_template(template_id: int, session: AsyncSession) -> NotificationTemplate:
    result = await session.execute(select(NotificationTemplate).where(NotificationTemplate.id == template_id))
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return template


def _validate(name: str, fmt: str, body: str, subject: Optional[str]) -> None:
    """Reject a template that cannot work, at save time.

    Compilation catches syntax errors. Undefined variables are not checked here:
    they depend on the event, and a template valid for one trigger may reference
    fields another doesn't carry — those degrade to the channel default at send
    time with the reason recorded.
    """
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="A template needs a name.")
    if fmt not in TEMPLATE_FORMATS:
        raise HTTPException(status_code=400, detail=f"format must be one of {TEMPLATE_FORMATS}")
    if not body or not body.strip():
        raise HTTPException(status_code=400, detail="A template needs a body.")

    autoescape = fmt in _HTML_FORMATS
    for label, source in (("body_template", body), ("subject_template", subject)):
        if not source:
            continue
        try:
            compile_template(source, autoescape=autoescape)
        except TemplateError as e:
            raise HTTPException(status_code=400, detail=f"{label} is not valid Jinja: {e}") from e


async def create_template(payload: Any, created_by: Optional[str], session: AsyncSession) -> NotificationTemplate:
    fmt = payload.format.value if hasattr(payload.format, "value") else payload.format
    _validate(payload.name, fmt, payload.body_template, payload.subject_template)

    template = NotificationTemplate(
        name=payload.name.strip(),
        description=payload.description,
        trigger=payload.trigger.value if hasattr(payload.trigger, "value") else payload.trigger,
        format=fmt,
        subject_template=payload.subject_template,
        body_template=payload.body_template,
        customer_code=payload.customer_code,
        # Only the seeder creates built-ins; an operator-created template is
        # always editable and deletable.
        is_default=False,
        created_by=created_by,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


async def update_template(template_id: int, payload: Any, session: AsyncSession) -> NotificationTemplate:
    template = await get_template(template_id, session)

    if template.is_default:
        raise HTTPException(
            status_code=400,
            detail=(
                "Built-in templates cannot be edited. Duplicate it first — the copy is yours to change, "
                "and the original stays available as a reference."
            ),
        )

    data = payload.model_dump(exclude_unset=True)
    new_format = data.get("format", template.format)
    _validate(
        data.get("name", template.name),
        new_format.value if hasattr(new_format, "value") else new_format,
        data.get("body_template", template.body_template),
        data.get("subject_template", template.subject_template),
    )

    for field, value in data.items():
        if hasattr(value, "value"):
            value = value.value
        setattr(template, field, value)
    template.updated_at = datetime.utcnow()

    # Changing `format`, `trigger` or `customer_code` can invalidate an
    # attachment that was legal when it was made — narrowing a shared template
    # to one customer, or switching it to HTML while a Teams route uses it.
    # Without this the attach-time check would only hold until the first edit.
    conflicts = await _attached_route_conflicts(template, session)
    if conflicts:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail=(
                "That change would break "
                + ("a route" if len(conflicts) == 1 else f"{len(conflicts)} routes")
                + " already using this template: "
                + "; ".join(conflicts)
            ),
        )

    await session.commit()
    await session.refresh(template)
    return template


async def _attached_route_conflicts(template: NotificationTemplate, session: AsyncSession) -> List[str]:
    """Routes that this template — as edited — could no longer serve.

    Returns one human-readable line per conflict so the operator sees which
    routes to fix rather than a bare refusal.
    """
    result = await session.execute(
        select(CustomerNotificationRoute).where(CustomerNotificationRoute.template_id == template.id),
    )
    conflicts: List[str] = []
    for route in result.scalars().all():
        problem = _incompatibility(
            template,
            channel=route.channel,
            trigger=route.trigger,
            customer_code=route.customer_code,
        )
        if problem:
            conflicts.append(f"{route.name!r} — {problem}")
    return conflicts


async def delete_template(template_id: int, session: AsyncSession) -> int:
    """Delete a template, detaching it from any routes using it.

    Returns how many routes were affected so the caller can say so.

    The FK deliberately has no cascade: deleting a template must not delete the
    routes referencing it. Those routes fall back to their inline template or
    the channel default, so notifications keep flowing — losing a template is an
    inconvenience, losing a route is an outage.
    """
    template = await get_template(template_id, session)

    if template.is_default:
        raise HTTPException(status_code=400, detail="Built-in templates cannot be deleted.")

    result = await session.execute(
        update(CustomerNotificationRoute).where(CustomerNotificationRoute.template_id == template_id).values(template_id=None),
    )
    detached = result.rowcount or 0

    await session.delete(template)
    await session.commit()

    if detached:
        logger.info(f"Deleted template {template_id}; detached from {detached} route(s), which fall back to their channel default.")
    return detached


async def assert_template_usable(
    template_id: int,
    *,
    channel: str,
    trigger: str,
    customer_code: Optional[str],
    session: AsyncSession,
) -> None:
    """Refuse a template the route being saved cannot actually render.

    Takes the route's properties rather than the ORM row, so route creation
    (where no row exists yet) and PATCH (where the effective values are a merge
    of the payload and the stored row) can both call it.

    Checked when the template is attached rather than when it fires. A mismatch
    caught at send time is a route that silently degrades to the channel default
    forever; caught here it is a 400 the operator can act on.
    """
    template = await get_template(template_id, session)
    problem = _incompatibility(template, channel=channel, trigger=trigger, customer_code=customer_code)
    if problem:
        raise HTTPException(status_code=400, detail=problem)


def _incompatibility(
    template: NotificationTemplate,
    *,
    channel: str,
    trigger: str,
    customer_code: Optional[str],
) -> Optional[str]:
    """Why this template cannot serve a route with these properties, or None.

    Pure and route-shaped rather than a raiser, because it is asked in two
    directions: when a route attaches a template, and when a template is edited
    while routes already point at it. Both need the same rules or the attach-time
    guarantee is worthless.
    """
    from app.notifications.channels import get_channel

    if template.customer_code and customer_code and template.customer_code != customer_code:
        return f"That template belongs to customer {template.customer_code!r}, but the route serves {customer_code!r}."

    # A shared template on an internal route is fine — it belongs to no tenant
    # either. A customer-scoped one is not: it would render a specific
    # customer's branding into a message that goes to the SOC.
    if template.customer_code and customer_code is None:
        return f"That template is scoped to customer {template.customer_code!r}, so it cannot be used on an internal route."

    if template.trigger and template.trigger != trigger:
        return (
            f"That template is scoped to the {template.trigger!r} trigger, but the route fires on "
            f"{trigger!r}. A template written around one trigger's variables renders empty on another."
        )

    provider = get_channel(channel)
    if provider is not None and template.format not in provider.template_formats:
        return f"The {channel!r} channel cannot render a {template.format!r} template (supports {sorted(provider.template_formats)})."

    return None


#: Returned when branding can't be resolved. Every key the resolver produces and
#: a template is likely to touch is present, because `StrictUndefined` turns a
#: missing key into a render error — and a template guarding each access would
#: be unreadable. Keeping the shape stable means `{{ branding.logo }}` is always
#: safe to write, whether or not the lookup succeeded.
_FALLBACK_BRANDING: Dict[str, Any] = {
    "logo": None,
    "title": "CoPilot",
    "footer_brand": "CoPilot",
    "accent": "#1f2937",
    "accent_strong": "#2563eb",
    "accent_text": "#ffffff",
    "accent_soft": "#e5e7eb",
}


async def build_branding_context(customer_code: Optional[str], session: AsyncSession) -> Dict[str, Any]:
    """The customer's logo and colours, for templates that want them.

    Reuses the report branding resolver rather than reading the tables directly,
    so a templated email inherits exactly the branding a generated PDF would —
    including the field-by-field fallback to global defaults.

    Note the logo is a data URI. That renders in a browser preview and in some
    mail clients, but Gmail and Outlook block data-URI images — the colours
    always apply, the logo may not.

    Never raises: branding is decoration, and a notification must not fail
    because a logo lookup did.
    """
    try:
        from app.incidents.services.customer_report_branding import resolve_theme

        theme = await resolve_theme(session, "customer", customer_code)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not resolve branding for {customer_code!r}: {type(e).__name__}: {e}")
        return dict(_FALLBACK_BRANDING)
    # Union rather than the raw theme: a resolver that ever stops emitting a key
    # would otherwise break every template referencing it.
    return {**_FALLBACK_BRANDING, **(theme or {})}


async def resolve_template_for_route(
    route: CustomerNotificationRoute,
    session: AsyncSession,
) -> Optional[NotificationTemplate]:
    """The named template a route should use, if any.

    Returns None when the route has no `template_id` — the caller then falls
    back to the inline `format_template` or the channel default, which is the
    precedence chain this module exists to implement.
    """
    if not getattr(route, "template_id", None):
        return None
    result = await session.execute(select(NotificationTemplate).where(NotificationTemplate.id == route.template_id))
    template = result.scalars().first()
    if template is None:
        # A dangling reference should not stop the notification. The route falls
        # back, and the mismatch is visible in the log.
        logger.warning(f"Route {route.id} references template {route.template_id}, which no longer exists.")
    return template


def sample_event(trigger: str, customer_code: Optional[str]) -> NotificationEvent:
    """A realistic event for previewing an unsaved template.

    Populated for every trigger rather than only the one being previewed, so a
    template that references `{{assignee}}` renders something even while the
    editor's trigger selector says `alert_created`. The alternative — undefined,
    which `StrictUndefined` turns into an error — would make the editor look
    broken while someone is halfway through writing.
    """
    from app.notifications.schema.events import EntityType
    from app.notifications.schema.notifications import NotificationSeverity
    from app.notifications.schema.notifications import NotificationTrigger

    parsed = NotificationTrigger(trigger) if trigger in {t.value for t in NotificationTrigger} else NotificationTrigger.ALERT_CREATED

    entity_type = EntityType.ALERT
    if parsed == NotificationTrigger.CASE_ASSIGNED:
        entity_type = EntityType.CASE
    elif parsed == NotificationTrigger.CASE_TASK_ASSIGNED:
        entity_type = EntityType.CASE_TASK

    return NotificationEvent(
        customer_code=customer_code or "ACME",
        trigger=parsed,
        severity=NotificationSeverity.HIGH,
        subject="Suspicious PowerShell execution on WKSTN-014",
        summary=(
            "An encoded PowerShell command was executed by a non-administrative user. "
            "The parent process was winword.exe, which is consistent with a malicious document."
        ),
        entity_type=entity_type,
        entity_id=4821,
        dedupe_key="preview",
        link_url="https://copilot.example.com/alerts/4821",
        assignee_username="jdoe",
        actor_username="asmith",
        context={
            "alert_name": "Suspicious PowerShell execution on WKSTN-014",
            "title": "Suspicious PowerShell execution on WKSTN-014",
            "asset_name": "WKSTN-014",
            "rule_level": 12,
            "iocs": [
                {"value": "185.199.108.153", "type": "ip"},
                {"value": "a1b2c3d4e5f6", "type": "hash"},
            ],
        },
    )


async def preview(payload: Any, session: AsyncSession) -> Dict[str, Any]:
    """Render template source against a sample event, without saving.

    Takes the source inline so the editor previews *unsaved* edits — the same
    reason the custom-dashboard builder previews an unsaved panel set, and what
    stops the preview and the real send from drifting.

    Errors are returned rather than raised: the editor shows them beside the
    template being written, which is more useful than a 400 that clears the form.
    """
    from app.notifications.services.rendering import render

    fmt = payload.format.value if hasattr(payload.format, "value") else payload.format
    trigger = payload.trigger.value if hasattr(payload.trigger, "value") else payload.trigger

    event = sample_event(trigger, payload.customer_code)
    autoescape = fmt in _HTML_FORMATS

    extra: Dict[str, Any] = {}
    source = f"{payload.body_template}{payload.subject_template or ''}"
    if "branding" in source:
        extra["branding"] = await build_branding_context(payload.customer_code, session)

    try:
        body = render(payload.body_template, event, autoescape=autoescape, extra_context=extra)
    except Exception as e:  # noqa: BLE001 — the message IS the useful output here
        return {"body": "", "subject": None, "error": f"{type(e).__name__}: {e}"}

    subject = None
    if payload.subject_template:
        try:
            subject = " ".join(render(payload.subject_template, event, autoescape=autoescape, extra_context=extra).split())
        except Exception as e:  # noqa: BLE001
            return {"body": body, "subject": None, "error": f"Subject: {type(e).__name__}: {e}"}

    return {"body": body, "subject": subject, "error": None}
