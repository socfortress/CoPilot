from fastapi import APIRouter

from app.ai_analyst.routes.ai_analyst import ai_analyst_router

# Instantiate the APIRouter
router = APIRouter()

router.include_router(ai_analyst_router, prefix="/ai_analyst", tags=["ai-analyst"])
