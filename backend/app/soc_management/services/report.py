"""PDF reports: the SOC operations report, and the SLA section of the customer report.

Both render a ``metrics.Snapshot`` — the same figures the dashboard shows — through the
shared report chrome (``incidents/templates/_report_base.html``) so every PDF CoPilot
produces looks like one family. Generation is synchronous: the report is a few pages of
tables and four small charts, built from data already aggregated in memory.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from jinja2 import ChoiceLoader
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.incidents.services.customer_report import TEMPLATE_DIR as INCIDENT_TEMPLATE_DIR
from app.incidents.services.customer_report import html_to_pdf_bytes
from app.incidents.services.customer_report_branding import resolve_theme
from app.incidents.services.customer_report_charts import hbar_png
from app.incidents.services.customer_report_charts import line_png
from app.soc_management.domain import analytics
from app.soc_management.domain.periods import Bucket
from app.soc_management.domain.periods import Period
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.domain.sla import Compliance
from app.soc_management.schema.metrics import Viewer
from app.soc_management.services import formatting as fmt
from app.soc_management.services.metrics import DashboardQuery
from app.soc_management.services.metrics import Snapshot
from app.soc_management.services.metrics import compute_snapshot
from app.soc_management.services.metrics import customer_visibility
from app.soc_management.services.metrics import snapshot_for_user

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
REPORT_TEMPLATE = "soc_operations_report.html"
TLP = "TLP:AMBER"
REPORT_ATTENTION_LIMIT = 20
REPORT_RULES_LIMIT = 15

_BUCKET_FORMAT = {Bucket.HOUR: "%H:%M", Bucket.DAY: "%d %b", Bucket.WEEK: "%d %b", Bucket.MONTH: "%b %Y"}


# ── shared row formatting ────────────────────────────────────────────────────


def _compliance(compliance: Compliance) -> Dict[str, Any]:
    return {
        "rate": fmt.rate(compliance.rate),
        "cls": fmt.rate_class(compliance.rate),
        "width": compliance.rate if compliance.rate is not None else 0,
        "met": compliance.met,
        "breached": compliance.breached,
    }


def _target_lookup(snapshot: Snapshot) -> Dict[Tuple[str, str], Dict[str, str]]:
    return {
        (cell.entity.value, cell.severity): {"ack": fmt.target(cell.ack_minutes), "resolve": fmt.target(cell.resolve_minutes)}
        for cell in snapshot.policy.cells
    }


def severity_table(snapshot: Snapshot, entity: SlaEntity) -> List[Dict[str, Any]]:
    targets = _target_lookup(snapshot)
    rows = []
    for row in snapshot.severities:
        if row.entity is not entity:
            continue
        target = targets.get((entity.value, row.severity), {"ack": fmt.EMPTY, "resolve": fmt.EMPTY})
        rows.append(
            {
                "severity": row.severity,
                "opened": row.opened,
                "resolved": row.resolved,
                "open_now": row.open_now,
                "breached_now": row.breached_now,
                "ack_target": target["ack"],
                "resolve_target": target["resolve"],
                "tta": fmt.duration(row.tta.median),
                "ttr": fmt.duration(row.ttr.median),
                "ack": _compliance(row.sla.ack),
                "resolve": _compliance(row.sla.resolve),
                "empty": row.opened == 0 and row.open_now == 0,
            },
        )
    return rows


def _entity_summary(headline: analytics.EntityHeadline, previous: analytics.EntityHeadline) -> Dict[str, Any]:
    return {
        "opened": headline.opened,
        "opened_delta": fmt.delta(headline.opened, previous.opened),
        "resolved": headline.resolved,
        "tta_median": fmt.duration(headline.tta.median),
        "tta_mean": fmt.duration(headline.tta.mean),
        "tta_p90": fmt.duration(headline.tta.p90),
        "ttr_median": fmt.duration(headline.ttr.median),
        "ttr_mean": fmt.duration(headline.ttr.mean),
        "ttr_p90": fmt.duration(headline.ttr.p90),
        "ack": _compliance(headline.sla.ack),
        "resolve": _compliance(headline.sla.resolve),
        "breaches": headline.sla.ack.breached + headline.sla.resolve.breached,
        "reopened": headline.reopened,
    }


def _period_label(period: Period) -> Dict[str, str]:
    return {"from": period.start.strftime("%Y-%m-%d %H:%M"), "to": period.end.strftime("%Y-%m-%d %H:%M")}


# ── SOC operations report ────────────────────────────────────────────────────


async def build_report_context(session: AsyncSession, snapshot: Snapshot) -> Dict[str, Any]:
    theme = await resolve_theme(session, "customer", customer_code=_single(snapshot.customer_codes))
    head, prev = snapshot.headline, snapshot.previous_headline
    labels = [point.start.strftime(_BUCKET_FORMAT[snapshot.bucket]) for point in snapshot.trends]
    accent = theme.get("accent_strong") or theme.get("chart_bar") or "#2563eb"

    charts = {
        "volume": line_png(
            labels,
            [
                ("Alerts opened", [p.alerts_opened for p in snapshot.trends], accent),
                ("Alerts resolved", [p.alerts_resolved for p in snapshot.trends], "#94a3b8"),
            ],
        ),
        "sla": line_png(
            labels,
            [("Resolve SLA met", [p.sla_rate for p in snapshot.trends], accent)],
            percent=True,
            reference=fmt.RATE_GOOD,
        ),
        "rules": hbar_png([(rule.alert_name, rule.alerts) for rule in snapshot.rules[:10]], color=theme.get("chart_bar"))
        if snapshot.rules
        else None,
    }

    customers_label = _scope_label(snapshot.customer_codes, snapshot.customer_names)
    return {
        "generated_at": snapshot.now.strftime("%Y-%m-%d %H:%M"),
        "period": _period_label(snapshot.period),
        "previous_period": _period_label(snapshot.previous),
        "scope": customers_label,
        "customer": {"name": customers_label, "code": ""},  # read by the shared base template's <title>
        "brand": theme["footer_brand"],
        "logo": theme["logo"],
        "theme": theme,
        "tlp": TLP,
        "sla_objective": fmt.RATE_GOOD,
        "viewer": snapshot.viewer,
        "tracking_since": snapshot.tracking_since.strftime("%Y-%m-%d") if snapshot.tracking_since else None,
        "alerts": _entity_summary(head.alerts, prev.alerts),
        "cases": _entity_summary(head.cases, prev.cases),
        "false_positive_rate": fmt.rate(head.false_positive_rate),
        "reviewed_alerts": head.reviewed_alerts,
        "case_conversion_rate": fmt.rate(head.case_conversion_rate),
        "escalated_alerts": head.escalated_alerts,
        "workload": {
            "open_alerts": snapshot.workload.open_alerts,
            "open_cases": snapshot.workload.open_cases,
            "unassigned_alerts": snapshot.workload.unassigned_alerts,
            "unassigned_cases": snapshot.workload.unassigned_cases,
            "breached": snapshot.workload.breached,
            "at_risk": snapshot.workload.at_risk,
            "by_severity": snapshot.workload.by_severity,
            "by_assignee": snapshot.workload.by_assignee,
        },
        "alert_severities": severity_table(snapshot, SlaEntity.ALERT),
        "case_severities": severity_table(snapshot, SlaEntity.CASE),
        "charts": charts,
        "analysts": [
            {
                "username": row.username,
                "alerts_resolved": row.alerts_resolved,
                "cases_resolved": row.cases_resolved,
                "acknowledged": row.alerts_acknowledged + row.cases_acknowledged,
                "tta": fmt.duration(row.tta.median),
                "ttr": fmt.duration(row.ttr.median),
                "sla": _compliance(row.sla),
                "open": row.open_alerts + row.open_cases,
                "breached": row.breached,
            }
            for row in snapshot.analysts
        ],
        "rules": [
            {
                "name": rule.alert_name,
                "sources": ", ".join(rule.sources) or fmt.EMPTY,
                "alerts": rule.alerts,
                "in_case": rule.in_case,
                "fp_rate": fmt.rate(rule.false_positive_rate),
                "reviewed": rule.reviewed,
                "noisy": rule.noisy,
                "ttr": fmt.duration(rule.ttr.median),
            }
            for rule in snapshot.rules[:REPORT_RULES_LIMIT]
        ],
        "customers": [
            {
                "code": row.customer_code,
                "name": snapshot.customer_names.get(row.customer_code) or row.customer_code,
                "alerts": row.alerts,
                "cases": row.cases,
                "open": row.open_now,
                "breached": row.breached_now,
                "alert_sla": _compliance(row.alert_sla),
                "case_sla": _compliance(row.case_sla),
                "ttr": fmt.duration(row.alert_ttr.median),
                "top_rule": row.top_rule or fmt.EMPTY,
            }
            for row in snapshot.customers
        ],
        "attention": [
            {
                "ref": f"{'ALERT' if item.entity is SlaEntity.ALERT else 'CASE'}-{item.id}",
                "title": item.title,
                "customer": item.customer_code or fmt.EMPTY,
                "severity": item.severity,
                "assigned_to": item.assigned_to or "unassigned",
                "state": item.state.value,
                "clock": "response" if item.clock == "ack" else "resolution",
                "overdue": fmt.duration(abs(item.overdue_seconds)),
                "late": item.overdue_seconds > 0,
            }
            for item in snapshot.attention
        ],
    }


def render_html(context: Dict[str, Any], template: str = REPORT_TEMPLATE) -> str:
    """Autoescaped, sandboxed: the only ``|safe`` values are server-rendered chart images."""
    env = SandboxedEnvironment(
        loader=ChoiceLoader([FileSystemLoader(TEMPLATE_DIR), FileSystemLoader(INCIDENT_TEMPLATE_DIR)]),
        autoescape=select_autoescape(["html", "htm", "xml"], default=True),
    )
    return env.get_template(template).render(context)


async def render_report(session: AsyncSession, user: User, query: DashboardQuery) -> Tuple[bytes, str]:
    snapshot = await snapshot_for_user(session, user, query, attention_limit=REPORT_ATTENTION_LIMIT)
    context = await build_report_context(session, snapshot)
    pdf = html_to_pdf_bytes(render_html(context), brand=context["brand"] or "CoPilot", tlp=TLP)
    name = f"soc_report_{snapshot.period.start:%Y%m%d}_{snapshot.period.end:%Y%m%d}.pdf"
    return pdf, name


# ── customer report SLA section ──────────────────────────────────────────────


async def customer_sla_context(session: AsyncSession, customer_code: str, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
    """The SLA section of a customer's PDF report: their figures only, no analyst names.

    The caller has already authorised the customer; visibility here is exactly that
    customer, and the viewer sees no per-analyst row by construction.
    """
    snapshot = await compute_snapshot(
        session,
        DashboardQuery(period=Period(date_from, date_to), customer_codes=[customer_code]),
        viewer=Viewer(username="", is_admin=False, sees_all_analysts=False),
        visibility=customer_visibility(customer_code),
        attention_limit=0,
    )
    head, prev = snapshot.headline, snapshot.previous_headline
    return {
        "tracking_since": snapshot.tracking_since.strftime("%Y-%m-%d") if snapshot.tracking_since else None,
        "alerts": _entity_summary(head.alerts, prev.alerts),
        "cases": _entity_summary(head.cases, prev.cases),
        "alert_severities": severity_table(snapshot, SlaEntity.ALERT),
        "case_severities": severity_table(snapshot, SlaEntity.CASE),
        "has_data": bool(head.alerts.opened or head.cases.opened),
    }


def _single(codes: Optional[List[str]]) -> Optional[str]:
    return codes[0] if codes and len(codes) == 1 else None


def _scope_label(codes: Optional[List[str]], names: Dict[str, str]) -> str:
    if codes is None:
        return "All customers"
    if not codes:
        return "No customer"
    if len(codes) == 1:
        return names.get(codes[0]) or codes[0]
    if len(codes) <= 4:
        return ", ".join(names.get(code) or code for code in codes)
    return f"{len(codes)} customers"
