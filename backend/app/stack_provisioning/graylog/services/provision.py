import json
from pathlib import Path

from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.services.content_packs import insert_content_pack
from app.connectors.graylog.services.content_packs import install_content_pack
from app.stack_provisioning.graylog.schema.provision import ProvisionGraylogResponse


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


async def provision_content_pack(content_pack_name: str) -> ProvisionGraylogResponse:
    """
    Provision the Wazuh Content Pack in the Graylog instance
    """
    logger.info(f"Provisioning {content_pack_name} Content Pack...")
    content_pack = load_content_pack_json(f"{content_pack_name}.json")
    # ! Only for testing purposes
    # await write_content_pack_to_file(content_pack)

    logger.info(f"Inserting {content_pack_name} Content Pack...")
    await insert_content_pack(content_pack)
    # ! Content Pack ID is found in the first `id` field and the revision is found in the first `rev` field
    id, rev = await get_id_and_rev(content_pack)
    logger.info(f"Id: {id}, Rev: {rev}")
    await install_content_pack(content_pack_id=id, revision=rev)
    return ProvisionGraylogResponse(success=True, message=f"{content_pack_name} Content Pack provisioned successfully")
