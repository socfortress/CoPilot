import requests
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.customer_provisioning.schema.decommission import DecommissionCustomerResponse
from app.customer_provisioning.schema.wazuh_worker import DecommissionWorkerRequest
from app.customer_provisioning.schema.wazuh_worker import DecommissionWorkerResponse
from app.customer_provisioning.services.dfir_iris import delete_customer
from app.customer_provisioning.services.grafana import delete_grafana_organization
from app.customer_provisioning.services.graylog import delete_index_set
from app.customer_provisioning.services.graylog import delete_stream
from app.customer_provisioning.services.wazuh_manager import delete_wazuh_agents
from app.customer_provisioning.services.wazuh_manager import delete_wazuh_groups
from app.customer_provisioning.services.wazuh_manager import gather_wazuh_agents
from app.db.universal_models import CustomersMeta
from app.utils import get_connector_attribute


async def decomission_wazuh_customer(
    customer_meta: CustomersMeta,
    session: AsyncSession,
) -> DecommissionCustomerResponse:
    """
    Decommissions a Wazuh customer by performing the following steps:
    1. Deletes the Wazuh Agents associated with the customer.
    2. Deletes the Wazuh Group associated with the customer.
    3. Deletes the Graylog Stream associated with the customer.
    4. Deletes the Graylog Index Set associated with the customer.
    5. Deletes the Grafana Organization associated with the customer.
    6. Decommissions the Wazuh Worker associated with the customer.
    7. Deletes the Customer Meta from the session.

    Args:
        customer_meta (CustomersMeta): The metadata of the customer to be decommissioned.
        session (AsyncSession): The database session.

    Returns:
        DecommissionCustomerResponse: The response indicating the success of the decommissioning process and the deleted data.

    """
    logger.info(f"Decomissioning customer {customer_meta.customer_name}")

    # Delete DFIR-IRIS Customer
    await delete_customer(customer_id=customer_meta.customer_meta_iris_customer_id)

    # Delete the Wazuh Agents
    agents = await gather_wazuh_agents(customer_meta.customer_code)
    agents_deleted = await delete_wazuh_agents(agents)
    logger.info(
        f"Deleted {agents_deleted} agents for customer {customer_meta.customer_name}",
    )

    # Delete Wazuh Group
    groups_deleted = await delete_wazuh_groups(customer_meta.customer_code)

    # Delete Graylog Stream
    await delete_stream(customer_meta.customer_meta_graylog_stream)

    # Delete Graylog Index Set
    await delete_index_set(customer_meta.customer_meta_graylog_index)

    # Delete Grafana Organization
    await delete_grafana_organization(
        organization_id=int(customer_meta.customer_meta_grafana_org_id),
    )

    # Decommission Wazuh Worker
    await decommission_wazuh_worker(
        request=DecommissionWorkerRequest(customer_name=customer_meta.customer_name),
        session=session,
    )

    # Delete Customer Meta
    await session.delete(customer_meta)
    await session.commit()

    return DecommissionCustomerResponse(
        message=f"Customer {customer_meta.customer_name} decomissioned successfully.",
        success=True,
        decomissioned_data={
            "agents_deleted": agents_deleted,
            "groups_deleted": groups_deleted,
            "stream_deleted": customer_meta.customer_meta_graylog_stream,
            "index_deleted": customer_meta.customer_meta_graylog_index,
        },
    )


######### ! Decommission Wazuh Worker ! ############
async def decommission_wazuh_worker(
    request: DecommissionWorkerRequest,
    session: AsyncSession,
) -> DecommissionWorkerResponse:
    """
    Decomissions a Wazuh worker. https://github.com/socfortress/Customer-Provisioning-Worker

    Args:
        request (DecommissionWorkerRequest): The request object containing the necessary information for provisioning.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        ProvisionWorkerResponse: The response object indicating the success or failure of the provisioning operation.
    """
    logger.info(f"Decommissioning Wazuh worker {request}")
    api_endpoint = await get_connector_attribute(
        connector_id=13,
        column_name="connector_url",
        session=session,
    )
    # Send the POST request to the Wazuh worker
    response = requests.post(
        url=f"{api_endpoint}/provision_worker/decommission",
        json=request.dict(),
    )
    # Check the response status code
    if response.status_code != 200:
        return DecommissionWorkerResponse(
            success=False,
            message=f"Failed to provision Wazuh worker: {response.text}",
        )
    # Return the response
    return DecommissionWorkerResponse(
        success=True,
        message="Wazuh worker provisioned successfully",
    )
