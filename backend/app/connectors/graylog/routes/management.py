from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.management import DeletedIndexBody
from app.connectors.graylog.schema.management import DeletedIndexResponse
from app.connectors.graylog.schema.management import StartInputBody
from app.connectors.graylog.schema.management import StartInputResponse
from app.connectors.graylog.schema.management import StartStreamBody
from app.connectors.graylog.schema.management import StartStreamResponse
from app.connectors.graylog.schema.management import StopInputBody
from app.connectors.graylog.schema.management import StopInputResponse
from app.connectors.graylog.schema.management import StopStreamBody
from app.connectors.graylog.schema.management import StopStreamResponse
from app.connectors.graylog.schema.management import UrlWhitelistEntryResponse
from app.connectors.graylog.services.collector import get_index_names
from app.connectors.graylog.services.collector import get_input_ids
from app.connectors.graylog.services.collector import get_url_whitelist_entries
from app.connectors.graylog.services.management import delete_index
from app.connectors.graylog.services.management import start_input
from app.connectors.graylog.services.management import start_stream
from app.connectors.graylog.services.management import stop_input
from app.connectors.graylog.services.management import stop_stream
from app.connectors.graylog.services.streams import get_stream_ids

graylog_management_router = APIRouter()


async def get_managed_index_names() -> List[str]:
    """
    Retrieves the names of the managed indexes.

    Returns:
        A list of strings representing the names of the managed indexes.
    """
    return await get_index_names()


async def get_managed_input_ids() -> List[str]:
    """
    Retrieves the IDs of the managed inputs.

    Returns:
        A list of strings representing the IDs of the managed inputs.
    """
    return await get_input_ids()


async def get_managed_stream_ids() -> List[str]:
    """
    Retrieves the IDs of the managed streams.

    Returns:
        A list of strings representing the IDs of the managed streams.
    """
    return await get_stream_ids()


async def verify_index_name(deleted_index_body: DeletedIndexBody) -> DeletedIndexBody:
    """
    Verifies if the given index name is managed by Graylog or still exists.

    Args:
        deleted_index_body (DeletedIndexBody): The body containing the index name to be verified.

    Raises:
        HTTPException: If the index name is not managed by Graylog or no longer exists.

    Returns:
        DeletedIndexBody: The verified index name.
    """
    # Remove any extra spaces from index_name
    deleted_index_body.index_name = deleted_index_body.index_name.strip()

    managed_index_names = await get_managed_index_names()
    if deleted_index_body.index_name not in managed_index_names:
        raise HTTPException(
            status_code=400,
            detail=f"Index name '{deleted_index_body.index_name}' is not managed by Graylog or no longer exists.",
        )
    return deleted_index_body


async def verify_input_id(stop_input_body: StopInputBody) -> StopInputBody:
    """
    Verifies if the given input ID is valid and managed by Graylog.

    Args:
        stop_input_body (StopInputBody): The input body containing the input ID to be verified.

    Raises:
        HTTPException: If the input ID is not managed by Graylog or no longer exists.

    Returns:
        StopInputBody: The verified input body.
    """
    # Remove any extra spaces from input_id
    stop_input_body.input_id = stop_input_body.input_id.strip()

    managed_input_ids = await get_managed_input_ids()
    if stop_input_body.input_id not in managed_input_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Input ID '{stop_input_body.input_id}' is not managed by Graylog or no longer exists.",
        )
    return stop_input_body


async def verify_stream_id(stop_stream_body: StopStreamBody) -> StopStreamBody:
    """
    Verifies if the provided stream ID is managed by Graylog or still exists.

    Args:
        stop_stream_body (StopStreamBody): The body containing the stream ID to be verified.

    Raises:
        HTTPException: If the stream ID is not managed by Graylog or no longer exists.

    Returns:
        StopStreamBody: The verified stop_stream_body object.
    """
    # Remove any extra spaces from stream_id
    stop_stream_body.stream_id = stop_stream_body.stream_id.strip()

    managed_stream_ids = await get_managed_stream_ids()
    if stop_stream_body.stream_id not in managed_stream_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Stream ID '{stop_stream_body.stream_id}' is not managed by Graylog or no longer exists.",
        )
    return stop_stream_body


@graylog_management_router.get(
    "/url_whitelist",
    response_model=UrlWhitelistEntryResponse,
    description="Get the URL whitelist entries.",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_url_whitelist() -> UrlWhitelistEntryResponse:
    """
    Get the URL whitelist entries.

    Returns:
    - UrlWhitelistEntryResponse: The response containing the URL whitelist entries.
    """
    logger.info("Getting URL whitelist entries")

    return await get_url_whitelist_entries()


@graylog_management_router.delete(
    "/index",
    response_model=DeletedIndexResponse,
    description="Delete index",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def delete_index_route(
    deleted_index_body: DeletedIndexBody = Depends(verify_index_name),
) -> DeletedIndexResponse:
    """
    Delete index route.

    This route is used to delete an index in Graylog.

    Parameters:
    - deleted_index_body (DeletedIndexBody): The body of the request containing the index name.

    Returns:
    - DeletedIndexResponse: The response containing the result of the deletion.

    """
    logger.info(f"Deleting index {deleted_index_body.index_name}")

    return await delete_index(deleted_index_body.index_name)


@graylog_management_router.post(
    "/input/stop",
    response_model=StopInputResponse,
    description="Stop input",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def stop_input_route(
    stop_input_body: StopInputBody = Depends(verify_input_id),
) -> StopInputResponse:
    """
    Stop input route.

    This route is used to stop an input in Graylog.

    Parameters:
    - stop_input_body (StopInputBody): The body of the request containing the input ID.

    Returns:
    - StopInputResponse: The response containing the status of the input stop operation.
    """
    logger.info(f"Stopping input {stop_input_body.input_id}")

    return await stop_input(stop_input_body.input_id)


@graylog_management_router.post(
    "/input/start",
    response_model=StartInputResponse,
    description="Start input",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def start_input_route(
    start_input_body: StartInputBody = Depends(verify_input_id),
) -> StartInputResponse:
    """
    Start the input with the given input ID.

    Args:
        start_input_body (StartInputBody): The request body containing the input ID.

    Returns:
        StartInputResponse: The response containing the result of starting the input.
    """
    logger.info(f"Starting input {start_input_body.input_id}")

    return await start_input(start_input_body.input_id)


@graylog_management_router.post(
    "/stream/stop",
    response_model=StopStreamResponse,
    description="Stop stream",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def stop_stream_route(
    stop_stream_body: StopStreamBody = Depends(verify_stream_id),
) -> StopStreamResponse:
    """
    Stop stream route.

    This route is used to stop a stream in Graylog.

    Parameters:
    - stop_stream_body (StopStreamBody): The request body containing the stream ID.

    Returns:
    - StopStreamResponse: The response containing the result of stopping the stream.
    """
    logger.info(f"Stopping stream {stop_stream_body.stream_id}")

    return await stop_stream(stop_stream_body.stream_id)


@graylog_management_router.post(
    "/stream/start",
    response_model=StartStreamResponse,
    description="Start stream",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def start_stream_route(
    start_stream_body: StartStreamBody = Depends(verify_stream_id),
) -> StartStreamResponse:
    """
    Start stream route.

    This route is used to start a stream in Graylog.

    Parameters:
    - start_stream_body (StartStreamBody): The request body containing the stream ID.

    Returns:
    - StartStreamResponse: The response containing the result of starting the stream.
    """
    logger.info(f"Starting stream {start_stream_body.stream_id}")

    return await start_stream(start_stream_body.stream_id)
