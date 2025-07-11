from fastapi import APIRouter

from fastapi import Security
from app.auth.routes.auth import AuthHandler
from loguru import logger





from app.connectors.wazuh_manager.utils.universal import restart_wazuh_manager_service




wazuh_manager_management_router = APIRouter()
auth_handler = AuthHandler()


@wazuh_manager_management_router.post(
    "/restart",
    description="Get all disabled rules",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def restart_wazuh_manager() -> dict:
    """
    Restart the Wazuh Manager service.
    """
    logger.info("Restarting Wazuh Manager service.")
    return await restart_wazuh_manager_service()

