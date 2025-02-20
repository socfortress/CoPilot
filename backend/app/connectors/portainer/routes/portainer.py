from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler

# from app.connectors.portainer.schema.integrations import ExecuteWorkflowRequest
from app.connectors.portainer.schema.nodes import NodesResponse
from app.connectors.portainer.schema.stack import StackResponse, StacksResponse
from app.connectors.portainer.services.nodes import get_node_details
from app.connectors.portainer.services.stack import create_wazuh_customer_stack, get_stack_details, get_stacks
from app.customer_provisioning.schema.provision import ProvisionNewCustomer

portainer_integrations_router = APIRouter()


@portainer_integrations_router.get(
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

@portainer_integrations_router.get(
    "/stacks",
    description="Get the list of stacks.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
    response_model=StacksResponse,
)
async def stacks_route():
    """
    Get the list of stacks.

    Returns:
        dict: The response object.
    """
    return await get_stacks()

@portainer_integrations_router.get(
    "/stack-details",
    description="Get the details of a stack.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
    response_model=StackResponse,
)
async def stack_details_route(stack_id: int):
    """
    Get the details of a stack.

    Args:
        stack_id (int): The ID of the stack.

    Returns:
        dict: The response object.
    """
    return await get_stack_details(stack_id)


@portainer_integrations_router.post(
    "/create-wazuh-customer-stack",
    description="Create a Wazuh stack for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
    response_model=StackResponse,
)
async def create_wazuh_customer_stack_route(request: ProvisionNewCustomer):
    """
    Create a Wazuh stack for a customer.

    Args:
        request (ProvisionNewCustomer): The request object.

    Returns:
        dict: The response object.
    """
    return await create_wazuh_customer_stack(request)
