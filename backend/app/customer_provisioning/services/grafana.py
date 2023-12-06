from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.grafana.utils.universal import create_grafana_client
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.customer_provisioning.schema.grafana import GrafanaDatasource
from app.customer_provisioning.schema.grafana import GrafanaDataSourceCreationResponse
from app.customer_provisioning.schema.grafana import GrafanaFolderCreationResponse
from app.customer_provisioning.schema.grafana import GrafanaOrganizationCreation
from app.customer_provisioning.schema.grafana import NodesVersionResponse
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.utils import get_connector_attribute


async def create_grafana_organization(request: ProvisionNewCustomer) -> GrafanaOrganizationCreation:
    logger.info(f"Creating Grafana organization for customer {request.customer_name}")
    grafana_client = await create_grafana_client("Grafana")
    results = grafana_client.organization.create_organization(
        organization={
            "name": request.customer_grafana_org_name,
        },
    )
    return GrafanaOrganizationCreation(**results)


async def create_grafana_datasource(
    request: ProvisionNewCustomer,
    organization_id: int,
    session: AsyncSession,
) -> GrafanaDataSourceCreationResponse:
    logger.info(f"Creating Grafana datasource")
    grafana_client = await create_grafana_client("Grafana")
    # Switch to the newly created organization
    grafana_client.user.switch_actual_user_organisation(organization_id)
    datasource_payload = GrafanaDatasource(
        name="WAZUH",
        type="grafana-opensearch-datasource",
        typeName="OpenSearch",
        access="proxy",
        url=await get_connector_attribute(connector_id=1, column_name="connector_url", session=session),
        database=f"{request.customer_index_name}*",
        basicAuth=True,
        basicAuthUser=await get_connector_attribute(connector_id=1, column_name="connector_username", session=session),
        secureJsonData={
            "basicAuthPassword": await get_connector_attribute(connector_id=1, column_name="connector_password", session=session),
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
