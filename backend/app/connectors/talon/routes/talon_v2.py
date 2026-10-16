"""CoPilot's Talon v2 routes, under ``/api/talon/v2`` (talon-analyst SPEC §5.3, §8 "v2 API"; plan M5-5a).

Two routers:
- ``talon_v2_router``: ``GET /availability`` (admin, analyst; whether the frontend shows the v2
  chat) and ``GET``/``PUT /settings`` (admin only). They answer whatever the setting is: they are
  how it is read and changed.
- ``talon_v2_proxy_router``: the threads, a thread's earlier turns (``/threads/{id}/messages``,
  talon-analyst M5-5t) and the chat stream, for admins and analysts (a responder's token carries
  ``analyst``), behind ``require_talon_v2``: with the setting off every declared route answers 404
  ``{"detail": "Not Found"}``, as if it didn't exist (a method no route declares still answers
  405). The scope check comes first.

The identity talon-analyst sees is computed from the JWT's user on every request
(``services/identity.py``); no header and no body field from the browser carries it.
"""
import uuid
from typing import Literal
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.schema.talon_v2 import TalonV2AvailabilityResponse
from app.connectors.talon.schema.talon_v2 import TalonV2ChatRequest
from app.connectors.talon.schema.talon_v2 import TalonV2SettingsResponse
from app.connectors.talon.schema.talon_v2 import TalonV2SettingsUpdate
from app.connectors.talon.schema.talon_v2 import TalonV2ThreadCreate
from app.connectors.talon.schema.talon_v2 import TalonV2ThreadRename
from app.connectors.talon.services import talon_v2 as service
from app.db.db_session import get_db

talon_v2_router = APIRouter()

talon_v2_proxy_router = APIRouter(
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(service.require_talon_v2()),
    ],
)


# ── the setting ───────────────────────────────────────────────────────────────


@talon_v2_router.get(
    "/availability",
    response_model=TalonV2AvailabilityResponse,
    description="Whether the Talon v2 chat is turned on. Reads the setting only; never calls Talon.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_talon_v2_availability(response: Response, session: AsyncSession = Depends(get_db)) -> TalonV2AvailabilityResponse:
    response.headers.update(service.NO_STORE)
    return await service.get_availability(session)


@talon_v2_router.get(
    "/settings",
    response_model=TalonV2SettingsResponse,
    description="The Talon v2 setting of the Talon connector",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_talon_v2_settings(
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TalonV2SettingsResponse:
    response.headers.update(service.NO_STORE)
    return await service.get_v2_settings(current_user, session)


@talon_v2_router.put(
    "/settings",
    response_model=TalonV2SettingsResponse,
    description="Turn the Talon v2 chat on or off. Turning it on is refused unless talon-analyst's v2 API answers.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def put_talon_v2_settings(
    body: TalonV2SettingsUpdate,
    request: Request,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TalonV2SettingsResponse:
    response.headers.update(service.NO_STORE)
    return await service.update_v2_settings(current_user, session, body.v2_enabled, request)


# ── threads ───────────────────────────────────────────────────────────────────


@talon_v2_proxy_router.get("/threads", description="The caller's own Talon v2 threads, newest activity first")
async def list_talon_v2_threads(
    status: Literal["active", "archived", "all"] = Query("active"),
    limit: Optional[int] = Query(None, ge=1, le=200),
    cursor: Optional[str] = Query(None, min_length=1, max_length=256),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await service.list_threads(current_user, session, {"status": status, "limit": limit, "cursor": cursor})


@talon_v2_proxy_router.post(
    "/threads",
    status_code=201,
    description="A new Talon v2 thread: general, or scoped to one customer the caller has",
)
async def create_talon_v2_thread(
    body: TalonV2ThreadCreate,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await service.create_thread(current_user, session, body)


@talon_v2_proxy_router.patch("/threads/{thread_id}", description="Rename one of the caller's Talon v2 threads")
async def rename_talon_v2_thread(
    thread_id: uuid.UUID,
    body: TalonV2ThreadRename,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await service.rename_thread(current_user, session, thread_id, body)


@talon_v2_proxy_router.get(
    "/threads/{thread_id}/messages",
    description="A page of one of the caller's Talon v2 threads' earlier turns, newest page first",
)
async def list_talon_v2_thread_messages(
    thread_id: uuid.UUID,
    limit: Optional[int] = Query(None, ge=1, le=100),
    before: Optional[str] = Query(None, min_length=1, max_length=64),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await service.thread_messages(current_user, session, thread_id, {"limit": limit, "before": before})


@talon_v2_proxy_router.delete("/threads/{thread_id}", description="Archive one of the caller's Talon v2 threads")
async def archive_talon_v2_thread(
    thread_id: uuid.UUID,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await service.archive_thread(current_user, session, thread_id)


# ── chat ──────────────────────────────────────────────────────────────────────


@talon_v2_proxy_router.post(
    "/chat/{thread_id}",
    response_class=Response,
    description="Send one message to a Talon v2 thread and stream the answer (Vercel AI UI message stream)",
)
async def talon_v2_chat(
    thread_id: uuid.UUID,
    body: TalonV2ChatRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    return await service.chat(current_user, session, thread_id, body)
