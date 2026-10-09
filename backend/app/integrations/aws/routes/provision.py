from typing import Dict

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.aws.schema.provision import AWS_INTEGRATION_NAME
from app.integrations.aws.schema.provision import ProvisionAwsAuthKeys
from app.integrations.aws.schema.provision import ProvisionAwsRequest
from app.integrations.aws.schema.provision import ProvisionAwsResponse
from app.integrations.aws.services.provision import provision_aws
from app.integrations.routes import find_customer_integration
from app.integrations.routes import get_customer_integrations_by_customer_code
from app.integrations.routes import normalize_instance_name
from app.integrations.routes import resolve_integration_instance
from app.integrations.schema import CustomerIntegrations
from app.middleware.customer_access import customer_access_handler

integration_aws_router = APIRouter()


def extract_aws_auth_keys(customer_integration: CustomerIntegrations) -> Dict[str, str]:
    """
    Flatten the AWS auth keys of one integration instance into a dict.

    The record must already be narrowed to a single instance (`match_instance=True`): a customer with
    several AWS accounts would otherwise get one account's key paired with another's secret.
    """
    auth_keys = {}
    for subscription in customer_integration.integration_subscriptions:
        if subscription.integration_service.service_name == AWS_INTEGRATION_NAME:
            for auth_key in subscription.integration_auth_keys:
                auth_keys[auth_key.auth_key_name] = auth_key.auth_value
    if not auth_keys:
        raise HTTPException(
            status_code=404,
            detail="No auth keys found for the AWS integration. Please create auth keys for the AWS integration.",
        )
    return auth_keys


def parse_aws_auth_keys(auth_keys: Dict[str, str]) -> ProvisionAwsAuthKeys:
    """Validate the stored auth keys, naming each bad field without echoing any value."""
    try:
        return ProvisionAwsAuthKeys(**auth_keys)
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(str(part) for part in error['loc']) or 'auth keys'}: {error['msg']}" for error in e.errors())
        raise HTTPException(status_code=400, detail=f"The AWS integration's auth keys are not valid: {problems}")


@integration_aws_router.post(
    "/provision",
    response_model=ProvisionAwsResponse,
    description=(
        "Provision (or re-sync) the AWS integration for a customer: validate the credentials, add the buckets to the Wazuh "
        "manager's aws-s3 wodle, and create the Graylog index sets, streams and Grafana datasources."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_aws_route(
    provision_aws_request: ProvisionAwsRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProvisionAwsResponse:
    # The customer is named in the body, where no route dependency can reach it.
    await customer_access_handler.enforce_customer_access(current_user, provision_aws_request.customer_code, session)

    customer_integration_response = await get_customer_integrations_by_customer_code(
        provision_aws_request.customer_code,
        session,
    )
    if customer_integration_response.available_integrations == []:
        raise HTTPException(status_code=404, detail="Customer integration settings not found.")

    instance_name = await resolve_integration_instance(
        session,
        provision_aws_request.customer_code,
        AWS_INTEGRATION_NAME,
        normalize_instance_name(provision_aws_request.instance_name),
    )

    customer_integration = await find_customer_integration(
        provision_aws_request.customer_code,
        AWS_INTEGRATION_NAME,
        customer_integration_response,
        instance_name=instance_name,
        match_instance=True,
    )
    if customer_integration is None:
        raise HTTPException(
            status_code=404,
            detail=f"AWS integration '{instance_name or 'Default'}' not found for customer {provision_aws_request.customer_code}.",
        )

    auth_keys = parse_aws_auth_keys(extract_aws_auth_keys(customer_integration))

    return await provision_aws(
        provision_aws_request.customer_code,
        auth_keys,
        session,
        instance_name=instance_name,
    )
