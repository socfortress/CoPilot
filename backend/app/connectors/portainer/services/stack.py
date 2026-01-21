from pathlib import Path
from typing import Any
from typing import Dict

from fastapi import HTTPException
from loguru import logger

from app.agents.routes.agents import get_wazuh_manager_version
from app.connectors.portainer.schema.stack import DeleteStackResponse
from app.connectors.portainer.schema.stack import StackResponse
from app.connectors.portainer.schema.stack import StacksResponse
from app.connectors.portainer.schema.stack import StackStatus
from app.connectors.portainer.utils.universal import get_endpoint_id
from app.connectors.portainer.utils.universal import get_swarm_id
from app.connectors.portainer.utils.universal import send_delete_request
from app.connectors.portainer.utils.universal import send_get_request
from app.connectors.portainer.utils.universal import send_post_request
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.customer_provisioning.services.portainer import list_node_ips


async def get_stacks() -> StackResponse:
    """
    Get the list of stacks from Portainer.

    Returns:
        StackResponse: The response from Portainer
    """
    response = await send_get_request("/api/stacks")
    logger.info(f"Stacks received: {response}")
    return StacksResponse(data=response["data"], message="Stacks fetched successfully", success=True)


async def get_stack_details(stack_id: int) -> StackResponse:
    """
    Get the details of a stack from Portainer.

    Args:
        stack_id (int): The ID of the stack

    Returns:
        StackResponse: The response from Portainer
    """
    endpoint_id = await get_endpoint_id()
    response = await send_get_request(f"/api/stacks/{stack_id}?endpointId={endpoint_id}")
    logger.info(f"Stack details received: {response}")
    return StackResponse(**response)


async def _load_stack_template(template_path: Path) -> str:
    """
    Load the stack template from file.

    Args:
        template_path (Path): Path to the template file

    Returns:
        str: Contents of the template file
    """
    with open(template_path, "r") as file:
        return file.read()


# async def _prepare_template_variables(request: ProvisionNewCustomer) -> Dict[str, str]:
#     """
#     Prepare variables for template replacement.

#     Args:
#         request (ProvisionNewCustomer): The customer provisioning request

#     Returns:
#         Dict[str, str]: Dictionary of template variables and their values
#     """
#     formatted_customer_name = request.customer_name.replace(" ", "_")
#     wazuh_manager_version = await get_wazuh_manager_version()

#     return {
#         "{{ wazuh_worker_customer_code }}": formatted_customer_name,
#         "{{ wazuh_manager_version }}": wazuh_manager_version,
#         "REPLACE_LOG": request.wazuh_logs_port,
#         "REPLACE_REGISTRATION": request.wazuh_registration_port,
#         "REPLACE_API": request.wazuh_api_port,
#         "customer_name": formatted_customer_name,
#     }


async def _prepare_template_variables(request: ProvisionNewCustomer, node_count: int) -> Dict[str, str]:
    """
    Prepare variables for template replacement.

    Args:
        request (ProvisionNewCustomer): The customer provisioning request
        node_count (int): Number of nodes in the swarm

    Returns:
        Dict[str, str]: Dictionary of template variables and their values
    """
    formatted_customer_name = request.customer_name.replace(" ", "_")
    wazuh_manager_version = await get_wazuh_manager_version()
    formatted_customer_code = request.customer_code.replace(" ", "_")

    return {
        "{{ wazuh_worker_customer_code }}": formatted_customer_code,
        "{{ wazuh_manager_version }}": wazuh_manager_version,
        "REPLACE_LOG": request.wazuh_logs_port,
        "REPLACE_REGISTRATION": request.wazuh_registration_port,
        "REPLACE_API": request.wazuh_api_port,
        "NUMBER_OF_NODES": str(node_count),
        "customer_name": formatted_customer_name,
        "customer_code": formatted_customer_code,
    }


async def _create_stack_payload(template: str, variables: Dict[str, str], swarm_id: str) -> Dict[str, Any]:
    """
    Create the payload for stack creation.

    Args:
        template (str): The processed template
        variables (Dict[str, str]): Template variables
        swarm_id (str): The swarm ID

    Returns:
        Dict[str, Any]: The payload for stack creation
    """
    return {
        "Name": f"wazuh-worker-{variables['customer_code']}",
        "StackFileContent": template,
        "SwarmID": swarm_id,
        "Env": [],
    }


# async def create_wazuh_customer_stack(request: ProvisionNewCustomer) -> StackResponse:
#     """
#     Create a Wazuh stack for a customer.

#     Args:
#         request (ProvisionNewCustomer): The customer provisioning request

#     Returns:
#         StackResponse: The response from Portainer stack creation
#     """
#     logger.info(f"Creating Wazuh stack for customer {request.customer_name}")

#     # Load template
#     template_path = Path(__file__).parent.parent / "templates" / "wazuh_worker_stack.yml"
#     template = await _load_stack_template(template_path)

#     # Prepare variables
#     variables = await _prepare_template_variables(request)
#     logger.info(f"Template variables prepared for customer: {variables['customer_name']}")

#     # Process template
#     for placeholder, value in variables.items():
#         template = template.replace(placeholder, value)
#     logger.info("Template processed with variables")

#     # Get required IDs
#     endpoint_id = await get_endpoint_id()
#     swarm_id = await get_swarm_id()
#     logger.info(f"Retrieved endpoint ID: {endpoint_id} and swarm ID: {swarm_id}")

#     # Create and send request
#     create_stack_url = f"/api/stacks?type=1&method=string&endpointId={endpoint_id}"
#     payload = await _create_stack_payload(template, variables, swarm_id)

#     response = await send_post_request(endpoint=create_stack_url, data=payload)
#     logger.info(f"Stack creation response received: {response}")

#     return StackResponse(**response)


async def create_wazuh_customer_stack(request: ProvisionNewCustomer) -> StackResponse:
    """
    Create a Wazuh stack for a customer.

    Args:
        request (ProvisionNewCustomer): The customer provisioning request

    Returns:
        StackResponse: The response from Portainer stack creation
    """
    logger.info(f"Creating Wazuh stack for customer {request.customer_name}")

    # Get the number of swarm nodes
    swarm_node_ips = await list_node_ips()
    node_count = len(swarm_node_ips)
    logger.info(f"Found {node_count} swarm nodes: {swarm_node_ips}")

    # Load template
    template_path = Path(__file__).parent.parent / "templates" / "wazuh_worker_stack.yml"
    template = await _load_stack_template(template_path)

    # Prepare variables with node count
    variables = await _prepare_template_variables(request, node_count)
    logger.info(f"Template variables prepared for customer: {variables['customer_name']} with {node_count} nodes")

    # Process template
    for placeholder, value in variables.items():
        template = template.replace(placeholder, value)
    logger.info(f"Template processed with variables, replicas set to {node_count}")

    # Get required IDs
    endpoint_id = await get_endpoint_id()
    swarm_id = await get_swarm_id()
    logger.info(f"Retrieved endpoint ID: {endpoint_id} and swarm ID: {swarm_id}")

    # Create and send request
    create_stack_url = f"/api/stacks?type=1&method=string&endpointId={endpoint_id}"
    payload = await _create_stack_payload(template, variables, swarm_id)

    response = await send_post_request(endpoint=create_stack_url, data=payload)
    logger.info(f"Stack creation response received: {response}")

    return StackResponse(**response)


async def start_wazuh_customer_stack(stack_id: int) -> StackResponse:
    """
    Start a Wazuh stack for a customer.

    Args:
        stack_id (int): The ID of the stack to start

    Returns:
        StackResponse: The response from Portainer stack start

    Raises:
        HTTPException: If the stack is already active or in an unexpected state
    """
    logger.info(f"Checking status of stack {stack_id} before starting")

    # Get current stack status
    stack_details = await get_stack_details(stack_id)

    # Check if stack is already active
    if stack_details.data.Status == StackStatus.ACTIVE:
        logger.info(f"Stack {stack_id} is already active")
        return stack_details

    # If stack is stopped, proceed with starting it
    if stack_details.data.Status == StackStatus.DOWN:
        logger.info(f"Starting stopped stack {stack_id}")
        endpoint_id = await get_endpoint_id()

        # Create and send request
        start_stack_url = f"/api/stacks/{stack_id}/start?endpointId={endpoint_id}"
        response = await send_post_request(endpoint=start_stack_url)
        logger.info(f"Stack start response received: {response}")

        return StackResponse(**response)

    # If stack is in any other state
    logger.warning(f"Stack {stack_id} is in an unexpected state: {stack_details.data.Status}")
    raise HTTPException(status_code=400, detail=f"Unexpected stack status: {stack_details.data.Status}")


async def stop_wazuh_customer_stack(stack_id: int) -> StackResponse:
    """
    Stop a Wazuh stack for a customer.

    Args:
        stack_id (int): The ID of the stack to stop

    Returns:
        StackResponse: The response from Portainer stack stop

    Raises:
        HTTPException: If the stack is already stopped
    """
    logger.info(f"Checking status of stack {stack_id} before stopping")

    # Get current stack status
    stack_details = await get_stack_details(stack_id)

    # Check if stack is already stopped
    if stack_details.data.Status == StackStatus.DOWN:
        logger.info(f"Stack {stack_id} is already stopped")
        return stack_details

    # If stack is active, proceed with stopping it
    if stack_details.data.Status == StackStatus.ACTIVE:
        logger.info(f"Stopping active stack {stack_id}")
        endpoint_id = await get_endpoint_id()

        # Create and send request
        stop_stack_url = f"/api/stacks/{stack_id}/stop?endpointId={endpoint_id}"
        response = await send_post_request(endpoint=stop_stack_url)
        logger.info(f"Stack stop response received: {response}")

        return StackResponse(**response)

    # If stack is in any other state
    logger.warning(f"Stack {stack_id} is in an unexpected state: {stack_details.data.Status}")
    raise HTTPException(status_code=400, detail=f"Unexpected stack status: {stack_details.data.Status}")


async def delete_wazuh_customer_stack(stack_id: int) -> DeleteStackResponse:
    """
    Delete a Wazuh stack for a customer.

    Args:
        request (ProvisionNewCustomer): The customer provisioning request

    Returns:
        DeleteStackResponse: The response from Portainer stack deletion
    """
    logger.info(f"Deleting Wazuh stack for stack id {stack_id}")

    # Get required IDs
    endpoint_id = await get_endpoint_id()
    logger.info(f"Retrieved endpoint ID: {endpoint_id} and stack ID: {stack_id}")

    # Stop the stack first
    await stop_wazuh_customer_stack(stack_id)

    # Create and send request
    delete_stack_url = f"/api/stacks/{stack_id}"
    response = await send_delete_request(endpoint=delete_stack_url, params={"endpointId": endpoint_id})
    logger.info(f"Stack deletion response received: {response}")

    return DeleteStackResponse(**response)
