from fastapi import APIRouter

from app.performance.routes.performance import performance_router

# Instantiate the APIRouter
router = APIRouter()

router.include_router(performance_router, prefix="/performance", tags=["Performance"])
