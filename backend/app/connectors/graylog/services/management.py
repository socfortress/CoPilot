from typing import Dict, List, Optional, Any, Tuple, Union
import requests
import xmltodict
from loguru import logger
from pydantic import Field

from app.connectors.graylog.schema.management import (
    DeletedIndexResponse, DeletedIndexBody, StopInputBody, StopInputResponse, StartInputBody, StartInputResponse, StopStreamBody, StopStreamResponse, StartStreamBody, StartStreamResponse
)

from app.connectors.graylog.utils.universal import (
    send_get_request, send_delete_request, send_put_request, send_post_request
)

from app.connectors.graylog.services.collector import (
    get_index_names
)

def delete_index(index_name: DeletedIndexBody) -> DeletedIndexResponse:
    """Delete an index from Graylog."""
    logger.info(f"Deleting index {index_name} from Graylog")
    send_delete_request(endpoint=f"/api/system/indexer/indices/{index_name}")
    # Check if the index still exists
    index_names = get_index_names()
    logger.info(f"Index names: {index_names}")
    if index_name in index_names:
        return DeletedIndexResponse(success=False, message=f"Failed to delete index {index_name}. If the index is still in use, it cannot be deleted.")
    else:
        return DeletedIndexResponse(success=True, message=f"Successfully deleted index {index_name}")

def stop_input(input_id: StopInputBody) -> StopInputResponse:
    """Stop an input in Graylog."""
    logger.info(f"Stopping input {input_id} in Graylog")
    response = send_delete_request(endpoint=f"/api/system/inputstates/{input_id}")
    if response["success"]:
        return StopInputResponse(success=True, message=f"Successfully stopped input {input_id}")
    else:
        return StopInputResponse(success=False, message=f"Failed to stop input {input_id}")
    
def start_input(input_id: StartInputBody) -> StartInputResponse:
    """Start an input in Graylog."""
    logger.info(f"Starting input {input_id} in Graylog")
    response = send_put_request(endpoint=f"/api/system/inputstates/{input_id}")
    if response["success"]:
        return StartInputResponse(success=True, message=f"Successfully started input {input_id}")
    else:
        return StartInputResponse(success=False, message=f"Failed to start input {input_id}")
    

def stop_stream(stream_id: StopStreamBody) -> StopStreamResponse:
    """Stop a stream in Graylog."""
    logger.info(f"Stopping stream {stream_id} in Graylog")
    response = send_post_request(endpoint=f"/api/streams/{stream_id}/pause")
    logger.info(f"Response: {response}")
    if response["success"]:
        return StopStreamResponse(success=True, message=f"Successfully stopped stream {stream_id}")
    else:
        return StopStreamResponse(success=False, message=f"Failed to stop stream {stream_id}")
    
def start_stream(stream_id: StartStreamBody) -> StartStreamResponse:
    """Start a stream in Graylog."""
    logger.info(f"Starting stream {stream_id} in Graylog")
    response = send_post_request(endpoint=f"/api/streams/{stream_id}/resume")
    if response["success"]:
        return StartStreamResponse(success=True, message=f"Successfully started stream {stream_id}")
    else:
        return StartStreamResponse(success=False, message=f"Failed to start stream {stream_id}")

    
