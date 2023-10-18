from typing import List

from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.schema.streams import GraylogStreamsResponse
from app.connectors.graylog.schema.streams import Stream
from app.connectors.graylog.utils.universal import send_get_request


def get_streams() -> GraylogStreamsResponse:
    """Get streams from Graylog."""
    logger.info("Getting streams from Graylog")
    streams_collected = send_get_request(endpoint="/api/streams")
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
            return GraylogStreamsResponse(streams=[], success=False, message="Failed to collect streams", total=0)
    except KeyError as e:
        logger.error(f"Failed to collect streams key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect streams key: {e}")
    except Exception as e:
        logger.error(f"Failed to collect streams: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect streams: {e}")


def get_stream_ids() -> List[str]:
    """Get stream IDs from Graylog."""
    logger.info("Getting stream IDs from Graylog")
    streams_collected = send_get_request(endpoint="/api/streams")
    try:
        if streams_collected["success"]:
            return [stream_data["id"] for stream_data in streams_collected["data"]["streams"]]
        else:
            return []
    except KeyError as e:
        logger.error(f"Failed to collect streams key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect streams key: {e}")
    except Exception as e:
        logger.error(f"Failed to collect streams: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect streams: {e}")
