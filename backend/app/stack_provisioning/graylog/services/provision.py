from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import json


from app.stack_provisioning.graylog.schema.provision import ProvisionGraylogResponse
from app.connectors.graylog.services.content_packs import insert_content_pack, install_content_pack
from app.connectors.graylog.schema.content_packs import ContentPack

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

        return ContentPack(**content_pack_data).dict()

    except FileNotFoundError:
        logger.error(f"Content pack JSON file not found at {file_path}")
        raise HTTPException(status_code=404, detail="Content pack JSON file not found")

async def provision_wazuh_content_pack(
    session: AsyncSession,
) -> ProvisionGraylogResponse:
    """
    Provision the Wazuh Content Pack in the Graylog instance
    """
    logger.info(f"Provisioning Wazuh Content Pack...")
    content_pack = load_content_pack_json("wazuh_content_pack.json")
    logger.info(f"Inserting Wazuh Content Pack...")
    await insert_content_pack(content_pack)
    # ! Content Pack ID is found in the `wazuh_content_pack.json` file
    await install_content_pack(content_pack_id='261577fe-d9a2-4141-af74-635f085eee54', revision=1)
    return ProvisionGraylogResponse(success=True, message="Wazuh Content Pack provisioned successfully")
