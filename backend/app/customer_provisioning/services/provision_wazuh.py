import json
from datetime import datetime
from pathlib import Path

from loguru import logger
from fastapi import HTTPException
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.graylog.services.pipelines import get_pipelines
from app.connectors.graylog.services.management import start_stream
from app.connectors.wazuh_manager.utils.universal import send_post_request as send_wazuh_post_request
from app.connectors.wazuh_manager.utils.universal import send_put_request as send_wazuh_put_request
from app.customer_provisioning.schema.provision import GraylogIndexSetCreationResponse
from app.customer_provisioning.schema.provision import ProvisionNewCustomer, WazuhEventStream, StreamCreationResponse, CustomerSubsctipion, StreamConnectionToPipelineRequest, StreamConnectionToPipelineResponse, WazuhAgentsTemplatePaths, GrafanaOrganizationCreation, GrafanaDatasource, GrafanaDataSourceCreationResponse, GrafanaFolderCreationResponse, NodesVersionResponse
from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponse
from app.customer_provisioning.schema.provision import TimeBasedIndexSet
from app.connectors.grafana.utils.universal import create_grafana_client
from app.connectors.grafana.services.dashboards import provision_dashboards
from app.connectors.grafana.schema.dashboards import DashboardProvisionRequest
from app.connectors.grafana.schema.dashboards import Office365Dashboard
from app.connectors.grafana.schema.dashboards import WazuhDashboard
from sqlalchemy.ext.asyncio import AsyncSession
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.connectors.services import ConnectorServices
from app.utils import get_connector_attribute

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


# Function to get the template file path
def get_template_path(template_info: WazuhAgentsTemplatePaths) -> Path:
    folder_name, file_name = template_info.value
    current_file = Path(__file__)  # Path to the current file
    base_dir = current_file.parent.parent  # Move up two levels to the base directory
    return base_dir / folder_name / file_name

# Function to update Wazuh group configuration
async def configure_wazuh_group(group_code, template_path):
    logger.info(f"Configuring Wazuh group {group_code}")

    # Read the contents of the template file
    with open(template_path, 'r') as template_file:
        config_template = template_file.read()

    # Replace placeholder with the customer code
    group_config = config_template.replace("REPLACE", group_code.split('_')[-1])

    # Make the API request to update the group configuration
    return await send_wazuh_put_request(endpoint=f"groups/{group_code}/configuration", data=group_config, xml_data=True)

# Function to apply configurations for all groups
async def apply_group_configurations(request: ProvisionNewCustomer):
    logger.info(f"Applying configurations for Wazuh groups for customer {request.customer_name} with code {request.customer_code}")

    group_templates = {
        'Linux': WazuhAgentsTemplatePaths.LINUX_AGENT,
        'Windows': WazuhAgentsTemplatePaths.WINDOWS_AGENT,
        'Mac': WazuhAgentsTemplatePaths.MAC_AGENT
    }

    for group, template in group_templates.items():
        group_code = f"{group}_{request.customer_code}"
        template_path = get_template_path(template)
        try:
            await configure_wazuh_group(group_code, template_path)
        except Exception as e:
            logger.error(f"Error configuring group {group_code}: {e}")


######### ! Grafana PROVISIONING ! ############
async def create_grafana_organization(request: ProvisionNewCustomer) -> GrafanaOrganizationCreation:
    logger.info(f"Creating Grafana organization for customer {request.customer_name}")
    grafana_client = await create_grafana_client("Grafana")
    results = grafana_client.organization.create_organization(
        organization={
            "name": request.customer_grafana_org_name,
        }
    )
    return GrafanaOrganizationCreation(**results)

async def create_grafana_datasource(request: ProvisionNewCustomer, organization_id: int, session: AsyncSession) -> GrafanaDataSourceCreationResponse:
    logger.info(f"Creating Grafana datasource")
    grafana_client = await create_grafana_client("Grafana")
    # Switch to the newly created organization
    grafana_client.user.switch_actual_user_organisation(organization_id)
    datasource_payload = GrafanaDatasource(
        name="WAZUH TEST",
        type="grafana-opensearch-datasource",
        typeName="OpenSearch",
        access="proxy",
        url=await get_connector_attribute(connector_id=1, column_name="connector_url", session=session),
        database=f"{request.customer_index_name}*",
        basicAuth=True,
        basicAuthUser=await get_connector_attribute(connector_id=1, column_name="connector_username", session=session),
        secureJsonData={
            "basicAuthPassword": await get_connector_attribute(connector_id=1, column_name="connector_password", session=session)
        },
        isDefault=False,
        jsonData={
            "database": f"{request.customer_index_name}*",
            "flavor": "opensearch",
            "includeFrozen": False,
            "logLevelField": "syslog_level",
            "logMessageField": "rule_description",
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

async def create_grafana_folder(organization_id: int, folder_title: str) -> GrafanaFolderCreationResponse:
    logger.info(f"Creating Grafana folder")
    grafana_client = await create_grafana_client("Grafana")
    # Switch to the newly created organization
    grafana_client.user.switch_actual_user_organisation(organization_id)
    results = grafana_client.folder.create_folder(
        title=folder_title,
    )
    logger.info(f"Folder creation results: {results}")
    return GrafanaFolderCreationResponse(**results)


async def get_opensearch_version() -> str:
    logger.info("Getting OpenSearch version")
    opensearch_client = await create_wazuh_indexer_client("Wazuh-Indexer")

    # Retrieve version information
    version_response = opensearch_client.nodes.info(node_id="_local", filter_path=["nodes.*.version"])

    # Parse the response to get the first version found
    nodes_version_response = NodesVersionResponse(**version_response)
    for node_id, node_info in nodes_version_response.nodes.items():
        return node_info.version

    # If no version is found, raise an exception
    raise HTTPException(status_code=500, detail=f"Failed to retrieve OpenSearch version.")


# ! MAIN FUNCTION ! #
async def provision_wazuh_customer(request: ProvisionNewCustomer, session: AsyncSession):
    logger.info(f"Provisioning new customer {request}")
    # created_index_response = await create_index_set(request)
    # index_set_id = created_index_response.data.id
    # created_stream_response = await create_event_stream(request, index_set_id)
    # stream_id = created_stream_response.data.stream_id
    # logger.info(f"Created index set with ID: {index_set_id} and stream with ID: {stream_id}")
    # pipeline_ids = await get_pipeline_id(subscription="Wazuh")
    # logger.info(f"Pipeline ID: {pipeline_ids}")
    # stream_and_pipeline = StreamConnectionToPipelineRequest(stream_id=stream_id, pipeline_ids=pipeline_ids)
    # await connect_stream_to_pipeline(stream_and_pipeline)
    # if await start_stream(stream_id=stream_id) is False:
    #     raise HTTPException(status_code=500, detail=f"Failed to start stream {stream_id}")
    #await create_wazuh_groups(request)
    #await apply_group_configurations(request)
    logger.info(f"Creating Grafana organization for customer {request.dashboards_to_include.dashboards}")
    grafana_organization_id = (await create_grafana_organization(request)).orgId
    wazuh_datasource_uid = (await create_grafana_datasource(request=request, organization_id=grafana_organization_id, session=session)).datasource.uid
    grafana_edr_folder_id = (await create_grafana_folder(organization_id=grafana_organization_id, folder_title="EDR")).id
    await provision_dashboards(DashboardProvisionRequest(dashboards=request.dashboards_to_include.dashboards, organizationId=grafana_organization_id, folderId=grafana_edr_folder_id, datasourceUid=wazuh_datasource_uid))

    return {"message": "Provisioning new customer"}
