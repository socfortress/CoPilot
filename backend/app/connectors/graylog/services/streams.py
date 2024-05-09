from typing import List

from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.schema.streams import GraylogStreamsResponse
from app.connectors.graylog.schema.streams import Stream
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_put_request


async def get_streams() -> GraylogStreamsResponse:
    """Get streams from Graylog.

    Returns:
        GraylogStreamsResponse: The response object containing the streams collected from Graylog.

    Raises:
        HTTPException: If there is an error while collecting the streams.
    """
    logger.info("Getting streams from Graylog")
    streams_collected = await send_get_request(endpoint="/api/streams")
    try:
        if streams_collected["success"]:
            streams_list = [Stream(**stream_data) for stream_data in streams_collected["data"]["streams"]]
            return GraylogStreamsResponse(
                streams=streams_list,
                success=True,
                message="Streams collected successfully",
                total=streams_collected["data"]["total"],
            )
        else:
            return GraylogStreamsResponse(
                streams=[],
                success=False,
                message="Failed to collect streams",
                total=0,
            )
    except KeyError as e:
        logger.error(f"Failed to collect streams key: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect streams key: {e}",
        )
    except Exception as e:
        logger.error(f"Failed to collect streams: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect streams: {e}")


async def get_stream_ids() -> List[str]:
    """Get stream IDs from Graylog.

    Returns:
        List[str]: A list of stream IDs.

    Raises:
        HTTPException: If there is an error collecting the stream IDs.
    """
    logger.info("Getting stream IDs from Graylog")
    streams_collected = await send_get_request(endpoint="/api/streams")
    try:
        if streams_collected["success"]:
            return [stream_data["id"] for stream_data in streams_collected["data"]["streams"]]
        else:
            return []
    except KeyError as e:
        logger.error(f"Failed to collect streams key: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect streams key: {e}",
        )
    except Exception as e:
        logger.error(f"Failed to collect streams: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect streams: {e}")


async def assign_stream_to_index(stream_id: str, index_id: str) -> bool:
    """Assign a stream to an index.

    Args:
        stream_id (str): The ID of the stream to assign.
        index_id (str): The ID of the index to assign the stream to.

    Returns:
        bool: True if the stream is successfully assigned to the index, False if it is not.

    Raises:
        HTTPException: If there is an error assigning the stream to the index.
    """
    logger.info(f"Assigning stream {stream_id} to index {index_id}")
    response = await send_put_request(endpoint=f"/api/streams/{stream_id}", data={"index_set_id": index_id})
    if response["success"]:
        return True
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to assign stream {stream_id} to index {index_id}",
        )
