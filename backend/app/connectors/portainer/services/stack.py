from pathlib import Path

from loguru import logger

from app.agents.routes.agents import get_wazuh_manager_version
from app.connectors.portainer.schema.stack import StackResponse
from app.connectors.portainer.utils.universal import get_endpoint_id
from app.connectors.portainer.utils.universal import get_swarm_id
from app.connectors.portainer.utils.universal import send_post_request
from app.customer_provisioning.schema.provision import ProvisionNewCustomer


async def create_wazuh_customer_stack(request: ProvisionNewCustomer) -> StackResponse:
    """
    Create a Wazuh stack.
    """
    logger.info(f"Creating Wazuh stack for customer {request.customer_name}")
    formatted_customer_name = request.customer_name.replace(" ", "_")
    wazuh_manager_version = await get_wazuh_manager_version()
    logger.info(f"Wazuh Manager version: {wazuh_manager_version}")
    # Get the template file from one directory up and under `templates` and the file is `wazuh_worker_stack.yml`
    template_path = Path(__file__).parent.parent / "templates" / "wazuh_worker_stack.yml"
    with open(template_path, "r") as file:
        template = file.read()

    # Replace the placeholders in the template with the actual values
    template = template.replace("{{ wazuh_worker_customer_code }}", formatted_customer_name)
    template = template.replace("{{ wazuh_manager_version }}", wazuh_manager_version)
    template = template.replace("REPLACE_LOG", request.wazuh_logs_port)
    template = template.replace("REPLACE_REGISTRATION", request.wazuh_registration_port)
    template = template.replace("REPLACE_API", request.wazuh_api_port)
    logger.info(f"Template: {template}")

    endpoint_id = await get_endpoint_id()
    logger.info(f"Endpoint ID: {endpoint_id}")
    swarm_id = await get_swarm_id()
    logger.info(f"Swarm ID: {swarm_id}")

    create_stack_url = f"/api/stacks?type=1&method=string&endpointId={endpoint_id}"
    payload = {
        "Name": f"wazuh-worker-{formatted_customer_name}",
        "StackFileContent": template,
        "SwarmID": swarm_id,
        "Env": [],
    }
    response = await send_post_request(endpoint=create_stack_url, data=payload)
    logger.info(f"Response: {response}")
    return StackResponse(**response)
