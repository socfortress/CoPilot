import json
from datetime import datetime

from loguru import logger
from sqlalchemy import and_
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.grafana.schema.dashboards import DashboardProvisionRequest
from app.connectors.grafana.schema.dashboards import DuoDashboard
from app.connectors.grafana.services.dashboards import provision_dashboards
from app.connectors.grafana.utils.universal import create_grafana_client
from app.connectors.graylog.services.management import start_stream
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.wazuh_indexer.services.monitoring import (
    output_shard_number_to_be_set_based_on_nodes,
)
from app.customer_provisioning.schema.grafana import GrafanaDatasource
from app.customer_provisioning.schema.grafana import GrafanaDataSourceCreationResponse
from app.customer_provisioning.schema.graylog import GraylogIndexSetCreationResponse
from app.customer_provisioning.schema.graylog import StreamCreationResponse
from app.customer_provisioning.schema.graylog import TimeBasedIndexSet
from app.customer_provisioning.services.grafana import create_grafana_folder
from app.customer_provisioning.services.grafana import get_opensearch_version
from app.customers.routes.customers import get_customer
from app.customers.routes.customers import get_customer_meta
from app.integrations.duo.schema.provision import DuoEventStream
from app.integrations.duo.schema.provision import ProvisionDuoRequest
from app.integrations.duo.schema.provision import ProvisionDuoResponse
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.routes import create_integration_meta
from app.integrations.schema import CustomerIntegrationsMetaSchema
from app.utils import get_connector_attribute


################## ! GRAYLOG ! ##################
async def build_index_set_config(
    customer_code: str,
    session: AsyncSession,
) -> TimeBasedIndexSet:
    """
    Build the configuration for a time-based index set.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.

    Returns:
        TimeBasedIndexSet: The configured time-based index set.
    """
    return TimeBasedIndexSet(
        title=f"{(await get_customer(customer_code, session)).customer.customer_name} - DUO",
        description=f"{customer_code} - DUO",
        index_prefix=f"duo-{customer_code.lower()}-",
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
            "max_number_of_indices": 30,
        },
        creation_date=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        index_analyzer="standard",
        shards=await output_shard_number_to_be_set_based_on_nodes(),
        replicas=0,
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


async def create_index_set(
    customer_code: str,
    session: AsyncSession,
) -> GraylogIndexSetCreationResponse:
    """
    Creates an index set for a new customer.

    Args:
        request (ProvisionNewCustomer): The request object containing the customer information.

    Returns:
        GraylogIndexSetCreationResponse: The response object containing the result of the index set creation.
    """
    logger.info(f"Creating index set for customer {customer_code}")
    index_set_config = await build_index_set_config(customer_code, session)
    return await send_index_set_creation_request(index_set_config)


# ! Event STREAMS ! #
# Function to create event stream configuration
async def build_event_stream_config(
    customer_code: str,
    index_set_id: str,
    session: AsyncSession,
) -> DuoEventStream:
    """
    Builds the configuration for the Duo event stream.

    Args:
        customer_code (str): The customer code.
        index_set_id (str): The index set ID.
        session (AsyncSession): The async session.

    Returns:
        DuoEventStream: The configured Duo event stream.
    """
    return DuoEventStream(
        title=f"{(await get_customer(customer_code, session)).customer.customer_name} - DUO",
        description=f"{(await get_customer(customer_code, session)).customer.customer_name} - DUO",
        index_set_id=index_set_id,
        rules=[
            {
                "field": "integration",
                "type": 1,
                "inverted": False,
                "value": "duo",
            },
            {
                "field": "customer_code",
                "type": 1,
                "inverted": False,
                "value": f"{customer_code}",
            },
        ],
        matching_type="AND",
        remove_matches_from_default_stream=True,
        content_pack=None,
    )


async def send_event_stream_creation_request(
    event_stream: DuoEventStream,
) -> StreamCreationResponse:
    """
    Sends a request to create an event stream.

    Args:
        event_stream (SapSiemEventStream): The event stream to be created.

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


async def create_event_stream(
    customer_code: str,
    index_set_id: str,
    session: AsyncSession,
) -> StreamCreationResponse:
    """
    Creates an event stream for a customer.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.
        index_set_id (str): The ID of the index set.

    Returns:
        The result of the event stream creation request.
    """
    event_stream_config = await build_event_stream_config(
        customer_code,
        index_set_id,
        session,
    )
    return await send_event_stream_creation_request(event_stream_config)


#### ! GRAFANA ! ####
async def create_grafana_datasource(
    customer_code: str,
    session: AsyncSession,
) -> GrafanaDataSourceCreationResponse:
    """
    Creates a Grafana datasource for the specified customer.

    Args:
        customer_code (str): The customer code.
        session (AsyncSession): The async session.

    Returns:
        GrafanaDataSourceCreationResponse: The response containing the created datasource details.
    """
    logger.info("Creating Grafana datasource")
    grafana_client = await create_grafana_client("Grafana")
    # Switch to the newly created organization
    grafana_client.user.switch_actual_user_organisation(
        (await get_customer_meta(customer_code, session)).customer_meta.customer_meta_grafana_org_id,
    )
    datasource_payload = GrafanaDatasource(
        name="DUO",
        type="grafana-opensearch-datasource",
        typeName="OpenSearch",
        access="proxy",
        url=await get_connector_attribute(
            connector_id=1,
            column_name="connector_url",
            session=session,
        ),
        database=f"duo-{customer_code}*",
        basicAuth=True,
        basicAuthUser=await get_connector_attribute(
            connector_id=1,
            column_name="connector_username",
            session=session,
        ),
        secureJsonData={
            "basicAuthPassword": await get_connector_attribute(
                connector_id=1,
                column_name="connector_password",
                session=session,
            ),
        },
        isDefault=False,
        jsonData={
            "database": f"duo-{customer_code}*",
            "flavor": "opensearch",
            "includeFrozen": False,
            "logLevelField": "severity",
            "logMessageField": "summary",
            "maxConcurrentShardRequests": 5,
            "pplEnabled": True,
            "timeField": "timestamp",
            "tlsSkipVerify": True,
            "version": await get_opensearch_version(),
        },
        readOnly=True,
    )
    results = grafana_client.datasource.create_datasource(
        datasource=datasource_payload.dict(),
    )
    return GrafanaDataSourceCreationResponse(**results)


async def provision_duo(
    provision_duo_request: ProvisionDuoRequest,
    session: AsyncSession,
) -> ProvisionDuoResponse:
    logger.info(
        f"Provisioning Duo integration for customer {provision_duo_request.customer_code}.",
    )

    # Create Index Set
    index_set_id = (
        await create_index_set(
            customer_code=provision_duo_request.customer_code,
            session=session,
        )
    ).data.id
    logger.info(f"Index set: {index_set_id}")
    # Create event stream
    stream_id = (
        await create_event_stream(
            provision_duo_request.customer_code,
            index_set_id,
            session,
        )
    ).data.stream_id
    # Start stream
    await start_stream(stream_id=stream_id)

    # Grafana Deployment
    duo_datasource_uid = (
        await create_grafana_datasource(
            customer_code=provision_duo_request.customer_code,
            session=session,
        )
    ).datasource.uid
    grafana_duo_folder_id = (
        await create_grafana_folder(
            organization_id=(
                await get_customer_meta(
                    provision_duo_request.customer_code,
                    session,
                )
            ).customer_meta.customer_meta_grafana_org_id,
            folder_title="DUO",
        )
    ).id
    await provision_dashboards(
        DashboardProvisionRequest(
            dashboards=[dashboard.name for dashboard in DuoDashboard],
            organizationId=(
                await get_customer_meta(
                    provision_duo_request.customer_code,
                    session,
                )
            ).customer_meta.customer_meta_grafana_org_id,
            folderId=grafana_duo_folder_id,
            datasourceUid=duo_datasource_uid,
        ),
    )
    await create_integration_meta_entry(
        CustomerIntegrationsMetaSchema(
            customer_code=provision_duo_request.customer_code,
            integration_name="Duo",
            graylog_input_id=None,
            graylog_index_id=index_set_id,
            graylog_stream_id=stream_id,
            grafana_org_id=(
                await get_customer_meta(
                    provision_duo_request.customer_code,
                    session,
                )
            ).customer_meta.customer_meta_grafana_org_id,
            grafana_dashboard_folder_id=grafana_duo_folder_id,
        ),
        session,
    )
    await update_customer_integration_table(
        provision_duo_request.customer_code,
        session,
    )

    return ProvisionDuoResponse(
        success=True,
        message="Duo integration provisioned successfully.",
    )


############## ! WRITE TO DB ! ##############
async def create_integration_meta_entry(
    customer_integration_meta: CustomerIntegrationsMetaSchema,
    session: AsyncSession,
) -> None:
    """
    Creates an entry for the customer integration meta in the database.

    Args:
        customer_integration_meta (CustomerIntegrationsMetaSchema): The customer integration meta object.
        session (AsyncSession): The async session object for database operations.
    """
    await create_integration_meta(customer_integration_meta, session)
    logger.info(
        f"Integration meta entry created for customer {customer_integration_meta.customer_code}.",
    )


async def update_customer_integration_table(
    customer_code: str,
    session: AsyncSession,
) -> None:
    """
    Updates the `customer_integrations` table to set the `deployed` column to True where the `customer_code`
    matches the given customer code and the `integration_service_name` is "Duo".

    Args:
        customer_code (str): The customer code.
        session (AsyncSession): The async session object for making HTTP requests.
    """
    await session.execute(
        update(CustomerIntegrations)
        .where(
            and_(
                CustomerIntegrations.customer_code == customer_code,
                CustomerIntegrations.integration_service_name == "Duo",
            ),
        )
        .values(deployed=True),
    )
    await session.commit()

    return None
