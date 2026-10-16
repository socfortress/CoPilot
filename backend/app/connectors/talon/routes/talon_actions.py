"""CoPilot's Talon v2 action routes, under ``/api/talon/actions`` (plan M5-11a; talon-analyst SPEC
§5.3 M5-11, §9.5, D46, D47).

Every route sits behind the "Talon v2" setting (``require_talon_v2``, after the scope check): off,
each answers 404 ``{"detail": "Not Found"}`` like a path that doesn't exist.

- ``GET ?scope=pending|mine`` (admin, analyst): the caller's decidable pending proposals plus their
  own (``pending``), or all of their own (``mine``), with ``can_decide`` and ``is_requester``;
- ``GET /{id}`` (admin, analyst): the card's read, synced from talon-analyst as the caller; 404
  unless the caller is its requester or may decide it;
- ``POST /{id}/approve`` and ``/deny`` (admin, analyst, responder, named on purpose: they are
  listed in ``tests/test_responder_role.py``'s ``RESPONDER_ROUTES``): D47 is checked by the user's
  role in the database, not by these scopes (``services/talon_action_execution.py``);
- ``POST /{id}/withdraw`` (admin, analyst; the requester only).

A responder's token carries ``analyst`` too, so the analyst routes admit responders.
"""
import uuid
from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.schema.talon_actions import ActionListResponse
from app.connectors.talon.schema.talon_actions import ActionResponse
from app.connectors.talon.services import talon_actions as service
from app.connectors.talon.services.talon_v2 import require_talon_v2
from app.db.db_session import get_db

talon_actions_router = APIRouter()

READERS = [Security(AuthHandler().require_any_scope("admin", "analyst")), Depends(require_talon_v2())]
DECIDERS = [Security(AuthHandler().require_any_scope("admin", "analyst", "responder")), Depends(require_talon_v2())]


@talon_actions_router.get(
    "",
    response_model=ActionListResponse,
    description="Talon action proposals: those the caller may decide now and their own (pending), or all of their own (mine)",
    dependencies=READERS,
)
async def list_talon_actions(
    scope: Literal["pending", "mine"] = Query("pending"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ActionListResponse:
    return await service.list_actions(current_user, session, scope)


@talon_actions_router.get(
    "/{action_id}",
    response_model=ActionResponse,
    description="One Talon action proposal, read back from talon-analyst",
    dependencies=READERS,
)
async def get_talon_action(
    action_id: uuid.UUID,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ActionResponse:
    return await service.get_action(str(action_id), current_user, session)


@talon_actions_router.post(
    "/{action_id}/approve",
    response_model=ActionResponse,
    description="Approve a Talon action proposal and run it in CoPilot, as the approver",
    dependencies=DECIDERS,
)
async def approve_talon_action(
    action_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ActionResponse:
    return await service.decide(str(action_id), current_user, session, request, approve=True)


@talon_actions_router.post(
    "/{action_id}/deny",
    response_model=ActionResponse,
    description="Deny a Talon action proposal; nothing runs",
    dependencies=DECIDERS,
)
async def deny_talon_action(
    action_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ActionResponse:
    return await service.decide(str(action_id), current_user, session, request, approve=False)


@talon_actions_router.post(
    "/{action_id}/withdraw",
    response_model=ActionResponse,
    description="Withdraw your own pending Talon action proposal",
    dependencies=READERS,
)
async def withdraw_talon_action(
    action_id: uuid.UUID,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ActionResponse:
    return await service.withdraw(str(action_id), current_user, session)
