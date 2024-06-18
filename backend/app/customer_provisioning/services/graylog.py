import json
from datetime import datetime

from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.services.pipelines import get_pipelines
from app.connectors.graylog.utils.universal import send_delete_request
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request
from app.customer_provisioning.schema.graylog import GraylogIndexSetCreationResponse
from app.customer_provisioning.schema.graylog import StreamConnectionToPipelineRequest
from app.customer_provisioning.schema.graylog import StreamConnectionToPipelineResponse
from app.customer_provisioning.schema.graylog import StreamCreationResponse
from app.customer_provisioning.schema.graylog import TimeBasedIndexSet
from app.customer_provisioning.schema.graylog import WazuhEventStream
from app.customer_provisioning.schema.provision import ProvisionNewCustomer


######### ! GRAYLOG PROVISIONING ! ############
# ! INDEX SETS ! #
def build_index_set_config(request: ProvisionNewCustomer) -> TimeBasedIndexSet:
    """
    Build the configuration for a time-based index set.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.

    Returns:
        TimeBasedIndexSet: The configured time-based index set.
    """
    return TimeBasedIndexSet(
        title=f"{request.customer_name} - Wazuh EDR EVENTS",
        description=f"{request.customer_name} - Wazuh EDR EVENTS",
        index_prefix=request.customer_index_name,
        rotation_strategy_class="org.graylog2.indexer.rotation.strategies.TimeBasedRotationStrategy",
        rotation_strategy={
            "type": "org.graylog2.indexer.rotation.strategies.TimeBasedRotationStrategyConfig",
            "rotation_period": "P1D",
            "rotate_empty_index_set": False,
            "max_rotation_period": None,
        },
        retention_strategy_class="org.graylog2.indexer.retention.strategies.DeletionRetentionStrategy",
        retention_strategy={
            "type": "org.graylog2.indexer.retention.strategies.DeletionRetentionStrategyConfig",
            "max_number_of_indices": request.hot_data_retention,
        },
        creation_date=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        index_analyzer="standard",
        shards=request.index_shards,
        replicas=request.index_replicas,
        index_optimization_max_num_segments=1,
        index_optimization_disabled=False,
        writable=True,
        field_type_refresh_interval=5000,
    )


# Function to send the POST request and handle the response
async def send_index_set_creation_request(
    index_set: TimeBasedIndexSet,
) -> GraylogIndexSetCreationResponse:
    """
    Sends a request to create an index set in Graylog.

    Args:
        index_set (TimeBasedIndexSet): The index set to be created.

    Returns:
        GraylogIndexSetCreationResponse: The response from Graylog after creating the index set.
    """
    json_index_set = json.dumps(index_set.dict())
    logger.info(f"json_index_set set: {json_index_set}")
    response_json = await send_post_request(
        endpoint="/api/system/indices/index_sets",
        data=index_set.dict(),
    )
    return GraylogIndexSetCreationResponse(**response_json)


# Refactored create_index_set function
async def create_index_set(
    request: ProvisionNewCustomer,
) -> GraylogIndexSetCreationResponse:
    """
    Creates an index set for a new customer.

    Args:
        request (ProvisionNewCustomer): The request object containing the customer information.

    Returns:
        GraylogIndexSetCreationResponse: The response object containing the result of the index set creation.
    """
    logger.info(f"Creating index set for customer {request.customer_name}")
    index_set_config = build_index_set_config(request)
    return await send_index_set_creation_request(index_set_config)


# Function to extract index set ID
def extract_index_set_id(response: GraylogIndexSetCreationResponse) -> str:
    """
    Extracts the index set ID from the given GraylogIndexSetCreationResponse object.

    Args:
        response (GraylogIndexSetCreationResponse): The GraylogIndexSetCreationResponse object.

    Returns:
        str: The index set ID extracted from the response.
    """
    return response.data.id


# ! Event STREAMS ! #
# Function to create event stream configuration
def build_event_stream_config(
    request: ProvisionNewCustomer,
    index_set_id: str,
) -> WazuhEventStream:
    """
    Build the configuration for a Wazuh event stream.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.
        index_set_id (str): The ID of the index set.

    Returns:
        WazuhEventStream: The configured Wazuh event stream.
    """
    return WazuhEventStream(
        title=f"{request.customer_name} - Wazuh EDR EVENTS",
        description=f"{request.customer_name} - Wazuh EDR EVENTS",
        index_set_id=index_set_id,
        rules=[
            {
                "field": "agent_labels_customer",
                "type": 1,
                "inverted": False,
                "value": request.customer_code,
            },
            {"field": "cluster_node", "type": 1, "inverted": False, "value": f"wazuh.worker.{request.customer_name}"},
        ],
        matching_type="OR",
        remove_matches_from_default_stream=True,
        content_pack=None,
    )


async def send_event_stream_creation_request(
    event_stream: WazuhEventStream,
) -> StreamCreationResponse:
    """
    Sends a request to create an event stream.

    Args:
        event_stream (WazuhEventStream): The event stream to be created.

    Returns:
        StreamCreationResponse: The response containing the created event stream.
    """
    json_event_stream = json.dumps(event_stream.dict())
    logger.info(f"json_event_stream set: {json_event_stream}")
    response_json = await send_post_request(
        endpoint="/api/streams",
        data=event_stream.dict(),
    )
    return StreamCreationResponse(**response_json)


async def create_event_stream(request: ProvisionNewCustomer, index_set_id: str):
    """
    Creates an event stream for a customer.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.
        index_set_id (str): The ID of the index set.

    Returns:
        The result of the event stream creation request.
    """
    logger.info(f"Creating event stream for customer {request.customer_name}")
    event_stream_config = build_event_stream_config(request, index_set_id)
    return await send_event_stream_creation_request(event_stream_config)


# ! PIPELINES ! #
# Function to get pipeline ID
async def get_pipeline_id(subscription: str) -> str:
    """
    Retrieves the pipeline ID for a given subscription.

    Args:
        subscription (str): The subscription name.

    Returns:
        str: The pipeline ID.

    Raises:
        HTTPException: If the pipeline ID cannot be retrieved.
    """
    logger.info(f"Getting pipeline ID for subscription {subscription}")
    pipelines_response = await get_pipelines()
    if pipelines_response.success:
        for pipeline in pipelines_response.pipelines:
            if subscription.lower() in pipeline.description.lower():
                return [pipeline.id]
        logger.error(f"Failed to get pipeline ID for subscription {subscription}")
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to get pipeline ID for subscription {subscription}. "
                "Please ensure you have installed the SOCFortress Wazuh Content Pack. "
                "See more at: https://youtu.be/euFrHP0VkD8?si=ajqjNobHvBjrTzAH"
            ),
        )
    else:
        logger.error(f"Failed to get pipelines: {pipelines_response.message}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pipelines: {pipelines_response.message}",
        )


async def connect_stream_to_pipeline(
    stream_and_pipeline: StreamConnectionToPipelineRequest,
):
    """
    Connects a stream to a pipeline.

    Args:
        stream_and_pipeline (StreamConnectionToPipelineRequest): The request object containing the stream ID and pipeline IDs.

    Returns:
        StreamConnectionToPipelineResponse: The response object containing the connection details.
    """
    logger.info(
        f"Connecting stream {stream_and_pipeline.stream_id} to pipeline {stream_and_pipeline.pipeline_ids}",
    )
    response_json = await send_post_request(
        endpoint="/api/system/pipelines/connections/to_stream",
        data=stream_and_pipeline.dict(),
    )
    logger.info(f"Response: {response_json}")
    return StreamConnectionToPipelineResponse(**response_json)


######### ! GRAYLOG DECOMISSIONGING ! ############
async def delete_stream(stream_id: str):
    """
    Deletes a stream.

    Args:
        stream_id (str): The ID of the stream to be deleted.

    Returns:
        The result of the stream deletion request.
    """
    logger.info(f"Deleting stream {stream_id}")
    response = await send_delete_request(endpoint=f"/api/streams/{stream_id}")
    return response


async def delete_index_set(index_set_id: str):
    """
    Deletes an index set.

    Args:
        index_set_id (str): The ID of the index set to be deleted.

    Returns:
        The result of the index set deletion request.
    """
    logger.info(f"Deleting index set {index_set_id}")
    response = await send_delete_request(
        endpoint=f"/api/system/indices/index_sets/{index_set_id}",
    )
    return response


async def get_content_pack_installation_id(content_pack_id: str):
    """
    Retrieves the installation ID of a content pack.

    Args:
        content_pack_id (str): The ID of the content pack.

    Returns:
        str: The installation ID of the content pack.
    """
    logger.info(f"Getting installation ID for content pack {content_pack_id}")
    response = await send_get_request(
        endpoint=f"/api/system/content_packs/{content_pack_id}/installations",
    )
    return response["data"]["installations"][0]["_id"]


async def uninstall_content_pack(content_pack_id: str):
    """
    Uninstalls a content pack.

    Args:
        content_pack_id (str): The ID of the content pack to be deleted.

    Returns:
        The result of the content pack deletion request.
    """
    logger.info(f"Deleting content pack {content_pack_id}")
    installation_id = await get_content_pack_installation_id(content_pack_id)
    response = await send_delete_request(
        endpoint=f"/api/system/content_packs/{content_pack_id}/installations/{installation_id}",
    )
    return response


async def delete_content_pack(content_pack_id: str):
    """
    Deletes a content pack.

    Args:
        content_pack_id (str): The ID of the content pack to be deleted.

    Returns:
        The result of the content pack deletion request.
    """
    logger.info(f"Deleting content pack {content_pack_id}")
    response = await send_delete_request(
        endpoint=f"/api/system/content_packs/{content_pack_id}",
    )
    return response
