from fastapi import APIRouter

from app.connectors.shuffle.routes.integrations import shuffle_integrations_router
from app.connectors.shuffle.routes.organizations import shuffle_organizations_router
from app.connectors.shuffle.routes.singul import shuffle_singul_router
from app.connectors.shuffle.routes.workflows import shuffle_workflows_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Shuffle related routes
router.include_router(
    shuffle_workflows_router,
    prefix="/workflows",
    tags=["shuffle-workflows"],
)

router.include_router(
    shuffle_integrations_router,
    prefix="/shuffle/integrations",
    tags=["shuffle-integrations"],
)

router.include_router(
    shuffle_singul_router,
    prefix="/shuffle/singul",
    tags=["shuffle-singul"],
)

router.include_router(
    shuffle_organizations_router,
    prefix="/shuffle/organizations",
    tags=["shuffle-organizations"],
)
