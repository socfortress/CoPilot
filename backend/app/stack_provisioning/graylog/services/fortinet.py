from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from datetime import datetime
import json

from app.stack_provisioning.graylog.schema.fortinet import FortinetCustomerDetails
from app.stack_provisioning.graylog.schema.fortinet import ProvisionFortinetKeys
from app.stack_provisioning.graylog.schema.provision import ContentPackKeywords
from app.stack_provisioning.graylog.schema.provision import (
    ProvisionNetworkContentPackRequest,
)
from app.customer_provisioning.schema.graylog import StreamConnectionToPipelineRequest
from app.stack_provisioning.graylog.services.provision import (
    provision_content_pack_network_connector,
)
from app.customer_provisioning.services.graylog import get_pipeline_id, connect_stream_to_pipeline
from app.connectors.graylog.services.collector import get_stream_id_by_stream_name, get_input_id_by_input_name
from app.utils import get_customer_meta_attribute

from app.connectors.graylog.utils.universal import send_post_request
from app.customer_provisioning.schema.graylog import GraylogIndexSetCreationResponse
from app.customer_provisioning.schema.graylog import TimeBasedIndexSet
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.connectors.wazuh_indexer.services.monitoring import (
    output_shard_number_to_be_set_based_on_nodes,
)
from app.connectors.graylog.services.streams import assign_stream_to_index
from app.network_connectors.models.network_connectors import CustomerNetworkConnectorsMeta

async def build_index_set_config(request: FortinetCustomerDetails) -> TimeBasedIndexSet:
    """
    Build the configuration for a time-based index set.

    Args:
        request (FortinetCustomerDetails): The request object containing customer information.

    Returns:
        TimeBasedIndexSet: The configured time-based index set.
    """
    return TimeBasedIndexSet(
        title=f"{request.customer_name} - FORTINET EVENTS",
        description=f"{request.customer_name} - FORTINET EVENTS",
        index_prefix=f"fortinet-{request.customer_code}",
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
        shards=await output_shard_number_to_be_set_based_on_nodes(),
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
    index_set_config = await build_index_set_config(request)
    return await send_index_set_creation_request(index_set_config)

async def provision_content_pack(customer_details):
    """
    Provisions a content pack for a customer.

    Args:
        customer_details (CustomerDetails): The details of the customer.

    Returns:
        ContentPack: The provisioned content pack.
    """
    return await provision_content_pack_network_connector(
        content_pack_request=ProvisionNetworkContentPackRequest(
            content_pack_name="FORTINET",
            keywords=ContentPackKeywords(
                customer_name=customer_details.customer_name,
                customer_code=customer_details.customer_code,
                protocol_type=customer_details.protocal_type,
                syslog_port=customer_details.syslog_port,
            ),
        ),
    )

async def get_stream_and_index_ids(customer_details):
    """
    Retrieves the stream ID and index ID for a given customer.

    Args:
        customer_details (CustomerDetails): The details of the customer.

    Returns:
        tuple: A tuple containing the stream ID and index ID.
    """
    stream_id = await get_stream_id_by_stream_name(stream_name=f'{customer_details.customer_name} - FORTINET LOGS AND EVENTS')
    index_id = (await create_index_set(request=customer_details)).data.id
    return stream_id, index_id

async def create_customer_network_connector_meta(customer_details, stream_id, index_id, session):
    """
    Create a CustomerNetworkConnectorsMeta object with the provided details.

    Args:
        customer_details (CustomerDetails): Details of the customer.
        stream_id (int): ID of the Graylog stream.
        index_id (int): ID of the Graylog index.
        session (Session): Database session.

    Returns:
        CustomerNetworkConnectorsMeta: The created CustomerNetworkConnectorsMeta object.
    """
    return CustomerNetworkConnectorsMeta(
        customer_code=customer_details.customer_code,
        network_connector_name="FORTINET",
        graylog_stream_id=stream_id,
        graylog_input_id=(await get_input_id_by_input_name(input_name=f'{customer_details.customer_name} - FORTINET LOGS AND EVENTS')),
        graylog_pipeline_id=((await get_pipeline_id(subscription="FORTINET"))[0]),
        grafana_org_id=(await get_customer_meta_attribute(session=session, customer_code=customer_details.customer_code, column_name='customer_meta_grafana_org_id')),
        graylog_index_id=index_id,
        grafana_dashboard_folder_id=None,
    )

async def provision_fortinet(customer_details: FortinetCustomerDetails, keys: ProvisionFortinetKeys, session: AsyncSession):
    """
    Provisions a Fortinet customer by performing the following steps:
    1. Provisions the content pack for the customer.
    2. Retrieves the stream and index IDs for the customer.
    3. Creates customer network connector metadata.
    4. Assigns the stream to the index.
    5. Retrieves the pipeline ID for the "FORTINET" subscription.
    6. Connects the stream to the pipeline.
    7. Inserts the customer network connector metadata into the database.

    Args:
        customer_details (FortinetCustomerDetails): The details of the Fortinet customer.
        keys (ProvisionFortinetKeys): The keys required for provisioning.
        session (AsyncSession): The database session.

    Returns:
        None
    """
    await provision_content_pack(customer_details)
    stream_id, index_id = await get_stream_and_index_ids(customer_details)
    customer_network_connector_meta = await create_customer_network_connector_meta(customer_details, stream_id, index_id, session)
    await assign_stream_to_index(stream_id=stream_id, index_id=index_id)
    pipeline_id = await get_pipeline_id(subscription="FORTINET")
    await connect_stream_to_pipeline(
        stream_and_pipeline=StreamConnectionToPipelineRequest(
            stream_id=stream_id, pipeline_ids=pipeline_id
        )
    )
    await insert_into_customer_network_connectors_meta_table(
        customer_network_connectors_meta=customer_network_connector_meta,
        session=session,
    )

async def insert_into_customer_network_connectors_meta_table(
    customer_network_connectors_meta: CustomerNetworkConnectorsMeta,
    session: AsyncSession,
) -> None:
    """
    Insert the customer network connectors meta into the database.

    Args:
        customer_network_connectors_meta (CustomerNetworkConnectorsMeta): The customer network connectors meta to insert.
        session (AsyncSession): The async session object for database operations.

    Returns:
        None
    """
    logger.info(f"Inserting customer network connectors meta into the database")
    session.add(customer_network_connectors_meta)
    await session.commit()
    logger.info(f"Customer network connectors meta inserted successfully")
    return None
