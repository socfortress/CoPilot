from typing import Callable

import requests
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.agents.routes.agents import check_wazuh_manager_version
from app.agents.routes.agents import get_wazuh_manager_version
from app.connectors.grafana.schema.dashboards import DashboardProvisionRequest
from app.connectors.grafana.services.dashboards import provision_dashboards
from app.connectors.grafana.utils.universal import verify_grafana_connection
from app.connectors.graylog.services.management import start_stream
from app.connectors.graylog.utils.universal import verify_graylog_connection
from app.connectors.portainer.services.stack import create_wazuh_customer_stack
from app.connectors.utils import is_connector_verified
from app.connectors.wazuh_manager.utils.universal import verify_wazuh_manager_connection
from app.customer_provisioning.schema.graylog import StreamConnectionToPipelineRequest
from app.customer_provisioning.schema.provision import CustomerProvisionMeta
from app.customer_provisioning.schema.provision import CustomerProvisionResponse
from app.customer_provisioning.schema.provision import ProvisionHaProxyRequest
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.customer_provisioning.schema.wazuh_worker import ProvisionWorkerRequest
from app.customer_provisioning.schema.wazuh_worker import ProvisionWorkerResponse
from app.customer_provisioning.services.grafana import create_grafana_datasource
from app.customer_provisioning.services.grafana import create_grafana_folder
from app.customer_provisioning.services.grafana import create_grafana_organization
from app.customer_provisioning.services.grafana import create_vulnerability_datasource
from app.customer_provisioning.services.graylog import connect_stream_to_pipeline
from app.customer_provisioning.services.graylog import create_event_stream
from app.customer_provisioning.services.graylog import create_index_set
from app.customer_provisioning.services.graylog import get_pipeline_id
from app.customer_provisioning.services.portainer import list_node_ips
from app.customer_provisioning.services.wazuh_manager import apply_group_configurations
from app.customer_provisioning.services.wazuh_manager import create_wazuh_groups
from app.db.universal_models import CustomersMeta
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)
from app.utils import get_connector_attribute


async def verify_connection(service_name: str, verify_connection_func: Callable) -> None:
    connection = await verify_connection_func(service_name)
    if connection["connectionSuccessful"] is False:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to {service_name}. {service_name} connection must be established to proceed.",
        )


async def verify_required_tools() -> None:
    """
    Verify the required tools for customer provisioning.
    """
    logger.info("Verifying required tools")
    await verify_connection("Graylog", verify_graylog_connection)
    await verify_connection("Wazuh-Manager", verify_wazuh_manager_connection)
    await verify_connection("Grafana", verify_grafana_connection)


# ! MAIN FUNCTION ! #
async def provision_wazuh_customer(
    request: ProvisionNewCustomer,
    session: AsyncSession,
) -> CustomerProvisionResponse:
    """
    This function is the main function for provisioning a new customer for their Wazuh instance.
    It will call all the other functions to provision the customer.

    Args:
        request (ProvisionNewCustomer): The request body from the API endpoint
        session (AsyncSession): The database session

    Raises:
        HTTPException: If the stream fails to start

    Returns:
        CustomerProvisionResponse: The response object containing the provisioned customer's information
    """
    await verify_required_tools()
    logger.info(f"Provisioning new customer {request}")
    # Initialize an empty dictionary to store the meta data
    provision_meta_data = {}
    provision_meta_data["pipeline_ids"] = await get_pipeline_id(subscription="Wazuh")
    provision_meta_data["index_set_id"] = (await create_index_set(request)).data.id
    provision_meta_data["stream_id"] = (await create_event_stream(request, provision_meta_data["index_set_id"])).data.stream_id
    stream_and_pipeline = StreamConnectionToPipelineRequest(
        stream_id=provision_meta_data["stream_id"],
        pipeline_ids=provision_meta_data["pipeline_ids"],
    )
    await connect_stream_to_pipeline(stream_and_pipeline)
    if await start_stream(stream_id=provision_meta_data["stream_id"]) is False:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start stream {provision_meta_data['stream_id']}",
        )
    await create_wazuh_groups(request)
    await apply_group_configurations(request)
    provision_meta_data["grafana_organization_id"] = (await create_grafana_organization(request)).orgId
    provision_meta_data["wazuh_datasource_uid"] = (
        await create_grafana_datasource(
            request=request,
            organization_id=provision_meta_data["grafana_organization_id"],
            session=session,
        )
    ).datasource.uid
    # ! CREATE THE VULNERABILITY DATASOURCE IF WAZUH VERSION 4.8.0 OR HIGHER ! #
    if await check_wazuh_manager_version() is True:
        logger.info("Creating vulnerability datasource since Wazuh version is 4.8.0 or higher")
        await create_vulnerability_datasource(
            request=request,
            organization_id=provision_meta_data["grafana_organization_id"],
            session=session,
        )
    logger.info("Creating EDR folder and dashboards")
    provision_meta_data["grafana_edr_folder_id"] = (
        await create_grafana_folder(
            organization_id=provision_meta_data["grafana_organization_id"],
            folder_title="EDR",
        )
    ).id
    await provision_dashboards(
        DashboardProvisionRequest(
            dashboards=request.dashboards_to_include.dashboards,
            organizationId=provision_meta_data["grafana_organization_id"],
            folderId=provision_meta_data["grafana_edr_folder_id"],
            datasourceUid=provision_meta_data["wazuh_datasource_uid"],
            grafana_url=request.grafana_url,
        ),
    )

    customer_provision_meta = CustomerProvisionMeta(**provision_meta_data)
    customer_meta = await update_customer_meta_table(
        request,
        customer_provision_meta,
        session,
    )
    await update_customer_alert_settings_table(
        request,
        customer_provision_meta,
        session,
    )

    if request.provision_wazuh_worker is True:
        provision_worker = await provision_wazuh_worker(
            ProvisionWorkerRequest(
                customer_name=request.customer_name,
                wazuh_auth_password=request.wazuh_auth_password,
                wazuh_registration_port=request.wazuh_registration_port,
                wazuh_logs_port=request.wazuh_logs_port,
                wazuh_api_port=request.wazuh_api_port,
                wazuh_cluster_name=request.wazuh_cluster_name,
                wazuh_cluster_key=request.wazuh_cluster_key,
                wazuh_master_ip=request.wazuh_master_ip,
            ),
            session,
        )

        if provision_worker.success is False:
            return CustomerProvisionResponse(
                message=f"Customer {request.customer_name} provisioned successfully, but the Wazuh worker failed to provision",
                success=True,
                customer_meta=customer_meta.dict(),
                wazuh_worker_provisioned=False,
            )

    if request.provision_ha_proxy is True:
        provsion_haproxy = await provision_haproxy(
            ProvisionHaProxyRequest(
                customer_name=request.customer_name,
                wazuh_registration_port=request.wazuh_registration_port,
                wazuh_logs_port=request.wazuh_logs_port,
                wazuh_worker_hostname=request.wazuh_worker_hostname,
            ),
            session,
        )

        if provsion_haproxy.success is False:
            return CustomerProvisionResponse(
                message=f"Customer {request.customer_name} provisioned successfully, but the HAProxy failed to provision",
                success=True,
                customer_meta=customer_meta.dict(),
                wazuh_worker_provisioned=True,
            )

    return CustomerProvisionResponse(
        message=f"Customer {request.customer_name} provisioned successfully",
        success=True,
        customer_meta=customer_meta.dict(),
        wazuh_worker_provisioned=True,
    )


######### ! Update CustomerMeta Table ! ############
async def update_customer_meta_table(
    request: ProvisionNewCustomer,
    customer_meta: CustomerProvisionMeta,
    session: AsyncSession,
):
    """
    Update the customer meta table with the provided information.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.
        customer_meta (CustomerProvisionMeta): The customer meta object containing additional information.
        session (AsyncSession): The database session.

    Returns:
        CustomerProvisionMeta: The updated customer meta object.
    """
    logger.info(f"Updating customer meta table for customer {request.customer_name}")
    customer_meta = CustomersMeta(
        customer_code=request.customer_code,
        customer_name=request.customer_name,
        customer_meta_graylog_index=customer_meta.index_set_id,
        customer_meta_graylog_stream=customer_meta.stream_id,
        customer_meta_grafana_org_id=customer_meta.grafana_organization_id,
        customer_meta_wazuh_group=request.customer_code,
        customer_meta_index_retention=str(request.hot_data_retention),
        customer_meta_wazuh_registration_port=request.wazuh_registration_port,
        customer_meta_wazuh_log_ingestion_port=request.wazuh_logs_port,
        customer_meta_wazuh_api_port=request.wazuh_api_port,
        customer_meta_wazuh_auth_password=request.wazuh_auth_password,
        customer_meta_iris_customer_id=customer_meta.iris_customer_id,
    )
    session.add(customer_meta)
    await session.commit()
    return customer_meta


async def update_customer_portainer_stack_id(
    customer_name: str,
    stack_id: int,
    session: AsyncSession,
) -> None:
    """
    Update the customer's Portainer stack ID in the CustomersMeta table.

    Args:
        customer_name (str): The name of the customer
        stack_id (int): The Portainer stack ID
        session (AsyncSession): The database session
    """
    logger.info(f"Updating Portainer stack ID {stack_id} for customer {customer_name}")

    # Find the customer record
    stmt = select(CustomersMeta).where(CustomersMeta.customer_name == customer_name)
    result = await session.execute(stmt)
    customer = result.scalar_one_or_none()

    if customer:
        # Update the customer's Portainer stack ID
        stmt = update(CustomersMeta).where(CustomersMeta.customer_name == customer_name).values(customer_meta_portainer_stack_id=stack_id)
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Successfully updated Portainer stack ID for customer {customer_name}")
    else:
        logger.error(f"Customer {customer_name} not found in database")
        raise HTTPException(status_code=404, detail=f"Customer {customer_name} not found in database")


######### ! Update Customer Alert Settings Table ! ############
async def update_customer_alert_settings_table(
    request: ProvisionNewCustomer,
    customer_meta: CustomerProvisionMeta,
    session: AsyncSession,
):
    """
    Update the customer alert settings table with the provided information.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.
        customer_meta (CustomerProvisionMeta): The customer meta object containing additional information.
        session (AsyncSession): The database session.

    Returns:
        AlertCreationSettings: The updated customer meta object.
    """
    logger.info(
        f"Updating customer alert settings table for customer {request.customer_name}",
    )
    customer_alert_settings = AlertCreationSettings(
        customer_code=request.customer_code,
        customer_name=request.customer_name,
        timefield="timestamp_utc",
        iris_customer_id=customer_meta.iris_customer_id,
        iris_customer_name=request.customer_name,
        iris_index=f'dfir_iris_{request.customer_name.lower().replace(" ", "_")}',
        grafana_url=request.grafana_url,
        custom_message="Open In SOCFortress",
        nvd_url="https://services.nvd.nist.gov/rest/json/cves/2.0?cveId",
    )
    session.add(customer_alert_settings)
    await session.commit()
    return customer_alert_settings


######### ! Provision Wazuh Worker ! ############
async def provision_wazuh_worker(
    request: ProvisionWorkerRequest,
    session: AsyncSession,
) -> ProvisionWorkerResponse:
    """
    Provisions a Wazuh worker. https://github.com/socfortress/Customer-Provisioning-Worker
    This can be done either by directly invoking the worker or by invoking the worker via Portainer.

    Args:
        request (ProvisionWorkerRequest): The request object containing the necessary information for provisioning.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        ProvisionWorkerResponse: The response object indicating the success or failure of the provisioning operation.
    """
    logger.info(f"Provisioning Wazuh worker {request}")
    if await is_connector_verified(connector_name="Portainer", db=session) is False:
        api_endpoint = await get_connector_attribute(
            connector_name="Wazuh Worker Provisioning",
            column_name="connector_url",
            session=session,
        )
        logger.info(f"Wazuh Worker API endpoint: {api_endpoint}")
        # Send the POST request to the Wazuh worker
        request.portainer_deployment = False
        request.wazuh_manager_version = await get_wazuh_manager_version()
        response = requests.post(
            url=f"{api_endpoint}/provision_worker",
            json=request.dict(),
        )
        logger.info(f"Status code from Wazuh Worker: {response.status_code}")
        # Check the response status code
        if response.status_code != 200:
            return ProvisionWorkerResponse(
                success=False,
                message=f"Failed to provision Wazuh worker: {response.text}",
            )
        # Return the response
        return ProvisionWorkerResponse(
            success=True,
            message="Wazuh worker provisioned successfully",
        )
    else:
        request.portainer_deployment = True
        swarm_node_ips = await list_node_ips()
        logger.info(f"Invoking the customer provisioning application on the swarm node IPs: {swarm_node_ips}")
        # Loop through each node IP and set the node_id based on position
        for index, ip in enumerate(swarm_node_ips, start=1):
            # Set the node_id to the current position in the list (1, 2, 3, etc.)
            request.node_id = str(index)
            logger.info(f"Provisioning Wazuh worker on IP: {ip} with node_id: {request.node_id}")

            response = requests.post(
                url=f"http://{ip}:5003/provision_worker",
                json=request.dict(),
            )
            logger.info(f"Status code from Wazuh Worker: {response.status_code}")
            if response.status_code != 200:
                return ProvisionWorkerResponse(
                    success=False,
                    message=f"Failed to provision Wazuh worker: {response.text}",
                )

        # Create the stack and get the response
        stack_response = await create_wazuh_customer_stack(request)

        # Update the customer's Portainer stack ID
        await update_customer_portainer_stack_id(customer_name=request.customer_name, stack_id=stack_response.data.Id, session=session)

        return ProvisionWorkerResponse(
            success=True,
            message="Wazuh worker provisioned successfully via Portainer",
        )


######### ! Provision HAProxy ! ############
async def provision_haproxy(
    request: ProvisionWorkerRequest,
    session: AsyncSession,
) -> ProvisionWorkerResponse:
    """
    Provisions a HAProxy.

    Args:
        request (ProvisionWorkerRequest): The request object containing the necessary information for provisioning.
        session (AsyncSession): The async session object for making HTTP requests.

    Returns:
        ProvisionWorkerResponse: The response object indicating the success or failure of the provisioning operation.
    """
    logger.info(f"Provisioning HAProxy {request}")
    if await is_connector_verified(connector_name="Portainer", db=session) is False:
        api_endpoint = await get_connector_attribute(
            connector_name="HAProxy Provisioning",
            column_name="connector_url",
            session=session,
        )
        logger.info(f"HAProxy API endpoint: {api_endpoint}")
        request.portainer_deployment = False
        # Send the POST request to the Wazuh worker
        response = requests.post(
            url=f"{api_endpoint}/provision_worker/haproxy",
            json=request.dict(),
        )
        # Check the response status code
        if response.status_code != 200:
            return ProvisionWorkerResponse(
                success=False,
                message=f"Failed to provision HAProxy: {response.text}",
            )
        # Return the response
        return ProvisionWorkerResponse(
            success=True,
            message="HAProxy provisioned successfully",
        )
    else:
        request.portainer_deployment = True
        request.swarm_nodes = await list_node_ips()
        api_endpoint = await get_connector_attribute(
            connector_name="HAProxy Provisioning",
            column_name="connector_url",
            session=session,
        )
        logger.info(f"HAProxy API endpoint: {api_endpoint}")
        logger.info(f"Invoking the customer provisioning application on the swarm node IPs: {request.swarm_nodes}")
        response = requests.post(
            url=f"{api_endpoint}/provision_worker/haproxy",
            json=request.dict(),
        )
        # Check the response status code
        if response.status_code != 200:
            return ProvisionWorkerResponse(
                success=False,
                message=f"Failed to provision HAProxy: {response.text}",
            )
        # Return the response
        return ProvisionWorkerResponse(
            success=True,
            message="HAProxy provisioned successfully via Portainer",
        )
