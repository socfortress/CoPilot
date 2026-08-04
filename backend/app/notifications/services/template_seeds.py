"""Built-in message templates, seeded at startup.

Named templates are useless with an empty list — an operator opening the picker
would see nothing and have to write Jinja from scratch to find out what the
feature does. These give every deployment a working starting point and, more
usefully, a set of worked examples: conditionals, loops over IOCs, filters, and
`{{ branding.* }}` in an HTML email.

**Built-ins are read-only.** `update_template` and `delete_template` refuse them
because the next startup would recreate them anyway; the UI offers *Duplicate*
instead, which produces a normal editable row.

**Seeding is by name and idempotent.** A row is inserted only when no built-in
with that name exists, so restarts don't multiply them. Existing built-ins are
deliberately NOT overwritten with the current source: a deployment that has been
running for a year keeps sending exactly what it sent yesterday, and changing
these strings never silently rewrites live notifications. Renaming one here
therefore creates a new template rather than editing the old one — which is the
safe direction.
"""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import NotificationTemplate

#: Each entry becomes one `notification_template` row with `is_default=True` and
#: `customer_code=None` (shared with every customer).
BUILTIN_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "Alert — concise",
        "description": "One-line summary with severity and a link. Good for high-volume chat channels.",
        "trigger": "alert_created",
        "format": "markdown",
        "subject_template": "{{ severity }} alert on {{ customer_code }}: {{ alert_name }}",
        "body_template": (
            "*{{ severity }}* — {{ alert_name }}\n"
            "Customer: `{{ customer_code }}`"
            "{% if context.asset_name %} · Asset: {{ context.asset_name }}{% endif %}\n"
            "{% if link_url %}<{{ link_url }}|Open in CoPilot>{% endif %}"
        ),
    },
    {
        "name": "Alert — detailed with IOCs",
        "description": "Full context including any indicators the investigation extracted.",
        "trigger": "alert_created",
        "format": "markdown",
        "subject_template": "{{ severity }} alert on {{ customer_code }}: {{ alert_name }}",
        # `context.iocs` is absent on most events, so the loop is guarded rather
        # than relying on a default — StrictUndefined makes an unguarded
        # reference an error, which would fall back to the channel default.
        "body_template": (
            "*New alert* — severity: *{{ severity }}*\n\n"
            "Customer: `{{ customer_code }}`\n"
            "Alert: #{{ alert_id }}{% if alert_name %} — {{ alert_name }}{% endif %}\n"
            "{% if context.asset_name %}Asset: {{ context.asset_name }}\n{% endif %}"
            "{% if context.rule_level is not none %}Rule level: {{ context.rule_level }}\n{% endif %}"
            "\n{{ summary }}\n"
            "{% if context.iocs %}\n*Indicators*\n"
            "{% for ioc in context.iocs %}• `{{ ioc.value }}` ({{ ioc.type }})\n{% endfor %}"
            "{% endif %}"
            "{% if link_url %}\nOpen in CoPilot: {{ link_url }}{% endif %}"
        ),
    },
    {
        "name": "Assignment — who and what",
        "description": "For internal routes: who picked something up, and what it was.",
        # Deliberately unscoped: the three assignment triggers share a shape, and
        # scoping to one would mean three near-identical built-ins.
        "trigger": None,
        "format": "markdown",
        "subject_template": "{{ entity_type | replace('_', ' ') | title }} #{{ entity_id }} assigned to {{ assignee }}",
        "body_template": (
            "*{{ entity_type | replace('_', ' ') | title }} assigned* — {{ assignee or 'unassigned' }}\n\n"
            "{{ entity_type | replace('_', ' ') | title }}: #{{ entity_id }}"
            "{% if context.title %} — {{ context.title }}{% endif %}\n"
            "{% if customer_code %}Customer: `{{ customer_code }}`\n{% endif %}"
            "{% if actor %}Assigned by: {{ actor }}\n{% endif %}"
            "{% if summary %}\n{{ summary }}\n{% endif %}"
            "{% if link_url %}\nOpen in CoPilot: {{ link_url }}{% endif %}"
        ),
    },
    {
        "name": "AI investigation — customer summary",
        "description": "Plain-language wrap-up of an AI investigation, written for the end customer.",
        "trigger": "investigation_complete",
        "format": "markdown",
        "subject_template": "Security investigation complete — {{ severity }} finding",
        "body_template": (
            "We completed an automated investigation of activity on your environment.\n\n"
            "*Severity:* {{ severity }}\n"
            "*What we saw:* {{ alert_name }}\n"
            "{% if context.asset_name %}*Where:* {{ context.asset_name }}\n{% endif %}"
            "\n{{ summary }}\n"
            "{% if link_url %}\nThe full report is available here: {{ link_url }}{% endif %}"
        ),
    },
    {
        "name": "AI report reviewed — sign-off",
        "description": (
            "An analyst checked an AI investigation. Works on both internal and customer-facing routes — "
            "the same event can tell your SOC and the customer."
        ),
        "trigger": "ai_report_reviewed",
        "format": "markdown",
        "subject_template": "Reviewed: {{ alert_name }}",
        # `reviewer` and `verdict` are guarded because a review can be submitted
        # without an overall verdict, and because the same template is offered
        # on both scopes — an operator may well want the customer-facing copy to
        # omit who internally signed it off.
        "body_template": (
            "*Analyst review complete* — {{ alert_name }}\n\n"
            "Customer: `{{ customer_code }}`\n"
            "Alert: #{{ alert_id }}\n"
            "{% if context.reviewer %}Reviewed by: {{ context.reviewer }}\n{% endif %}"
            "{% if context.verdict %}Verdict: {{ context.verdict }}\n{% endif %}"
            "\n{{ summary }}\n"
            "{% if link_url %}\nOpen in CoPilot: {{ link_url }}{% endif %}"
        ),
    },
    {
        "name": "AI investigation — full report (HTML email)",
        "description": (
            "The complete AI investigation write-up with its tables rendered, in the customer's brand colours. "
            "Email channels only. Falls back to the summary when an alert has no report."
        ),
        "trigger": "investigation_complete",
        "format": "html",
        # `context.ai_report` is resolved lazily — mentioning it here is what
        # causes the report to be loaded at all (`_ensure_ai_report_context`).
        # Every access stays guarded: an alert with no investigation renders the
        # summary instead of failing to the channel default, which on a
        # customer-facing route would be the worse outcome.
        #
        # `.html` is already `Markup`, so autoescape leaves it alone; everything
        # else in this template is escaped normally.
        "body_template": (
            '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
            'max-width:760px;margin:0 auto;padding:24px">'
            "{% if branding.logo %}"
            '<img src="{{ branding.logo }}" alt="{{ branding.title | default("") }}" '
            'style="max-height:48px;margin-bottom:24px">'
            "{% endif %}"
            '<h2 style="color:{{ branding.accent | default("#1f2937") }};margin:0 0 8px">{{ alert_name }}</h2>'
            '<p style="color:#6b7280;margin:0 0 24px">'
            "Alert severity: <strong>{{ severity }}</strong>"
            "{% if context.ai_report and context.ai_report.severity %}"
            " · Assessed: <strong>{{ context.ai_report.severity }}</strong>"
            "{% endif %}"
            "{% if customer_code %} · {{ customer_code }}{% endif %}</p>"
            "{% if context.ai_report and context.ai_report.html %}"
            "{{ context.ai_report.html }}"
            "{% else %}"
            '<div style="line-height:1.6;color:#374151">{{ summary }}</div>'
            "{% endif %}"
            "{% if link_url %}"
            '<p style="margin-top:32px">'
            '<a href="{{ link_url }}" style="background:{{ branding.accent_strong | default("#2563eb") }};'
            'color:{{ branding.accent_text | default("#ffffff") }};padding:10px 20px;border-radius:6px;'
            'text-decoration:none;display:inline-block">View in CoPilot</a></p>'
            "{% endif %}"
            "</div>"
        ),
        "subject_template": "Investigation complete — {{ alert_name }}",
    },
    {
        "name": "Branded email — HTML",
        "description": (
            "HTML email in the customer's brand colours. Email channels only. "
            "The logo is embedded as a data URI, which some email clients block — the colours always apply."
        ),
        "trigger": None,
        "format": "html",
        "subject_template": "{{ severity }} security notification — {{ alert_name }}",
        # `branding` comes from the same resolver the PDF reports use, so this
        # inherits per-customer overrides and their field-by-field global
        # fallbacks. Keys are that theme's own: `logo` (a data URI, possibly
        # None), `accent_strong` (the raw brand colour), `accent_text` (legible
        # on it), `title`. Every access is guarded — `branding` is {} when the
        # lookup fails, and StrictUndefined turns a bare miss into a render
        # error that would drop the message to the channel default.
        "body_template": (
            '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
            'max-width:600px;margin:0 auto;padding:24px">'
            "{% if branding.logo %}"
            '<img src="{{ branding.logo }}" alt="{{ branding.title | default("") }}" '
            'style="max-height:48px;margin-bottom:24px">'
            "{% endif %}"
            '<h2 style="color:{{ branding.accent | default("#1f2937") }};margin:0 0 8px">{{ alert_name }}</h2>'
            '<p style="color:#6b7280;margin:0 0 24px">Severity: <strong>{{ severity }}</strong>'
            "{% if customer_code %} · {{ customer_code }}{% endif %}</p>"
            '<div style="line-height:1.6;color:#374151">{{ summary }}</div>'
            "{% if link_url %}"
            '<p style="margin-top:32px">'
            '<a href="{{ link_url }}" style="background:{{ branding.accent_strong | default("#2563eb") }};'
            'color:{{ branding.accent_text | default("#ffffff") }};padding:10px 20px;border-radius:6px;'
            'text-decoration:none;display:inline-block">View in CoPilot</a></p>'
            "{% endif %}"
            "</div>"
        ),
    },
]


async def seed_builtin_templates(async_engine) -> int:
    """Insert any missing built-in templates. Returns how many were added.

    Takes the engine and opens its own session, matching the other startup
    seeders in `db_setup.py`.

    Never raises: templates are a convenience, and a failure here must not stop
    the app from booting — every notification path works without them.
    """
    added = 0
    try:
        async with AsyncSession(async_engine) as session:
            result = await session.execute(
                select(NotificationTemplate.name).where(NotificationTemplate.is_default.is_(True)),
            )
            existing = set(result.scalars().all())

            for spec in BUILTIN_TEMPLATES:
                if spec["name"] in existing:
                    continue
                session.add(
                    NotificationTemplate(
                        name=spec["name"],
                        description=spec["description"],
                        trigger=spec["trigger"],
                        format=spec["format"],
                        subject_template=spec["subject_template"],
                        body_template=spec["body_template"],
                        customer_code=None,
                        is_default=True,
                        created_by="system",
                    ),
                )
                added += 1

            if added:
                await session.commit()
                logger.info(f"Seeded {added} built-in notification template(s).")
    except Exception as e:  # noqa: BLE001 — never block startup
        logger.warning(f"Could not seed built-in notification templates: {type(e).__name__}: {e}")
        return 0
    return added
