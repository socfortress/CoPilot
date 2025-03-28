import requests
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.portainer.services.stack import delete_wazuh_customer_stack
from app.connectors.utils import is_connector_verified
from app.customer_provisioning.schema.decommission import DecommissionCustomerResponse
from app.customer_provisioning.schema.wazuh_worker import DecommissionWorkerRequest
from app.customer_provisioning.schema.wazuh_worker import DecommissionWorkerResponse
from app.customer_provisioning.services.grafana import delete_grafana_organization
from app.customer_provisioning.services.graylog import delete_index_set
from app.customer_provisioning.services.graylog import delete_stream
from app.customer_provisioning.services.portainer import list_node_ips
from app.customer_provisioning.services.wazuh_manager import delete_wazuh_agents
from app.customer_provisioning.services.wazuh_manager import delete_wazuh_groups
from app.customer_provisioning.services.wazuh_manager import gather_wazuh_agents
from app.db.universal_models import CustomersMeta
from app.utils import get_connector_attribute


async def get_customer_portainer_stack_id(
    customer_name: str,
    session: AsyncSession,
) -> int:
    """
    Get the customer's Portainer stack ID from the CustomersMeta table.

    Args:
        customer_name (str): The name of the customer
        session (AsyncSession): The database session

    Returns:
        int: The Portainer stack ID for the customer

    Raises:
        HTTPException: If the customer is not found or has no stack ID
    """
    logger.info(f"Getting Portainer stack ID for customer {customer_name}")

    # Find the customer record
    stmt = select(CustomersMeta).where(CustomersMeta.customer_name == customer_name)
    result = await session.execute(stmt)
    customer = result.scalar_one_or_none()

    if not customer:
        logger.error(f"Customer {customer_name} not found in database")
        raise HTTPException(status_code=404, detail=f"Customer {customer_name} not found in database")

    if not customer.customer_meta_portainer_stack_id:
        logger.error(f"No Portainer stack ID found for customer {customer_name}")
        raise HTTPException(status_code=404, detail=f"No Portainer stack ID found for customer {customer_name}")

    logger.info(f"Found Portainer stack ID {customer.customer_meta_portainer_stack_id} for customer {customer_name}")
    return customer.customer_meta_portainer_stack_id


async def clear_customer_portainer_stack_id(
    customer_name: str,
    session: AsyncSession,
) -> None:
    """
    Clear the customer's Portainer stack ID in the CustomersMeta table by setting it to None.

    Args:
        customer_name (str): The name of the customer
        session (AsyncSession): The database session

    Raises:
        HTTPException: If the customer is not found in the database
    """
    logger.info(f"Clearing Portainer stack ID for customer {customer_name}")

    # Find the customer record
    stmt = select(CustomersMeta).where(CustomersMeta.customer_name == customer_name)
    result = await session.execute(stmt)
    customer = result.scalar_one_or_none()

    if not customer:
        logger.error(f"Customer {customer_name} not found in database")
        raise HTTPException(status_code=404, detail=f"Customer {customer_name} not found in database")

    # Update the customer's Portainer stack ID to None
    stmt = update(CustomersMeta).where(CustomersMeta.customer_name == customer_name).values(customer_meta_portainer_stack_id=None)
    await session.execute(stmt)
    await session.commit()

    logger.info(f"Successfully cleared Portainer stack ID for customer {customer_name}")


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

    # Decommission HAProxy
    await decommission_haproxy(
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
    if await is_connector_verified(connector_name="Portainer", db=session) is False:
        # Check if the connector is verified
        if (
            await get_connector_attribute(
                connector_name="Wazuh Worker Provisioning",
                column_name="connector_verified",
                session=session,
            )
            is False
        ):
            logger.info("Wazuh Worker Provisioning connector is not verified, skipping ...")
            return DecommissionWorkerResponse(
                success=False,
                message="Wazuh Worker Provisioning connector is not verified",
            )
        api_endpoint = await get_connector_attribute(
            connector_name="Wazuh Worker Provisioning",
            column_name="connector_url",
            session=session,
        )
        # Send the POST request to the Wazuh worker
        request.portainer_deployment = False
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
    else:
        request.portainer_deployment = True
        # ! Delete the stack via Portainer first then clean up the file system on the worker node ! #
        # Delete the stack and get the response
        await delete_wazuh_customer_stack(stack_id=await get_customer_portainer_stack_id(request.customer_name, session))

        # Clear the stack ID from the database
        await clear_customer_portainer_stack_id(request.customer_name, session)

        swarm_node_ips = await list_node_ips()
        logger.info(f"Invoking the customer provisioning application on the swarm node IPs: {swarm_node_ips}")
        for ip in swarm_node_ips:
            logger.info(f"Provisioning Wazuh worker on IP: {ip}")
            response = requests.post(
                url=f"http://{ip}:5003/provision_worker/decommission",
                json=request.dict(),
            )
            logger.info(f"Status code from Wazuh Worker: {response.status_code}")
            if response.status_code != 200:
                return DecommissionWorkerResponse(
                    success=False,
                    message=f"Failed to provision Wazuh worker: {response.text}",
                )

        return DecommissionWorkerResponse(
            success=True,
            message="Wazuh worker decommissioned successfully",
        )


######### ! Decommission HAProxy ! ############
async def decommission_haproxy(
    request: DecommissionWorkerRequest,
    session: AsyncSession,
) -> DecommissionWorkerResponse:
    """
    Decomissions a HAProxy worker.

    Args:
        request (DecommissionWorkerRequest): The request object containing the necessary information for provisioning.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        ProvisionWorkerResponse: The response object indicating the success or failure of the provisioning operation.
    """
    logger.info(f"Decommissioning HAProxy worker {request}")
    # Check if the connector is verified
    if (
        await get_connector_attribute(
            connector_name="HAProxy Provisioning",
            column_name="connector_verified",
            session=session,
        )
        is False
    ):
        logger.info("HAProxy Provisioning connector is not verified, skipping ...")
        return DecommissionWorkerResponse(
            success=False,
            message="HAProxy Provisioning connector is not verified",
        )
    api_endpoint = await get_connector_attribute(
        connector_name="HAProxy Provisioning",
        column_name="connector_url",
        session=session,
    )
    # Send the POST request to the HAProxy worker
    response = requests.post(
        url=f"{api_endpoint}/provision_worker/haproxy/decommission",
        json=request.dict(),
    )
    # Check the response status code
    if response.status_code != 200:
        return DecommissionWorkerResponse(
            success=False,
            message=f"Failed to provision HAProxy worker: {response.text}",
        )
    # Return the response
    return DecommissionWorkerResponse(
        success=True,
        message="HAProxy worker provisioned successfully",
    )
