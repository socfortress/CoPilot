from app.connectors.portainer.services.nodes import get_node_details

async def list_node_ips() -> list:
    """
    Get the node IPs from the Portainer API.
    """
    nodes = await get_node_details()
    return [node.Status.Addr for node in nodes.nodes]
