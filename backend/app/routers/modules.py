from fastapi import APIRouter

from app.integrations.modules.routes.huntress import module_huntress_router

router = APIRouter()

router.include_router(
    module_huntress_router,
    prefix="/integrations/modules/huntress",
    tags=["Huntress"],
)
