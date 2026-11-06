"""The customer page's "What Talon sees" route, under ``/api/talon/knowledge``
(``services/talon_knowledge.py``).

Admins and analysts (a responder's token carries ``analyst``), then the "Talon v2" setting: with it
off the route answers 404 ``{"detail": "Not Found"}`` like an unknown path (``require_talon_v2``,
after the scope check). The customer in the path is checked against the caller's own customers in
the service. Every answer is ``no-store``. There is no ``customer_user`` route.
"""
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.schema.talon_knowledge import TalonKnowledge
from app.connectors.talon.services import talon_knowledge as service
from app.connectors.talon.services.talon_memory import NO_STORE
from app.connectors.talon.services.talon_v2 import require_talon_v2
from app.db.db_session import get_db

talon_knowledge_router = APIRouter(
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(require_talon_v2()),
    ],
)


@talon_knowledge_router.get(
    "/{customer_code}",
    response_model=TalonKnowledge,
    description="What talon-analyst has measured of a customer's log sources",
)
async def get_what_talon_sees(
    customer_code: str,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    response.headers.update(NO_STORE)
    return await service.what_talon_sees(current_user, session, customer_code)
