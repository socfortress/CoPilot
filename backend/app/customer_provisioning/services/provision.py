import json
from datetime import datetime
from loguru import logger


from app.connectors.graylog.utils.universal import send_post_request
from app.customer_provisioning.schema.provision import GraylogIndexSetCreationResponse
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.customer_provisioning.schema.provision import TimeBasedIndexSet

# ! GRAYLOG PROVISIONING ! #


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


# ! MAIN FUNCTION ! #
async def provision_customer(request: ProvisionNewCustomer):
    logger.info(f"Provisioning new customer {request}")
    created_index_response = await create_index_set(request)
    index_set_id = extract_index_set_id(created_index_response)
    logger.info(f"Index set ID: {index_set_id}")
    return {"message": "Provisioning new customer"}
