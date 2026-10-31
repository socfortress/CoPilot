"""Talon chat in the Customer Portal (talon-analyst SPEC D97, §5.3 "Portal chat: CoPilot's side";
plan PC-3), under ``/api/customer_portal/talon_chat``.

Three audiences:

* **Operators** read a customer's switches (admin, analyst) and change them (admin only, by the
  token's scope and the database role, audited) under ``/talon_chat/settings/{customer_code}``.
* **Everyone who may see the portal's pages** asks ``/talon_chat/availability`` whether "Ask Talon"
  shows.
* **Portal users** (``customer_user`` only) reach talon-analyst's portal chat through the proxy:
  threads, a thread's turns, the stream, feedback and the drafts. The switch is checked on every
  request (``services/talon_chat_proxy.py``), and the draft submit files through the portal's own
  "Ask the SOC" service (``services/talon_chat_drafts.py``).

Every refusal of these routes is ``{"detail", "code"}`` with a code from talon-analyst's table
(``connectors/talon/utils/portal_errors``), plus two of CoPilot's own on the settings routes
(``admin_only``, ``customer_not_found``). The exceptions are the token's own refusals (401, and 403
for a role the route doesn't take: the shared ``AuthHandler``) and an unexpected failure
(``internal_errors``' 500).
Bodies and path ids are checked in the services for the same reason. Static paths before those with
a parameter under the same prefix.
"""
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import Security
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.services.identity import is_talon_customer_code
from app.connectors.talon.utils.portal_errors import NO_STORE
from app.connectors.talon.utils.portal_errors import coded
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.talon_chat import PortalChatAvailabilityResponse
from app.customer_portal.schema.talon_chat import PortalChatSettings
from app.customer_portal.schema.talon_chat import PortalChatSettingsResponse
from app.customer_portal.schema.talon_chat import UpdatePortalChatSettingsRequest
from app.customer_portal.services import talon_chat
from app.customer_portal.services import talon_chat_drafts as drafts
from app.customer_portal.services import talon_chat_proxy as proxy
from app.customer_portal.services.ai_reports import is_ai_reports_enabled
from app.db.db_session import get_db
from app.db.universal_models import Customers
from app.middleware.customer_access import customer_access_handler

customer_portal_talon_chat_router = APIRouter()

PORTAL = Security(AuthHandler().require_any_scope("customer_user"))
SOC = Security(AuthHandler().require_any_scope("admin", "analyst"))
ADMIN = Security(AuthHandler().require_any_scope("admin"))
EVERYONE = Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))


def _settings_schema(customer_code: str, row) -> PortalChatSettings:
    values = talon_chat.values_of(row)
    return PortalChatSettings(
        customer_code=customer_code,
        **values,
        version=row.version if row is not None else None,
        updated_at=row.updated_at.isoformat() if row is not None and row.updated_at else None,
        updated_by=row.updated_by if row is not None else None,
    )


# --- Operator-facing switches ---


@customer_portal_talon_chat_router.get(
    "/talon_chat/settings/{customer_code}",
    response_model=PortalChatSettingsResponse,
    description="A customer's Talon portal chat switches and daily message limits, with the form's proposed limits",
    dependencies=[SOC],
)
async def get_portal_chat_settings(
    customer_code: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    # The access check here, not ``verify_customer_code_access``, so its refusal is coded too.
    if not await customer_access_handler.check_customer_access(current_user, customer_code, session):
        return coded("customer_not_accessible")
    async with internal_errors("read the portal chat settings"):
        row = await talon_chat.get_settings(customer_code, session)
        ai_reports = await is_ai_reports_enabled(customer_code, session)
    answer = PortalChatSettingsResponse(settings=_settings_schema(customer_code, row), ai_reports_enabled=ai_reports)
    return JSONResponse(answer.model_dump(), headers=NO_STORE)


@customer_portal_talon_chat_router.put(
    "/talon_chat/settings/{customer_code}",
    response_model=PortalChatSettingsResponse,
    description=(
        "Turn Talon portal chat and its log search on or off for a customer, and set the daily message limits (admin only, audited). "
        "Turning the chat on needs the customer's AI reports on and a daily message limit."
    ),
    dependencies=[ADMIN],
)
async def put_portal_chat_settings(
    customer_code: str,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    # The database role too: a token issued before a demotion still carries the admin scope.
    if current_user.role_id != RoleEnum.admin.value:
        return coded("admin_only")
    body = await proxy.read_body(request, UpdatePortalChatSettingsRequest)
    if isinstance(body, JSONResponse):
        return body
    exists = await session.execute(select(Customers.customer_code).where(Customers.customer_code == customer_code))
    if customer_code not in set(exists.scalars().all()):
        return coded("customer_not_found")
    async with internal_errors("save the portal chat settings", session):
        row, problem = await talon_chat.save_settings(customer_code, body.model_dump(), current_user, session)
        ai_reports = await is_ai_reports_enabled(customer_code, session)
    if problem is not None:
        return JSONResponse({"detail": problem, "code": "invalid_request"}, status_code=422, headers=NO_STORE)
    answer = PortalChatSettingsResponse(
        settings=_settings_schema(customer_code, row),
        ai_reports_enabled=ai_reports,
        message="Portal chat settings saved",
    )
    return JSONResponse(answer.model_dump(), headers=NO_STORE)


# --- Availability ---


@customer_portal_talon_chat_router.get(
    "/talon_chat/availability",
    response_model=PortalChatAvailabilityResponse,
    description="Whether 'Ask Talon' shows in the portal for the caller (or one of their customers), and what it may offer",
    dependencies=[EVERYONE],
)
async def get_portal_chat_availability(
    customer_code: Optional[str] = Query(None, max_length=64),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    if customer_code is not None:
        if not is_talon_customer_code(customer_code) or not await customer_access_handler.check_customer_access(
            current_user,
            customer_code,
            session,
        ):
            return coded("customer_not_accessible")
    async with internal_errors("resolve the portal chat availability"):
        found = await talon_chat.availability(current_user, session, customer_code)
    answer = PortalChatAvailabilityResponse(
        customer_code=found.customer_code,
        enabled=found.enabled,
        log_search=found.log_search,
        can_draft=found.can_draft,
        can_request_analysis=found.can_request_analysis,
        message="Portal chat is available" if found.enabled else "Portal chat is not available",
    )
    return JSONResponse(answer.model_dump(), headers=NO_STORE)


# --- The portal proxy (customer_user only) ---


@customer_portal_talon_chat_router.get(
    "/talon_chat/threads",
    description="The caller's portal chat threads (FR-API-33)",
    dependencies=[PORTAL],
)
async def list_portal_chat_threads(
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
    return await proxy.list_threads(current_user, session, {"status": status, "limit": int(limit) if limit else None, "cursor": cursor})


@customer_portal_talon_chat_router.post(
    "/talon_chat/threads",
    description="A new portal chat thread for one of the caller's customers (FR-API-34)",
    dependencies=[PORTAL],
)
async def create_portal_chat_thread(
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await proxy.create_thread(current_user, session, request)


@customer_portal_talon_chat_router.patch(
    "/talon_chat/threads/{thread_id}",
    description="Rename one of the caller's portal chat threads (FR-API-35)",
    dependencies=[PORTAL],
)
async def rename_portal_chat_thread(
    thread_id: str,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await proxy.rename_thread(current_user, session, thread_id, request)


@customer_portal_talon_chat_router.delete(
    "/talon_chat/threads/{thread_id}",
    description="Archive one of the caller's portal chat threads (FR-API-36)",
    dependencies=[PORTAL],
)
async def archive_portal_chat_thread(
    thread_id: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await proxy.archive_thread(current_user, session, thread_id)


@customer_portal_talon_chat_router.get(
    "/talon_chat/threads/{thread_id}/messages",
    description="A page of one of the caller's portal chat threads' earlier turns (FR-API-37)",
    dependencies=[PORTAL],
)
async def portal_chat_thread_messages(
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
    return await proxy.thread_messages(current_user, session, thread_id, {"limit": int(limit) if limit else None, "before": before})


@customer_portal_talon_chat_router.post(
    "/talon_chat/threads/{thread_id}/feedback",
    description="Thumbs up or down on a completed turn of one of the caller's portal chat threads (FR-API-42)",
    dependencies=[PORTAL],
)
async def portal_chat_feedback(
    thread_id: str,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await proxy.feedback(current_user, session, thread_id, request)


@customer_portal_talon_chat_router.post(
    "/talon_chat/chat/{thread_id}",
    response_class=Response,
    description="Send one message to a portal chat thread and stream the answer (FR-API-38, the Vercel AI UI message stream)",
    dependencies=[PORTAL],
)
async def portal_chat(
    thread_id: str,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await proxy.chat(current_user, session, thread_id, request)


@customer_portal_talon_chat_router.get(
    "/talon_chat/drafts/{draft_id}",
    description="A question for the SOC that Talon drafted in the caller's thread (FR-API-39)",
    dependencies=[PORTAL],
)
async def get_portal_chat_draft(
    draft_id: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await proxy.get_draft(current_user, session, draft_id)


@customer_portal_talon_chat_router.post(
    "/talon_chat/drafts/{draft_id}/submit",
    description="Send a Talon draft, as edited, to the SOC: claimed, filed as an 'Ask the SOC' question, then reported back",
    dependencies=[PORTAL],
)
async def submit_portal_chat_draft(
    draft_id: str,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await drafts.submit(current_user, session, draft_id, request)


@customer_portal_talon_chat_router.post(
    "/talon_chat/drafts/{draft_id}/discard",
    description="Discard a Talon draft (FR-API-41 discarded)",
    dependencies=[PORTAL],
)
async def discard_portal_chat_draft(
    draft_id: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await proxy.discard_draft(current_user, session, draft_id)
