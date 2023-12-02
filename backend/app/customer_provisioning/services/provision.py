import json
from pathlib import Path
from typing import List
from pydantic.json import pydantic_encoder

from fastapi import HTTPException
from loguru import logger
from datetime import datetime

from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.customer_provisioning.schema.provision import TimeBasedIndexSet
from app.connectors.graylog.utils.universal import send_post_request

# ! GRAYLOG PROVISIONING ! #
async def create_index_set(provision_customer_request: ProvisionNewCustomer):
    logger.info(f"Creating index set for customer {provision_customer_request.customer_name}")
    index_set = TimeBasedIndexSet(
        title="Wazuh - " + provision_customer_request.customer_name,
        description="Wazuh - " + provision_customer_request.customer_name,
        index_prefix=provision_customer_request.customer_index_name,
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
            "max_number_of_indices": provision_customer_request.hot_data_retention,
        },
        creation_date=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        index_analyzer="standard",
        shards=provision_customer_request.index_shards,
        replicas=provision_customer_request.index_replicas,
        index_optimization_max_num_segments=1,
        # index_optimization_disabled=False,
        # writable=True,
        field_type_refresh_interval=5000,
    )

    # Print the index set
    json_index_set = json.dumps(index_set.dict())

    logger.info(f"json_index_set set: {json_index_set}")

    # response = await send_post_request(endpoint="/api/events/search", data=alert_query.dict())
    response = await send_post_request(endpoint="/api/system/indices/index_sets", data=(index_set.dict()))
    logger.info(f"Response from Graylog: {response}")
    return response

async def provision_customer(provision_customer_request: ProvisionNewCustomer):
    logger.info(f"Provisioning new customer {provision_customer_request}")
    # Create index set
    index_set = await create_index_set(provision_customer_request)
    return {"message": "Provisioning new customer"}
