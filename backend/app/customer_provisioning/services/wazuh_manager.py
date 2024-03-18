from pathlib import Path
from typing import List

from loguru import logger

from app.connectors.wazuh_manager.utils.universal import (
    send_delete_request as send_wazuh_delete_request,
)
from app.connectors.wazuh_manager.utils.universal import (
    send_get_request as send_wazuh_get_request,
)
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
    """
    Generates a group code by combining the group name and customer code.

    Args:
        group (str): The name of the group.
        customer_code (str): The customer code.

    Returns:
        str: The generated group code.
    """
    return f"{group}_{customer_code}"


# Separate function for sending POST requests to Wazuh
async def create_wazuh_group(group_code):
    """
    Create a Wazuh group with the given group code.

    Args:
        group_code (str): The code for the group.

    Returns:
        dict: The response from the Wazuh API.

    """
    endpoint = "groups"
    data = {"group_id": group_code}
    return await send_wazuh_post_request(endpoint=endpoint, data=data)


# Main function to create Wazuh groups
async def create_wazuh_groups(request: ProvisionNewCustomer):
    """
    Create Wazuh groups for a customer.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.

    Returns:
        None
    """
    logger.info(
        f"Creating Wazuh groups for customer {request.customer_name} with code {request.customer_code}",
    )

    wazuh_groups = [
        "Linux",
        "Windows",
        "Mac",
    ]  # This list can be moved to a config file or a global variable

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
    """
    Get the path to the template file based on the provided template_info.

    Args:
        template_info (WazuhAgentsTemplatePaths): The template information.

    Returns:
        Path: The path to the template file.
    """
    folder_name, file_name = template_info.value
    current_file = Path(__file__)  # Path to the current file
    base_dir = current_file.parent.parent  # Move up two levels to the base directory
    return base_dir / folder_name / file_name


# Function to update Wazuh group configuration
async def configure_wazuh_group(group_code, template_path, request: ProvisionNewCustomer):
    """
    Configures a Wazuh group with the provided group code and template file.

    Args:
        group_code (str): The code of the Wazuh group to configure.
        template_path (str): The path to the template file.

    Returns:
        dict: The response from the API request to update the group configuration.
    """
    logger.info(f"Configuring Wazuh group {group_code}")

    # Read the contents of the template file
    with open(template_path, "r") as template_file:
        config_template = template_file.read()

    # Replace placeholder with the customer code
    group_config = config_template.replace("REPLACE", group_code.split("_")[-1])
    # Replace placeholder with the cluster name
    group_config = group_config.replace("CLUSTER_NAME", request.wazuh_cluster_name)

    # Make the API request to update the group configuration
    return await send_wazuh_put_request(
        endpoint=f"groups/{group_code}/configuration",
        data=group_config,
        xml_data=True,
    )


# Function to apply configurations for all groups
async def apply_group_configurations(request: ProvisionNewCustomer):
    """
    Apply configurations for Wazuh groups for a new customer.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.

    Returns:
        None

    Raises:
        Exception: If there is an error configuring a group.

    """
    logger.info(
        f"Applying configurations for Wazuh groups for customer {request.customer_name} with code {request.customer_code}",
    )

    group_templates = {
        "Linux": WazuhAgentsTemplatePaths.LINUX_AGENT,
        "Windows": WazuhAgentsTemplatePaths.WINDOWS_AGENT,
        "Mac": WazuhAgentsTemplatePaths.MAC_AGENT,
    }

    for group, template in group_templates.items():
        group_code = f"{group}_{request.customer_code}"
        template_path = get_template_path(template)
        try:
            await configure_wazuh_group(group_code, template_path, request)
        except Exception as e:
            logger.error(f"Error configuring group {group_code}: {e}")


######### ! WAZUH MANAGER DECOMISSIONING ! ############


async def get_agent_ids(group_code: str) -> List[str]:
    """
    Retrieves the agent IDs for a given group code.

    Args:
        group_code (str): The group code for which to retrieve the agent IDs.

    Returns:
        List[str]: A list of agent IDs.

    """
    try:
        response = await send_wazuh_get_request(
            endpoint="agents",
            params={"group": group_code},
        )
        logger.info(f"Response for {group_code}: {response}")

        # Extracting agents from the nested response
        agents_data = response.get("data", {}).get("data", {}).get("affected_items", [])

        agent_ids = [agent.get("id") for agent in agents_data]
        return agent_ids
    except Exception as e:
        logger.error(f"Error getting agents for group {group_code}: {e}")
        return []


async def gather_wazuh_agents(customer_meta_wazuh_group: str):
    """
    Gather the Wazuh agents for a given customer meta Wazuh group.

    Args:
        customer_meta_wazuh_group (str): The customer meta Wazuh group.

    Returns:
        list: A list of agent IDs for the Wazuh agents.
    """
    # Append the Group Templates from the WazuhAgentsTemplatePaths Enum
    wazuh_groups = ["Linux", "Windows", "Mac"]

    # Initialize an empty list to store the agents
    agents = []

    # Loop through the groups and get the agent IDs for each group and append them to the list
    for group in wazuh_groups:
        group_code = generate_group_code(group, customer_meta_wazuh_group)
        logger.info(f"Getting agents for group {group_code}")
        agent_ids = await get_agent_ids(group_code)
        agents.extend(agent_ids)

    return agents


async def delete_wazuh_agents(agent_ids: List[str]):
    """
    Delete Wazuh agents.

    Args:
        agent_ids (List[str]): List of agent IDs to be deleted.

    Returns:
        List[str]: List of agent IDs that were successfully deleted.
    """
    # Initialize an empty list to store the agents
    agents = []

    # Loop through the groups and get the agent IDs for each group and append them to the list
    for agent_id in agent_ids:
        logger.info(f"Deleting agent {agent_id}")
        try:
            response = await send_wazuh_delete_request(
                endpoint="agents",
                params={
                    "older_than": "0s",
                    "agents_list": agent_id,
                    "status": "all",
                },
            )
            logger.info(f"Response for {agent_id}: {response}")
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {e}")
            continue

        agents.append(agent_id)

    return agents


async def delete_wazuh_groups(customer_meta_wazuh_group: str):
    """
    Deletes Wazuh groups for a given customer.

    Args:
        customer_meta_wazuh_group (str): The customer's Wazuh group.

    Returns:
        list: A list of group codes that were successfully deleted.
    """
    wazuh_groups = ["Linux", "Windows", "Mac"]

    # Initialize an empty list to store the groups deleted
    groups_deleted = []

    # Loop through the groups and get the agent IDs for each group and append them to the list
    for group in wazuh_groups:
        group_code = generate_group_code(group, customer_meta_wazuh_group)
        logger.info(f"Deleting group {group_code}")
        try:
            response = await send_wazuh_delete_request(
                endpoint="groups",
                params={
                    "groups_list": group_code,
                },
            )
            logger.info(f"Response for {group_code}: {response}")
        except Exception as e:
            logger.error(f"Error deleting group {group_code}: {e}")
            continue

        groups_deleted.append(group_code)

    return groups_deleted
