import calendar
import csv
from datetime import datetime
from io import StringIO
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.customers.routes.customers import get_customer
from app.db.db_session import get_db
from app.incidents.models import Alert
from app.incidents.models import AlertToIoC
from app.incidents.models import AlertToTag
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.schema.db_operations import CaseDownloadDocxRequest
from app.incidents.services.reports import cleanup_temp_files
from app.incidents.services.reports import create_case_context
from app.incidents.services.reports import create_file_response
from app.incidents.services.reports import download_template
from app.incidents.services.reports import render_document_with_context
from app.incidents.services.reports import save_template_to_tempfile
from app.incidents.services.reports_pdf import convert_html_to_pdf
from app.incidents.services.reports_pdf import create_case_context_pdf
from app.incidents.services.reports_pdf import create_file_response_pdf
from app.incidents.services.reports_pdf import download_template_pdf
from app.incidents.services.reports_pdf import render_html_template

incidents_report_router = APIRouter()

# Constants
FIELDNAMES = [
    "Case ID",
    "Case Name",
    "Case Description",
    "Case Creation Time",
    "Case Status",
    "Case Closed Time",
    "Case Assigned To",
    "Case Customer Code",
    "Alert ID",
    "Alert Name",
    "Alert Description",
    "Alert Status",
    "Alert Creation Time",
    "Alert Time Closed",
    "Alert Source",
    "Alert Assigned To",
    "Assets",
    "Tags",
    "Comments",
    "Customer Code",
]


# Helper Functions
def _build_month_range(year: int, month: int) -> tuple[datetime, datetime]:
    """Return (start, end) datetimes for a given year/month."""
    last_day = calendar.monthrange(year, month)[1]
    start = datetime(year, month, 1)
    end = datetime(year, month, last_day, 23, 59, 59)
    return start, end


async def fetch_cases_with_related_data(
    session: AsyncSession,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> List[Case]:
    """Fetch cases with related alerts, assets, tags, and comments."""
    query = select(Case).options(
        selectinload(Case.alerts)
        .selectinload(CaseAlertLink.alert)
        .options(selectinload(Alert.assets), selectinload(Alert.tags).selectinload(AlertToTag.tag), selectinload(Alert.comments)),
    )
    if year and month:
        start, end = _build_month_range(year, month)
        query = query.where(Case.case_creation_time >= start, Case.case_creation_time <= end)
    result = await session.execute(query)
    return result.scalars().all()


async def fetch_cases_by_customer(
    session: AsyncSession,
    customer_code: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> List[Case]:
    """Fetch cases for a specific customer with related data."""
    query = (
        select(Case)
        .where(Case.customer_code == customer_code)
        .options(
            selectinload(Case.alerts)
            .selectinload(CaseAlertLink.alert)
            .options(selectinload(Alert.assets), selectinload(Alert.tags).selectinload(AlertToTag.tag), selectinload(Alert.comments)),
        )
    )
    if year and month:
        start, end = _build_month_range(year, month)
        query = query.where(Case.case_creation_time >= start, Case.case_creation_time <= end)
    result = await session.execute(query)
    return result.scalars().all()


async def fetch_case_by_id(session: AsyncSession, case_id: int) -> Case:
    """Fetch a case by its ID."""
    result = await session.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.alerts)
            .selectinload(CaseAlertLink.alert)
            .options(
                selectinload(Alert.assets).selectinload(Asset.alert_context),  # Load alert_context
                selectinload(Alert.tags).selectinload(AlertToTag.tag),  # Load tags
                selectinload(Alert.comments),  # Load comments
                selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),  # Load IoCs
            ),
        ),
    )
    return result.scalars().first()


def serialize_case_alert_to_row(case: Case, alert: Alert) -> Dict[str, Any]:
    """Serialize a case and its alert into a CSV row."""
    assets = ";".join(asset.asset_name for asset in alert.assets or [])
    tags = ";".join(alert_tag.tag.tag for alert_tag in alert.tags or [])
    comments = ";".join(comment.comment for comment in alert.comments or [])

    return {
        "Case ID": case.id,
        "Case Name": case.case_name,
        "Case Description": case.case_description,
        "Case Creation Time": case.case_creation_time.strftime("%Y-%m-%d %H:%M:%S"),
        "Case Status": case.case_status,
        "Case Closed Time": case.case_closed_time.strftime("%Y-%m-%d %H:%M:%S") if case.case_closed_time else "",
        "Case Assigned To": case.assigned_to or "",
        "Case Customer Code": case.customer_code or "",
        "Alert ID": alert.id,
        "Alert Name": alert.alert_name,
        "Alert Description": alert.alert_description,
        "Alert Status": alert.status,
        "Alert Creation Time": alert.alert_creation_time.strftime("%Y-%m-%d %H:%M:%S"),
        "Alert Time Closed": alert.time_closed.strftime("%Y-%m-%d %H:%M:%S") if alert.time_closed else "",
        "Alert Source": alert.source,
        "Alert Assigned To": alert.assigned_to or "",
        "Assets": assets,
        "Tags": tags,
        "Comments": comments,
        "Customer Code": alert.customer_code,
    }


def generate_csv_content(rows: List[Dict[str, Any]]) -> StringIO:
    """Generate CSV content from rows."""
    csv_stream = StringIO()
    writer = csv.DictWriter(csv_stream, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    csv_stream.seek(0)
    return csv_stream


# Route Handler
@incidents_report_router.post(
    "/generate-report-csv",
    description="Generate a report for all cases. Optionally filter by year and month.",
)
async def get_cases_export_all_route(
    year: Optional[int] = Query(None, description="Filter by year (e.g. 2026)", ge=2000, le=2100),
    month: Optional[int] = Query(None, description="Filter by month (1-12)", ge=1, le=12),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if (year is None) != (month is None):
        raise HTTPException(status_code=400, detail="Both year and month must be provided together")
    cases = await fetch_cases_with_related_data(session, year=year, month=month)
    rows = [serialize_case_alert_to_row(case, alert_link.alert) for case in cases for alert_link in case.alerts]
    csv_stream = generate_csv_content(rows)
    month_suffix = f"_{year}-{month:02d}" if year and month else ""
    filename = f"cases_export{month_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = StreamingResponse(csv_stream, media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@incidents_report_router.post(
    "/generate-report-csv/{customer_code}",
    description="Generate a report for a customer. Optionally filter by year and month.",
)
async def get_cases_export_customer_route(
    customer_code: str,
    year: Optional[int] = Query(None, description="Filter by year (e.g. 2026)", ge=2000, le=2100),
    month: Optional[int] = Query(None, description="Filter by month (1-12)", ge=1, le=12),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if (year is None) != (month is None):
        raise HTTPException(status_code=400, detail="Both year and month must be provided together")
    await get_customer(customer_code=customer_code, session=session)
    cases = await fetch_cases_by_customer(session, customer_code, year=year, month=month)
    rows = [serialize_case_alert_to_row(case, alert_link.alert) for case in cases for alert_link in case.alerts]
    csv_stream = generate_csv_content(rows)
    month_suffix = f"_{year}-{month:02d}" if year and month else ""
    filename = f"cases_export_{customer_code}{month_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = StreamingResponse(csv_stream, media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@incidents_report_router.post(
    "/generate-report-docx",
    description="Generate a docx report for a case.",
)
async def get_cases_export_docx_route(
    request: CaseDownloadDocxRequest,
    session: AsyncSession = Depends(get_db),
) -> FileResponse:
    case = await fetch_case_by_id(session, request.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="No cases found")

    context = create_case_context(case)

    template_file_content = await download_template(request.template_name)
    tmp_template_name = save_template_to_tempfile(template_file_content)

    rendered_file_name = render_document_with_context(tmp_template_name, context)

    response = create_file_response(file_path=rendered_file_name, file_name=request.file_name)

    # Clean up temporary files
    cleanup_temp_files([tmp_template_name])

    return response


@incidents_report_router.post(
    "/generate-report-pdf",
    description="Generate a PDF report for a case.",
)
async def get_cases_export_pdf_route(
    request: CaseDownloadDocxRequest,
    session: AsyncSession = Depends(get_db),
) -> FileResponse:
    case = await fetch_case_by_id(session, request.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="No cases found")

    context = create_case_context_pdf(case)

    # Download and save the template
    tmp_template_name = await download_template_pdf(request.template_name)

    # Render the HTML template with the context
    rendered_html_file_name = render_html_template(tmp_template_name, context)

    # Convert HTML to PDF using WeasyPrint
    rendered_pdf_file_name = convert_html_to_pdf(rendered_html_file_name)

    # Create the FileResponse for PDF
    response = create_file_response_pdf(file_path=rendered_pdf_file_name, file_name=request.file_name.replace(".docx", ".pdf"))

    # Clean up temporary files
    cleanup_temp_files([tmp_template_name, rendered_html_file_name])

    return response


# ! TODO: ROUTE FOR MARKDOWN TEMPLATE ! #
