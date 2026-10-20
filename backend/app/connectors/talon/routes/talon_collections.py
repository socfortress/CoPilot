"""The collection start route for talon-analyst's investigations and its setting (talon-analyst
EA-4b, D77; ``services/talon_collections.py``).

- ``talon_collect_start_router``, mounted at ``/api/artifacts``: ``POST /collect/start``, admin or
  analyst by token (as ``/collect``), then the "Talon v2" setting (D54: 404 while it is off).
- ``talon_collection_settings_router``, mounted at ``/api/talon/v2``: ``GET``/``PUT
  /settings/collections``, admin only by token and by the database role, whatever "Talon v2" says
  (it is how the gate is set before the route is turned on).
"""
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.schema.talon_collections import CollectStartBody
from app.connectors.talon.schema.talon_collections import CollectStartResponse
from app.connectors.talon.schema.talon_collections import (
    TalonCollectionSettingsResponse,
)
from app.connectors.talon.schema.talon_collections import TalonCollectionSettingsUpdate
from app.connectors.talon.services import talon_collections as service
from app.connectors.talon.services.talon_v2 import NO_STORE
from app.connectors.talon.services.talon_v2 import require_talon_v2
from app.db.db_session import get_db

talon_collect_start_router = APIRouter()
talon_collection_settings_router = APIRouter()


@talon_collect_start_router.post(
    "/collect/start",
    response_model=CollectStartResponse,
    description=(
        "Start an artifact collection on a host and answer its flow id, without waiting: /collect's checks and audit, "
        "the host's client id checked, resource limits on the flow, never rows. The Talon service account is held to "
        "its auto-run allowlist."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst")), Depends(require_talon_v2())],
)
async def start_collection(
    body: CollectStartBody,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CollectStartResponse:
    return await service.start(current_user, body, request, session)


@talon_collection_settings_router.get(
    "/settings/collections",
    response_model=TalonCollectionSettingsResponse,
    description="The Talon service account and the auto-run artifacts it may start on /api/artifacts/collect/start",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_collection_settings(
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TalonCollectionSettingsResponse:
    response.headers.update(NO_STORE)
    return await service.get_settings(current_user, session)


@talon_collection_settings_router.put(
    "/settings/collections",
    response_model=TalonCollectionSettingsResponse,
    description="Name the Talon service account and set the auto-run artifacts it may start (null: the default name; no artifacts)",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def put_collection_settings(
    body: TalonCollectionSettingsUpdate,
    request: Request,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TalonCollectionSettingsResponse:
    response.headers.update(NO_STORE)
    return await service.update_settings(current_user, session, body.service_username, body.allowed_artifacts, request)
