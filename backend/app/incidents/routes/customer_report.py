import io
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.routes.auth import AuthHandler
from app.db.db_session import get_db
from app.db.db_session import get_db_session
from app.db.universal_models import Customers
from app.db.universal_models import IncidentManagementCustomerReport
from app.incidents.schema.customer_report import (
    CustomerReportGenerateBackgroundResponse,
)
from app.incidents.schema.customer_report import CustomerReportGenerateRequest
from app.incidents.schema.customer_report import CustomerReportListResponse
from app.incidents.schema.customer_report import CustomerReportVisibilityRequest
from app.incidents.services.customer_report import delete_customer_report
from app.incidents.services.customer_report import generate_customer_report
from app.incidents.services.customer_report import get_customer_report_download
from app.incidents.services.customer_report import list_customer_reports
from app.incidents.services.customer_report import resolve_user_names
from app.incidents.services.customer_report import set_report_visibility
from app.incidents.services.customer_report import to_response
from app.middleware.customer_access import customer_access_handler

customer_reports_router = APIRouter()


async def _require_report(session: AsyncSession, report_id: int) -> IncidentManagementCustomerReport:
    result = await session.execute(
        select(IncidentManagementCustomerReport).where(IncidentManagementCustomerReport.id == report_id),
    )
    report = result.scalars().first()
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    return report


async def _ensure_customer_access(user: User, session: AsyncSession, customer_code: str) -> None:
    if not await customer_access_handler.check_customer_access(user, customer_code, session):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")


@customer_reports_router.post(
    "/generate/background",
    response_model=CustomerReportGenerateBackgroundResponse,
    description="Queue generation of a customer Incident-Management PDF report (aggregated over a date range).",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def generate_report_background(
    request: CustomerReportGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerReportGenerateBackgroundResponse:
    """Create a ``processing`` placeholder row, then render the PDF in the background.

    The client polls ``GET /`` until ``status`` flips to ``completed``/``failed``,
    then downloads via ``GET /{report_id}/download``.
    """
    await _ensure_customer_access(current_user, db, request.customer_code)

    # Verify the customer exists up front so the caller gets a clean 404.
    customer_result = await db.execute(select(Customers).where(Customers.customer_code == request.customer_code))
    if customer_result.scalars().first() is None:
        raise HTTPException(status_code=404, detail=f"Customer {request.customer_code} not found")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_name = request.report_name or f"incident_report_{timestamp}"

    role_name = None
    try:
        role_name = {
            RoleEnum.admin: "admin",
            RoleEnum.analyst: "analyst",
            RoleEnum.scheduler: "scheduler",
            RoleEnum.customer_user: "customer_user",
        }.get(RoleEnum(current_user.role_id))
    except (ValueError, TypeError):
        role_name = None

    report_record = IncidentManagementCustomerReport(
        report_name=report_name,
        customer_code=request.customer_code,
        bucket_name="incident-management-reports",
        object_key=f"{request.customer_code}/{report_name}_{timestamp}.pdf",
        file_name=f"{report_name}.pdf",
        file_size=0,
        file_hash="pending",
        generated_by=current_user.id,
        generated_by_role=role_name,
        date_from=request.date_from,
        date_to=request.date_to,
        filters_json=json.dumps(
            {
                "date_from": request.date_from.isoformat(),
                "date_to": request.date_to.isoformat(),
                "brand_theme": request.brand_theme,
                "report_template": request.report_template,
            },
        ),
        # Customer-generated reports are always visible to the customer; otherwise
        # honour the analyst/admin's choice from the generation form.
        visible_to_customer=(role_name == "customer_user") or request.visible_to_customer,
        status="processing",
    )
    db.add(report_record)
    await db.commit()
    await db.refresh(report_record)
    report_id = report_record.id

    async def generate_task() -> None:
        try:
            async with get_db_session() as bg_db:
                await generate_customer_report(bg_db, current_user, request, report_id=report_id)
        except Exception as e:  # noqa: BLE001 - status already persisted as failed by the service
            logger.error(f"Background incident report generation failed (ID: {report_id}): {e}")

    background_tasks.add_task(generate_task)

    return CustomerReportGenerateBackgroundResponse(
        success=True,
        message="Report generation queued successfully",
        report_id=report_id,
        report_name=report_name,
        customer_code=request.customer_code,
        status="processing",
        check_status_url="/api/v1/incidents/customer_reports",
        download_url=f"/api/v1/incidents/customer_reports/{report_id}/download",
    )


@customer_reports_router.get(
    "",
    response_model=CustomerReportListResponse,
    description="List customer Incident-Management reports (scoped to the user's accessible customers).",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_reports(
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerReportListResponse:
    accessible = await customer_access_handler.get_user_accessible_customers(current_user, db)
    # A customer_user (portal) only sees their own reports plus analyst/admin reports
    # explicitly flagged visible; analysts/admins (CoPilot) see everything.
    only_customer_visible = current_user.role_id == RoleEnum.customer_user
    reports = await list_customer_reports(db, accessible, customer_code, only_customer_visible=only_customer_visible)
    names = await resolve_user_names(db, [r.generated_by for r in reports])
    items = [to_response(r, names.get(r.generated_by)) for r in reports]
    return CustomerReportListResponse(
        reports=items,
        total_count=len(items),
        success=True,
        message="Reports retrieved successfully",
    )


@customer_reports_router.get(
    "/{report_id}/download",
    description="Download a customer Incident-Management report PDF.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def download_report(
    report_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    report = await _require_report(db, report_id)
    await _ensure_customer_access(current_user, db, report.customer_code)
    # A customer_user may only download reports they are allowed to see.
    if current_user.role_id == RoleEnum.customer_user and not (report.visible_to_customer or report.generated_by_role == "customer_user"):
        raise HTTPException(status_code=403, detail="This report is not available.")
    if report.status != "completed":
        raise HTTPException(status_code=409, detail=f"Report is not ready to download (status: {report.status})")

    data = await get_customer_report_download(db, report)
    return StreamingResponse(
        io.BytesIO(data["file_content"]),
        media_type=data["content_type"],
        headers={"Content-Disposition": f'attachment; filename="{data["file_name"]}"'},
    )


@customer_reports_router.delete(
    "/{report_id}",
    response_model=dict,
    description="Delete a customer Incident-Management report (admin, or the user who generated it).",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def delete_report(
    report_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    report = await _require_report(db, report_id)
    await _ensure_customer_access(current_user, db, report.customer_code)

    is_admin = current_user.role_id == RoleEnum.admin
    is_creator = report.generated_by == current_user.id
    if not (is_admin or is_creator):
        raise HTTPException(status_code=403, detail="Only an admin or the report creator can delete this report")

    report_name = report.report_name
    customer_code = report.customer_code
    await delete_customer_report(db, report)
    logger.info(f"Deleted incident report {report_id} ({report_name}) for customer {customer_code}")
    return {
        "success": True,
        "message": f"Report '{report_name}' deleted successfully",
        "report_id": report_id,
        "report_name": report_name,
        "customer_code": customer_code,
    }


@customer_reports_router.patch(
    "/{report_id}/visibility",
    response_model=dict,
    description="Set whether an analyst/admin report is visible to the customer portal (analyst/admin only).",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def set_report_visibility_endpoint(
    report_id: int,
    request: CustomerReportVisibilityRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    report = await _require_report(db, report_id)
    await _ensure_customer_access(current_user, db, report.customer_code)

    # Customer-generated reports are always visible to the customer; the flag only
    # applies to analyst/admin reports.
    if report.generated_by_role == "customer_user":
        raise HTTPException(status_code=400, detail="Customer-generated reports are always visible to the customer.")

    await set_report_visibility(db, report, request.visible)
    logger.info(
        f"{current_user.username} set report {report_id} visible_to_customer={request.visible} " f"for customer {report.customer_code}",
    )
    return {
        "success": True,
        "message": ("Report is now visible to the customer." if request.visible else "Report is now hidden from the customer."),
        "report_id": report_id,
        "visible_to_customer": request.visible,
    }
