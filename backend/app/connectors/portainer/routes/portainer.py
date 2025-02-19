from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
#from app.connectors.portainer.schema.integrations import ExecuteWorkflowRequest
from app.connectors.portainer.schema.nodes import NodesResponse
from app.connectors.portainer.services.nodes import get_node_details

portainer_integrations_router = APIRouter()


@portainer_integrations_router.post(
    "/node-details",
    description="Execute a portainer Integration.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
    response_model=NodesResponse,
)
async def node_details_route():
    """
    Get the IP addresses of all nodes in the swarm.

    Returns:
        list: The list of IP addresses.
    """
    logger.info("Getting swarm node details")
    return await get_node_details()
