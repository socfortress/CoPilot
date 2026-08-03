"""Loading an AI investigation report into notification template context.

Until #1048 the notification engine could see an investigation's 400-character
`summary` and nothing else. The report itself — `ai_analyst_report.
report_markdown`, typically 6–8 KB of structured findings — was written by Talon,
displayed in CoPilot, exposed to the customer portal, and invisible to every
delivery channel.

This module closes that gap by projecting a report into a dict that templates
reach as `{{ context.ai_report.* }}`.

**A projection, never storage.** No column, no table, no migration; the same
discipline the Detections Catalog follows. Markdown stays the source of truth
and HTML is computed per send, because a cached copy would drift from the
markdown the moment the renderer changes — and the conversion is sub-millisecond
on a report this size, so there is nothing to save.

**Loading is authorization-sensitive.** A report is customer data. The loader
takes an alert id and reads unconditionally, so every caller must run its own
access checks *first* — `manual_send` does, after `_require_object_access` and
`_require_ai_report_permitted`. On the automatic path `dispatch_event` has
already applied the #1014 opt-out before any rendering happens. Calling this
earlier than either would turn it into a read primitive.

**Absence is normal, not an error.** Most alerts have no investigation, cases
never do, and a route can be configured for a customer whose AI trigger is off.
Every path returns `None` rather than raising, and the templates guard on it.
"""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import AiAnalystIoc
from app.db.universal_models import AiAnalystReport
from app.notifications.utils.markdown_html import markdown_to_html

#: Cap on how many indicators reach a template. A pathological investigation
#: could extract hundreds, and a template looping over all of them would blow
#: through MAX_RENDERED_BYTES and drop the whole message to the channel default.
#: Truncating is the better failure: the report body still names every indicator,
#: and `ioc_count` tells the template the true total so it can say so.
MAX_IOCS = 50


def _ioc_to_dict(ioc: AiAnalystIoc) -> Dict[str, Any]:
    return {
        "value": ioc.ioc_value,
        "type": ioc.ioc_type,
        "vt_verdict": ioc.vt_verdict,
        "vt_score": ioc.vt_score or "",
        "details": ioc.details or "",
    }


async def load_ai_report_context(alert_id: int, session: AsyncSession) -> Optional[Dict[str, Any]]:
    """The newest AI report for `alert_id`, shaped for template rendering.

    Returns `None` when the alert has no report — which the callers treat as
    "nothing to include" rather than a failure.

    **Newest wins.** An alert can accumulate several reports: the 15-minute
    scheduled sweep and the real-time trigger both run the same workflow, and a
    re-investigation adds a row rather than replacing one. Ordering by
    `created_at` then `id` breaks the tie deterministically when two land in the
    same second, which the bare timestamp would not.
    """
    result = await session.execute(
        select(AiAnalystReport)
        .where(AiAnalystReport.alert_id == alert_id)
        .order_by(AiAnalystReport.created_at.desc(), AiAnalystReport.id.desc())
        .limit(1),
    )
    report = result.scalars().first()
    if report is None:
        return None

    ioc_result = await session.execute(
        select(AiAnalystIoc).where(AiAnalystIoc.report_id == report.id).order_by(AiAnalystIoc.id),
    )
    iocs: List[AiAnalystIoc] = list(ioc_result.scalars().all())

    markdown = report.report_markdown or ""

    return {
        "markdown": markdown,
        # Pre-rendered so an html-format template is one substitution rather than
        # a filter chain, and so the conversion happens once even if a template
        # references it twice.
        "html": markdown_to_html(markdown),
        "summary": report.summary or "",
        "recommended_actions": report.recommended_actions or "",
        # The AI's assessment of the *finding*, which is a different judgement
        # from the alert's own severity — an alert can be Critical while its
        # investigation concludes Medium. Exposed under its own name so a
        # template can show both without them being confused for each other.
        "severity": report.severity_assessment or "",
        "created_at": report.created_at,
        "report_id": report.id,
        "iocs": [_ioc_to_dict(i) for i in iocs[:MAX_IOCS]],
        "ioc_count": len(iocs),
        "iocs_truncated": len(iocs) > MAX_IOCS,
    }


async def safe_load_ai_report_context(alert_id: int, session: AsyncSession) -> Optional[Dict[str, Any]]:
    """`load_ai_report_context`, but a failure degrades instead of propagating.

    Rendering sits between an event and a delivery. A malformed report or a
    transient DB error must cost the recipient the report section, not the whole
    notification — the same reasoning that makes `render_body` fall back rather
    than raise.
    """
    try:
        return await load_ai_report_context(alert_id, session)
    except Exception as e:  # noqa: BLE001 — a report must never break a dispatch
        logger.warning(f"Could not load AI report for alert {alert_id}: {type(e).__name__}: {e}")
        return None
