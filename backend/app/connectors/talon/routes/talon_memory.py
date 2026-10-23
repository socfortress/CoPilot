"""The Talon Memory tab's routes, under ``/api/talon/memory`` (``services/talon_memory.py``).

Admins and analysts (a responder's token carries ``analyst``), then the "Talon v2" setting: with it
off every route answers 404 ``{"detail": "Not Found"}`` like an unknown path (``require_talon_v2``,
after the scope check). The customer in the path is checked against the caller's own customers in
the service; the chat-memory routes take no user id at all, the caller's own is used. Every answer
is ``no-store``.

Paths: ``/chat/mine…`` and ``/{customer_code}/stats|drawers|assets…`` never overlap, whatever a
customer is called (a customer named ``chat`` reads ``/chat/stats``).
"""
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.schema.talon_memory import TalonChatMemory
from app.connectors.talon.schema.talon_memory import TalonMemoryAssets
from app.connectors.talon.schema.talon_memory import TalonMemoryDrawer
from app.connectors.talon.schema.talon_memory import TalonMemoryForgotten
from app.connectors.talon.schema.talon_memory import TalonMemoryPage
from app.connectors.talon.schema.talon_memory import TalonMemoryStats
from app.connectors.talon.schema.talon_memory import TalonMemoryTimeline
from app.connectors.talon.services import talon_memory as service
from app.connectors.talon.services.talon_v2 import require_talon_v2
from app.db.db_session import get_db

talon_memory_router = APIRouter(
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(require_talon_v2()),
    ],
)


def _no_store(response: Response) -> None:
    response.headers.update(service.NO_STORE)


# ── the caller's own chat memory ──────────────────────────────────────────────


@talon_memory_router.get("/chat/mine", response_model=TalonChatMemory, description="The caller's own Talon chat memory")
async def get_my_chat_memory(
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.list_chat_memory(current_user, session)


@talon_memory_router.delete(
    "/chat/mine/{drawer_id}",
    response_model=TalonMemoryForgotten,
    description="Forget one of the caller's own chat memories (audited)",
)
async def forget_my_chat_memory(
    drawer_id: str,
    request: Request,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.forget_chat_memory(current_user, session, drawer_id, request)


# ── a customer's memory ───────────────────────────────────────────────────────


@talon_memory_router.get("/{customer_code}/stats", response_model=TalonMemoryStats, description="How much Talon remembers about a customer")
async def get_memory_stats(
    customer_code: str,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.get_stats(current_user, session, customer_code)


@talon_memory_router.get(
    "/{customer_code}/drawers",
    response_model=TalonMemoryPage,
    description="A page of a customer's memories, newest first; with q, a semantic search",
)
async def list_memory_drawers(
    customer_code: str,
    response: Response,
    room: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description=f"A semantic search, at most {service.MAX_QUERY} characters"),
    since: Optional[str] = Query(None, description="Filed at or after: a UTC day or an ISO 8601 date-time"),
    before: Optional[str] = Query(None, description="Filed before: a UTC day or an ISO 8601 date-time"),
    limit: Optional[int] = Query(None, description=f"At most {service.MAX_LIMIT} (more is capped); default {service.DEFAULT_LIMIT}"),
    cursor: Optional[str] = Query(None),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.list_drawers(
        current_user,
        session,
        customer_code,
        room=room,
        source=source,
        q=q,
        since=since,
        before=before,
        limit=limit,
        cursor=cursor,
    )


@talon_memory_router.get(
    "/{customer_code}/drawers/{drawer_id}",
    response_model=TalonMemoryDrawer,
    description="One memory: its markdown, whether it may be forgotten, and why it is hidden from investigations",
)
async def get_memory_drawer(
    customer_code: str,
    drawer_id: str,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.get_drawer(current_user, session, customer_code, drawer_id)


@talon_memory_router.delete(
    "/{customer_code}/drawers/{drawer_id}",
    response_model=TalonMemoryForgotten,
    description="Forget a customer's one-off review lesson or chat remember lesson (audited); anything else is refused (409)",
)
async def forget_memory_drawer(
    customer_code: str,
    drawer_id: str,
    request: Request,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.forget_drawer(current_user, session, customer_code, drawer_id, request)


@talon_memory_router.get(
    "/{customer_code}/assets",
    response_model=TalonMemoryAssets,
    description="The assets Talon remembers for a customer",
)
async def list_memory_assets(
    customer_code: str,
    response: Response,
    q: Optional[str] = Query(None, description=f"Filter by name, at most {service.MAX_QUERY} characters"),
    limit: Optional[int] = Query(None, description=f"At most {service.MAX_LIMIT} (more is capped); default {service.DEFAULT_LIMIT}"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.list_assets(current_user, session, customer_code, q=q, limit=limit)


@talon_memory_router.get(
    "/{customer_code}/assets/{asset}/timeline",
    response_model=TalonMemoryTimeline,
    description="What Talon has learnt about one asset over time",
)
async def get_memory_asset_timeline(
    customer_code: str,
    asset: str,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _no_store(response)
    return await service.asset_timeline(current_user, session, customer_code, asset)
