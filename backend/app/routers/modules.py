from fastapi import APIRouter

from app.integrations.modules.routes.huntress import module_huntress_router
from app.integrations.modules.routes.mimecast import module_mimecast_router

router = APIRouter()

router.include_router(
    module_huntress_router,
    prefix="/integrations/modules/huntress",
    tags=["Huntress"],
)

router.include_router(
    module_mimecast_router,
    prefix="/integrations/modules/mimecast",
    tags=["Mimecast"],
)
