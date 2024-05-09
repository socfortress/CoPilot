from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.customer_provisioning.services.grafana import delete_grafana_dashboard_folder
from app.customer_provisioning.services.grafana import delete_grafana_datasource
from app.customer_provisioning.services.graylog import delete_content_pack
from app.customer_provisioning.services.graylog import uninstall_content_pack
from app.network_connectors.models.network_connectors import (
    CustomerNetworkConnectorsMeta,
)
from app.stack_provisioning.graylog.schema.decommission import (
    DecommissionNetworkContentPackResponse,
)
from app.stack_provisioning.graylog.services.utils import set_deployed_flag


async def uninstall_and_delete_content_pack(content_pack_id: str):
    """
    Uninstalls and deletes a content pack.

    Args:
        content_pack_id (str): The ID of the content pack to be uninstalled and deleted.
    """
    await uninstall_content_pack(content_pack_id)
    await delete_content_pack(content_pack_id)


async def delete_grafana_resources(organization_id: str, folder_uid: str, datasource_uid: str):
    """
    Deletes Grafana resources.

    Args:
        organization_id (str): The ID of the Grafana organization.
        folder_uid (str): The UID of the Grafana Dashboard Folder.
        datasource_uid (str): The UID of the Grafana Datasource.
    """
    await delete_grafana_dashboard_folder(organization_id=organization_id, folder_uid=folder_uid)
    await delete_grafana_datasource(organization_id=organization_id, datasource_uid=datasource_uid)


async def decommission_network_connector(
    network_connector_meta: CustomerNetworkConnectorsMeta,
    session: AsyncSession,
) -> DecommissionNetworkContentPackResponse:
    """
    Decommissions the network connector by performing the following steps:
    1. Uninstalls and deletes the content pack associated with the network connector.
    2. Deletes the Grafana resources associated with the network connector.
    3. Deletes the network connector meta from the session.

    Args:
        network_connector_meta (CustomerNetworkConnectorsMeta): The metadata of the network connector to be decommissioned.
        session (AsyncSession): The database session.

    Returns:
        DecommissionNetworkContentPackResponse: The response of the decommission operation.
    """
    logger.info(f"Decommissioning network connector {network_connector_meta.network_connector_name}")

    # Uninstall and delete the content pack Input ID and Stream ID
    await uninstall_and_delete_content_pack(network_connector_meta.graylog_content_pack_input_id)
    await uninstall_and_delete_content_pack(network_connector_meta.graylog_content_pack_stream_id)

    # Delete the Grafana resources
    await delete_grafana_resources(
        organization_id=network_connector_meta.grafana_org_id,
        folder_uid=network_connector_meta.grafana_dashboard_folder_id,
        datasource_uid=network_connector_meta.grafana_datasource_uid,
    )

    # Delete the network connector meta from the session
    await session.delete(network_connector_meta)
    await session.commit()

    await set_deployed_flag(
        customer_code=network_connector_meta.customer_code,
        network_connector_service_name=network_connector_meta.network_connector_name,
        flag=False,
        session=session,
    )

    return DecommissionNetworkContentPackResponse(
        message=(
            f"Network connector {network_connector_meta.network_connector_name} has been "
            f"decommissioned. However, the indices still remain. If you want to remove the "
            f"index set, do so within Graylog."
        ),
        success=True,
    )
