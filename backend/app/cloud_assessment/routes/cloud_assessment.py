"""Cloud security assessment routes (#1328), under ``/api/cloud_assessment``.

Admins and analysts, for their own customers (``verify_customer_code_access`` on every route
naming one; an account or scan of another customer is a 404). Adding, changing or deleting an
account (its credential) and deleting a scan are an admin's, by the token's scope and the user's
role in the database. Starting, cancelling and testing are an analyst's too, but never the Talon
service account's (it acts with a customer's cloud credentials). No customer portal route.
"""

from typing import List
from typing import Literal
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Security
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.cloud_assessment.schema.cloud_assessment import SCAN_STATUSES
from app.cloud_assessment.schema.cloud_assessment import SEVERITIES
from app.cloud_assessment.schema.cloud_assessment import AccountCreate
from app.cloud_assessment.schema.cloud_assessment import AccountDeleteResponse
from app.cloud_assessment.schema.cloud_assessment import AccountListResponse
from app.cloud_assessment.schema.cloud_assessment import AccountResponse
from app.cloud_assessment.schema.cloud_assessment import AccountUpdate
from app.cloud_assessment.schema.cloud_assessment import AvailabilityResponse
from app.cloud_assessment.schema.cloud_assessment import CheckListResponse
from app.cloud_assessment.schema.cloud_assessment import ComplianceDetailResponse
from app.cloud_assessment.schema.cloud_assessment import ComplianceListResponse
from app.cloud_assessment.schema.cloud_assessment import ConnectionTestResponse
from app.cloud_assessment.schema.cloud_assessment import FindingListResponse
from app.cloud_assessment.schema.cloud_assessment import ScanDeleteResponse
from app.cloud_assessment.schema.cloud_assessment import ScanListResponse
from app.cloud_assessment.schema.cloud_assessment import ScanResponse
from app.cloud_assessment.services import accounts as account_service
from app.cloud_assessment.services import reports
from app.cloud_assessment.services import results
from app.cloud_assessment.services import scans as scan_service
from app.cloud_assessment.services.availability import availability
from app.cloud_assessment.services.crypto import key_configured
from app.cloud_assessment.services.runner_client import RunnerClient
from app.connectors.talon.services.talon_service_account import (
    refuse_talon_service_account_dependency,
)
from app.db.db_session import get_db
from app.middleware.customer_access import scoped_customer_codes
from app.middleware.customer_access import verify_customer_code_access

cloud_assessment_router = APIRouter()

SOC = [Security(AuthHandler().require_any_scope("admin", "analyst")), Depends(verify_customer_code_access)]
ACT = SOC + [Depends(refuse_talon_service_account_dependency)]
ADMIN = [
    Security(AuthHandler().require_any_scope("admin")),
    Depends(verify_customer_code_access),
    Depends(refuse_talon_service_account_dependency),
]


def _severities(values: Optional[List[str]]) -> Optional[List[str]]:
    if not values:
        return None
    unknown = [value for value in values if value not in SEVERITIES]
    if unknown:
        raise HTTPException(status_code=422, detail=f"severity must be one of {', '.join(SEVERITIES)}")
    return list(dict.fromkeys(values))


@cloud_assessment_router.get(
    "/availability",
    response_model=AvailabilityResponse,
    description="Whether cloud credentials can be stored and scans run, and copilot-prowler's versions.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_availability() -> AvailabilityResponse:
    return await availability()


# --- accounts -----------------------------------------------------------------------------------


@cloud_assessment_router.get(
    "/accounts",
    response_model=AccountListResponse,
    description="Every cloud account of the customers the caller can see, each with its newest scan.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_all_accounts(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> AccountListResponse:
    # The one account route without a {customer_code}: tenancy comes from scoped_customer_codes.
    # [] means "sees nothing", which list_all_accounts answers without a query.
    codes = await scoped_customer_codes(current_user, None, session)
    found = await account_service.list_all_accounts(session, codes)
    return AccountListResponse(
        success=True,
        message=f"{len(found)} cloud account(s)",
        accounts=found,
        encryption_key_configured=key_configured(),
        runner_configured=RunnerClient.from_env().problem() is None,
    )


@cloud_assessment_router.get(
    "/{customer_code}/accounts",
    response_model=AccountListResponse,
    description="The customer's cloud accounts, each with its newest scan.",
    dependencies=SOC,
)
async def list_accounts(customer_code: str, session: AsyncSession = Depends(get_db)) -> AccountListResponse:
    found = await account_service.list_accounts(session, customer_code)
    return AccountListResponse(
        success=True,
        message=f"{len(found)} cloud account(s)",
        accounts=found,
        encryption_key_configured=key_configured(),
        runner_configured=RunnerClient.from_env().problem() is None,
    )


@cloud_assessment_router.post(
    "/{customer_code}/accounts",
    response_model=AccountResponse,
    description="Add a cloud account (admin). An AWS role gets its External ID here.",
    dependencies=ADMIN,
)
async def create_account(
    customer_code: str,
    body: AccountCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> AccountResponse:
    account = await account_service.create_account(session, customer_code, body, current_user, request)
    return AccountResponse(success=True, message="Cloud account added", account=account)


@cloud_assessment_router.get(
    "/{customer_code}/accounts/{account_id}",
    response_model=AccountResponse,
    description="One cloud account.",
    dependencies=SOC,
)
async def get_account(customer_code: str, account_id: int, session: AsyncSession = Depends(get_db)) -> AccountResponse:
    code = await account_service.stored_customer_code(session, customer_code)
    account = await account_service.get_account(session, code, account_id)
    return AccountResponse(success=True, message="Cloud account", account=await account_service.account_out(session, account))


@cloud_assessment_router.put(
    "/{customer_code}/accounts/{account_id}",
    response_model=AccountResponse,
    description="Change a cloud account (admin). Fields not sent stay; a credential not sent stays.",
    dependencies=ADMIN,
)
async def update_account(
    customer_code: str,
    account_id: int,
    body: AccountUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> AccountResponse:
    account = await account_service.update_account(session, customer_code, account_id, body, current_user, request)
    return AccountResponse(success=True, message="Cloud account saved", account=account)


@cloud_assessment_router.delete(
    "/{customer_code}/accounts/{account_id}",
    response_model=AccountDeleteResponse,
    description="Delete a cloud account with its scans, findings and reports (admin).",
    dependencies=ADMIN,
)
async def delete_account(
    customer_code: str,
    account_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> AccountDeleteResponse:
    deleted = await account_service.delete_account(session, customer_code, account_id, current_user, request)
    return AccountDeleteResponse(success=True, message="Cloud account deleted", scans_deleted=deleted)


@cloud_assessment_router.post(
    "/{customer_code}/accounts/{account_id}/test",
    response_model=ConnectionTestResponse,
    description="Check the account's credential through copilot-prowler. Takes up to two minutes.",
    dependencies=ACT,
)
async def test_connection(
    customer_code: str,
    account_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> ConnectionTestResponse:
    return await account_service.test_connection(session, customer_code, account_id, current_user, request)


@cloud_assessment_router.post(
    "/{customer_code}/accounts/{account_id}/scans",
    response_model=ScanResponse,
    description="Scan the account now.",
    dependencies=ACT,
)
async def start_scan(
    customer_code: str,
    account_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> ScanResponse:
    scan = await scan_service.start_scan(session, customer_code, account_id, current_user, request)
    return ScanResponse(success=True, message="Scan started" if scan.status == "running" else "Scan queued", scan=scan)


# --- scans --------------------------------------------------------------------------------------


@cloud_assessment_router.get(
    "/{customer_code}/scans",
    response_model=ScanListResponse,
    description="The customer's scans, newest first.",
    dependencies=SOC,
)
async def list_scans(
    customer_code: str,
    account_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> ScanListResponse:
    if status is not None and status not in SCAN_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {', '.join(SCAN_STATUSES)}")
    found, total = await scan_service.list_scans(session, customer_code, account_id, status, page, page_size)
    return ScanListResponse(success=True, message=f"{total} scan(s)", scans=found, total=total, page=page, page_size=page_size)


@cloud_assessment_router.get(
    "/{customer_code}/scans/{scan_id}",
    response_model=ScanResponse,
    description="One scan, with its counts.",
    dependencies=SOC,
)
async def get_scan(customer_code: str, scan_id: int, session: AsyncSession = Depends(get_db)) -> ScanResponse:
    _, scan, account = await scan_service.scan_with_account(session, customer_code, scan_id)
    return ScanResponse(success=True, message="Scan", scan=await scan_service.scan_detail(session, scan, account))


@cloud_assessment_router.post(
    "/{customer_code}/scans/{scan_id}/cancel",
    response_model=ScanResponse,
    description="Stop a queued or running scan.",
    dependencies=ACT,
)
async def cancel_scan(
    customer_code: str,
    scan_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> ScanResponse:
    scan = await scan_service.cancel_scan(session, customer_code, scan_id, current_user, request)
    return ScanResponse(success=True, message="Scan cancelled", scan=scan)


@cloud_assessment_router.delete(
    "/{customer_code}/scans/{scan_id}",
    response_model=ScanDeleteResponse,
    description="Delete a scan that has ended, with its findings and reports (admin).",
    dependencies=ADMIN,
)
async def delete_scan(
    customer_code: str,
    scan_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> ScanDeleteResponse:
    await scan_service.delete_scan(session, customer_code, scan_id, current_user, request)
    return ScanDeleteResponse(success=True, message="Scan deleted")


@cloud_assessment_router.get(
    "/{customer_code}/scans/{scan_id}/checks",
    response_model=CheckListResponse,
    description="The checks a completed scan ran, worst first.",
    dependencies=SOC,
)
async def list_checks(
    customer_code: str,
    scan_id: int,
    status: Optional[Literal["fail", "manual", "pass"]] = Query(None),
    severity: Optional[List[str]] = Query(None),
    service: Optional[str] = Query(None, max_length=64),
    q: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> CheckListResponse:
    _, scan, _ = await scan_service.scan_with_account(session, customer_code, scan_id)
    found, total, services = await results.list_checks(session, scan, status, _severities(severity), service, q, page, page_size)
    return CheckListResponse(
        success=True,
        message=f"{total} check(s)",
        checks=found,
        total=total,
        page=page,
        page_size=page_size,
        services=services,
    )


@cloud_assessment_router.get(
    "/{customer_code}/scans/{scan_id}/findings",
    response_model=FindingListResponse,
    description="A completed scan's FAIL and MANUAL findings, worst first.",
    dependencies=SOC,
)
async def list_findings(
    customer_code: str,
    scan_id: int,
    severity: Optional[List[str]] = Query(None),
    status: Optional[Literal["FAIL", "MANUAL"]] = Query(None),
    check_id: Optional[str] = Query(None, max_length=128),
    service: Optional[str] = Query(None, max_length=64),
    region: Optional[str] = Query(None, max_length=64),
    muted: Optional[bool] = Query(None),
    new: bool = Query(False, description="Only findings the account's previous scan didn't have"),
    q: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> FindingListResponse:
    _, scan, _ = await scan_service.scan_with_account(session, customer_code, scan_id)
    found, total = await results.list_findings(
        session,
        scan,
        _severities(severity),
        status,
        check_id,
        service,
        region,
        muted,
        new,
        q,
        page,
        page_size,
    )
    return FindingListResponse(success=True, message=f"{total} finding(s)", findings=found, total=total, page=page, page_size=page_size)


@cloud_assessment_router.get(
    "/{customer_code}/scans/{scan_id}/compliance",
    response_model=ComplianceListResponse,
    description="How a completed scan maps onto each compliance framework its checks cover.",
    dependencies=SOC,
)
async def compliance_overview(customer_code: str, scan_id: int, session: AsyncSession = Depends(get_db)) -> ComplianceListResponse:
    _, scan, account = await scan_service.scan_with_account(session, customer_code, scan_id)
    frameworks, catalog = await results.compliance_overview(session, scan, account.provider if account else None)
    return ComplianceListResponse(success=True, message=f"{len(frameworks)} framework(s)", frameworks=frameworks, catalog_available=catalog)


@cloud_assessment_router.get(
    "/{customer_code}/scans/{scan_id}/compliance/{framework_key}",
    response_model=ComplianceDetailResponse,
    description="One framework's requirements, each with its checks and status.",
    dependencies=SOC,
)
async def compliance_detail(
    customer_code: str,
    scan_id: int,
    framework_key: str,
    session: AsyncSession = Depends(get_db),
) -> ComplianceDetailResponse:
    _, scan, account = await scan_service.scan_with_account(session, customer_code, scan_id)
    framework, requirements, catalog = await results.compliance_detail(session, scan, account.provider if account else None, framework_key)
    return ComplianceDetailResponse(
        success=True,
        message="Framework",
        framework=framework,
        requirements=requirements,
        catalog_available=catalog,
    )


@cloud_assessment_router.get(
    "/{customer_code}/scans/{scan_id}/reports/{kind}",
    description="Prowler's HTML or CSV report of a completed scan, as a download.",
    dependencies=SOC,
)
async def download_report(
    customer_code: str,
    scan_id: int,
    kind: Literal["html", "csv"],
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> StreamingResponse:
    code, scan, _ = await scan_service.scan_with_account(session, customer_code, scan_id)
    key = scan.html_object_key if kind == "html" else scan.csv_object_key
    if not scan.report_bucket or not key or scan.findings_pruned_at is not None:
        raise HTTPException(status_code=404, detail="The scan has no such report")
    bucket = scan.report_bucket
    await session.close()
    try:
        chunks = await reports.open_report(bucket, key)
    except Exception as error:  # noqa: BLE001 - MinIO's own error says nothing the analyst can use
        raise HTTPException(status_code=404, detail="The report isn't available") from error
    await account_service.audit(
        AuditAction.CLOUD_ASSESSMENT_REPORT_DOWNLOAD,
        current_user,
        code,
        "cloud_assessment_scan",
        scan_id,
        request,
        new={"scan_id": scan_id, "kind": kind},
    )
    filename = f"prowler-scan-{scan_id}.{kind}"
    return StreamingResponse(
        chunks,
        # A download, never a page of CoPilot's: the report holds names and tags from the customer's
        # cloud, so no browser is told it is HTML (the file name still says what it is).
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Security-Policy": "sandbox",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )
