import json
from pathlib import Path

from fastapi import HTTPException
from loguru import logger


from app.connectors.grafana.utils.universal import create_grafana_client


async def delete_folder(
    organization_id: int,
    folder_id: int,
) -> dict:
    """
    """
    logger.info(
        f"Updating dashboards for organization {organization_id} and folder {folder_id}",
    )
    try:
        grafana_client = await create_grafana_client("Grafana")
        # Switch to the newly created organization
        grafana_client.user.switch_actual_user_organisation(organization_id)
        logger.info(
            f"Deleting folder {folder_id} for organization {organization_id}",
        )
        return grafana_client.folder.delete_folder(folder_id)
    except Exception as e:
        logger.error(f"Error deleting folder: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting dashboard folder: {e}")
