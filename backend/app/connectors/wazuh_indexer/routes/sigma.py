import asyncio
import os
from datetime import datetime

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.schema.sigma import ActivateSigmaQueryResponse
from app.connectors.wazuh_indexer.schema.sigma import BulkUploadToDBResponse
from app.connectors.wazuh_indexer.schema.sigma import CreateSigmaQuery
from app.connectors.wazuh_indexer.schema.sigma import DeactivateSigmaQueryResponse
from app.connectors.wazuh_indexer.schema.sigma import DeleteSigmaQueryResponse
from app.connectors.wazuh_indexer.schema.sigma import DownloadSigmaRulesRequest
from app.connectors.wazuh_indexer.schema.sigma import RunActiveSigmaQueries
from app.connectors.wazuh_indexer.schema.sigma import SigmaQueryOutResponse
from app.connectors.wazuh_indexer.schema.sigma import SigmaRuleUploadRequest
from app.connectors.wazuh_indexer.schema.sigma import UpdateSigmaActive
from app.connectors.wazuh_indexer.schema.sigma import UpdateSigmaTimeInterval
from app.connectors.wazuh_indexer.services.sigma.execute_query import execute_query
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    add_sigma_queries_to_db,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    create_sigma_query,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    delete_sigma_rule,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    get_sigma_query_by_id,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    list_active_sigma_queries,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    list_inactive_sigma_queries,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    list_sigma_queries,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    parse_time_interval,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    process_sigma_file,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    set_sigma_query_active,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_db_operations import (
    update_sigma_time_interval,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_download import (
    download_and_extract_zip,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_download import (
    keep_only_folder_directory,
)
from app.db.db_session import get_db

wazuh_indexer_sigma_router = APIRouter()


def save_file(file: UploadFile, file_path: str):
    """
    Save the uploaded file to the specified path.

    Args:
        file (UploadFile): The uploaded file.
        file_path (str): The path to save the file.
    """
    try:
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        logger.info(f"File saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while saving the file.")


def cleanup_file(file_path: str):
    """
    Remove the file from the specified path.

    Args:
        file_path (str): The path of the file to remove.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"File {file_path} removed")
    except Exception as e:
        logger.error(f"Error removing file: {e}")


@wazuh_indexer_sigma_router.get("/queries/available", response_model=SigmaQueryOutResponse)
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


@wazuh_indexer_sigma_router.get("/queries/active", response_model=SigmaQueryOutResponse)
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


@wazuh_indexer_sigma_router.get("/queries/inactive", response_model=SigmaQueryOutResponse)
async def get_inactive_sigma_queries_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a list of inactive Sigma queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        List[SigmaQuery]: A list of Sigma queries.
    """
    return SigmaQueryOutResponse(
        sigma_queries=await list_inactive_sigma_queries(db),
        success=True,
        message="Successfully retrieved the inactive Sigma queries.",
    )


@wazuh_indexer_sigma_router.post("/queries/create", response_model=SigmaQueryOutResponse)
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


@wazuh_indexer_sigma_router.post("/bulk-upload-to-db", response_model=BulkUploadToDBResponse)
async def upload_sigma_queries_to_db_endpoint(
    request: SigmaRuleUploadRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads the Sigma queries to the database.

    Args:
        db (AsyncSession): The database session.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    await add_sigma_queries_to_db(request, db)
    return BulkUploadToDBResponse(success=True, message="Successfully uploaded the Sigma queries to the database.")


@wazuh_indexer_sigma_router.post("/activate-all-queries", response_model=ActivateSigmaQueryResponse)
async def activate_all_sigma_queries_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Activates all Sigma queries.


    Args:
        db (AsyncSession): The database session.

    Returns:
        ActivateSigmaQueryResponse: The Sigma queries response.
    """
    sigma_queries = await list_sigma_queries(db)
    enabled_queries = []
    for query in sigma_queries:
        await set_sigma_query_active(query.rule_name, True, db)
        enabled_queries.append(query.rule_name)
    return ActivateSigmaQueryResponse(
        success=True,
        message="Successfully activated all Sigma queries.",
        enabled_queries=enabled_queries,
    )


@wazuh_indexer_sigma_router.post("/deactivate-all-queries", response_model=DeactivateSigmaQueryResponse)
async def deactivate_all_sigma_queries_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivates all Sigma queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        DeactivateSigmaQueryResponse: The Sigma queries response.
    """
    sigma_queries = await list_sigma_queries(db)
    disabled_queries = []
    for query in sigma_queries:
        await set_sigma_query_active(query.rule_name, False, db)
        disabled_queries.append(query.rule_name)
    return DeactivateSigmaQueryResponse(
        success=True,
        message="Successfully deactivated all Sigma queries.",
        disabled_queries=disabled_queries,
    )


# @wazuh_indexer_sigma_router.post("/run-active-queries", response_model=SigmaQueryOutResponse)
# async def run_active_sigma_queries_endpoint(
#     index_name: str = Query(default="wazuh*"),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Runs the active Sigma queries.

#     Args:
#         db (AsyncSession): The database session.

#     Returns:
#         SigmaQueryOutResponse: The Sigma queries response.
#     """
#     active_sigma_queries = await list_active_sigma_queries(db)
#     for query in active_sigma_queries:
#         time_interval_delta = parse_time_interval(query.time_interval)
#         logger.info(f"Time interval delta: {time_interval_delta}")
#         current_time = datetime.now()
#         logger.info(f"Current time: {current_time}")
#         logger.info(f"Last execution time: {query.last_execution_time}")

#         # Check if the current time is less than the last execution time
#         if current_time < query.last_execution_time or current_time - query.last_execution_time >= time_interval_delta:
#             logger.info(f"Running Sigma query: {query.rule_name}")
#             await execute_query(
#                 RunActiveSigmaQueries(
#                     query=query.rule_query,
#                     time_interval=query.time_interval,
#                     last_execution_time=query.last_execution_time,
#                     rule_name=query.rule_name,
#                     index=index_name,
#                 ),
#                 session=db,
#             )
#             # Update the last execution time to the current time and commit the changes
#             # ! Remove commented out code after testing ! #
#             query.last_execution_time = current_time
#             await db.commit()
#         else:
#             time_comparison = current_time - query.last_execution_time
#             logger.info(f"Time comparison: {time_comparison}")
#             logger.info(f"Skipping Sigma query because the time interval has not passed: {query.rule_name}")
#     return SigmaQueryOutResponse(
#         success=True,
#         message="Successfully ran the active Sigma queries.",
#     )


@wazuh_indexer_sigma_router.post("/run-active-queries", response_model=SigmaQueryOutResponse)
async def run_active_sigma_queries_endpoint(
    index_name: str = Query(default="wazuh*"),
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
    tasks = []

    for query in active_sigma_queries:
        time_interval_delta = parse_time_interval(query.time_interval)
        logger.info(f"Time interval delta: {time_interval_delta}")
        current_time = datetime.now()
        logger.info(f"Current time: {current_time}")
        logger.info(f"Last execution time: {query.last_execution_time}")

        # Check if the current time is less than the last execution time
        if current_time < query.last_execution_time or current_time - query.last_execution_time >= time_interval_delta:
            logger.info(f"Running Sigma query: {query.rule_name}")
            task = execute_query(
                RunActiveSigmaQueries(
                    query=query.rule_query,
                    time_interval=query.time_interval,
                    last_execution_time=query.last_execution_time,
                    rule_name=query.rule_name,
                    index=index_name,
                ),
                session=db,
            )
            tasks.append(task)
            # Update the last execution time to the current time
            query.last_execution_time = current_time

    # Run all tasks concurrently
    await asyncio.gather(*tasks)

    # Commit the changes to the database
    await db.commit()

    return SigmaQueryOutResponse(
        success=True,
        message="Successfully ran the active Sigma queries.",
    )


@wazuh_indexer_sigma_router.post("/run-single-query", response_model=SigmaQueryOutResponse)
async def run_single_sigma_query_endpoint(
    index_name: str = Query(default="wazuh*"),
    rule_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Runs a single Sigma query.

    Args:
        db (AsyncSession): The database session.
        rule_id (int): The rule ID to run.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    query = await get_sigma_query_by_id(db=db, sigma_query_id=rule_id)
    time_interval_delta = parse_time_interval(query.time_interval)
    current_time = datetime.now()
    if current_time < query.last_execution_time or current_time - query.last_execution_time >= time_interval_delta:
        await execute_query(
            RunActiveSigmaQueries(
                query=query.rule_query,
                time_interval=query.time_interval,
                last_execution_time=query.last_execution_time,
                rule_name=query.rule_name,
                index=index_name,
            ),
            session=db,
        )
        query.last_execution_time = current_time
        await db.commit()
    else:
        time_comparison = current_time - query.last_execution_time
        logger.info(f"Time comparison: {time_comparison}")
        logger.info(f"Skipping Sigma query because the time interval has not passed: {query.rule_name}")
    return SigmaQueryOutResponse(
        success=True,
        message="Successfully ran the active Sigma queries.",
    )


@wazuh_indexer_sigma_router.post("/upload")
async def upload_sigma_queries_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads the Sigma queries to the database.

    Args:
        db (AsyncSession): The database session.

    Returns:
        SigmaQueryOutResponse: The Sigma queries response.
    """
    if not file.filename.endswith(".yml"):
        raise HTTPException(status_code=400, detail="File must be a YAML file.")

    file_path = f"app/connectors/wazuh_indexer/sigma_artifacts/{file.filename}"

    try:
        save_file(file, file_path)
        await process_sigma_file(file=file_path, db=db)
    except Exception as e:
        logger.error(f"Error processing Sigma file: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the file.")
    finally:
        cleanup_file(file_path)

    return {"message": "Successfully uploaded the Sigma queries to the database.", "success": True}


@wazuh_indexer_sigma_router.put("/queries/set-active", response_model=SigmaQueryOutResponse)
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
    return SigmaQueryOutResponse(
        sigma_queries=[await set_sigma_query_active(request.rule_name, request.active, db)],
        success=True,
        message=f"Successfully set the active status of the Sigma query: {request.rule_name} to {request.active}",
    )


@wazuh_indexer_sigma_router.put("/queries/set-time-interval", response_model=SigmaQueryOutResponse)
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
    return SigmaQueryOutResponse(
        sigma_queries=[await update_sigma_time_interval(request.rule_name, request.time_interval, db)],
        success=True,
        message=f"Successfully set the time interval of the Sigma query: {request.rule_name} to {request.time_interval}",
    )


@wazuh_indexer_sigma_router.delete("/queries/delete", response_model=DeleteSigmaQueryResponse)
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
    return DeleteSigmaQueryResponse(
        deleted_queries=[rule_name],
        success=True,
        message=f"Successfully deleted the Sigma query: {rule_name}",
    )


@wazuh_indexer_sigma_router.delete("/queries/delete-all", response_model=DeleteSigmaQueryResponse)
async def delete_all_sigma_rules_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes all Sigma queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        DeleteSigmaQueryResponse: The Sigma queries response.
    """
    sigma_queries = await list_sigma_queries(db)
    deleted_queries = []
    for query in sigma_queries:
        await delete_sigma_rule(query.rule_name, db)
        deleted_queries.append(query.rule_name)
    return DeleteSigmaQueryResponse(
        deleted_queries=deleted_queries,
        success=True,
        message="Successfully deleted all Sigma queries.",
    )
