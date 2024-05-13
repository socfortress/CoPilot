from fastapi import APIRouter

from app.connectors.dfir_iris.routes.alerts import dfir_iris_alerts_router
from app.connectors.dfir_iris.routes.assets import dfir_iris_assets_router
from app.connectors.dfir_iris.routes.cases import dfir_iris_cases_router
from app.connectors.dfir_iris.routes.notes import dfir_iris_notes_router
from app.connectors.dfir_iris.routes.users import dfir_iris_users_router
from app.integrations.alert_escalation.routes.escalate_alert import (
    integration_escalate_alerts_router,
)

# Instantiate the APIRouter
router = APIRouter()

# Include the DFIR Iris related routes
router.include_router(
    dfir_iris_alerts_router,
    prefix="/soc/alerts",
    tags=["soc-alerts"],
)
router.include_router(
    dfir_iris_assets_router,
    prefix="/soc/assets",
    tags=["soc-assets"],
)
router.include_router(dfir_iris_cases_router, prefix="/soc/cases", tags=["soc-cases"])
router.include_router(dfir_iris_notes_router, prefix="/soc/notes", tags=["soc-notes"])
router.include_router(dfir_iris_users_router, prefix="/soc/users", tags=["soc-users"])
router.include_router(
    integration_escalate_alerts_router,
    prefix="/soc/general_alert",
    tags=["soc-general-alerts"],
)
