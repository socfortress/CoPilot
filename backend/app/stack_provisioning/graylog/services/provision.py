import json
from enum import Enum
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.schema.pipelines import CreatePipelineRule
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse
from app.connectors.graylog.services.content_packs import insert_content_pack
from app.connectors.graylog.services.content_packs import install_content_pack
from app.connectors.graylog.services.pipelines import create_pipeline_rule
from app.connectors.graylog.services.pipelines import get_pipeline_rules
from app.stack_provisioning.graylog.schema.provision import AvailableContentPacks
from app.stack_provisioning.graylog.schema.provision import ProvisionContentPackRequest
from app.stack_provisioning.graylog.schema.provision import ProvisionGraylogResponse
from app.stack_provisioning.graylog.schema.provision import (
    ProvisionNetworkContentPackRequest,
)
from app.stack_provisioning.graylog.schema.provision import ReplaceContentPackKeywords
from app.stack_provisioning.graylog.services.utils import does_content_pack_exist


def get_content_pack_path(file_name: str) -> Path:
    """
    Returns the path to the dashboard JSON file.

    Parameters:
    - dashboard_info (tuple): A tuple containing the folder name and file name of the dashboard.

    Returns:
    - Path: The path to the dashboard JSON file.
    """
    current_file = Path(__file__)  # Path to the current file
    base_dir = current_file.parent.parent  # Move up two levels to the 'grafana' directory
    return base_dir / "templates" / file_name


def load_content_pack_json(file_name: str) -> dict:
    """
    Load the JSON data of a dashboard from a file and replace the 'uid' value with the provided datasource UID.

    Args:
        dashboard_info (tuple): Information about the dashboard (e.g., file name, directory).
        datasource_uid (str): The UID of the datasource to replace in the dashboard JSON.

    Returns:
        dict: The loaded dashboard data with the replaced 'uid' value.

    Raises:
        FileNotFoundError: If the dashboard JSON file is not found.
        HTTPException: If there is an error decoding the JSON from the file.
    """
    logger.info(f"Loading content pack JSON file: {file_name}")
    file_path = get_content_pack_path(file_name)
    try:
        with open(file_path, "r") as file:
            content_pack_data = json.load(file)

        return content_pack_data

    except FileNotFoundError:
        logger.error(f"Content pack JSON file not found at {file_path}")
        raise HTTPException(status_code=404, detail="Content pack JSON file not found")


async def get_id_and_rev(data: dict) -> tuple:
    return data.get("id"), data.get("rev")


# ! Only for testing purposes
async def write_content_pack_to_file(content_pack: dict) -> None:
    """
    Write the content pack to a file. Just for testing purposes.

    Args:
        content_pack (dict): The content pack to write to a file.
    """
    file_path = get_content_pack_path("wazuh_content_pack_testing.json")
    with open(file_path, "w") as file:
        json.dump(content_pack, file, indent=4)


async def retrieve_valid_content_packs(content_pack_type: str) -> list:
    """
    Returns a list of content pack template names based on the type.

    Args:
        content_pack_type (str): The type of content pack to retrieve.

    Returns:
        list: A list of content pack template names.
    """
    available_content_packs = [pack.name for pack in AvailableContentPacks]
    logger.info(f"Available content packs: {available_content_packs}")
    # Create a list of valid content pack names based on the content pack type
    valid_content_pack_names = []
    for content_pack in available_content_packs:
        if content_pack_type in content_pack:
            valid_content_pack_names.append(content_pack)
    return valid_content_pack_names


def replace_keywords_in_json_complex(data, replacements):
    """
    Recursively replace specified keywords in JSON data, including within strings, with the provided values in the replacements dictionary.

    Args:
    data (dict or list): The JSON data in which replacements need to be made.
    replacements (dict): A dictionary mapping keywords to their respective replacement values.

    Returns:
    dict or list: The modified JSON data with the keywords replaced.
    """
    if isinstance(data, dict):
        return {key: replace_keywords_in_json_complex(value, replacements) for key, value in data.items()}
    elif isinstance(data, list):
        return [replace_keywords_in_json_complex(item, replacements) for item in data]
    elif isinstance(data, str):
        for key, value in replacements.items():
            data = data.replace(key, str(value))
        return data
    else:
        return data


def convert_port_value_to_int(data):
    """
    Recursively navigates through a JSON-like dictionary and converts the port value to an integer.

    Args:
    data (dict or list): The JSON data in which the port value needs to be converted.

    Returns:
    dict or list: The modified JSON data with the port value converted to integer.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "port" and isinstance(value, dict) and "@value" in value and isinstance(value["@value"], str):
                try:
                    # Convert the string to an integer
                    value["@value"] = int(value["@value"])
                except ValueError:
                    # Handle the case where the string cannot be converted to an integer
                    pass
            else:
                # Recurse into the value
                data[key] = convert_port_value_to_int(value)
    elif isinstance(data, list):
        # Process each item in the list
        data = [convert_port_value_to_int(item) for item in data]
    return data


async def provision_content_pack(content_pack_request: ProvisionContentPackRequest) -> ProvisionGraylogResponse:
    """
    Provision the Wazuh Content Pack in the Graylog instance
    """
    logger.info(
        f"Provisioning {content_pack_request.content_pack_name.name} Content Pack with keywords {content_pack_request.keywords} ...",
    )

    content_pack = load_content_pack_json(f"{content_pack_request.content_pack_name.name}.json")
    # ! Only for testing purposes
    # await write_content_pack_to_file(content_pack)
    # return ProvisionGraylogResponse(success=True, message=f"{content_pack_request.content_pack_name.name} Content Pack provisioned successfully")

    logger.info(f"Inserting {content_pack_request.content_pack_name.name} Content Pack...")
    await insert_content_pack(content_pack)
    # ! Content Pack ID is found in the first `id` field and the revision is found in the first `rev` field
    id, rev = await get_id_and_rev(content_pack)
    logger.info(f"Id: {id}, Rev: {rev}")
    await install_content_pack(content_pack_id=id, revision=rev)
    return ProvisionGraylogResponse(
        success=True,
        message=f"{content_pack_request.content_pack_name.name} Content Pack provisioned successfully",
    )


class PipelineRuleTitles(Enum):
    ETW = "Set Syslog Level to ALERT for ETW Registry"


async def check_pipeline_rules() -> None:
    """
    Checks if the pipeline rules exist in Graylog. If they don't, create them.
    """
    pipeline_rules = await get_pipeline_rules()
    non_existing_rules = await pipeline_rules_exists(pipeline_rules)
    if non_existing_rules:
        logger.info(f"Creating pipeline rules: {non_existing_rules}")
        await create_pipeline_rules(non_existing_rules)


async def pipeline_rules_exists(pipeline_rules: PipelineRulesResponse) -> List[str]:
    """
    Checks if the pipeline rules exist in Graylog and returns a list of non-existing pipeline rules.
    """
    return [
        rule_title.value
        for rule_title in PipelineRuleTitles
        if not any(rule.title == rule_title.value for rule in pipeline_rules.pipeline_rules)
    ]


async def create_pipeline_rules(non_existing_rules: List[str]) -> None:
    """
    Creates the given pipeline rules.
    """
    rule_creators = {
        "Set Syslog Level to ALERT for ETW Registry": create_etw_rule,
    }

    for rule_title in non_existing_rules:
        logger.info(f"Creating pipeline rule {rule_title}.")
        await rule_creators[rule_title](rule_title)


async def create_etw_rule(rule_title: str) -> None:
    """
    Creates the 'Set Syslog Level to ALERT for ETW Registry' pipeline rule.
    """
    rule_source = (
        f'rule "{rule_title}"\n'
        "when\n"
        '  has_field("syscheck_path") &&\n'
        '  starts_with(to_string($message.syscheck_path), "HKEY_LOCAL_MACHINE\\\\SYSTEM\\\\CurrentControlSet\\\\Control\\\\WMI\\\\Autologger\\\\EventLog")\n'
        "then\n"
        '  set_field("syslog_level", "ALERT");\n'
        "end"
    )
    await create_pipeline_rule(
        CreatePipelineRule(
            title=rule_title,
            description=rule_title,
            source=rule_source,
        ),
    )


# ! NETWORK CONNECTOR CONTENT PACKS PROVISIONING ! #
async def filter_content_packs(content_packs, protocol_type):
    if protocol_type == "TCP":
        return [pack for pack in content_packs if "UDP" not in pack]
    if protocol_type == "UDP":
        return [pack for pack in content_packs if "TCP" not in pack]
    return content_packs


async def process_content_pack(content_pack, content_pack_request):
    content_pack_exists = await does_content_pack_exist(content_pack_request.keywords.customer_name)
    if content_pack_exists is True:
        return
    content_pack = load_content_pack_json(f"{content_pack}.json")
    replace_content_pack_keywords = ReplaceContentPackKeywords(
        REPLACE_UUID_GLOBAL=str(uuid4()),
        REPLACE_UUID_SPECIFIC=str(uuid4()),
        customer_name=content_pack_request.keywords.customer_name,
        customer_code=content_pack_request.keywords.customer_code,
        SYSLOG_PORT=content_pack_request.keywords.syslog_port,
    )
    if "PROCESSING_PIPELINE" not in content_pack:
        content_pack = replace_keywords_in_json_complex(content_pack, replace_content_pack_keywords.dict())
        content_pack = convert_port_value_to_int(content_pack)
    await insert_and_install_content_pack(content_pack)


async def insert_and_install_content_pack(content_pack):
    logger.info(f"Inserting {content_pack} Content Pack...")
    content_pack_inserted = await insert_content_pack(content_pack)
    id, rev = await get_id_and_rev(content_pack)
    logger.info(f"Id: {id}, Rev: {rev}")
    if content_pack_inserted is True:
        await install_content_pack(content_pack_id=id, revision=rev)
    else:
        logger.info(f"Content pack {content_pack['name']} already inserted, skipping install...")


async def provision_content_pack_network_connector(content_pack_request: ProvisionNetworkContentPackRequest) -> ProvisionGraylogResponse:
    logger.info(f"Provisioning {content_pack_request.content_pack_name} Content Pack with keywords {content_pack_request.keywords} ...")
    content_packs = await retrieve_valid_content_packs(content_pack_request.content_pack_name)
    content_packs = await filter_content_packs(content_packs, content_pack_request.keywords.protocol_type)
    logger.info(f"Valid content packs: {content_packs}")
    for content_pack in content_packs:
        await process_content_pack(content_pack, content_pack_request)
    return ProvisionGraylogResponse(success=True, message=f"{content_pack_request.content_pack_name} Content Pack provisioned successfully")
