from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler

# from app.connectors.portainer.schema.integrations import ExecuteWorkflowRequest
from app.connectors.portainer.schema.nodes import NodesResponse
from app.connectors.portainer.schema.stack import DeleteStackResponse
from app.connectors.portainer.schema.stack import StackIDResponse
from app.connectors.portainer.schema.stack import StackResponse
from app.connectors.portainer.schema.stack import StacksResponse
from app.connectors.portainer.services.nodes import get_node_details
from app.connectors.portainer.services.stack import create_wazuh_customer_stack
from app.connectors.portainer.services.stack import delete_wazuh_customer_stack
from app.connectors.portainer.services.stack import get_stack_details
from app.connectors.portainer.services.stack import get_stacks
from app.connectors.portainer.services.stack import start_wazuh_customer_stack
from app.connectors.portainer.services.stack import stop_wazuh_customer_stack
from app.connectors.portainer.utils.universal import get_customer_portainer_stack_id
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.db.db_session import get_db

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


@portainer_integrations_router.get(
    "/get-customer-stack-id",
    description="Get the ID of a customer stack.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
    response_model=StackIDResponse,
)
async def get_customer_stack_id_route(
    customer_name: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Get the ID of a customer stack by the customer name.

    Args:
        customer_name (str): The name of the customer.

    Returns:
        dict: The response object.
    """
    return StackIDResponse(
        stack_id=await get_customer_portainer_stack_id(customer_name=customer_name, session=session),
        success=True,
        message="Customer stack ID retrieved successfully.",
    )


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


@portainer_integrations_router.post(
    "/start-wazuh-customer-stack",
    description="Start a Wazuh stack for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
    response_model=StackResponse,
)
async def start_wazuh_customer_stack_route(stack_id: int):
    """
    Start a Wazuh stack for a customer.

    Args:
        request (ProvisionNewCustomer): The request object.

    Returns:
        dict: The response object.
    """
    return await start_wazuh_customer_stack(stack_id)


@portainer_integrations_router.post(
    "/stop-wazuh-customer-stack",
    description="Stop a Wazuh stack for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
    response_model=StackResponse,
)
async def stop_wazuh_customer_stack_route(stack_id: int):
    """
    Stop a Wazuh stack for a customer.

    Args:
        request (ProvisionNewCustomer): The request object.

    Returns:
        dict: The response object.
    """
    return await stop_wazuh_customer_stack(stack_id)


@portainer_integrations_router.delete(
    "/delete-wazuh-customer-stack",
    description="Delete a Wazuh stack for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
    response_model=DeleteStackResponse,
)
async def delete_wazuh_customer_stack_route(stack_id: int):
    """
    Delete a Wazuh stack for a customer.

    Args:
        request (ProvisionNewCustomer): The request object.

    Returns:
        dict: The response object.
    """
    return await delete_wazuh_customer_stack(stack_id)
