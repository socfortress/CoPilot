import json
from datetime import datetime

from loguru import logger
from fastapi import HTTPException
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.graylog.services.pipelines import get_pipelines
from app.connectors.graylog.services.management import start_stream
from app.connectors.wazuh_manager.utils.universal import send_post_request as send_wazuh_post_request
from app.customer_provisioning.schema.provision import GraylogIndexSetCreationResponse
from app.customer_provisioning.schema.provision import ProvisionNewCustomer, WazuhEventStream, StreamCreationResponse, CustomerSubsctipion, StreamConnectionToPipelineRequest, StreamConnectionToPipelineResponse
from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponse
from app.customer_provisioning.schema.provision import TimeBasedIndexSet


######### ! GRAYLOG PROVISIONING ! ############
# ! INDEX SETS ! #
# Function to create index set configuration
def build_index_set_config(request: ProvisionNewCustomer) -> TimeBasedIndexSet:
    return TimeBasedIndexSet(
        title=f"Wazuh - {request.customer_name}",
        description=f"Wazuh - {request.customer_name}",
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
async def send_index_set_creation_request(index_set: TimeBasedIndexSet) -> GraylogIndexSetCreationResponse:
    json_index_set = json.dumps(index_set.dict())
    logger.info(f"json_index_set set: {json_index_set}")
    response_json = await send_post_request(endpoint="/api/system/indices/index_sets", data=index_set.dict())
    return GraylogIndexSetCreationResponse(**response_json)


# Refactored create_index_set function
async def create_index_set(request: ProvisionNewCustomer) -> GraylogIndexSetCreationResponse:
    logger.info(f"Creating index set for customer {request.customer_name}")
    index_set_config = build_index_set_config(request)
    return await send_index_set_creation_request(index_set_config)


# Function to extract index set ID
def extract_index_set_id(response: GraylogIndexSetCreationResponse) -> str:
    return response.data.id


# ! Event STREAMS ! #
# Function to create event stream configuration
def build_event_stream_config(request: ProvisionNewCustomer, index_set_id: str) -> WazuhEventStream:
    return WazuhEventStream(
        title=f"WAZUH EVENTS CUSTOMERS - {request.customer_name}",
        description=f"WAZUH EVENTS CUSTOMERS - {request.customer_name}",
        index_set_id=index_set_id,
        rules=[
            {
                "field": "agent_labels_customer",
                "type": 1,
                "inverted": False,
                "value": request.customer_code,
            }
        ],
        matching_type="AND",
        remove_matches_from_default_stream=True,
        content_pack=None,
    )

async def send_event_stream_creation_request(event_stream: WazuhEventStream) -> StreamCreationResponse:
    json_event_stream = json.dumps(event_stream.dict())
    logger.info(f"json_event_stream set: {json_event_stream}")
    response_json = await send_post_request(endpoint="/api/streams", data=event_stream.dict())
    return StreamCreationResponse(**response_json)

async def create_event_stream(request: ProvisionNewCustomer, index_set_id: str):
    logger.info(f"Creating event stream for customer {request.customer_name}")
    event_stream_config = build_event_stream_config(request, index_set_id)
    return await send_event_stream_creation_request(event_stream_config)

# ! PIPELINES ! #
# Function to get pipeline ID
async def get_pipeline_id(subscription: str) -> str:
    logger.info(f"Getting pipeline ID for subscription {subscription}")
    pipelines_response = await get_pipelines()
    if pipelines_response.success:
        for pipeline in pipelines_response.pipelines:
            if subscription.lower() in pipeline.description.lower():
                return [pipeline.id]
        logger.error(f"Failed to get pipeline ID for subscription {subscription}")
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline ID for subscription {subscription}")
    else:
        logger.error(f"Failed to get pipelines: {pipelines_response.message}")
        raise HTTPException(status_code=500, detail=f"Failed to get pipelines: {pipelines_response.message}")

async def connect_stream_to_pipeline(stream_and_pipeline: StreamConnectionToPipelineRequest):
    logger.info(f"Connecting stream {stream_and_pipeline.stream_id} to pipeline {stream_and_pipeline.pipeline_ids}")
    response_json = await send_post_request(endpoint="/api/system/pipelines/connections/to_stream", data=stream_and_pipeline.dict())
    logger.info(f"Response: {response_json}")
    return StreamConnectionToPipelineResponse(**response_json)


######### ! WAZUH MANAGER PROVISIONING ! ############
# Function to generate group codes
def generate_group_code(group, customer_code):
    return f"{group}_{customer_code}"

# Separate function for sending POST requests to Wazuh
async def create_wazuh_group(group_code):
    endpoint = "groups"
    data = {"group_id": group_code}
    return await send_wazuh_post_request(endpoint=endpoint, data=data)

# Main function to create Wazuh groups
async def create_wazuh_groups(request: ProvisionNewCustomer):
    logger.info(f"Creating Wazuh groups for customer {request.customer_name} with code {request.customer_code}")

    wazuh_groups = ['Linux', 'Windows', 'Mac']  # This list can be moved to a config file or a global variable

    for group in wazuh_groups:
        group_code = generate_group_code(group, request.customer_code)
        logger.info(f"Creating group with code {group_code}")
        try:
            response = await create_wazuh_group(group_code)
            logger.info(f"Response for {group_code}: {response}")
        except Exception as e:
            logger.error(f"Error creating group {group_code}: {e}")


# ! MAIN FUNCTION ! #
async def provision_wazuh_customer(request: ProvisionNewCustomer):
    logger.info(f"Provisioning new customer {request}")
    created_index_response = await create_index_set(request)
    index_set_id = created_index_response.data.id
    created_stream_response = await create_event_stream(request, index_set_id)
    stream_id = created_stream_response.data.stream_id
    logger.info(f"Created index set with ID: {index_set_id} and stream with ID: {stream_id}")
    pipeline_ids = await get_pipeline_id(subscription="Wazuh")
    logger.info(f"Pipeline ID: {pipeline_ids}")
    stream_and_pipeline = StreamConnectionToPipelineRequest(stream_id=stream_id, pipeline_ids=pipeline_ids)
    await connect_stream_to_pipeline(stream_and_pipeline)
    if await start_stream(stream_id=stream_id) is False:
        raise HTTPException(status_code=500, detail=f"Failed to start stream {stream_id}")
    await create_wazuh_groups(request)
    return {"message": "Provisioning new customer"}
