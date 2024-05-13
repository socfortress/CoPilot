import json
import os
from datetime import datetime

import aiofiles
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import and_
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.grafana.schema.dashboards import CrowdstrikeDashboard
from app.connectors.grafana.schema.dashboards import DashboardProvisionRequest
from app.connectors.grafana.services.dashboards import provision_dashboards
from app.connectors.grafana.utils.universal import create_grafana_client
from app.connectors.graylog.services.collector import (
    get_content_pack_id_by_content_pack_name,
)
from app.connectors.graylog.services.collector import get_input_id_by_input_name
from app.connectors.graylog.services.collector import get_stream_id_by_stream_name
from app.connectors.graylog.services.streams import assign_stream_to_index
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.wazuh_indexer.services.monitoring import (
    output_shard_number_to_be_set_based_on_nodes,
)
from app.customer_provisioning.schema.grafana import GrafanaDatasource
from app.customer_provisioning.schema.grafana import GrafanaDataSourceCreationResponse
from app.customer_provisioning.schema.graylog import GraylogIndexSetCreationResponse
from app.customer_provisioning.schema.graylog import StreamConnectionToPipelineRequest
from app.customer_provisioning.schema.graylog import TimeBasedIndexSet
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.customer_provisioning.services.grafana import create_grafana_folder
from app.customer_provisioning.services.grafana import get_opensearch_version
from app.customer_provisioning.services.graylog import connect_stream_to_pipeline
from app.customer_provisioning.services.graylog import get_pipeline_id
from app.customers.routes.customers import get_customer_meta
from app.integrations.crowdstrike.schema.provision import CrowdstrikeCustomerDetails
from app.integrations.crowdstrike.schema.provision import ProvisionCrowdstrikeAuthKeys
from app.integrations.crowdstrike.schema.provision import ProvisionCrowdstrikeResponse
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.network_connectors.models.network_connectors import (
    CustomerNetworkConnectorsMeta,
)
from app.stack_provisioning.graylog.schema.provision import ContentPackKeywords
from app.stack_provisioning.graylog.schema.provision import (
    ProvisionNetworkContentPackRequest,
)
from app.stack_provisioning.graylog.services.provision import (
    provision_content_pack_network_connector,
)
from app.utils import get_connector_attribute
from app.utils import get_customer_meta_attribute


#### ! GRAYLOG ! ####
async def build_index_set_config(request: CrowdstrikeCustomerDetails) -> TimeBasedIndexSet:
    """
    Build the configuration for a time-based index set.

    Args:
        request (CrowdstrikeCustomerDetails): The request object containing customer information.

    Returns:
        TimeBasedIndexSet: The configured time-based index set.
    """
    return TimeBasedIndexSet(
        title=f"{request.customer_name} - CROWDSTRIKE EVENTS",
        description=f"{request.customer_name} - CROWDSTRIKE EVENTS",
        index_prefix=f"crowdstrike-{request.customer_code}",
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
            content_pack_name="CROWDSTRIKE",
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
    stream_id = await get_stream_id_by_stream_name(stream_name=f"{customer_details.customer_name} - CROWDSTRIKE LOGS AND EVENTS")
    index_id = (await create_index_set(request=customer_details)).data.id
    content_pack_stream_id = await get_content_pack_id_by_content_pack_name(
        content_pack_name=f"{customer_details.customer_name}_CROWDSTRIKE_STREAM",
    )
    if customer_details.protocal_type == "TCP":
        content_pack_input_id = await get_content_pack_id_by_content_pack_name(
            content_pack_name=f"{customer_details.customer_name}_CROWDSTRIKE_INPUT_TCP",
        )
    elif customer_details.protocal_type == "UDP":
        content_pack_input_id = await get_content_pack_id_by_content_pack_name(
            content_pack_name=f"{customer_details.customer_name}_CROWDSTRIKE_INPUT_SYSLOG_UDP",
        )
    return stream_id, index_id, content_pack_stream_id, content_pack_input_id


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
        name="CROWDSTRIKE",
        type="grafana-opensearch-datasource",
        typeName="OpenSearch",
        access="proxy",
        url=await get_connector_attribute(
            connector_id=1,
            column_name="connector_url",
            session=session,
        ),
        database=f"crowdstrike-{customer_code}*",
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
            "database": f"crowdstrike-{customer_code}*",
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


async def create_customer_network_connector_meta(
    customer_details,
    stream_id,
    index_id,
    content_pack_stream_id,
    content_pack_input_id,
    session,
):
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
        network_connector_name="CROWDSTRIKE",
        graylog_stream_id=stream_id,
        graylog_input_id=(await get_input_id_by_input_name(input_name=f"{customer_details.customer_name} - CROWDSTRIKE LOGS AND EVENTS")),
        graylog_pipeline_id=((await get_pipeline_id(subscription="CROWDSTRIKE"))[0]),
        graylog_content_pack_input_id=content_pack_input_id,
        graylog_content_pack_stream_id=content_pack_stream_id,
        grafana_org_id=(
            await get_customer_meta_attribute(
                session=session,
                customer_code=customer_details.customer_code,
                column_name="customer_meta_grafana_org_id",
            )
        ),
        graylog_index_id=index_id,
        grafana_dashboard_folder_id=None,
        grafana_datasource_uid=None,
    )


async def validate_grafana_organization_id(customer_code, session):
    """
    Validate the Grafana organization ID for the customer.

    Args:
        customer_code (str): The customer code.
        session (Session): Database session.

    Returns:
        int: The Grafana organization ID.
    """
    return await get_customer_meta_attribute(session=session, customer_code=customer_code, column_name="customer_meta_grafana_org_id")


async def provision_crowdstrike(
    customer_details: CrowdstrikeCustomerDetails,
    keys: ProvisionCrowdstrikeAuthKeys,
    session: AsyncSession,
) -> ProvisionCrowdstrikeResponse:
    """
    Provisions a Crowdstrike customer by performing the following steps:
    1. Provisions the content pack for the customer.
    2. Retrieves the stream and index IDs for the customer.
    3. Creates customer network connector metadata.
    4. Assigns the stream to the index.
    5. Retrieves the pipeline ID for the "CROWDSTRIKE" subscription.
    6. Connects the stream to the pipeline.
    7. Inserts the customer network connector metadata into the database.
    8. Creates a directory for the customer to store the docker compose and falconhose cfg.

    Args:
        customer_details (CrowdstrikeCustomerDetails): The details of the Crowdstrike customer.
        keys (ProvisionCrowdstrikeKeys): The keys required for provisioning.
        session (AsyncSession): The database session.

    Returns:
        None
    """
    # If customer name contains a space, replace it with a _
    if " " in customer_details.customer_name:
        customer_details.customer_name = customer_details.customer_name.replace(" ", "_")
    if await validate_grafana_organization_id(customer_details.customer_code, session) is None:
        raise HTTPException(status_code=404, detail="Grafana organization ID not found. Please provision Grafana for the customer first.")
    await provision_content_pack(customer_details)
    stream_id, index_id, content_pack_stream_id, content_pack_input_id = await get_stream_and_index_ids(customer_details)
    customer_network_connector_meta = await create_customer_network_connector_meta(
        customer_details,
        stream_id,
        index_id,
        content_pack_stream_id,
        content_pack_input_id,
        session,
    )
    await assign_stream_to_index(stream_id=stream_id, index_id=index_id)
    pipeline_id = await get_pipeline_id(subscription="CROWDSTRIKE")
    await connect_stream_to_pipeline(stream_and_pipeline=StreamConnectionToPipelineRequest(stream_id=stream_id, pipeline_ids=pipeline_id))
    # Grafana Deployment
    customer_network_connector_meta.grafana_datasource_uid = (
        await create_grafana_datasource(
            customer_code=customer_details.customer_code,
            session=session,
        )
    ).datasource.uid
    grafana_folder = await create_grafana_folder(
        organization_id=(
            await get_customer_meta(
                customer_details.customer_code,
                session,
            )
        ).customer_meta.customer_meta_grafana_org_id,
        folder_title="CROWDSTRIKE",
    )
    await provision_dashboards(
        DashboardProvisionRequest(
            dashboards=[dashboard.name for dashboard in CrowdstrikeDashboard],
            organizationId=(
                await get_customer_meta(
                    customer_details.customer_code,
                    session,
                )
            ).customer_meta.customer_meta_grafana_org_id,
            folderId=grafana_folder.id,
            datasourceUid=customer_network_connector_meta.grafana_datasource_uid,
        ),
    )
    customer_network_connector_meta.grafana_dashboard_folder_id = grafana_folder.uid
    await insert_into_customer_network_connectors_meta_table(
        customer_network_connectors_meta=customer_network_connector_meta,
        session=session,
    )
    await create_customer_directory_if_needed(customer_name=customer_details.customer_name)
    file = await load_and_replace_docker_compose(customer_name=customer_details.customer_name)
    await save_uploaded_file(
        file=file,
        filename=f"{customer_details.customer_name}_docker-compose.yml",
        customer_name=customer_details.customer_name,
    )
    await load_and_replace_falconhose_cfg(customer_details=customer_details, keys=keys, session=session)

    await update_customer_integration_table(
        customer_code=customer_details.customer_code,
        session=session,
    )

    return ProvisionCrowdstrikeResponse(
        message="Crowdstrike customer provisioned successfully",
        success=True,
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
    logger.info("Inserting customer network connectors meta into the database")
    session.add(customer_network_connectors_meta)
    await session.commit()
    logger.info("Customer network connectors meta inserted successfully")
    return None


# ! Add the docker-compose.yml file to the `data` folder
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
UPLOAD_FOLDER = os.path.join(project_root, "data")


async def create_customer_directory_if_needed(customer_name: str):
    """
    Create a directory for the customer in the UPLOAD_FOLDER if it doesn't exist.

    Args:
        customer_name (str): The name of the customer.
    """
    # Create the path to the customer's directory
    # If customer name contains a space, replace it with a _
    if " " in customer_name:
        customer_name = customer_name.replace(" ", "_")
    customer_directory = os.path.join(UPLOAD_FOLDER, customer_name)
    # Check if the directory exists
    if not os.path.exists(customer_directory):
        # If it doesn't exist, create it
        os.makedirs(customer_directory)


async def load_and_replace_docker_compose(customer_name: str):
    """
    Load the docker-compose.yml file and replace the placeholder with the customer name.

    Args:
        customer_name (str): The name of the customer.

    Returns:
        str: The content of the docker-compose.yml file with the placeholder replaced.
    """
    # Get the current directory:
    current_directory = os.path.dirname(os.path.abspath(__file__))
    # Go up one level
    parent_directory = os.path.dirname(current_directory)
    # If customer name contains a space, replace it with a _
    if " " in customer_name:
        customer_name = customer_name.replace(" ", "_")
    # Open the docker-compose.yml file and read the content
    with open(os.path.join(parent_directory, "templates", "docker-compose.yml"), "r") as file:
        data = file.read()
    data = data.replace("CUSTOMER_NAME", customer_name)
    return data


async def save_uploaded_file(file, filename, customer_name):
    """
    Save the uploaded file to the server.

    Args:
        file: The file to save.
        filename: The name of the file.

    Returns:
        str: The path to the saved file.
    """
    # If customer name contains a space, replace it with a _
    if " " in customer_name:
        customer_name = customer_name.replace(" ", "_")
    customer_upload_folder = os.path.join(UPLOAD_FOLDER, customer_name)
    async with aiofiles.open(os.path.join(customer_upload_folder, filename), "wb") as f:
        await f.write(file.encode())
    return os.path.join(customer_upload_folder, filename)


async def load_and_replace_falconhose_cfg(
    customer_details: CrowdstrikeCustomerDetails,
    keys: ProvisionCrowdstrikeAuthKeys,
    session: AsyncSession,
):
    """
    Load the falconhose.cfg file and replace the placeholders with the customer details.

    Args:
        customer_details (CrowdstrikeCustomerDetails): The details of the customer.
        keys (ProvisionCrowdstrikeAuthKeys): The authentication keys for Crowdstrike.

    Returns:
        str: The content of the falconhose.cfg file with the placeholders replaced.
    """
    # Get the current directory:
    current_directory = os.path.dirname(os.path.abspath(__file__))
    # Go up one level
    parent_directory = os.path.dirname(current_directory)
    connector_url = str(await get_connector_attribute(connector_id=3, column_name="connector_url", session=session))
    connector_url = connector_url.replace("https://", "").replace("http://", "").replace(":9000", "")
    # Open the falconhose.cfg file and read the content
    with open(os.path.join(parent_directory, "templates", "cs.falconhoseclient.cfg"), "r") as file:
        data = file.read()
    data = data.replace("REPLACE_BASE_URL", keys.BASE_URL)
    data = data.replace("REPLACE_CLIENT_ID", keys.CLIENT_ID)
    data = data.replace("REPLACE_CLIENT_SECRET", keys.CLIENT_SECRET)
    data = data.replace("REPLACE_SYSLOG_HOST", connector_url)
    data = data.replace("REPLACE_SYSLOG_PORT", keys.SYSLOG_PORT)
    # Save the file
    # If customer name contains a space, replace it with a _
    if " " in customer_details.customer_name:
        customer_details.customer_name = customer_details.customer_name.replace(" ", "_")
    customer_upload_folder = os.path.join(UPLOAD_FOLDER, customer_details.customer_name)
    async with aiofiles.open(os.path.join(customer_upload_folder, "cs.falconhoseclient.cfg"), "w") as f:
        await f.write(data)
    return os.path.join(customer_upload_folder, "cs.falconhoseclient.cfg")


async def update_customer_integration_table(
    customer_code: str,
    session: AsyncSession,
) -> None:
    """
    Updates the `customer_integrations` table to set the `deployed` column to True where the `customer_code`
    matches the given customer code and the `integration_service_name` is "Crowdstrike".

    Args:
        customer_code (str): The customer code.
        session (AsyncSession): The async session object for making HTTP requests.
    """
    logger.info(f"Updating customer integrations table for customer {customer_code}")
    await session.execute(
        update(CustomerIntegrations)
        .where(
            and_(
                CustomerIntegrations.customer_code == customer_code,
                CustomerIntegrations.integration_service_name == "Crowdstrike",
            ),
        )
        .values(deployed=True),
    )
    await session.commit()

    return None
