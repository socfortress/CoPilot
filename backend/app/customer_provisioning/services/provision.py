from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.grafana.schema.dashboards import DashboardProvisionRequest
from app.connectors.grafana.services.dashboards import provision_dashboards

from app.connectors.graylog.services.management import start_stream

from app.customer_provisioning.services.graylog import (
    create_event_stream, create_index_set, get_pipeline_id, connect_stream_to_pipeline
)
from app.customer_provisioning.services.wazuh_manager import (
    apply_group_configurations, create_wazuh_groups
)
from app.customer_provisioning.services.grafana import (
    create_grafana_organization, create_grafana_datasource, create_grafana_folder
)
from app.customer_provisioning.schema.provision import CustomerProvisionMeta
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.customer_provisioning.schema.graylog import StreamConnectionToPipelineRequest
from app.customer_provisioning.schema.provision import CustomerProvisionResponse

from app.db.universal_models import CustomersMeta




# ! MAIN FUNCTION ! #
async def provision_wazuh_customer(request: ProvisionNewCustomer, session: AsyncSession) -> CustomerProvisionResponse:
    logger.info(f"Provisioning new customer {request}")
    # Initialize an empty dictionary to store the meta data
    provision_meta_data = {}
    provision_meta_data["index_set_id"] = (await create_index_set(request)).data.id
    provision_meta_data["stream_id"] = (await create_event_stream(request, provision_meta_data["index_set_id"])).data.stream_id
    provision_meta_data["pipeline_ids"] = await get_pipeline_id(subscription="Wazuh")
    stream_and_pipeline = StreamConnectionToPipelineRequest(
        stream_id=provision_meta_data["stream_id"],
        pipeline_ids=provision_meta_data["pipeline_ids"],
    )
    await connect_stream_to_pipeline(stream_and_pipeline)
    if await start_stream(stream_id=provision_meta_data["stream_id"]) is False:
        raise HTTPException(status_code=500, detail=f"Failed to start stream {provision_meta_data['stream_id']}")
    await create_wazuh_groups(request)
    await apply_group_configurations(request)
    provision_meta_data["grafana_organization_id"] = (await create_grafana_organization(request)).orgId
    provision_meta_data["wazuh_datasource_uid"] = (
        await create_grafana_datasource(request=request, organization_id=provision_meta_data["grafana_organization_id"], session=session)
    ).datasource.uid
    provision_meta_data["grafana_edr_folder_id"] = (
        await create_grafana_folder(organization_id=provision_meta_data["grafana_organization_id"], folder_title="EDR")
    ).id
    await provision_dashboards(
        DashboardProvisionRequest(
            dashboards=request.dashboards_to_include.dashboards,
            organizationId=provision_meta_data["grafana_organization_id"],
            folderId=provision_meta_data["grafana_edr_folder_id"],
            datasourceUid=provision_meta_data["wazuh_datasource_uid"],
        ),
    )

    customer_provision_meta = CustomerProvisionMeta(**provision_meta_data)
    customer_meta = await update_customer_meta_table(request, customer_provision_meta, session)

    return CustomerProvisionResponse(message=f"Customer {request.customer_name} provisioned successfully",
                                        success=True,
                                        customer_meta=customer_meta.dict())



######### ! Update CustomerMeta Table ! ############
async def update_customer_meta_table(request: ProvisionNewCustomer, customer_meta: CustomerProvisionMeta, session: AsyncSession):
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
        customer_meta_wazuh_auth_password=request.wazuh_auth_password,
    )
    session.add(customer_meta)
    await session.commit()
    return customer_meta
