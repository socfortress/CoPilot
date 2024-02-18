from loguru import logger

from app.connectors.graylog.schema.management import DeletedIndexBody
from app.connectors.graylog.schema.management import DeletedIndexResponse
from app.connectors.graylog.schema.management import GraylogServerInfo
from app.connectors.graylog.schema.management import StartInputBody
from app.connectors.graylog.schema.management import StartInputResponse
from app.connectors.graylog.schema.management import StartStreamBody
from app.connectors.graylog.schema.management import StartStreamResponse
from app.connectors.graylog.schema.management import StopInputBody
from app.connectors.graylog.schema.management import StopInputResponse
from app.connectors.graylog.schema.management import StopStreamBody
from app.connectors.graylog.schema.management import StopStreamResponse
from app.connectors.graylog.services.collector import get_index_names
from app.connectors.graylog.utils.universal import send_delete_request
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.graylog.utils.universal import send_put_request


async def get_system_info() -> GraylogServerInfo:
    """Get system information from Graylog.

    Returns:
        GraylogServerInfo: The system information from Graylog.
    """
    logger.info("Getting system information from Graylog")
    response = await send_get_request(endpoint="/api/system")
    return GraylogServerInfo(**response["data"])


async def delete_index(index_name: DeletedIndexBody) -> DeletedIndexResponse:
    """Delete an index from Graylog.

    Args:
        index_name (DeletedIndexBody): The name of the index to be deleted.

    Returns:
        DeletedIndexResponse: The response indicating the success or failure of the index deletion.
    """
    logger.info(f"Deleting index {index_name} from Graylog")
    await send_delete_request(endpoint=f"/api/system/indexer/indices/{index_name}")
    # Check if the index still exists
    index_names = await get_index_names()
    logger.info(f"Index names: {index_names}")
    if index_name in index_names:
        return DeletedIndexResponse(
            success=False,
            message=f"Failed to delete index {index_name}. If the index is still in use, it cannot be deleted.",
        )
    else:
        return DeletedIndexResponse(
            success=True,
            message=f"Successfully deleted index {index_name}",
        )


async def stop_input(input_id: StopInputBody) -> StopInputResponse:
    """Stop an input in Graylog.

    Args:
        input_id (StopInputBody): The ID of the input to stop.

    Returns:
        StopInputResponse: The response indicating the success or failure of stopping the input.
    """
    logger.info(f"Stopping input {input_id} in Graylog")
    response = await send_delete_request(endpoint=f"/api/system/inputstates/{input_id}")
    if response["success"]:
        return StopInputResponse(
            success=True,
            message=f"Successfully stopped input {input_id}",
        )
    else:
        return StopInputResponse(
            success=False,
            message=f"Failed to stop input {input_id}",
        )


async def start_input(input_id: StartInputBody) -> StartInputResponse:
    """Start an input in Graylog.

    Args:
        input_id (StartInputBody): The ID of the input to start.

    Returns:
        StartInputResponse: The response indicating the success or failure of starting the input.
    """
    logger.info(f"Starting input {input_id} in Graylog")
    response = await send_put_request(endpoint=f"/api/system/inputstates/{input_id}")
    if response["success"]:
        return StartInputResponse(
            success=True,
            message=f"Successfully started input {input_id}",
        )
    else:
        return StartInputResponse(
            success=False,
            message=f"Failed to start input {input_id}",
        )


async def stop_stream(stream_id: StopStreamBody) -> StopStreamResponse:
    """Stop a stream in Graylog.

    Args:
        stream_id (StopStreamBody): The ID of the stream to stop.

    Returns:
        StopStreamResponse: The response indicating the success or failure of stopping the stream.
    """
    logger.info(f"Stopping stream {stream_id} in Graylog")
    response = await send_post_request(endpoint=f"/api/streams/{stream_id}/pause")
    logger.info(f"Response: {response}")
    if response["success"]:
        return StopStreamResponse(
            success=True,
            message=f"Successfully stopped stream {stream_id}",
        )
    else:
        return StopStreamResponse(
            success=False,
            message=f"Failed to stop stream {stream_id}",
        )


async def start_stream(stream_id: StartStreamBody) -> StartStreamResponse:
    """Start a stream in Graylog.

    Args:
        stream_id (StartStreamBody): The ID of the stream to start.

    Returns:
        StartStreamResponse: The response indicating the success or failure of starting the stream.
    """
    logger.info(f"Starting stream {stream_id} in Graylog")
    response = await send_post_request(endpoint=f"/api/streams/{stream_id}/resume")
    if response["success"]:
        return StartStreamResponse(
            success=True,
            message=f"Successfully started stream {stream_id}",
        )
    else:
        return StartStreamResponse(
            success=False,
            message=f"Failed to start stream {stream_id}",
        )
