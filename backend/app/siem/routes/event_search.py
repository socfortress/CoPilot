"""Event search's memory (#1258): what a user saved, ran and picked, per customer.

Every row belongs to the caller: the user comes from the token, never from the request,
and the customer must be one the caller may see. Each route answers with the whole
memory, so the client never has to merge.
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.middleware.customer_access import customer_access_handler
from app.siem.schema.event_search import EventSearchMemory
from app.siem.schema.event_search import EventSearchMemoryResponse
from app.siem.schema.event_search import EventSearchState
from app.siem.schema.event_search import SaveQueryRequest
from app.siem.schema.event_search import SetColumnsRequest
from app.siem.services import event_search as memory_service

event_search_router = APIRouter()

SCOPE = [Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))]


async def _owner(customer_code: str, current_user: User, db: AsyncSession) -> int:
    if not await customer_access_handler.check_customer_access(current_user, customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
    return current_user.id


def _response(memory: EventSearchMemory, message: str, replaced=None) -> EventSearchMemoryResponse:
    return EventSearchMemoryResponse(**memory.model_dump(), success=True, message=message, replaced=replaced)


@event_search_router.get(
    "/{customer_code}",
    response_model=EventSearchMemoryResponse,
    description="The caller's saved queries, recent queries and picked columns for a customer",
    dependencies=SCOPE,
)
async def get_memory(
    customer_code: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSearchMemoryResponse:
    user_id = await _owner(customer_code, current_user, db)
    return _response(await memory_service.load_memory(db, user_id, customer_code), "Event search memory retrieved")


@event_search_router.post(
    "/{customer_code}/saved",
    response_model=EventSearchMemoryResponse,
    description="Save a search under a name; a name already used is updated",
    dependencies=SCOPE,
)
async def save_query(
    customer_code: str,
    request: SaveQueryRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSearchMemoryResponse:
    user_id = await _owner(customer_code, current_user, db)
    memory, replaced = await memory_service.save_query(db, user_id, customer_code, request)
    return _response(memory, "Query updated" if replaced else "Query saved", replaced=replaced)


@event_search_router.delete(
    "/{customer_code}/saved/{query_id}",
    response_model=EventSearchMemoryResponse,
    description="Delete one of the caller's saved queries",
    dependencies=SCOPE,
)
async def delete_query(
    customer_code: str,
    query_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSearchMemoryResponse:
    user_id = await _owner(customer_code, current_user, db)
    return _response(await memory_service.delete_query(db, user_id, customer_code, query_id), "Query deleted")


@event_search_router.post(
    "/{customer_code}/recent",
    response_model=EventSearchMemoryResponse,
    description="Record a search just run among the caller's recent ones",
    dependencies=SCOPE,
)
async def remember_search(
    customer_code: str,
    state: EventSearchState,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSearchMemoryResponse:
    user_id = await _owner(customer_code, current_user, db)
    return _response(await memory_service.remember(db, user_id, customer_code, state), "Search recorded")


@event_search_router.delete(
    "/{customer_code}/recent",
    response_model=EventSearchMemoryResponse,
    description="Forget the caller's recent searches for a customer",
    dependencies=SCOPE,
)
async def clear_recent(
    customer_code: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSearchMemoryResponse:
    user_id = await _owner(customer_code, current_user, db)
    return _response(await memory_service.clear_recent(db, user_id, customer_code), "Recent searches cleared")


@event_search_router.put(
    "/{customer_code}/columns",
    response_model=EventSearchMemoryResponse,
    description="Set the caller's columns for an event source; none goes back to the source's layout",
    dependencies=SCOPE,
)
async def set_columns(
    customer_code: str,
    request: SetColumnsRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSearchMemoryResponse:
    user_id = await _owner(customer_code, current_user, db)
    return _response(await memory_service.set_columns(db, user_id, customer_code, request), "Columns saved")
