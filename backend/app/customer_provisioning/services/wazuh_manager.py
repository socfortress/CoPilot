from pathlib import Path

from loguru import logger

from app.connectors.wazuh_manager.utils.universal import (
    send_post_request as send_wazuh_post_request,
)
from app.connectors.wazuh_manager.utils.universal import (
    send_put_request as send_wazuh_put_request,
)
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.customer_provisioning.schema.wazuh_manager import WazuhAgentsTemplatePaths


######### ! WAZUH MANAGER PROVISIONING ! ############
# Function to generate group codes
def generate_group_code(group, customer_code):
    return f"{group}_{customer_code}"


# Separate function for sending POST requests to Wazuh
async def create_wazuh_group(group_code):
    endpoint = "groups"
    data = {"group_id": group_code}
    return await send_wazuh_post_request(endpoint=endpoint, data=data)


# Main function to create Wazuh groups
async def create_wazuh_groups(request: ProvisionNewCustomer):
    logger.info(f"Creating Wazuh groups for customer {request.customer_name} with code {request.customer_code}")

    wazuh_groups = ["Linux", "Windows", "Mac"]  # This list can be moved to a config file or a global variable

    for group in wazuh_groups:
        group_code = generate_group_code(group, request.customer_code)
        logger.info(f"Creating group with code {group_code}")
        try:
            response = await create_wazuh_group(group_code)
            logger.info(f"Response for {group_code}: {response}")
        except Exception as e:
            logger.error(f"Error creating group {group_code}: {e}")


# Function to get the template file path
def get_template_path(template_info: WazuhAgentsTemplatePaths) -> Path:
    folder_name, file_name = template_info.value
    current_file = Path(__file__)  # Path to the current file
    base_dir = current_file.parent.parent  # Move up two levels to the base directory
    return base_dir / folder_name / file_name


# Function to update Wazuh group configuration
async def configure_wazuh_group(group_code, template_path):
    logger.info(f"Configuring Wazuh group {group_code}")

    # Read the contents of the template file
    with open(template_path, "r") as template_file:
        config_template = template_file.read()

    # Replace placeholder with the customer code
    group_config = config_template.replace("REPLACE", group_code.split("_")[-1])

    # Make the API request to update the group configuration
    return await send_wazuh_put_request(endpoint=f"groups/{group_code}/configuration", data=group_config, xml_data=True)


# Function to apply configurations for all groups
async def apply_group_configurations(request: ProvisionNewCustomer):
    logger.info(f"Applying configurations for Wazuh groups for customer {request.customer_name} with code {request.customer_code}")

    group_templates = {
        "Linux": WazuhAgentsTemplatePaths.LINUX_AGENT,
        "Windows": WazuhAgentsTemplatePaths.WINDOWS_AGENT,
        "Mac": WazuhAgentsTemplatePaths.MAC_AGENT,
    }

    for group, template in group_templates.items():
        group_code = f"{group}_{request.customer_code}"
        template_path = get_template_path(template)
        try:
            await configure_wazuh_group(group_code, template_path)
        except Exception as e:
            logger.error(f"Error configuring group {group_code}: {e}")
