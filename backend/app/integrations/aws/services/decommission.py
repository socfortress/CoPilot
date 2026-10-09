"""Removing one AWS instance from the Wazuh manager, Graylog and Grafana.

Called from the generic `delete_integration` route. That route's own infrastructure cleanup assumes
one index set, one stream and one datasource per instance; an AWS instance records one of each *per
service* (as `service:id` pairs, see `app/integrations/aws/utils/services.py`), so AWS takes this
path instead.
"""

from typing import Dict
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.grafana.services.folders import delete_folder
from app.connectors.graylog.services.management import delete_index_by_id
from app.connectors.graylog.services.streams import delete_stream
from app.customer_provisioning.services.grafana import delete_grafana_datasource
from app.integrations.aws.schema.provision import AWS_INTEGRATION_NAME
from app.integrations.aws.services.wazuh_manager import apply_instance_buckets
from app.integrations.aws.utils.services import decode_service_ids
from app.integrations.models.customer_integration_settings import (
    CustomerIntegrationsMeta,
)


async def remove_service_resources(
    services: List[str],
    stream_ids: Dict[str, str],
    index_ids: Dict[str, str],
    datasource_uids: Dict[str, str],
    grafana_org_id: Optional[str],
    keep_shared: set,
) -> List[str]:
    """
    Remove an instance's Graylog and Grafana resources for the given services.

    The stream always goes; the index set and datasource only when no other instance of the customer
    still collects that service (``keep_shared``). Each removal is attempted independently and a
    failure becomes a warning, never an exception: the caller has already committed to the removal.
    """
    warnings: List[str] = []

    async def attempt(description: str, coroutine_factory) -> None:
        try:
            await coroutine_factory()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to delete {description}: {e}")
            warnings.append(f"Could not delete {description}: {e}. Remove it manually if it still exists.")

    for service in services:
        if stream_ids.get(service):
            await attempt(f"Graylog stream {stream_ids[service]}", lambda s=stream_ids[service]: delete_stream(stream_id=s))
        if service in keep_shared:
            continue
        if index_ids.get(service):
            await attempt(f"Graylog index set {index_ids[service]}", lambda i=index_ids[service]: delete_index_by_id(index_id=i))
        if grafana_org_id and datasource_uids.get(service):
            await attempt(
                f"Grafana datasource {datasource_uids[service]}",
                lambda u=datasource_uids[service]: delete_grafana_datasource(organization_id=grafana_org_id, datasource_uid=u),
            )
    return warnings


async def _sibling_metas(
    customer_code: str,
    instance_name: Optional[str],
    session: AsyncSession,
) -> List[CustomerIntegrationsMeta]:
    """The metadata of the customer's *other* AWS instances (NULL-safe, like `instance_name_differs`)."""
    column = CustomerIntegrationsMeta.instance_name
    other = column.isnot(None) if instance_name is None else or_(column.is_(None), column != instance_name)
    result = await session.execute(
        select(CustomerIntegrationsMeta).where(
            CustomerIntegrationsMeta.customer_code == customer_code,
            CustomerIntegrationsMeta.integration_name == AWS_INTEGRATION_NAME,
            other,
        ),
    )
    return list(result.scalars().all())


async def cleanup_aws_infrastructure(
    meta: CustomerIntegrationsMeta,
    customer_code: str,
    instance_name: Optional[str],
    session: AsyncSession,
    cleanup_warnings: List[str],
) -> None:
    """
    Remove one instance's Graylog streams, and whatever the customer no longer needs after it.

    A service's index set and Grafana datasource are shared by every AWS account of the customer
    that collects that service, so they go only when no other instance still collects it; the
    Grafana folder goes with the customer's last AWS instance.
    """
    siblings = await _sibling_metas(customer_code, instance_name, session)
    still_used = {service for sibling in siblings for service in decode_service_ids(sibling.graylog_stream_id)}
    stream_ids = decode_service_ids(meta.graylog_stream_id)

    cleanup_warnings.extend(
        await remove_service_resources(
            sorted(stream_ids),
            stream_ids=stream_ids,
            index_ids=decode_service_ids(meta.graylog_index_id),
            datasource_uids=decode_service_ids(meta.grafana_datasource_uid),
            grafana_org_id=meta.grafana_org_id,
            keep_shared=still_used,
        ),
    )

    if siblings:
        logger.info(f"Other AWS instances of {customer_code} remain; keeping the AWS Grafana folder.")
        return
    if meta.grafana_org_id and meta.grafana_dashboard_folder_id:
        try:
            await delete_folder(meta.grafana_org_id, meta.grafana_dashboard_folder_id)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to delete Grafana folder {meta.grafana_dashboard_folder_id}: {e}")
            cleanup_warnings.append(
                f"Could not delete Grafana folder {meta.grafana_dashboard_folder_id}: {e}. Remove it manually if it still exists.",
            )


async def decommission_aws_instance(bucket_name: str, account_id: str) -> None:
    """
    Stop the Wazuh manager collecting one instance's buckets.

    Only `<bucket>` entries for this bucket and account are removed; every other customer's buckets
    stay exactly as they are, and the wodle itself goes only when nothing is left in it. Raises on a
    failure — the caller reports it as a cleanup warning.
    """
    result = await apply_instance_buckets([], bucket_name, account_id, adopt_existing=True)
    if not result.changed:
        logger.info(f"No aws-s3 buckets for {bucket_name} / account {account_id} on the Wazuh manager; nothing to remove.")
