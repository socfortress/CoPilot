from fastapi import APIRouter

from app.agents.routes.agents import agents_router
from app.agents.sca.routes.sca import sca_router
from app.agents.vulnerabilities.routes.vulnerabilities import vulnerabilities_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Wazuh Manager related routes
router.include_router(agents_router, prefix="/agents", tags=["agents"])
router.include_router(vulnerabilities_router, prefix="/vulnerabilities", tags=["vulnerabilities"])
router.include_router(sca_router, prefix="/sca", tags=["sca"])
