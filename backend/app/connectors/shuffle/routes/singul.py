from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.shuffle.schema.singul import SingulRequest
from app.connectors.shuffle.services.singul import execute_singul

shuffle_singul_router = APIRouter()


@shuffle_singul_router.post(
    "/execute",
    description="Execute a Shuffle Integration.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def execute_integration_route(request: SingulRequest):
    """
    Execute a workflow.

    Args:
        request (SingulRequest): The request object containing the workflow ID.

    Returns:
        dict: The response containing the execution ID.
    """
    logger.info("Executing Singul integration")
    return await execute_singul(request)
