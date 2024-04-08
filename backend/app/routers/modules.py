from fastapi import APIRouter

from app.integrations.modules.routes.huntress import module_huntress_router
from app.integrations.modules.routes.results import module_results_router

router = APIRouter()

router.include_router(
    module_huntress_router,
    prefix="/integrations/modules/huntress",
    tags=["Huntress"],
)

router.include_router(
    module_results_router,
    prefix="/integrations/modules/results",
    tags=["Integration Results"],
)
