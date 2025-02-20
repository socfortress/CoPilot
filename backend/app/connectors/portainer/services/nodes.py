from loguru import logger

from app.connectors.portainer.schema.nodes import NodesResponse
from app.connectors.portainer.utils.universal import get_endpoint_id
from app.connectors.portainer.utils.universal import send_get_request


async def get_node_details() -> NodesResponse:
    """
    Get the node details from the Portainer API.
    """
    logger.info("Getting swarm node IPs")
    endpoint_id = await get_endpoint_id()
    logger.info(f"Endpoint ID: {endpoint_id}")
    nodes_response = await send_get_request(f"/api/endpoints/{endpoint_id}/docker/nodes")
    # Transform the response to match our simpler model
    return NodesResponse(nodes=nodes_response["data"], success=True, message="Nodes fetched successfully")
