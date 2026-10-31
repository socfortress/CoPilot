"""The SOC side of Talon portal chat, under ``/api/talon/v2`` (talon-analyst SPEC D97, §5.3; plan PC-3).

- ``GET /portal_review/threads?customer_code=`` and ``GET /portal_review/threads/{id}/messages``:
  the review proxy (FR-API-43, -44), for admins, and analysts and responders (a responder's token
  carries ``analyst``) with unrestricted tag access for the customer.
- ``POST /portal/ioc_lookups`` and ``POST /portal/ioc_lookups/{id}/complete``: the lookup meter, for
  the Talon service account only (an analyst by role, recognised as ``talon_service_account`` does).

Behind the "Talon v2" setting like every other ``/talon/v2`` proxy route (404 while it is off, after
the scope check). Refusals other than the token's are ``{"detail", "code"}`` (``portal_errors``).
"""
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Query
from fastapi import Request
from fastapi import Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.services import talon_portal as service
from app.connectors.talon.services import talon_v2
from app.connectors.talon.utils.portal_errors import coded
from app.customer_portal.services.talon_chat_proxy import read_json
from app.db.db_session import get_db

talon_portal_router = APIRouter(
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(talon_v2.require_talon_v2()),
    ],
)


# ── the review proxy ──────────────────────────────────────────────────────────


@talon_portal_router.get(
    "/portal_review/threads",
    response_class=Response,
    description="One customer's Talon portal chat threads, for a SOC reviewer (read-only, audited by Talon)",
)
async def review_portal_threads(
    customer_code: Optional[str] = Query(None, max_length=64),
    status: Optional[str] = Query(None),
    limit: Optional[str] = Query(None),
    cursor: Optional[str] = Query(None),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    if status is not None and status not in ("active", "archived", "all"):
        return coded("invalid_request")
    if limit is not None and not (limit.isdigit() and 1 <= int(limit) <= 200):
        return coded("invalid_request")
    if cursor is not None and not 1 <= len(cursor) <= 256:
        return coded("invalid_request")
    params = {"status": status, "limit": int(limit) if limit else None, "cursor": cursor}
    return await service.review_threads(current_user, session, customer_code, params)


@talon_portal_router.get(
    "/portal_review/threads/{thread_id}/messages",
    response_class=Response,
    description="A page of one Talon portal chat thread's transcript, for a SOC reviewer (read-only, audited by Talon)",
)
async def review_portal_thread_messages(
    thread_id: str,
    limit: Optional[str] = Query(None),
    before: Optional[str] = Query(None),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    if limit is not None and not (limit.isdigit() and 1 <= int(limit) <= 100):
        return coded("invalid_request")
    if before is not None and not 1 <= len(before) <= 64:
        return coded("invalid_request")
    return await service.review_messages(current_user, session, thread_id, {"limit": int(limit) if limit else None, "before": before})


# ── the lookup meter (the Talon service account only) ─────────────────────────


@talon_portal_router.post(
    "/portal/ioc_lookups",
    response_class=Response,
    status_code=201,
    description="Reserve one of a customer's portal IOC lookups for a Talon portal chat intel call (the Talon service account only)",
)
async def reserve_portal_ioc_lookup(
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await service.require_service_account(current_user, session)
    body = await read_json(request)
    if isinstance(body, JSONResponse):
        return body
    if not isinstance(body, dict):
        return coded("invalid_request")
    return await service.reserve(current_user, session, body)


@talon_portal_router.post(
    "/portal/ioc_lookups/{lookup_id}/complete",
    response_class=Response,
    status_code=204,
    description="Complete a reserved portal IOC lookup: answered keeps it counted, unanswered gives it back (the Talon service account only)",
)
async def complete_portal_ioc_lookup(
    request: Request,
    lookup_id: int = Path(..., ge=1, le=2_147_483_647),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await service.require_service_account(current_user, session)
    body = await read_json(request)
    if isinstance(body, JSONResponse):
        return body
    if not isinstance(body, dict):
        return coded("invalid_request")
    return await service.complete(current_user, session, lookup_id, body)
