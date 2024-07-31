from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services.universal import select_all_users
from app.auth.utils import AuthHandler
from app.connectors.wazuh_indexer.utils.universal import (
    get_available_indices_via_source,
)
from app.db.db_session import get_db
from app.connectors.wazuh_indexer.schema.sigma import SigmaQueryOutResponse, CreateSigmaQuery
from app.connectors.wazuh_indexer.services.sigma_db_operations import list_sigma_queries, create_sigma_query
from app.connectors.wazuh_indexer.services.sigma_download import download_and_extract_zip, keep_only_windows_directory


wazuh_indexer_sigma_router = APIRouter()

@wazuh_indexer_sigma_router.post(
    "/download",
    response_model=SigmaQueryOutResponse
)
async def download_sigma_queries_endpoint(
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
    sigma_url = "https://github.com/SigmaHQ/sigma/releases/download/r2024-07-17/sigma_all_rules.zip"
    await download_and_extract_zip(sigma_url)
    await keep_only_windows_directory()

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
