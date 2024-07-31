from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
import yaml
import re
from fastapi import Security
import os
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services.universal import select_all_users
from app.auth.utils import AuthHandler
from app.connectors.wazuh_indexer.utils.universal import (
    get_available_indices_via_source,
)
from app.db.db_session import get_db
from app.connectors.wazuh_indexer.schema.sigma import SigmaQueryOutResponse, CreateSigmaQuery, DownloadSigmaRulesRequest, BulkUploadToDBResponse
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import list_sigma_queries, create_sigma_query, add_sigma_queries_to_db
from app.connectors.wazuh_indexer.services.sigma.sigma_download import download_and_extract_zip, keep_only_folder_directory, find_yaml_files
from app.connectors.wazuh_indexer.services.sigma.generate_query import create_sigma_query_from_rule

wazuh_indexer_sigma_router = APIRouter()


@wazuh_indexer_sigma_router.post(
    "/download",
)
async def download_sigma_queries_endpoint(
    request: DownloadSigmaRulesRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Downloads the Sigma queries from the Wazuh repository.

    Args:
        db (AsyncSession): The database session.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    # Define the URL to download the Sigma queries from
    await download_and_extract_zip(request.url)
    await keep_only_folder_directory(folder=request.folder)
    return {"message": "Successfully downloaded the Sigma queries.", "success": True}

@wazuh_indexer_sigma_router.post(
    "/bulk-upload-to-db",
    response_model=BulkUploadToDBResponse
)
async def upload_sigma_queries_to_db_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads the Sigma queries to the database.

    Args:
        db (AsyncSession): The database session.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    await add_sigma_queries_to_db(db)
    return BulkUploadToDBResponse(success=True, message="Successfully uploaded the Sigma queries to the database.")



@wazuh_indexer_sigma_router.get(
    "/queries/available",
    response_model=SigmaQueryOutResponse
)
async def get_sigma_queries_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a list of Sigma queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        List[SigmaQuery]: A list of Sigma queries.
    """
    return SigmaQueryOutResponse(
        sigma_queries=await list_sigma_queries(db),
        success=True,
        message="Successfully retrieved the Sigma queries.",
    )

@wazuh_indexer_sigma_router.post(
    "/queries/create",
    response_model=SigmaQueryOutResponse
)
async def create_sigma_query_endpoint(
    sigma_query: CreateSigmaQuery,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a Sigma query.

    Args:
        db (AsyncSession): The database session.
        sigma_query (CreateSigmaQuery): The Sigma query creation request.

    Returns:
        SigmaQuery: The created Sigma query.
    """
    logger.info(f"Creating Sigma query: {sigma_query.dict()}")
    return SigmaQueryOutResponse(
        sigma_queries=[await create_sigma_query(sigma_query, db)],
        success=True,
        message="Successfully created the Sigma query.",
    )
