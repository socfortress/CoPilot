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
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services.universal import select_all_users
from app.auth.utils import AuthHandler
from app.connectors.wazuh_indexer.utils.universal import (
    get_available_indices_via_source,
)
from app.db.db_session import get_db
from app.connectors.wazuh_indexer.schema.sigma import SigmaQueryOutResponse, CreateSigmaQuery, DownloadSigmaRulesRequest, BulkUploadToDBResponse, UpdateSigmaActive, UpdateSigmaTimeInterval, RunActiveSigmaQueries
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import list_sigma_queries, create_sigma_query, add_sigma_queries_to_db, delete_sigma_rule, set_sigma_query_active, list_active_sigma_queries, update_sigma_time_interval, parse_time_interval
from app.connectors.wazuh_indexer.services.sigma.sigma_download import download_and_extract_zip, keep_only_folder_directory, find_yaml_files
from app.connectors.wazuh_indexer.services.sigma.generate_query import create_sigma_query_from_rule
from app.connectors.wazuh_indexer.services.sigma.execute_query import execute_query

wazuh_indexer_sigma_router = APIRouter()

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

@wazuh_indexer_sigma_router.get(
    "/queries/active",
    response_model=SigmaQueryOutResponse
)
async def get_active_sigma_queries_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a list of active Sigma queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        List[SigmaQuery]: A list of Sigma queries.
    """
    return SigmaQueryOutResponse(
        sigma_queries=await list_active_sigma_queries(db),
        success=True,
        message="Successfully retrieved the active Sigma queries.",
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

@wazuh_indexer_sigma_router.post(
    "/activate-all-queries",
    response_model=SigmaQueryOutResponse
)
async def activate_all_sigma_queries_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Activates all Sigma queries.


    Args:
        db (AsyncSession): The database session.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    sigma_queries = await list_sigma_queries(db)
    for query in sigma_queries:
        await set_sigma_query_active(query.rule_name, True, db)
    return SigmaQueryOutResponse(
        success=True,
        message="Successfully activated all Sigma queries.",
    )

@wazuh_indexer_sigma_router.post(
    "/run-active-queries",
    response_model=SigmaQueryOutResponse
)
async def run_active_sigma_queries_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Runs the active Sigma queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    active_sigma_queries = await list_active_sigma_queries(db)
    for query in active_sigma_queries:
        time_interval_delta = parse_time_interval(query.time_interval)
        if datetime.now() - query.last_execution_time >= time_interval_delta:
            logger.info(f"Running Sigma query: {query.rule_name}")
            response = await execute_query(RunActiveSigmaQueries(query=query.rule_query, time_interval=query.time_interval, last_execution_time=query.last_execution_time, rule_name=query.rule_name, index="new-wazuh*"), session=db)
            # Update the last execution time to the current time and commit the changes
            query.last_execution_time = datetime.now()
            await db.commit()
    return SigmaQueryOutResponse(
        success=True,
        message="Successfully ran the active Sigma queries.",
    )

@wazuh_indexer_sigma_router.put(
    "/queries/set-active",
    response_model=SigmaQueryOutResponse
)
async def set_sigma_query_active_endpoint(
    request: UpdateSigmaActive,
    db: AsyncSession = Depends(get_db),
):
    """
    Sets the active status of a Sigma query.

    Args:
        db (AsyncSession): The database session.
        rule_name (str): The rule name to set active.
        active (bool): The active status to set.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    await set_sigma_query_active(request.rule_name, request.active, db)
    return SigmaQueryOutResponse(
        success=True,
        message=f"Successfully set the active status of the Sigma query: {request.rule_name} to {request.active}",
    )

@wazuh_indexer_sigma_router.put(
    "/queries/set-time-interval",
    response_model=SigmaQueryOutResponse
)
async def set_sigma_query_time_interval_endpoint(
    request: UpdateSigmaTimeInterval,
    db: AsyncSession = Depends(get_db),
):
    """
    Sets the time interval of a Sigma query.

    Args:
        db (AsyncSession): The database session.
        rule_name (str): The rule name to set active.
        time_interval (str): The time interval to set.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    await update_sigma_time_interval(request.rule_name, request.time_interval, db)
    return SigmaQueryOutResponse(
        success=True,
        message=f"Successfully set the time interval of the Sigma query: {request.rule_name} to {request.time_interval}",
    )

@wazuh_indexer_sigma_router.delete(
    "/queries/delete",
    response_model=SigmaQueryOutResponse
)
async def delete_sigma_rule_endpoint(
    rule_name: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes a Sigma query.

    Args:
        db (AsyncSession): The database session.
        rule_name (str): The rule name to delete.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    await delete_sigma_rule(rule_name, db)
    return SigmaQueryOutResponse(
        success=True,
        message=f"Successfully deleted the Sigma query: {rule_name}",
    )

@wazuh_indexer_sigma_router.delete(
    "/queries/delete-all",
    response_model=SigmaQueryOutResponse
)
async def delete_all_sigma_rules_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes all Sigma queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    sigma_queries = await list_sigma_queries(db)
    for query in sigma_queries:
        await delete_sigma_rule(query.rule_name, db)
    return SigmaQueryOutResponse(
        success=True,
        message="Successfully deleted all Sigma queries.",
    )
