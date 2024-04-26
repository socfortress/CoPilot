from sqlalchemy.ext.asyncio import AsyncSession

from app.stack_provisioning.graylog.schema.fortinet import FortinetCustomerDetails
from app.stack_provisioning.graylog.schema.fortinet import ProvisionFortinetKeys
from app.stack_provisioning.graylog.schema.provision import ContentPackKeywords
from app.stack_provisioning.graylog.schema.provision import (
    ProvisionNetworkContentPackRequest,
)
from app.stack_provisioning.graylog.services.provision import (
    provision_content_pack_network_connector,
)


async def provision_fortinet(customer_details: FortinetCustomerDetails, keys: ProvisionFortinetKeys, session: AsyncSession):
    await provision_content_pack_network_connector(
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
