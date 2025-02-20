from pathlib import Path

from loguru import logger
from typing import Any
from typing import Dict

from app.agents.routes.agents import get_wazuh_manager_version
from app.connectors.portainer.schema.stack import StackResponse
from app.connectors.portainer.utils.universal import get_endpoint_id
from app.connectors.portainer.utils.universal import get_swarm_id
from app.connectors.portainer.utils.universal import send_post_request
from app.customer_provisioning.schema.provision import ProvisionNewCustomer


# async def create_wazuh_customer_stack(request: ProvisionNewCustomer) -> StackResponse:
#     """
#     Create a Wazuh stack.
#     """
#     logger.info(f"Creating Wazuh stack for customer {request.customer_name}")
#     formatted_customer_name = request.customer_name.replace(" ", "_")
#     wazuh_manager_version = await get_wazuh_manager_version()
#     logger.info(f"Wazuh Manager version: {wazuh_manager_version}")
#     # Get the template file from one directory up and under `templates` and the file is `wazuh_worker_stack.yml`
#     template_path = Path(__file__).parent.parent / "templates" / "wazuh_worker_stack.yml"
#     with open(template_path, "r") as file:
#         template = file.read()

#     # Replace the placeholders in the template with the actual values
#     template = template.replace("{{ wazuh_worker_customer_code }}", formatted_customer_name)
#     template = template.replace("{{ wazuh_manager_version }}", wazuh_manager_version)
#     template = template.replace("REPLACE_LOG", request.wazuh_logs_port)
#     template = template.replace("REPLACE_REGISTRATION", request.wazuh_registration_port)
#     template = template.replace("REPLACE_API", request.wazuh_api_port)
#     logger.info(f"Template: {template}")

#     endpoint_id = await get_endpoint_id()
#     logger.info(f"Endpoint ID: {endpoint_id}")
#     swarm_id = await get_swarm_id()
#     logger.info(f"Swarm ID: {swarm_id}")

#     create_stack_url = f"/api/stacks?type=1&method=string&endpointId={endpoint_id}"
#     payload = {
#         "Name": f"wazuh-worker-{formatted_customer_name}",
#         "StackFileContent": template,
#         "SwarmID": swarm_id,
#         "Env": [],
#     }
#     response = await send_post_request(endpoint=create_stack_url, data=payload)
#     logger.info(f"Response: {response}")
#     return StackResponse(**response)

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


async def _prepare_template_variables(request: ProvisionNewCustomer) -> Dict[str, str]:
    """
    Prepare variables for template replacement.

    Args:
        request (ProvisionNewCustomer): The customer provisioning request

    Returns:
        Dict[str, str]: Dictionary of template variables and their values
    """
    formatted_customer_name = request.customer_name.replace(" ", "_")
    wazuh_manager_version = await get_wazuh_manager_version()

    return {
        "{{ wazuh_worker_customer_code }}": formatted_customer_name,
        "{{ wazuh_manager_version }}": wazuh_manager_version,
        "REPLACE_LOG": request.wazuh_logs_port,
        "REPLACE_REGISTRATION": request.wazuh_registration_port,
        "REPLACE_API": request.wazuh_api_port,
        "customer_name": formatted_customer_name
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
        "Name": f"wazuh-worker-{variables['customer_name']}",
        "StackFileContent": template,
        "SwarmID": swarm_id,
        "Env": [],
    }


async def create_wazuh_customer_stack(request: ProvisionNewCustomer) -> StackResponse:
    """
    Create a Wazuh stack for a customer.

    Args:
        request (ProvisionNewCustomer): The customer provisioning request

    Returns:
        StackResponse: The response from Portainer stack creation
    """
    logger.info(f"Creating Wazuh stack for customer {request.customer_name}")

    # Load template
    template_path = Path(__file__).parent.parent / "templates" / "wazuh_worker_stack.yml"
    template = await _load_stack_template(template_path)

    # Prepare variables
    variables = await _prepare_template_variables(request)
    logger.info(f"Template variables prepared for customer: {variables['customer_name']}")

    # Process template
    for placeholder, value in variables.items():
        template = template.replace(placeholder, value)
    logger.info("Template processed with variables")

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
