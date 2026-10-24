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
`_require_ai_report_permitted`. Rendering checks the customer's AI report
setting per route (`payload_v1.report_permitted_for_route`) before it loads, on
every trigger and on manual and test sends. Calling this earlier than either
would turn it into a read primitive.

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
from app.notifications.schema.events import EntityType
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


def named_report_id(context: Optional[Dict[str, Any]]) -> Optional[int]:
    """The report an event is about, when it names one (`ai_report_reviewed` does).

    A bool is not an id, though Python says it is an int.
    """
    value = (context or {}).get("report_id")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


async def select_report(
    alert_id: int,
    session: AsyncSession,
    *,
    report_id: Optional[int] = None,
    customer_code: Optional[str] = None,
    entity_type: str = EntityType.ALERT,
) -> Optional[AiAnalystReport]:
    """The one report a notification carries, for every report surface.

    The v1 block (`payload_v1`), the webhook's flat fields (`build_full_report`)
    and `context.ai_report` all choose through here, so they never name different
    reports:

    - nothing unless the notification is about an **alert**: a case or a task with
      the same id as an alert must not carry that alert's report;
    - the report the event names (`report_id`, a review's) when there is one, and
      nothing if that report is gone or is another alert's: a review is about one
      report, never a different one announced in its place;
    - otherwise the alert's newest, by `created_at` and then `id`, so two reports
      landing in the same second still give one answer;
    - nothing when `customer_code` is given and the report is another customer's.
    """
    if entity_type != EntityType.ALERT:
        return None
    if report_id is not None:
        report = await session.get(AiAnalystReport, report_id)
        if report is None or report.alert_id != alert_id:
            logger.warning(f"Notification for alert {alert_id} names report {report_id}, not one of its own; no report.")
            return None
    else:
        result = await session.execute(
            select(AiAnalystReport)
            .where(AiAnalystReport.alert_id == alert_id)
            .order_by(AiAnalystReport.created_at.desc(), AiAnalystReport.id.desc())
            .limit(1),
        )
        report = result.scalars().first()
    if report is None:
        return None
    if customer_code and report.customer_code != customer_code:
        logger.warning(f"AI report {report.id} is not customer {customer_code}'s; not loaded for its notification.")
        return None
    return report


async def load_ai_report_context(
    alert_id: int,
    session: AsyncSession,
    customer_code: Optional[str] = None,
    *,
    report_id: Optional[int] = None,
    entity_type: str = EntityType.ALERT,
) -> Optional[Dict[str, Any]]:
    """The notification's AI report (`select_report`), shaped for template rendering.

    Returns `None` when there is none to carry — which the callers treat as
    "nothing to include" rather than a failure: no report yet, not an alert, a
    named report that is gone, or another customer's report.

    **Newest wins** unless the event names its report. An alert can accumulate
    several reports: the 15-minute scheduled sweep and the real-time trigger both
    run the same workflow, and a re-investigation adds a row rather than
    replacing one.
    """
    report = await select_report(alert_id, session, report_id=report_id, customer_code=customer_code, entity_type=entity_type)
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


async def safe_load_ai_report_context(
    alert_id: int,
    session: AsyncSession,
    customer_code: Optional[str] = None,
    *,
    report_id: Optional[int] = None,
    entity_type: str = EntityType.ALERT,
) -> Optional[Dict[str, Any]]:
    """`load_ai_report_context`, but a failure degrades instead of propagating.

    Rendering sits between an event and a delivery. A malformed report or a
    transient DB error must cost the recipient the report section, not the whole
    notification — the same reasoning that makes `render_body` fall back rather
    than raise.
    """
    try:
        return await load_ai_report_context(alert_id, session, customer_code, report_id=report_id, entity_type=entity_type)
    except Exception as e:  # noqa: BLE001 — a report must never break a dispatch
        logger.warning(f"Could not load AI report for alert {alert_id}: {type(e).__name__}: {e}")
        return None
