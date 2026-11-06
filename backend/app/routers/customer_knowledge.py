from fastapi import APIRouter

from app.customer_knowledge.routes.customer_knowledge import customer_knowledge_router

# Routes declare their full paths (/customers/{code}/knowledge), as the notifications module does.
router = APIRouter()

router.include_router(customer_knowledge_router, tags=["customer knowledge"])
