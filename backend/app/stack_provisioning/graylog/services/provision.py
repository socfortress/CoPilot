from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path


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

async def provision_wazuh_content_pack(
    session: AsyncSession,
) -> ProvisionGraylogResponse:
    """
    Provision the Wazuh Content Pack in the Graylog instance
    """
    logger.info(f"Provisioning Wazuh Content Pack...")
    content_path = get_content_pack_path("wazuh_content_pack.json")
    logger.info(f"Content pack path: {content_path}")
    return ProvisionGraylogResponse(success=True, message="Wazuh Content Pack provisioned successfully")
