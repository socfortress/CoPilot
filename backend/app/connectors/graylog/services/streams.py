from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import requests
import xmltodict
from loguru import logger
from pydantic import Field

from app.connectors.graylog.schema.streams import GraylogStreamsResponse
from app.connectors.graylog.schema.streams import Stream
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request


def get_streams() -> GraylogStreamsResponse:
    """Get streams from Graylog."""
    logger.info(f"Getting streams from Graylog")
    streams_collected = send_get_request(endpoint="/api/streams")
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


def get_stream_ids() -> List[str]:
    """Get stream IDs from Graylog."""
    logger.info(f"Getting stream IDs from Graylog")
    streams_collected = send_get_request(endpoint="/api/streams")
    if streams_collected["success"]:
        return [stream_data["id"] for stream_data in streams_collected["data"]["streams"]]
    else:
        return []
