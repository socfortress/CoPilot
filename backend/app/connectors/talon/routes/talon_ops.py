"""The Talon Ops tab's routes, under ``/api/talon/ops`` (``services/talon_ops.py``; talon-analyst
SPEC §5.7, D96; plan OJ-5).

Admins and analysts (a responder's token carries ``analyst``), the roles that see the Memory tab,
then the "Talon v2" setting: with it off every route answers 404 ``{"detail": "Not Found"}`` like an
unknown path (``require_talon_v2``, after the scope check). Run now is an admin's, checked by the
database role in the service. The actor of an action is the signed-in user; no body field names
one. Every answer is ``no-store``.
"""
from typing import Literal
from typing import Optional

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.schema.talon_ops import TalonOpsActionRequest
from app.connectors.talon.schema.talon_ops import TalonOpsFindingPage
from app.connectors.talon.schema.talon_ops import TalonOpsFindingResponse
from app.connectors.talon.schema.talon_ops import TalonOpsJobs
from app.connectors.talon.schema.talon_ops import TalonOpsMuteRequest
from app.connectors.talon.schema.talon_ops import TalonOpsRunNow
from app.connectors.talon.schema.talon_ops import TalonOpsRuns
from app.connectors.talon.schema.talon_ops import TalonOpsSummary
from app.connectors.talon.services import talon_ops as service
from app.connectors.talon.services.talon_v2 import require_talon_v2
from app.db.db_session import get_db

talon_ops_router = APIRouter(
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(require_talon_v2()),
    ],
)


def _no_store(response: Response) -> None:
    response.headers.update(service.NO_STORE)


@talon_ops_router.get(
    "/summary",
    response_model=TalonOpsSummary,
    description="Open ops finding counts by severity, job and customer, of the caller's customers only",
)
async def ops_summary(
    response: Response,
    job: Optional[str] = Query(None, max_length=64),
    customer_code: Optional[str] = Query(None, max_length=64),
    platform: bool = Query(False, description="Platform findings only (users with every customer)"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.summary(current_user, session, job=job, customer_code=customer_code, platform=platform)


@talon_ops_router.get(
    "/findings",
    response_model=TalonOpsFindingPage,
    description="A page of Talon's ops findings: newest change first (order=recent), or high severity first (order=severity)",
)
async def list_ops_findings(
    response: Response,
    job: Optional[str] = Query(None, max_length=64),
    customer_code: Optional[str] = Query(None, max_length=64),
    status: Optional[str] = Query(None, max_length=16),
    severity: Optional[str] = Query(None, max_length=16),
    platform: bool = Query(False, description="Platform findings only (users with every customer)"),
    limit: Optional[int] = Query(None, description=f"1 to {service.MAX_LIMIT}; default {service.DEFAULT_LIMIT}"),
    cursor: Optional[str] = Query(None, max_length=128),
    order: Literal["recent", "severity"] = Query("recent", description="recent: newest change first; severity: high first, then last seen"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.list_findings(
        current_user,
        session,
        job=job,
        customer_code=customer_code,
        status=status,
        severity=severity,
        platform=platform,
        limit=limit,
        cursor=cursor,
        order=order,
    )


@talon_ops_router.get("/findings/{finding_id}", response_model=TalonOpsFindingResponse, description="One ops finding")
async def get_ops_finding(
    finding_id: int,
    response: Response,
    customer_code: Optional[str] = Query(None, max_length=64),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.get_finding(current_user, session, finding_id, customer_code)


@talon_ops_router.post(
    "/findings/{finding_id}/acknowledge",
    response_model=TalonOpsFindingResponse,
    description="Acknowledge an open or muted finding, as the signed-in user (audited)",
)
async def acknowledge_ops_finding(
    finding_id: int,
    request: Request,
    response: Response,
    body: Optional[TalonOpsActionRequest] = Body(None),
    customer_code: Optional[str] = Query(None, max_length=64),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.act(current_user, session, finding_id, "acknowledge", customer_code=customer_code, request=request)


@talon_ops_router.post(
    "/findings/{finding_id}/mute",
    response_model=TalonOpsFindingResponse,
    description="Mute a finding until a time (in the future, at most 90 days), as the signed-in user (audited)",
)
async def mute_ops_finding(
    finding_id: int,
    body: TalonOpsMuteRequest,
    request: Request,
    response: Response,
    customer_code: Optional[str] = Query(None, max_length=64),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.act(current_user, session, finding_id, "mute", until=body.until, customer_code=customer_code, request=request)


@talon_ops_router.post(
    "/findings/{finding_id}/reopen",
    response_model=TalonOpsFindingResponse,
    description="Reopen an acknowledged or muted finding, as the signed-in user (audited)",
)
async def reopen_ops_finding(
    finding_id: int,
    request: Request,
    response: Response,
    body: Optional[TalonOpsActionRequest] = Body(None),
    customer_code: Optional[str] = Query(None, max_length=64),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.act(current_user, session, finding_id, "reopen", customer_code=customer_code, request=request)


@talon_ops_router.get("/jobs", response_model=TalonOpsJobs, description="Every ops job: schedule, last run, next run")
async def list_ops_jobs(
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.list_jobs(current_user, session)


@talon_ops_router.get("/runs", response_model=TalonOpsRuns, description="Recent ops runs of the caller's customers, newest first")
async def list_ops_runs(
    response: Response,
    job: Optional[str] = Query(None, max_length=64),
    customer_code: Optional[str] = Query(None, max_length=64),
    limit: Optional[int] = Query(None),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.list_runs(current_user, session, job=job, customer_code=customer_code, limit=limit)


@talon_ops_router.post(
    "/jobs/{name}/run",
    response_model=TalonOpsRunNow,
    status_code=202,
    description="Run an enabled ops job now (admin only, audited)",
)
async def run_ops_job_now(
    name: str,
    request: Request,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.run_now(current_user, session, name, request)
