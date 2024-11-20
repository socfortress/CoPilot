import json
from pathlib import Path

from fastapi import HTTPException
from loguru import logger


from app.connectors.grafana.utils.universal import create_grafana_client
from app.connectors.grafana.schema.folders import FoldersResponse, Folder


async def delete_folder(
    organization_id: int,
    folder_id: int,
) -> dict:
    """
    Delete a folder for a given organization.

    Args:
        organization_id (int): The ID of the organization.
        folder_id (int): The ID of the folder to be deleted.

    Returns:
        dict: The response from the Grafana client.
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
        list_all_folders = grafana_client.folder.get_all_folders()

        # Parse the response using the Pydantic model
        folders_response = FoldersResponse(folders=[Folder(**folder) for folder in list_all_folders])
        logger.info(f"Search for folder with ID {folder_id}")

        # Ensure the folder_id is being compared correctly
        folder_uid = next((folder.uid for folder in folders_response.folders if folder.id == folder_id), None)

        if not folder_uid:
            raise HTTPException(status_code=404, detail=f"Folder with ID {folder_id} not found")

        return grafana_client.folder.delete_folder(folder_uid)
    except Exception as e:
        logger.error(f"Error deleting folder: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting dashboard folder: {e}")
