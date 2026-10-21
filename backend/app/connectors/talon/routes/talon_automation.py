"""The per-customer automation policy, the global automation switch and the dry-run route
(talon-analyst plan AP-2; SPEC D85, D86; ``services/talon_automation.py``), mounted at
``/api/talon/v2``:

- ``GET``/``PUT /automation/{customer_code}``: admin by token scope and by the database role; the
  Talon service account refused whatever its role. Whatever "Talon v2" says: it is how the policy
  is set before the start route is turned on. ``no-store``.
- ``GET``/``PUT /settings/automation``: the global switch, the same rules.
- ``POST /automation/dry-run``: admin or analyst by token, then "Talon v2" (404 while off), then the
  Talon service account only. The start route's body; nothing starts.
"""
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Request
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.schema.talon_automation import TalonAutomationDryRunResponse
from app.connectors.talon.schema.talon_automation import TalonAutomationPolicyResponse
from app.connectors.talon.schema.talon_automation import TalonAutomationPolicyUpdate
from app.connectors.talon.schema.talon_automation import TalonAutomationSwitchResponse
from app.connectors.talon.schema.talon_automation import TalonAutomationSwitchUpdate
from app.connectors.talon.schema.talon_collections import CollectStartBody
from app.connectors.talon.services import talon_automation as service
from app.connectors.talon.services import talon_collections
from app.connectors.talon.services.talon_v2 import NO_STORE
from app.connectors.talon.services.talon_v2 import require_talon_v2
from app.db.db_session import get_db

talon_automation_router = APIRouter()

CUSTOMER_CODE = Path(..., min_length=1, max_length=64, description="The customer's code, exactly as CoPilot has it")


@talon_automation_router.post(
    "/automation/dry-run",
    response_model=TalonAutomationDryRunResponse,
    description=(
        "The Talon service account's dry run of POST /api/artifacts/collect/start: the same body and checks (the level on "
        "shadow or auto), the verdict recorded; nothing starts"
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst")), Depends(require_talon_v2())],
)
async def automation_dry_run(
    body: CollectStartBody,
    request: Request,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TalonAutomationDryRunResponse:
    response.headers.update(NO_STORE)
    return await talon_collections.dry_run(current_user, body, request, session)


@talon_automation_router.get(
    "/automation/{customer_code}",
    response_model=TalonAutomationPolicyResponse,
    description="A customer's automation policy (no row: every level off)",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_automation_policy(
    response: Response,
    customer_code: str = CUSTOMER_CODE,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TalonAutomationPolicyResponse:
    response.headers.update(NO_STORE)
    return await service.get_policy(current_user, session, customer_code)


@talon_automation_router.put(
    "/automation/{customer_code}",
    response_model=TalonAutomationPolicyResponse,
    description="Replace a customer's automation policy: any mode per level; raising level 3 or 4 needs acknowledge_risk",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def put_automation_policy(
    body: TalonAutomationPolicyUpdate,
    request: Request,
    response: Response,
    customer_code: str = CUSTOMER_CODE,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TalonAutomationPolicyResponse:
    response.headers.update(NO_STORE)
    return await service.update_policy(current_user, session, customer_code, body, request)


@talon_automation_router.get(
    "/settings/automation",
    response_model=TalonAutomationSwitchResponse,
    description="The global automation switch: off, every automated start by the Talon service account is refused",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_automation_switch(
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TalonAutomationSwitchResponse:
    response.headers.update(NO_STORE)
    return await service.get_switch(current_user, session)


@talon_automation_router.put(
    "/settings/automation",
    response_model=TalonAutomationSwitchResponse,
    description="Turn automated starts on or off for every customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def put_automation_switch(
    body: TalonAutomationSwitchUpdate,
    request: Request,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TalonAutomationSwitchResponse:
    response.headers.update(NO_STORE)
    return await service.update_switch(current_user, session, body.automation_enabled, request)
