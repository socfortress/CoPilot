"""What SOC analysts record about a customer (talon-analyst SPEC D98, plan K1), under
``/api/customers/{customer_code}/knowledge``. Admins and analysts, for their own customers. Portal
users have no route here: customer edits come later, with an approval queue."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_knowledge.schema.customer_knowledge import KnowledgeDeleteResponse
from app.customer_knowledge.schema.customer_knowledge import KnowledgeItemBody
from app.customer_knowledge.schema.customer_knowledge import KnowledgeItemResponse
from app.customer_knowledge.schema.customer_knowledge import KnowledgeItemUpdate
from app.customer_knowledge.schema.customer_knowledge import KnowledgeListResponse
from app.customer_knowledge.services import customer_knowledge as svc
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access

customer_knowledge_router = APIRouter()

SOC = [Security(AuthHandler().require_any_scope("admin", "analyst")), Depends(verify_customer_code_access)]


@customer_knowledge_router.get(
    "/customers/{customer_code}/knowledge",
    response_model=KnowledgeListResponse,
    description="What the SOC has recorded about a customer.",
    dependencies=SOC,
)
async def list_knowledge(customer_code: str, session: AsyncSession = Depends(get_db)) -> KnowledgeListResponse:
    code, rows = await svc.list_items(customer_code, session)
    return KnowledgeListResponse(
        success=True,
        message=f"{len(rows)} item(s) retrieved",
        customer_code=code,
        items=[svc.to_schema(row) for row in rows],
    )


@customer_knowledge_router.post(
    "/customers/{customer_code}/knowledge",
    response_model=KnowledgeItemResponse,
    description="Record a fact about a customer.",
    dependencies=SOC,
)
async def create_knowledge(
    customer_code: str,
    body: KnowledgeItemBody,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> KnowledgeItemResponse:
    row, warnings = await svc.create_item(customer_code, body, current_user, session, request)
    return KnowledgeItemResponse(success=True, message="Fact saved", item=svc.to_schema(row), warnings=warnings)


@customer_knowledge_router.put(
    "/customers/{customer_code}/knowledge/{item_id}",
    response_model=KnowledgeItemResponse,
    description="Change a fact about a customer. A fact keeps its kind, and a 409 means it changed after you read it.",
    dependencies=SOC,
)
async def update_knowledge(
    customer_code: str,
    item_id: int,
    body: KnowledgeItemUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> KnowledgeItemResponse:
    row, warnings = await svc.update_item(customer_code, item_id, body, current_user, session, request)
    return KnowledgeItemResponse(success=True, message="Fact saved", item=svc.to_schema(row), warnings=warnings)


@customer_knowledge_router.delete(
    "/customers/{customer_code}/knowledge/{item_id}",
    response_model=KnowledgeDeleteResponse,
    description="Delete a fact about a customer. The audit log keeps what it held.",
    dependencies=SOC,
)
async def delete_knowledge(
    customer_code: str,
    item_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> KnowledgeDeleteResponse:
    await svc.delete_item(customer_code, item_id, current_user, session, request)
    return KnowledgeDeleteResponse(success=True, message="Fact deleted")
