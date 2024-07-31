from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import requests
import shutil
import zipfile
import os

from app.connectors.wazuh_indexer.models.sigma import SigmaQuery
from app.connectors.wazuh_indexer.schema.sigma import CreateSigmaQuery

async def download_and_extract_zip(url: str) -> None:
    """
    Downloads a zipped folder from the given URL and extracts its contents into the specified directory.

    Args:
        url (str): The URL of the zipped folder.
        extract_to (str): The directory to extract the contents to. Defaults to the current directory.
    """
    #local_zip_path = os.path.join(extract_to, "sigma_all_rules.zip")
    directory = "app/connectors/wazuh_indexer/sigma_artifacts"
    full_path = os.path.abspath(directory)

    logger.info(f"Checking directory: {full_path}")
    local_zip_path = os.path.join(full_path, "sigma_all_rules.zip")

    # Ensure the directory exists
    os.makedirs(full_path, exist_ok=True)

    # Download the zipped folder
    response = requests.get(url)
    response.raise_for_status()  # Check if the request was successful

    # Save the zipped folder to a local file
    with open(local_zip_path, "wb") as file:
        file.write(response.content)

    # Extract the contents of the zipped folder
    with zipfile.ZipFile(local_zip_path, "r") as zip_ref:
        zip_ref.extractall(full_path)

    # Remove the downloaded zip file
    os.remove(local_zip_path)

async def keep_only_folder_directory(folder: str, directory: str = "app/connectors/wazuh_indexer/sigma_artifacts/rules"):
    """
    Removes all directories except the Windows directory from the specified directory.

    Args:
        directory (str): The directory to clean up.
    """
    for item in os.listdir(directory):
        if item != folder:
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                logger.info(f"Removing directory and its contents: {item_path}")
                shutil.rmtree(item_path)

async def find_yaml_files(directory: str = "app/connectors/wazuh_indexer/sigma_artifacts/rules/windows") -> List[str]:
    """
    Finds all YAML files in the specified directory.

    Args:
        directory (str): The directory to search for YAML files.

    Returns:
        List[str]: A list of YAML file paths.
    """
    yaml_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".yml"):
                #yaml_files.append(os.path.join(root, file))
                #logger.info(f"Found YAML file: {file}")
                full_path = os.path.join(root, file)
                yaml_files.append(full_path)

    return yaml_files
