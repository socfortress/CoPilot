"""Customer Incident-Management PDF report — orchestration service.

Composes two existing patterns:
- the Vulnerability/SCA report *lifecycle* (DB row + MinIO object + generate/list/
  download/delete with a ``processing -> completed/failed`` status), and
- the single-case *PDF mechanics* in ``reports_pdf`` (Jinja ``SandboxedEnvironment``
  + autoescape -> pdfkit/wkhtmltopdf with ``disable-local-file-access``).

The template is shipped in-repo (trusted) and rendered with autoescaping on. The
report layout follows the reference SOC report design: a cover, an executive-
summary metrics table, matplotlib-rendered charts (donut / bar / evolution,
embedded as base64 PNG ``<img>`` data URIs), and colour-coded open/closed case
tables plus per-case detail cards.
"""
import json
import os
import re
from datetime import datetime
from tempfile import NamedTemporaryFile
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from jinja2.sandbox import SandboxedEnvironment
from loguru import logger
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.data_store.data_store_operations import delete_file_from_minio
from app.data_store.data_store_operations import retrieve_file_from_minio
from app.data_store.data_store_operations import store_file_in_minio
from app.db.universal_models import Customers
from app.db.universal_models import IncidentManagementCustomerReport
from app.incidents.schema.customer_report import CustomerReportGenerateRequest
from app.incidents.schema.customer_report import CustomerReportResponse
from app.incidents.services import customer_report_aggregations as agg
from app.incidents.services.customer_report_branding import resolve_theme
from app.incidents.services.customer_report_charts import donut_png
from app.incidents.services.customer_report_charts import evolution_png
from app.incidents.services.customer_report_charts import hbar_png
from app.incidents.services.reports_pdf import convert_html_to_pdf

BUCKET_NAME = "incident-management-reports"
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
# Report layout -> Jinja template file. All four share `build_report_context`;
# they only render different subsets of it (see schema.ReportTemplate). "full"
# keeps the original filename for backward-compatibility.
TEMPLATE_FILES = {
    "full": "customer_incident_report_template.html",
    "executive": "customer_incident_report_executive.html",
    "operational": "customer_incident_report_operational.html",
    "analytics": "customer_incident_report_analytics.html",
}
DEFAULT_TEMPLATE = "full"
# Cap on assets / IOCs surfaced per case card (full & operational reports).
MAX_CASE_ASSETS = 20
MAX_CASE_IOCS = 25
MAX_CASE_SHEETS = 50
DOWNLOAD_URL_TEMPLATE = "/api/v1/incidents/customer_reports/{report_id}/download"

_ROLE_NAMES = {
    RoleEnum.admin: "admin",
    RoleEnum.analyst: "analyst",
    RoleEnum.scheduler: "scheduler",
    RoleEnum.customer_user: "customer_user",
}
# Best-effort case-type extraction from a "[RFI] ..." style prefix (see gap
# analysis in issue #961 — no native case-type column exists).
_CASE_TYPE_RE = re.compile(r"\[(RFI|INC|CONF|CTI)\]", re.IGNORECASE)
# Priority is not a native column either; derive it from a linked-alert tag when
# the deployment tags one, mapping to a CSS class the template colour-codes.
_PRIORITY_KEYWORDS = {
    "critica": "CRITICA",
    "critical": "CRITICA",
    "critico": "CRITICA",
    "alta": "ALTA",
    "high": "ALTA",
    "media": "MEDIA",
    "medium": "MEDIA",
    "baja": "BAJA",
    "low": "BAJA",
    "info": "INFO",
    "informational": "INFO",
}
_TYPE_LABELS = {"RFI": "Investigation (RFI)", "INC": "Incident (INC)", "CONF": "Configuration (CONF)", "CTI": "Cyber Intelligence (CTI)"}


def _role_name(user: User) -> Optional[str]:
    try:
        return _ROLE_NAMES.get(RoleEnum(user.role_id))
    except (ValueError, TypeError):
        return None


def _fmt_dt(value: Optional[datetime]) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "—"


def _fmt_date(value: Optional[datetime]) -> str:
    return value.strftime("%Y-%m-%d") if value else "—"


def _case_type(case_name: str) -> Optional[str]:
    match = _CASE_TYPE_RE.search(case_name or "")
    return match.group(1).upper() if match else None


def _priority_from_tags(tags: List[str]) -> Optional[str]:
    """Derive a priority label from linked-alert tags (best effort, may be None)."""
    for tag in tags:
        normalised = (tag or "").strip().lower()
        if normalised in _PRIORITY_KEYWORDS:
            return _PRIORITY_KEYWORDS[normalised]
    return None


def _build_case_card(case) -> Dict[str, Any]:
    """Flatten a Case ORM row (with eager-loaded relations) into template data."""
    linked_alerts = [link.alert for link in (case.alerts or []) if link.alert is not None]
    alert_titles = [a.alert_name for a in linked_alerts]
    # Collect distinct linked-alert tags — the closest available proxy for the
    # "taxonomía" column in the reference reports.
    tags: List[str] = []
    for alert in linked_alerts:
        for link in alert.tags or []:
            if link.tag and link.tag.tag and link.tag.tag not in tags:
                tags.append(link.tag.tag)
    comments = sorted(case.comments or [], key=lambda c: c.created_at or datetime.min)
    case_type = _case_type(case.case_name)

    # Distinct affected assets + observed IOCs across the linked alerts. These are
    # eager-loaded by the aggregation queries and surfaced only in the technical
    # reports (full / operational); executive & analytics ignore these keys.
    assets: List[Dict[str, Any]] = []
    seen_assets = set()
    iocs: List[Dict[str, Any]] = []
    seen_iocs = set()
    for alert in linked_alerts:
        for asset in alert.assets or []:
            if asset.asset_name and asset.asset_name not in seen_assets:
                seen_assets.add(asset.asset_name)
                assets.append({"name": asset.asset_name, "agent_id": asset.agent_id})
        for link in alert.iocs or []:
            ioc = link.ioc
            if ioc and ioc.value and ioc.value not in seen_iocs:
                seen_iocs.add(ioc.value)
                iocs.append({"value": ioc.value, "type": ioc.type, "description": ioc.description})

    return {
        "id": case.id,
        "name": case.case_name,
        "type": case_type,
        "type_label": _TYPE_LABELS.get(case_type) if case_type else None,
        "priority": _priority_from_tags(tags),
        "taxonomy": " / ".join(tags[:3]) if tags else None,
        "is_closed": case.case_closed_time is not None,
        "status_label": "CLOSED" if case.case_closed_time is not None else "OPEN",
        "assigned_to": case.assigned_to or "—",
        "creation_time": _fmt_dt(case.case_creation_time),
        "closed_time": _fmt_dt(case.case_closed_time),
        "reported_short": case.case_creation_time.strftime("%d/%m/%y") if case.case_creation_time else "—",
        "closed_short": case.case_closed_time.strftime("%d/%m/%y") if case.case_closed_time else "—",
        "description": case.case_description or "",
        "linked_alert_count": len(linked_alerts),
        "linked_alert_titles": alert_titles[:15],
        "linked_alert_overflow": max(0, len(alert_titles) - 15),
        "assets": assets[:MAX_CASE_ASSETS],
        "asset_overflow": max(0, len(assets) - MAX_CASE_ASSETS),
        "iocs": iocs[:MAX_CASE_IOCS],
        "ioc_overflow": max(0, len(iocs) - MAX_CASE_IOCS),
        "comments": [{"user_name": c.user_name, "created_at": _fmt_dt(c.created_at), "comment": c.comment} for c in comments],
    }


async def build_report_context(
    session: AsyncSession,
    customer: Customers,
    request: CustomerReportGenerateRequest,
) -> Dict[str, Any]:
    """Aggregate incident data + charts into the Jinja template context.

    Also returns the snapshot stats used to populate the DB row (under the
    ``_stats`` key; the template ignores it).
    """
    cc = request.customer_code
    date_from = request.date_from
    date_to = request.date_to

    total_alerts = await agg.count_alerts(session, cc, date_from, date_to)
    by_source = await agg.alerts_by_source(session, cc, date_from, date_to)
    by_status = await agg.alerts_by_status(session, cc, date_from, date_to)
    top_alert_names = await agg.top_alerts_by_name(session, cc, date_from, date_to)
    top_alert_tags = await agg.top_tags(session, cc, date_from, date_to)

    total_cases = await agg.count_cases(session, cc, date_from, date_to)
    open_count, closed_count = await agg.open_closed_case_counts(session, cc, date_from, date_to)
    cases_by_type = await agg.cases_reported_by_type(session, cc, date_from, date_to)
    trend = await agg.monthly_trend(session, cc, date_from, date_to)

    open_cases_rows, open_total = await agg.fetch_open_cases(session, cc, date_from, date_to, limit=MAX_CASE_SHEETS)
    closed_cases_rows, closed_total = await agg.fetch_closed_cases(session, cc, date_from, date_to, limit=MAX_CASE_SHEETS)
    open_cards = [_build_case_card(c) for c in open_cases_rows]
    closed_cards = [_build_case_card(c) for c in closed_cases_rows]

    theme = await resolve_theme(session, request.brand_theme)

    months = [row["month"] for row in trend]
    show_evolution = len(trend) >= 2

    context = {
        "generated_at": _fmt_dt(datetime.utcnow()),
        "customer": {"code": customer.customer_code, "name": customer.customer_name},
        "period": {"from": _fmt_date(date_from), "to": _fmt_date(date_to)},
        "brand": theme["footer_brand"],
        "logo": theme["logo"],
        "theme": theme,
        "tlp": "TLP:RED",
        "metrics": {
            "total_alerts": total_alerts,
            "total_cases": total_cases,
            "open_cases": open_count,
            "closed_cases": closed_count,
            "reported_cases": cases_by_type.get("total", 0),
        },
        "alerts_by_source": by_source,
        "cases_by_type": cases_by_type,
        "charts": {
            "alerts_by_status": donut_png(by_status, status_aware=True) if total_alerts else None,
            "alerts_by_source": donut_png(by_source) if total_alerts else None,
            "top_alert_names": hbar_png(top_alert_names, color=theme["chart_bar"]) if top_alert_names else None,
            "top_tags": hbar_png(top_alert_tags, color=theme["chart_bar"]) if top_alert_tags else None,
            "evolution_alerts": evolution_png(months, [row["alerts"] for row in trend], color=theme["chart_evo_alerts"])
            if show_evolution
            else None,
            "evolution_cases": evolution_png(months, [row["cases"] for row in trend], color=theme["chart_evo_cases"])
            if show_evolution
            else None,
        },
        "monthly_trend": trend,
        "open_cases": open_cards,
        "open_overflow": max(0, open_total - len(open_cards)),
        "closed_cases": closed_cards,
        "closed_overflow": max(0, closed_total - len(closed_cards)),
        "has_alerts": total_alerts > 0,
        "has_cases": total_cases > 0,
        "_stats": {
            "total_alerts": total_alerts,
            "total_cases": total_cases,
            "open_cases": open_count,
            "closed_cases": closed_count,
        },
    }
    return context


def _render_pdf(context: Dict[str, Any], template: str = DEFAULT_TEMPLATE) -> bytes:
    """Render the selected in-repo Jinja template and convert it to PDF bytes.

    ``template`` is one of ``schema.ReportTemplate``; an unknown value falls back
    to the full report. Autoescaping is on; the only ``|safe`` values in the
    template are the server-generated chart images (base64 PNG data URIs), which
    contain no caller-controlled markup. The repeating footer (brand line + TLP +
    page number) is drawn by wkhtmltopdf so it appears on every page.
    """
    env = SandboxedEnvironment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "htm", "xml"], default=True),
    )
    template_name = TEMPLATE_FILES.get(template, TEMPLATE_FILES[DEFAULT_TEMPLATE])
    rendered_html = env.get_template(template_name).render(context)

    brand = context.get("brand") or "CoPilot"
    tlp = context.get("tlp") or "TLP:RED"

    html_path = None
    pdf_path = None
    try:
        with NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            tmp.write(rendered_html.encode("utf-8"))
            html_path = tmp.name
        pdf_path = convert_html_to_pdf(
            html_path,
            extra_options={
                "footer-left": f"{brand}  ·  {tlp}",
                "footer-right": "[page] / [topage]",
                "footer-font-size": "8",
                "footer-font-name": "Helvetica",
                "footer-spacing": "4",
                "margin-top": "16mm",
                "margin-bottom": "16mm",
                "margin-left": "14mm",
                "margin-right": "14mm",
                "encoding": "UTF-8",
            },
        )
        with open(pdf_path, "rb") as fh:
            return fh.read()
    finally:
        for path in (html_path, pdf_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


def _to_response(report: IncidentManagementCustomerReport, user_name: Optional[str] = None) -> CustomerReportResponse:
    filters: Dict[str, Any] = {}
    if report.filters_json:
        try:
            filters = json.loads(report.filters_json)
        except (ValueError, TypeError):
            filters = {}
    return CustomerReportResponse(
        id=report.id,
        report_name=report.report_name,
        customer_code=report.customer_code,
        file_name=report.file_name,
        file_size=report.file_size,
        generated_at=report.generated_at,
        generated_by=report.generated_by,
        generated_by_role=report.generated_by_role,
        generated_by_name=user_name,
        date_from=report.date_from,
        date_to=report.date_to,
        filters_applied=filters,
        total_alerts=report.total_alerts,
        total_cases=report.total_cases,
        open_cases=report.open_cases,
        closed_cases=report.closed_cases,
        visible_to_customer=report.visible_to_customer,
        status=report.status,
        error_message=report.error_message,
        download_url=DOWNLOAD_URL_TEMPLATE.format(report_id=report.id) if report.status == "completed" else None,
    )


async def resolve_user_names(session: AsyncSession, user_ids: List[int]) -> Dict[int, str]:
    """Map ``generated_by`` user ids to usernames for display in the report list."""
    ids = {uid for uid in user_ids if uid is not None}
    if not ids:
        return {}
    result = await session.execute(select(User.id, User.username).where(User.id.in_(ids)))
    return {row[0]: row[1] for row in result.all()}


async def generate_customer_report(
    session: AsyncSession,
    current_user: User,
    request: CustomerReportGenerateRequest,
    report_id: Optional[int] = None,
) -> IncidentManagementCustomerReport:
    """Generate (or complete an existing ``processing`` row for) a customer PDF report.

    When ``report_id`` is provided (background path) the existing row is updated;
    otherwise a new row is inserted. On failure the row is set to ``failed`` with
    an ``error_message`` and the exception is re-raised.
    """
    report: Optional[IncidentManagementCustomerReport] = None
    if report_id is not None:
        result = await session.execute(
            select(IncidentManagementCustomerReport).where(IncidentManagementCustomerReport.id == report_id),
        )
        report = result.scalars().first()
        if report is None:
            raise ValueError(f"Report {report_id} not found")

    try:
        customer_result = await session.execute(select(Customers).where(Customers.customer_code == request.customer_code))
        customer = customer_result.scalars().first()
        if customer is None:
            raise ValueError(f"Customer {request.customer_code} not found")

        context = await build_report_context(session, customer, request)
        pdf_bytes = _render_pdf(context, template=request.report_template)
        stats = context["_stats"]

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_name = (report.report_name if report else None) or request.report_name or f"incident_report_{timestamp}"
        file_name = (report.file_name if report else None) or f"{report_name}.pdf"
        object_key = (report.object_key if report else None) or f"{request.customer_code}/{report_name}_{timestamp}.pdf"

        upload = await store_file_in_minio(
            file_content=pdf_bytes,
            bucket_name=BUCKET_NAME,
            object_key=object_key,
            content_type="application/pdf",
        )
        if not upload.get("success"):
            raise RuntimeError(f"Failed to store report in MinIO: {upload.get('error')}")

        filters_json = json.dumps(
            {
                "date_from": request.date_from.isoformat(),
                "date_to": request.date_to.isoformat(),
                "brand_theme": request.brand_theme,
                "report_template": request.report_template,
            },
        )

        if report is None:
            report = IncidentManagementCustomerReport(
                report_name=report_name,
                customer_code=request.customer_code,
                bucket_name=BUCKET_NAME,
                object_key=object_key,
                file_name=file_name,
                generated_by=current_user.id,
                generated_by_role=_role_name(current_user),
                date_from=request.date_from,
                date_to=request.date_to,
                filters_json=filters_json,
            )
            session.add(report)

        report.bucket_name = BUCKET_NAME
        report.object_key = object_key
        report.file_name = file_name
        report.file_size = upload["file_size"]
        report.file_hash = upload["file_hash"]
        report.filters_json = filters_json
        report.total_alerts = stats["total_alerts"]
        report.total_cases = stats["total_cases"]
        report.open_cases = stats["open_cases"]
        report.closed_cases = stats["closed_cases"]
        report.status = "completed"
        report.error_message = None

        await session.commit()
        await session.refresh(report)
        logger.info(f"Generated incident report {report.id} for customer {request.customer_code}")
        return report

    except Exception as e:
        logger.error(f"Failed to generate incident report for {request.customer_code}: {e}")
        if report is not None:
            report.status = "failed"
            report.error_message = str(e)
            await session.commit()
        raise


async def list_customer_reports(
    session: AsyncSession,
    accessible_customers: List[str],
    customer_code: Optional[str] = None,
    only_customer_visible: bool = False,
) -> List[IncidentManagementCustomerReport]:
    """List reports filtered by the user's accessible customers (``["*"]`` = all).

    When ``only_customer_visible`` is True (the portal / customer_user view), the
    result is further limited to reports the customer is allowed to see: their own
    (customer-generated) reports, plus analyst/admin reports explicitly flagged
    ``visible_to_customer``.
    """
    query = select(IncidentManagementCustomerReport).order_by(IncidentManagementCustomerReport.generated_at.desc())
    if customer_code:
        query = query.where(IncidentManagementCustomerReport.customer_code == customer_code)
    if "*" not in accessible_customers:
        if not accessible_customers:
            return []
        query = query.where(IncidentManagementCustomerReport.customer_code.in_(accessible_customers))
    if only_customer_visible:
        query = query.where(
            or_(
                IncidentManagementCustomerReport.visible_to_customer.is_(True),
                IncidentManagementCustomerReport.generated_by_role == "customer_user",
            ),
        )
    result = await session.execute(query)
    return list(result.scalars().all())


async def set_report_visibility(
    session: AsyncSession,
    report: IncidentManagementCustomerReport,
    visible: bool,
) -> IncidentManagementCustomerReport:
    """Set whether an analyst/admin report is shared with the customer portal."""
    report.visible_to_customer = visible
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def get_customer_report_download(
    session: AsyncSession,
    report: IncidentManagementCustomerReport,
) -> Dict[str, Any]:
    retrieval = await retrieve_file_from_minio(bucket_name=report.bucket_name, object_key=report.object_key)
    if not retrieval.get("success"):
        raise RuntimeError(f"Failed to retrieve report file: {retrieval.get('error')}")
    return {
        "file_content": retrieval["file_content"],
        "file_name": report.file_name,
        "content_type": "application/pdf",
    }


async def delete_customer_report(
    session: AsyncSession,
    report: IncidentManagementCustomerReport,
) -> None:
    minio_result = await delete_file_from_minio(bucket_name=report.bucket_name, object_key=report.object_key)
    if not minio_result.get("success"):
        logger.warning(
            f"Failed to delete report {report.id} file from MinIO: {minio_result.get('error')}. " "Proceeding with database deletion.",
        )
    await session.delete(report)
    await session.commit()


def to_response(report: IncidentManagementCustomerReport, user_name: Optional[str] = None) -> CustomerReportResponse:
    return _to_response(report, user_name)
