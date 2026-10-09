from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.integrations.aws.schema.provision import AWS_INTEGRATION_NAME
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.models.customer_integration_settings import IntegrationAuthKeys
from app.integrations.models.customer_integration_settings import IntegrationService
from app.integrations.models.customer_integration_settings import (
    IntegrationSubscription,
)


@dataclass
class AwsInstanceRecord:
    """The identifying auth keys of one configured AWS integration instance."""

    customer_code: str
    instance_name: Optional[str]
    account_id: Optional[str]
    bucket_name: Optional[str]


async def list_aws_instances(session: AsyncSession) -> List[AwsInstanceRecord]:
    """Every configured AWS instance with its account and bucket, read from the stored auth keys."""
    result = await session.execute(
        select(
            CustomerIntegrations.id,
            CustomerIntegrations.customer_code,
            CustomerIntegrations.instance_name,
            IntegrationAuthKeys.auth_key_name,
            IntegrationAuthKeys.auth_value,
        )
        .join(
            IntegrationSubscription,
            CustomerIntegrations.id == IntegrationSubscription.customer_id,
        )
        .join(
            IntegrationService,
            IntegrationSubscription.integration_service_id == IntegrationService.id,
        )
        .join(
            IntegrationAuthKeys,
            IntegrationAuthKeys.subscription_id == IntegrationSubscription.id,
        )
        .where(
            IntegrationService.service_name == AWS_INTEGRATION_NAME,
            IntegrationAuthKeys.auth_key_name.in_(("AWS_ACCOUNT_ID", "BUCKET_NAME")),
        ),
    )
    instances: Dict[int, AwsInstanceRecord] = {}
    for integration_id, customer_code, instance_name, key_name, value in result.all():
        record = instances.setdefault(integration_id, AwsInstanceRecord(customer_code, instance_name, None, None))
        if key_name == "AWS_ACCOUNT_ID":
            record.account_id = (value or "").strip() or None
        else:
            record.bucket_name = (value or "").strip() or None
    return list(instances.values())


async def find_aws_instance(
    customer_code: str,
    instance_name: Optional[str],
    session: AsyncSession,
) -> Optional[AwsInstanceRecord]:
    for record in await list_aws_instances(session):
        if record.customer_code == customer_code and record.instance_name == instance_name:
            return record
    return None


async def resolve_customer_code_from_aws_account(
    account_id: str,
    session: AsyncSession,
) -> Optional[str]:
    """
    Map an AWS account ID to the CoPilot customer that owns it.

    AWS events come from the Wazuh master (agent 000), so they carry no agent customer label; the
    `AWS ACCOUNT ID` pipeline rule copies the account into `aws_account_id`, and that is what the
    ingest path has to translate — the same way Office365 tenant GUIDs are translated through
    `resolve_customer_code_from_office365_tenant`.

    Only *deployed* instances count: a deployed one passed provisioning's ownership check, while a
    merely created one could name any account. Should two customers still claim the account (rows
    edited by hand, a pre-existing conflict), nobody gets the alert — routing it to the wrong tenant
    would be worse than not routing it.
    """
    if not account_id:
        return None

    result = await session.execute(
        select(CustomerIntegrations.customer_code)
        .distinct()
        .join(
            IntegrationSubscription,
            CustomerIntegrations.id == IntegrationSubscription.customer_id,
        )
        .join(
            IntegrationService,
            IntegrationSubscription.integration_service_id == IntegrationService.id,
        )
        .join(
            IntegrationAuthKeys,
            IntegrationAuthKeys.subscription_id == IntegrationSubscription.id,
        )
        .where(
            IntegrationService.service_name == AWS_INTEGRATION_NAME,
            IntegrationAuthKeys.auth_key_name == "AWS_ACCOUNT_ID",
            IntegrationAuthKeys.auth_value == account_id,
            CustomerIntegrations.deployed.is_(True),
        ),
    )
    customer_codes = list(result.scalars().all())

    if len(customer_codes) > 1:
        logger.error(
            f"AWS account {account_id} is claimed by several customers ({', '.join(sorted(customer_codes))}); "
            "not routing it to any of them.",
        )
        return None
    if customer_codes:
        logger.info(f"Resolved AWS account {account_id} to customer {customer_codes[0]}.")
        return customer_codes[0]
    return None


async def ensure_aws_account_not_owned_elsewhere(
    customer_code: str,
    account_id: Optional[str],
    session: AsyncSession,
) -> None:
    """
    Refuse an AWS account another customer already has configured, deployed or not.

    Checked when an AWS integration is created or its keys are edited, so a conflicting account is
    caught at entry rather than only at deployment.
    """
    account_id = (account_id or "").strip()
    if not account_id:
        return
    for record in await list_aws_instances(session):
        if record.account_id == account_id and record.customer_code != customer_code:
            raise HTTPException(
                status_code=400,
                detail=f"AWS account {account_id} is already configured for customer {record.customer_code}.",
            )
