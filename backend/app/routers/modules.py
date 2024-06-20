from fastapi import APIRouter

from app.integrations.modules.routes.duo import module_duo_router
from app.integrations.modules.routes.huntress import module_huntress_router
from app.integrations.modules.routes.mimecast import module_mimecast_router
from app.integrations.modules.routes.sap_siem import module_sap_siem_router

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

router.include_router(
    module_sap_siem_router,
    prefix="/integrations/modules/sap_siem",
    tags=["SAP SIEM"],
)

router.include_router(
    module_duo_router,
    prefix="/integrations/modules/duo",
    tags=["DUO"],
)
