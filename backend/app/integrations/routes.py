from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.auth.utils import AuthHandler
from app.connectors.grafana.services.folders import delete_folder
from app.connectors.graylog.services.management import delete_index_by_id
from app.connectors.graylog.services.streams import delete_stream
from app.customer_provisioning.services.grafana import delete_grafana_datasource
from app.db.db_session import get_db
from app.db.universal_models import Customers
from app.db.universal_models import CustomersMeta
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)
from app.integrations.models.customer_integration_settings import AvailableIntegrations
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.models.customer_integration_settings import (
    CustomerIntegrationsMeta,
)
from app.integrations.models.customer_integration_settings import IntegrationAuthKeys
from app.integrations.models.customer_integration_settings import IntegrationConfig
from app.integrations.models.customer_integration_settings import IntegrationService
from app.integrations.models.customer_integration_settings import (
    IntegrationSubscription,
)
from app.integrations.schema import AuthKey
from app.integrations.schema import AvailableIntegrationsResponse
from app.integrations.schema import CreateIntegrationAuthKeys
from app.integrations.schema import CreateIntegrationService
from app.integrations.schema import CustomerByAuthKeyResponse
from app.integrations.schema import CustomerIntegrationCreate
from app.integrations.schema import CustomerIntegrationCreateResponse
from app.integrations.schema import CustomerIntegrationDeleteResponse
from app.integrations.schema import CustomerIntegrationsMetaResponse
from app.integrations.schema import CustomerIntegrationsMetaSchema
from app.integrations.schema import CustomerIntegrationsResponse
from app.integrations.schema import DeleteCustomerIntegration
from app.integrations.schema import IntegrationWithAuthKeys
from app.integrations.schema import UpdateCustomerIntegration
from app.integrations.schema import UpdateMetaAutoRequest
from app.integrations.schema import UpdateMetaResponse
from app.network_connectors.models.network_connectors import (
    CustomerNetworkConnectorsMeta,
)

integration_settings_router = APIRouter()

NETWORK_INTEGRATIONS = [
    "DefenderForEndpoint",
    "BITDEFENDER",
    "CROWDSTRIKE",
    # Add other network integrations as needed
]


async def fetch_available_integrations(session: AsyncSession):
    """
    Fetches available integrations and their auth keys from the database.

    Args:
        session (AsyncSession): The database session.

    Returns:
        List[IntegrationWithAuthKeys]: A list of available integrations with their auth keys.
    """
    stmt = select(AvailableIntegrations).options(
        joinedload(AvailableIntegrations.auth_keys),
    )
    result = await session.execute(stmt)

    # Use unique() to avoid duplicates caused by joined eager loading
    unique_integrations = result.unique().scalars().all()

    integrations_with_auth_keys = []
    for integration in unique_integrations:
        auth_keys = [AuthKey(auth_key_name=key.auth_key_name) for key in integration.auth_keys]
        integration_data = IntegrationWithAuthKeys(
            id=integration.id,
            integration_name=integration.integration_name,
            description=integration.description,
            integration_details=integration.integration_details,
            auth_keys=auth_keys,
        )
        integrations_with_auth_keys.append(integration_data)

    return integrations_with_auth_keys


async def validate_integration_name(integration_name: str, session: AsyncSession):
    """
    Validate if the integration name exists in available integrations.
    """
    available_integrations = await fetch_available_integrations(session)
    if integration_name not in [ai.integration_name for ai in available_integrations]:
        raise HTTPException(
            status_code=400,
            detail=f"Integration {integration_name} is not a valid integration.",
        )


async def validate_integration_auth_keys(
    integration_name: str,
    integration_auth_keys: List[AuthKey],
    session: AsyncSession,
):
    """
    Validate if the integration auth keys are valid.
    """
    available_integrations = await fetch_available_integrations(session)
    integration = [ai for ai in available_integrations if ai.integration_name == integration_name][0]
    available_auth_keys = [ak.auth_key_name for ak in integration.auth_keys]
    # loop through the `available_auth_keys` and check if the `integration_auth_keys` contains the `auth_key_name`
    for auth_key in available_auth_keys:
        if auth_key not in [iak.auth_key_name for iak in integration_auth_keys]:
            raise HTTPException(
                status_code=400,
                detail=f"Integration auth key {auth_key} does not exist.",
            )


async def validate_integration_auth_key_update(
    integration_name: str,
    integration_auth_key: List[AuthKey],
    session: AsyncSession,
):
    """
    Validate if the integration auth key is valid.
    """
    logger.info(f"integration_auth_key: {integration_auth_key}")
    available_integrations = await fetch_available_integrations(session)
    integration = [ai for ai in available_integrations if ai.integration_name == integration_name][0]
    available_auth_keys = [ak.auth_key_name for ak in integration.auth_keys]
    for auth_key in integration_auth_key:
        if auth_key.auth_key_name not in available_auth_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Integration auth key {auth_key.auth_key_name} does not exist.",
            )


async def validate_customer_code(customer_code: str, session: AsyncSession):
    """
    Validate if the customer code exists in the customers table.
    """
    stmt = select(Customers).where(Customers.customer_code == customer_code)
    result = await session.execute(stmt)
    if result.scalars().first() is None:
        raise HTTPException(
            status_code=400,
            detail=f"Customer {customer_code} does not exist.",
        )


async def validate_customer_meta(customer_code: str, session: AsyncSession):
    """
    Validate if the customer code exists in the customers_meta table.
    """
    stmt = select(CustomersMeta).where(CustomersMeta.customer_code == customer_code)
    result = await session.execute(stmt)
    if result.scalars().first() is None:
        raise HTTPException(
            status_code=400,
            detail=f"Customer {customer_code} meta does not exist. Please provision the customer before creating an integration.",
        )


async def check_existing_customer_integration(
    customer_code: str,
    integration_name: str,
    session: AsyncSession,
):
    """
    Check if the customer integration already exists.
    """
    # Assuming IntegrationService has an 'integration_name' field or similar
    stmt = (
        select(CustomerIntegrations)
        .join(CustomerIntegrations.integration_subscriptions)
        .join(IntegrationSubscription.integration_service)
        .where(
            CustomerIntegrations.customer_code == customer_code,
            IntegrationService.service_name == integration_name,
        )
    )
    result = await session.execute(stmt)
    if result.scalars().first() is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Customer integration {customer_code} {integration_name} already exists.",
        )


async def check_existing_customer_integration_meta(
    customer_code: str,
    integration_name: str,
    session: AsyncSession,
):
    """
    Check if the customer integration meta already exists for the customer code and integration name.
    """
    stmt = select(CustomerIntegrationsMeta).where(
        CustomerIntegrationsMeta.customer_code == customer_code,
        CustomerIntegrationsMeta.integration_name == integration_name,
    )
    result = await session.execute(stmt)
    if result.scalars().first() is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Customer integration meta {customer_code} {integration_name} already exists.",
        )


async def create_integration_service(
    integration_name: str,
    settings: CreateIntegrationService,
    session: AsyncSession,
) -> IntegrationService:
    """
    Create or fetch IntegrationService instance with custom configuration.
    """
    integration_service = IntegrationService(
        service_name=integration_name,
        auth_type=settings.auth_type,
        configs=[
            IntegrationConfig(
                config_key=settings.config_key,
                config_value=settings.config_value,
            ),
        ],
    )
    session.add(integration_service)
    await session.flush()
    return integration_service


async def create_customer_integrations(
    customer_code: str,
    customer_name: str,
    integration_service_id: int,
    integration_service_name: str,
    session: AsyncSession,
) -> CustomerIntegrations:
    """
    Create CustomerIntegrations instance.
    """
    customer_integrations = CustomerIntegrations(
        customer_code=customer_code,
        customer_name=customer_name,
        integration_service_id=integration_service_id,
        integration_service_name=integration_service_name,
        deployed=False,
    )
    session.add(customer_integrations)
    await session.flush()
    return customer_integrations


async def create_integration_subscription(
    customer_integrations: CustomerIntegrations,
    integration_service: IntegrationService,
    integration_auth_keys: List[CreateIntegrationAuthKeys],
    session: AsyncSession,
):
    """
    Create IntegrationSubscription instance.
    """
    logger.info(f"integration_auth_keys: {integration_auth_keys}")
    for auth_key in integration_auth_keys:
        new_integration_subscription = IntegrationSubscription(
            customer_integrations=customer_integrations,
            integration_service=integration_service,
            integration_auth_keys=[
                IntegrationAuthKeys(
                    auth_key_name=auth_key.auth_key_name,
                    auth_value=auth_key.auth_value,
                ),
            ],
        )
        session.add(new_integration_subscription)
        await session.commit()


async def get_customer_and_service_ids(session, customer_code, integration_name):
    try:
        result = await session.execute(
            select(CustomerIntegrations.id, IntegrationService.id)
            .join(
                IntegrationSubscription,
                CustomerIntegrations.id == IntegrationSubscription.customer_id,
            )
            .join(
                IntegrationService,
                IntegrationSubscription.integration_service_id == IntegrationService.id,
            )
            .where(
                CustomerIntegrations.customer_code == customer_code,
                IntegrationService.service_name == integration_name,
            ),
        )
        return result.all()
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Customer integration not found")


async def get_subscription_ids(session, customer_id, integration_service_id):
    result = await session.execute(
        select(IntegrationSubscription.id).where(
            IntegrationSubscription.customer_id == customer_id,
            IntegrationSubscription.integration_service_id == integration_service_id,
        ),
    )
    # Fetch all results
    subscription_ids_raw = result.scalars().all()

    # Process the results
    # If the result is a list of tuples (even with one element), extract the first element
    if subscription_ids_raw and isinstance(subscription_ids_raw[0], tuple):
        return [id_tuple[0] for id_tuple in subscription_ids_raw]
    # If the result is a list of integers
    elif subscription_ids_raw and isinstance(subscription_ids_raw[0], int):
        return subscription_ids_raw
    # If there are no results
    else:
        return []


async def delete_metadata(session, subscription_ids):
    await session.execute(
        delete(IntegrationAuthKeys).where(
            IntegrationAuthKeys.subscription_id.in_(subscription_ids),
        ),
    )


async def delete_subscriptions(session, subscription_ids):
    await session.execute(
        delete(IntegrationSubscription).where(
            IntegrationSubscription.id.in_(subscription_ids),
        ),
    )


async def delete_configs(session, integration_service_id):
    await session.execute(
        delete(IntegrationConfig).where(
            IntegrationConfig.integration_service_id == integration_service_id,
        ),
    )


async def delete_integration_service(session, integration_service_id):
    await session.execute(
        delete(IntegrationService).where(
            IntegrationService.id == integration_service_id,
        ),
    )


async def delete_customer_integration_record(session, customer_id):
    await session.execute(
        delete(CustomerIntegrations).where(CustomerIntegrations.id == customer_id),
    )


async def find_customer_integration(
    customer_code: str,
    integration_name: str,
    customer_integration_response,
) -> Optional[CustomerIntegrations]:
    for ci in customer_integration_response.available_integrations:
        for subscription in ci.integration_subscriptions:
            if subscription.integration_service.service_name == integration_name:
                return ci
    return None


def get_subscription_id(
    customer_integration,
    integration_name: str,
    auth_key_name: str,
) -> Optional[int]:
    for subscription in customer_integration.integration_subscriptions:
        if subscription.integration_service.service_name == integration_name:
            for auth_key in subscription.integration_auth_keys:
                if auth_key.auth_key_name == auth_key_name:
                    return subscription.id
    return None


async def get_tenant_id(
    customer_integration: CustomerIntegrationCreate,
    session: AsyncSession,
) -> str:
    """
    Retrieves the Tenant ID for a given customer integration. This is the Office365 organization ID and
    is used to create alerts for the customer in DFIR-IRIS.
    """
    stmt = (
        select(IntegrationAuthKeys)
        .join(
            IntegrationSubscription,
            IntegrationAuthKeys.subscription_id == IntegrationSubscription.id,
        )
        .join(
            CustomerIntegrations,
            IntegrationSubscription.customer_id == CustomerIntegrations.id,
        )
        .join(
            IntegrationService,
            IntegrationSubscription.integration_service_id == IntegrationService.id,
        )
        .where(
            CustomerIntegrations.customer_code == customer_integration.customer_code,
            IntegrationService.service_name == customer_integration.integration_name,
            IntegrationAuthKeys.auth_key_name == "TENANT_ID",
        )
    )

    result = await session.execute(stmt)
    tenant_id = result.scalars().first()
    if tenant_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tenant ID for customer {customer_integration.customer_code} not found.",
        )
    logger.info(f"tenant_id: {tenant_id.auth_value}")
    return tenant_id.auth_value


async def update_office365_organization_id(
    customer_code: str,
    tenant_id: str,
    session: AsyncSession,
):
    """
    Updates the Office365 organization ID in the alert_creation_settings table.
    """
    stmt = (
        update(AlertCreationSettings)
        .where(AlertCreationSettings.customer_code == customer_code)
        .values(office365_organization_id=tenant_id)
    )
    await session.execute(stmt)
    await session.commit()


async def get_integration_service_id(
    integration_name: str,
    session: AsyncSession,
) -> int:
    """
    Retrieves the AvailableIntegrations ID for a given integration name.
    """
    stmt = select(AvailableIntegrations).where(
        AvailableIntegrations.integration_name == integration_name,
    )
    result = await session.execute(stmt)
    integration_service = result.scalars().first()
    if integration_service is None:
        raise HTTPException(
            status_code=404,
            detail=f"Integration service {integration_name} not found.",
        )
    return integration_service.id


async def get_integration_service_name(
    integration_name: str,
    session: AsyncSession,
) -> str:
    """
    Retrieves the AvailableIntegrations ID for a given integration name.
    """
    stmt = select(AvailableIntegrations).where(
        AvailableIntegrations.integration_name == integration_name,
    )
    result = await session.execute(stmt)
    integration_service = result.scalars().first()
    if integration_service is None:
        raise HTTPException(
            status_code=404,
            detail=f"Integration service {integration_name} not found.",
        )
    return integration_service.integration_name


async def fetch_customer_integrations_data(session: AsyncSession):
    """
    Fetches customer integrations data from the database.
    """
    stmt = select(CustomerIntegrations).options(
        joinedload(CustomerIntegrations.integration_subscriptions).joinedload(
            IntegrationSubscription.integration_service,
        ),
        joinedload(CustomerIntegrations.integration_subscriptions).subqueryload(
            IntegrationSubscription.integration_auth_keys,
        ),
    )
    result = await session.execute(stmt)
    return result.scalars().unique().all()


def process_customer_integrations(customer_integrations_data):
    """
    Processes customer integrations data and returns a list of CustomerIntegrations objects.
    """
    processed_customer_integrations = []
    for ci in customer_integrations_data:
        first_service_id = ci.integration_subscriptions[0].integration_service_id if ci.integration_subscriptions else None
        customer_integration_obj = CustomerIntegrations(
            id=ci.id,
            customer_code=ci.customer_code,
            customer_name=ci.customer_name,
            integration_subscriptions=ci.integration_subscriptions,
            integration_service_id=first_service_id,
            integration_service_name=ci.integration_subscriptions[0].integration_service.service_name
            if ci.integration_subscriptions
            else None,
            deployed=ci.deployed,
        )
        processed_customer_integrations.append(customer_integration_obj)
    return processed_customer_integrations


def generate_integration_response(customer_code: str, integration_name: str) -> CustomerIntegrationCreateResponse:
    additional_info_map = {
        "Office365": (
            "Make sure to update the Office365 integration block in the Wazuh Manager ossec.conf file and restart the Wazuh Manager service. "
            "Also make sure to update the Office365 Graylog stream rule for this customer with the new organization ID if this has changed. "
            "YouTube video: https://youtu.be/ihj2F2rA6BQ?si=p4c8Xnk6PX8r29IB"
        ),
        "Crowdstrike": (
            "Make sure to update the Crowdstrike docker application with the new connection details and restart the docker container. "
            "YouTube video: https://youtu.be/YOVUOpZDEzM?si=jzpHw8vcnqnfVPzt"
        ),
        "BitDefender": (
            "Make sure to update the BitDefender docker application with the new connection details and restart the docker container."
        ),
    }

    additional_info = additional_info_map.get(integration_name, "")
    if additional_info == "":
        additional_info = None

    return CustomerIntegrationCreateResponse(
        message=f"Customer integration {customer_code} {integration_name} successfully updated.",
        success=True,
        additional_info=additional_info,
    )


def generate_decommission_response(customer_code: str, integration_name: str) -> CustomerIntegrationDeleteResponse:
    additional_info_map = {
        "Office365": (
            "Make sure to remove the Office365 integration block from the Wazuh Manager ossec.conf file and restart the Wazuh Manager service. "
        ),
        "Crowdstrike": ("Make sure to remove the Crowdstrike docker application."),
        "BitDefender": ("Make sure to remove the BitDefender docker application."),
    }

    additional_info = additional_info_map.get(integration_name, "")
    if additional_info == "":
        additional_info = None

    return CustomerIntegrationDeleteResponse(
        message=f"Customer integration {customer_code} {integration_name} successfully deleted.",
        success=True,
        additional_info=additional_info,
    )


@integration_settings_router.get(
    "/available_integrations",
    response_model=AvailableIntegrationsResponse,
    description="Get a list of available integrations.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_available_integrations(
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to get a list of available integrations.
    """
    available_integrations = await fetch_available_integrations(session)
    return AvailableIntegrationsResponse(
        available_integrations=available_integrations,
        message="Available integrations successfully retrieved.",
        success=True,
    )


@integration_settings_router.get(
    "/customer_integrations",
    response_model=CustomerIntegrationsResponse,
    description="Get a list of customer integrations.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_integrations(session: AsyncSession = Depends(get_db)):
    """
    Endpoint to get a list of customer integrations.
    """
    customer_integrations_data = await fetch_customer_integrations_data(session)
    processed_customer_integrations = process_customer_integrations(
        customer_integrations_data,
    )

    logger.info(f"Processed customer_integrations: {processed_customer_integrations}")
    return CustomerIntegrationsResponse(
        available_integrations=processed_customer_integrations,
        message="Customer integrations successfully retrieved.",
        success=True,
    )


@integration_settings_router.get(
    "/customer_integrations_meta",
    response_model=CustomerIntegrationsMetaResponse,
    description="Get a list of customer integrations metadata.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_integrations_meta(session: AsyncSession = Depends(get_db)):
    """
    Endpoint to get a list of customer integrations metadata.
    """
    try:
        stmt = select(CustomerIntegrationsMeta)
        result = await session.execute(stmt)
        customer_integrations_meta = result.scalars().all()
    except Exception as e:
        logger.error(f"Error while fetching customer integrations metadata: {e}")
        customer_integrations_meta = []

    logger.info(f"customer_integrations_meta: {customer_integrations_meta}")
    return CustomerIntegrationsMetaResponse(
        customer_integrations_meta=customer_integrations_meta,
        message="Customer integrations metadata successfully retrieved.",
        success=True,
    )


@integration_settings_router.get(
    "/customer_integrations/{customer_code}",
    response_model=CustomerIntegrationsResponse,
    description="Get a list of customer integrations for a specific customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_integrations_by_customer_code(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to get a list of customer integrations for a specific customer.
    """
    stmt = (
        select(CustomerIntegrations)
        .options(
            joinedload(CustomerIntegrations.integration_subscriptions).joinedload(
                IntegrationSubscription.integration_service,
            ),
            joinedload(CustomerIntegrations.integration_subscriptions).subqueryload(
                IntegrationSubscription.integration_auth_keys,
            ),  # Load IntegrationAuthKeys
        )
        .where(CustomerIntegrations.customer_code == customer_code)
    )
    result = await session.execute(stmt)
    customer_integrations = result.scalars().unique().all()
    return CustomerIntegrationsResponse(
        available_integrations=customer_integrations,
        message="Customer integrations successfully retrieved.",
        success=True,
    )


@integration_settings_router.get(
    "/customer_integrations_meta/{customer_code}",
    response_model=CustomerIntegrationsMetaResponse,
    description="Get a list of customer integrations metadata for a specific customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_integrations_meta_by_customer_code(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to get a list of customer integrations metadata for a specific customer.
    """
    stmt = select(CustomerIntegrationsMeta).where(
        CustomerIntegrationsMeta.customer_code == customer_code,
    )
    result = await session.execute(stmt)
    customer_integrations_meta = result.scalars().all()
    logger.info(f"customer_integrations_meta: {customer_integrations_meta}")
    return CustomerIntegrationsMetaResponse(
        customer_integrations_meta=customer_integrations_meta,
        message="Customer integrations metadata successfully retrieved.",
        success=True,
    )


@integration_settings_router.post(
    "/create_integration",
    response_model=CustomerIntegrationCreateResponse,
    description="Create a new customer integration.",
    # dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_integration(
    customer_integration_create: CustomerIntegrationCreate,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to create a new customer integration.
    """
    await validate_integration_name(
        customer_integration_create.integration_name,
        session,
    )
    await validate_integration_auth_keys(
        customer_integration_create.integration_name,
        customer_integration_create.integration_auth_keys,
        session,
    )
    await validate_customer_code(customer_integration_create.customer_code, session)
    await validate_customer_meta(customer_integration_create.customer_code, session)
    await check_existing_customer_integration(
        customer_integration_create.customer_code,
        customer_integration_create.integration_name,
        session,
    )
    integration_service_id = await get_integration_service_id(
        customer_integration_create.integration_name,
        session,
    )
    integration_service_name = await get_integration_service_name(
        customer_integration_create.integration_name,
        session,
    )

    integration_service = await create_integration_service(
        customer_integration_create.integration_name,
        settings=customer_integration_create.integration_config,
        session=session,
    )
    customer_integrations = await create_customer_integrations(
        customer_integration_create.customer_code,
        customer_integration_create.customer_name,
        integration_service_id=integration_service_id,
        integration_service_name=integration_service_name,
        session=session,
    )
    await create_integration_subscription(
        customer_integrations,
        integration_service,
        integration_auth_keys=customer_integration_create.integration_auth_keys,
        session=session,
    )

    # Office365 specific integration handling
    if customer_integration_create.integration_name == "Office365":
        tenant_id = await get_tenant_id(customer_integration_create, session)
        await update_office365_organization_id(
            customer_integration_create.customer_code,
            tenant_id,
            session,
        )

    return CustomerIntegrationCreateResponse(
        message=f"Customer integration {customer_integration_create.customer_code} {customer_integration_create.integration_name} successfully created.",
        success=True,
    )


@integration_settings_router.post(
    "/create_integration_meta",
    response_model=CustomerIntegrationsMetaResponse,
    description="Create a new customer integration metadata.",
    # dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_integration_meta(
    customer_integration_meta: CustomerIntegrationsMetaSchema,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to create a new customer integration metadata.
    """
    await validate_customer_code(customer_integration_meta.customer_code, session)
    await validate_customer_meta(customer_integration_meta.customer_code, session)
    await check_existing_customer_integration_meta(
        customer_integration_meta.customer_code,
        customer_integration_meta.integration_name,
        session,
    )
    try:
        new_customer_integration_meta = CustomerIntegrationsMeta(
            **customer_integration_meta.dict(),
        )
        session.add(new_customer_integration_meta)
        await session.commit()
        return CustomerIntegrationsMetaResponse(
            message="Customer integration metadata successfully created.",
            success=True,
        )
    except Exception as e:
        logger.error(f"Error while creating customer integration metadata: {e}")
        return CustomerIntegrationsMetaResponse(
            customer_integrations_meta=None,
            message="Error while creating customer integration metadata.",
            success=False,
        )


@integration_settings_router.put(
    "/update_integration/{customer_code}",
    response_model=CustomerIntegrationCreateResponse,
    description="Update a customer integration.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_integration(
    customer_code: str,
    customer_integration_update: UpdateCustomerIntegration,
    session: AsyncSession = Depends(get_db),
):
    await validate_integration_name(
        customer_integration_update.integration_name,
        session,
    )
    customer_integration_response = await get_customer_integrations_by_customer_code(
        customer_code,
        session,
    )

    if not customer_integration_response:
        raise HTTPException(status_code=404, detail="Customer integrations not found")

    customer_integration = await find_customer_integration(
        customer_code,
        customer_integration_update.integration_name,
        customer_integration_response,
    )

    if not customer_integration:
        raise HTTPException(
            status_code=404,
            detail="Customer integration with specified service name not found.",
        )

    await validate_integration_auth_key_update(
        customer_integration_update.integration_name,
        customer_integration_update.integration_auth_keys,
        session,
    )

    for auth_key in customer_integration_update.integration_auth_keys:
        subscription_id = get_subscription_id(
            customer_integration,
            customer_integration_update.integration_name,
            auth_key.auth_key_name,
        )

        if not subscription_id:
            raise HTTPException(
                status_code=404,
                detail=f"Integration auth key {auth_key.auth_key_name} not found.",
            )

        await session.execute(
            update(IntegrationAuthKeys)
            .where(IntegrationAuthKeys.subscription_id == subscription_id)
            .values(
                auth_value=auth_key.auth_value,
            ),
        )

    await session.commit()

    return generate_integration_response(customer_code, customer_integration_update.integration_name)


@integration_settings_router.put(
    "/available_integrations",
    response_model=AvailableIntegrationsResponse,
    description="Update an available integration.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_available_integrations(
    available_integrations: List[AvailableIntegrations],
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to update an available integration.
    """
    for integration in available_integrations:
        stmt = select(AvailableIntegrations).where(
            AvailableIntegrations.integration_name == integration.integration_name,
        )
        result = await session.execute(stmt)
        existing_integration = result.scalars().first()

        if existing_integration is None:
            raise HTTPException(
                status_code=404,
                detail=f"Integration {integration.integration_name} not found.",
            )

        existing_integration.description = integration.description
        existing_integration.integration_details = integration.integration_details

    await session.commit()

    return AvailableIntegrationsResponse(
        available_integrations=available_integrations,
        message="Available integrations successfully updated.",
        success=True,
    )


async def fetch_customer_integration_meta(session: AsyncSession, customer_code: str, integration_name: str):
    """
    Fetches customer integrations metadata from the database.
    """
    stmt = select(CustomerIntegrationsMeta).where(
        CustomerIntegrationsMeta.customer_code == customer_code,
        CustomerIntegrationsMeta.integration_name == integration_name,
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def delete_customer_integration_meta(session: AsyncSession, customer_code: str, integration_name: str):
    """
    Deletes customer integrations metadata from the database.
    """
    await session.execute(
        delete(CustomerIntegrationsMeta).where(
            CustomerIntegrationsMeta.customer_code == customer_code,
            CustomerIntegrationsMeta.integration_name == integration_name,
        ),
    )


async def fetch_customer_network_connectors_meta(session: AsyncSession, customer_code: str, network_connector_name: str):
    """
    Fetches customer network connectors metadata from the database.
    """
    stmt = select(CustomerNetworkConnectorsMeta).where(
        CustomerNetworkConnectorsMeta.customer_code == customer_code,
        CustomerNetworkConnectorsMeta.network_connector_name == network_connector_name,
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def delete_customer_network_connectors_meta(session: AsyncSession, customer_code: str, network_connector_name: str):
    """
    Deletes customer network connectors metadata from the database.
    """
    await session.execute(
        delete(CustomerNetworkConnectorsMeta).where(
            CustomerNetworkConnectorsMeta.customer_code == customer_code,
            CustomerNetworkConnectorsMeta.network_connector_name == network_connector_name,
        ),
    )


# @integration_settings_router.delete(
#     "/delete_integration",
#     response_model=CustomerIntegrationDeleteResponse,
#     description="Delete a customer integration.",
#     dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
# )
# async def delete_integration(
#     delete_customer_integration: DeleteCustomerIntegration,
#     session: AsyncSession = Depends(get_db),
# ):
#     customer_code = delete_customer_integration.customer_code
#     integration_name = delete_customer_integration.integration_name

#     results = await get_customer_and_service_ids(
#         session,
#         customer_code,
#         integration_name,
#     )
#     # Check if results is not empty
#     if results:
#         # Unpack the first tuple in results
#         customer_id, integration_service_id = results[0]
#     else:
#         # Handle the case where results is empty
#         raise HTTPException(status_code=404, detail="Customer integration not found")

#     subscription_ids = await get_subscription_ids(
#         session,
#         customer_id,
#         integration_service_id,
#     )
#     if not subscription_ids:
#         raise HTTPException(
#             status_code=404,
#             detail="No subscriptions found for customer integration",
#         )

#     stream_id = (await fetch_customer_integration_meta(session, customer_code, integration_name)).graylog_stream_id
#     logger.info(f"stream_id: {stream_id}")
#     await delete_stream(stream_id=stream_id)

#     index_id = (await fetch_customer_integration_meta(session, customer_code, integration_name)).graylog_index_id
#     logger.info(f"index_id: {index_id}")
#     await delete_index_by_id(index_id=index_id)

#     # Delete the folder in Grafana
#     grafana_org_id = (await fetch_customer_integration_meta(session, customer_code, integration_name)).grafana_org_id
#     grafana_dashboard_folder_id = (
#         await fetch_customer_integration_meta(session, customer_code, integration_name)
#     ).grafana_dashboard_folder_id

#     await delete_folder(grafana_org_id, int(grafana_dashboard_folder_id))

#     await delete_metadata(session, subscription_ids)
#     await delete_subscriptions(session, subscription_ids)
#     await delete_configs(session, integration_service_id)
#     await delete_integration_service(session, integration_service_id)
#     await delete_customer_integration_record(session, customer_id)
#     await delete_customer_integration_meta(session, customer_code, integration_name)

#     await session.commit()

#     return generate_decommission_response(customer_code, integration_name)


@integration_settings_router.delete(
    "/delete_integration",
    response_model=CustomerIntegrationDeleteResponse,
    description="Delete a customer integration.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_integration(
    delete_customer_integration: DeleteCustomerIntegration,
    session: AsyncSession = Depends(get_db),
):
    customer_code = delete_customer_integration.customer_code
    integration_name = delete_customer_integration.integration_name

    # Check if this is a network integration
    is_network_integration = integration_name in NETWORK_INTEGRATIONS

    results = await get_customer_and_service_ids(
        session,
        customer_code,
        integration_name,
    )
    # Check if results is not empty
    if results:
        # Unpack the first tuple in results
        customer_id, integration_service_id = results[0]
    else:
        # Handle the case where results is empty
        raise HTTPException(status_code=404, detail="Customer integration not found")

    subscription_ids = await get_subscription_ids(
        session,
        customer_id,
        integration_service_id,
    )
    if not subscription_ids:
        raise HTTPException(
            status_code=404,
            detail="No subscriptions found for customer integration",
        )

    # Fetch metadata from appropriate table based on integration type
    if is_network_integration:
        meta_data = await fetch_customer_network_connectors_meta(session, customer_code, integration_name)
    else:
        meta_data = await fetch_customer_integration_meta(session, customer_code, integration_name)

    if not meta_data:
        raise HTTPException(status_code=404, detail=f"Metadata not found for {integration_name} integration")

    # Delete stream and index using metadata
    stream_id = meta_data.graylog_stream_id
    logger.info(f"stream_id: {stream_id}")
    await delete_stream(stream_id=stream_id)

    index_id = meta_data.graylog_index_id
    logger.info(f"index_id: {index_id}")
    await delete_index_by_id(index_id=index_id)

    # Delete the folder in Grafana
    grafana_org_id = meta_data.grafana_org_id
    grafana_dashboard_folder_id = meta_data.grafana_dashboard_folder_id

    await delete_folder(grafana_org_id, int(grafana_dashboard_folder_id))

    # Delete the grafana datasource
    if meta_data.grafana_datasource_uid is not None:
        logger.info(f"Deleting Grafana datasource with UID: {meta_data.grafana_datasource_uid}")
        await delete_grafana_datasource(
            organization_id=grafana_org_id,
            datasource_uid=meta_data.grafana_datasource_uid,
        )
    else:
        logger.info("No Grafana datasource UID found, skipping deletion.")

    await delete_metadata(session, subscription_ids)
    await delete_subscriptions(session, subscription_ids)
    await delete_configs(session, integration_service_id)
    await delete_integration_service(session, integration_service_id)
    await delete_customer_integration_record(session, customer_id)

    # Delete metadata from appropriate table
    if is_network_integration:
        await delete_customer_network_connectors_meta(session, customer_code, integration_name)
    else:
        await delete_customer_integration_meta(session, customer_code, integration_name)

    await session.commit()

    return generate_decommission_response(customer_code, integration_name)


@integration_settings_router.get(
    "/integration_customer/{integration_name}/{auth_key_name}/{auth_key_value}",
    description="Get customer code by integration details and auth key value",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_by_auth_key(
    integration_name: str,
    auth_key_name: str,
    auth_key_value: str,
    session: AsyncSession = Depends(get_db),
) -> CustomerByAuthKeyResponse:
    """
    Retrieve a customer code based on integration name, auth key name, and auth key value.

    This is useful for identifying which customer an integration belongs to when you only
    have specific integration details, like a tenant ID.

    Args:
        integration_name: The name of the integration (e.g., "Office365")
        auth_key_name: The name of the auth key (e.g., "TENANT_ID")
        auth_key_value: The value of the auth key to look up

    Returns:
        Customer code and name associated with the provided integration details
    """
    try:
        # Build query to find customer by auth key value
        query = (
            select(CustomerIntegrations.customer_code, CustomerIntegrations.customer_name)
            .join(IntegrationSubscription, CustomerIntegrations.id == IntegrationSubscription.customer_id)
            .join(IntegrationService, IntegrationSubscription.integration_service_id == IntegrationService.id)
            .join(IntegrationAuthKeys, IntegrationSubscription.id == IntegrationAuthKeys.subscription_id)
            .where(
                IntegrationService.service_name == integration_name,
                IntegrationAuthKeys.auth_key_name == auth_key_name,
                IntegrationAuthKeys.auth_value == auth_key_value,
            )
        )

        # Execute query
        result = await session.execute(query)
        customer_info = result.first()

        if customer_info is None:
            raise HTTPException(
                status_code=404,
                detail=f"No customer found with {integration_name} integration having {auth_key_name}={auth_key_value}",
            )

        customer_code, customer_name = customer_info

        return CustomerByAuthKeyResponse(
            customer_code=customer_code,
            customer_name=customer_name,
            integration_name=integration_name,
            auth_key_name=auth_key_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up customer by integration auth key: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to look up customer: {str(e)}")


@integration_settings_router.get(
    "/meta_auto/{customer_code}/{integration_name}",
    description="Get integration or network connector metadata automatically based on integration name",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_meta_auto(
    customer_code: str,
    integration_name: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Automatically retrieve metadata from the appropriate table based on integration name.

    This route checks if the integration is in the NETWORK_INTEGRATIONS list and
    fetches from the appropriate table accordingly.

    Args:
        customer_code (str): The customer code to filter by
        integration_name (str): The integration/connector name to filter by
        session (AsyncSession): Database session

    Returns:
        dict: The metadata record from the appropriate table
    """
    logger.info(f"Fetching metadata for customer {customer_code} and integration {integration_name}")

    is_network_integration = integration_name in NETWORK_INTEGRATIONS

    try:
        if is_network_integration:
            # Fetch from network connectors table
            stmt = select(CustomerNetworkConnectorsMeta).where(
                CustomerNetworkConnectorsMeta.customer_code == customer_code,
                CustomerNetworkConnectorsMeta.network_connector_name == integration_name,
            )
            result = await session.execute(stmt)
            meta_record = result.scalars().first()

            if not meta_record:
                raise HTTPException(
                    status_code=404,
                    detail=f"Network connector metadata not found for customer {customer_code} and connector {integration_name}",
                )

            logger.info(f"Successfully retrieved network connector metadata for {customer_code}/{integration_name}")

        else:
            # Fetch from regular integrations table
            stmt = select(CustomerIntegrationsMeta).where(
                CustomerIntegrationsMeta.customer_code == customer_code,
                CustomerIntegrationsMeta.integration_name == integration_name,
            )
            result = await session.execute(stmt)
            meta_record = result.scalars().first()

            if not meta_record:
                raise HTTPException(
                    status_code=404,
                    detail=f"Integration metadata not found for customer {customer_code} and integration {integration_name}",
                )

            logger.info(f"Successfully retrieved integration metadata for {customer_code}/{integration_name}")

        # Convert SQLModel to dict for response
        return {
            "success": True,
            "message": f"Successfully retrieved metadata for {customer_code}/{integration_name}",
            "data": meta_record.dict() if hasattr(meta_record, "dict") else meta_record.__dict__,
            "table_type": "network_connector" if is_network_integration else "integration",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@integration_settings_router.put(
    "/update_meta_auto",
    response_model=UpdateMetaResponse,
    description="Automatically update integration or network connector metadata based on integration name",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_meta_auto(
    update_request: UpdateMetaAutoRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Automatically determine which table to update based on integration name.

    This route checks if the integration is in the NETWORK_INTEGRATIONS list and
    updates the appropriate table accordingly.
    """
    is_network_integration = update_request.integration_name in NETWORK_INTEGRATIONS

    try:
        if is_network_integration:
            # Check if record exists in network connectors table
            stmt = select(CustomerNetworkConnectorsMeta).where(
                CustomerNetworkConnectorsMeta.customer_code == update_request.customer_code,
                CustomerNetworkConnectorsMeta.network_connector_name == update_request.integration_name,
            )
            result = await session.execute(stmt)
            existing_record = result.scalars().first()

            if not existing_record:
                raise HTTPException(
                    status_code=404,
                    detail=f"Network connector metadata not found for customer {update_request.customer_code} and connector {update_request.integration_name}",
                )

            # Update network connector metadata
            update_data = {}
            if update_request.graylog_input_id is not None:
                update_data["graylog_input_id"] = update_request.graylog_input_id
            if update_request.graylog_index_id is not None:
                update_data["graylog_index_id"] = update_request.graylog_index_id
            if update_request.graylog_stream_id is not None:
                update_data["graylog_stream_id"] = update_request.graylog_stream_id
            if update_request.graylog_pipeline_id is not None:
                update_data["graylog_pipeline_id"] = update_request.graylog_pipeline_id
            if update_request.graylog_content_pack_input_id is not None:
                update_data["graylog_content_pack_input_id"] = update_request.graylog_content_pack_input_id
            if update_request.graylog_content_pack_stream_id is not None:
                update_data["graylog_content_pack_stream_id"] = update_request.graylog_content_pack_stream_id
            if update_request.grafana_org_id is not None:
                update_data["grafana_org_id"] = update_request.grafana_org_id
            if update_request.grafana_dashboard_folder_id is not None:
                update_data["grafana_dashboard_folder_id"] = update_request.grafana_dashboard_folder_id
            if update_request.grafana_datasource_uid is not None:
                update_data["grafana_datasource_uid"] = update_request.grafana_datasource_uid

            if update_data:
                update_stmt = (
                    update(CustomerNetworkConnectorsMeta)
                    .where(
                        CustomerNetworkConnectorsMeta.customer_code == update_request.customer_code,
                        CustomerNetworkConnectorsMeta.network_connector_name == update_request.integration_name,
                    )
                    .values(**update_data)
                )
                await session.execute(update_stmt)

        else:
            # Check if record exists in integrations table
            stmt = select(CustomerIntegrationsMeta).where(
                CustomerIntegrationsMeta.customer_code == update_request.customer_code,
                CustomerIntegrationsMeta.integration_name == update_request.integration_name,
            )
            result = await session.execute(stmt)
            existing_record = result.scalars().first()

            if not existing_record:
                raise HTTPException(
                    status_code=404,
                    detail=f"Integration metadata not found for customer {update_request.customer_code} and integration {update_request.integration_name}",
                )

            # Update regular integration metadata
            update_data = {}
            if update_request.graylog_input_id is not None:
                update_data["graylog_input_id"] = update_request.graylog_input_id
            if update_request.graylog_index_id is not None:
                update_data["graylog_index_id"] = update_request.graylog_index_id
            if update_request.graylog_stream_id is not None:
                update_data["graylog_stream_id"] = update_request.graylog_stream_id
            if update_request.grafana_org_id is not None:
                update_data["grafana_org_id"] = update_request.grafana_org_id
            if update_request.grafana_dashboard_folder_id is not None:
                update_data["grafana_dashboard_folder_id"] = update_request.grafana_dashboard_folder_id
            if update_request.grafana_datasource_uid is not None:
                update_data["grafana_datasource_uid"] = update_request.grafana_datasource_uid

            if update_data:
                update_stmt = (
                    update(CustomerIntegrationsMeta)
                    .where(
                        CustomerIntegrationsMeta.customer_code == update_request.customer_code,
                        CustomerIntegrationsMeta.integration_name == update_request.integration_name,
                    )
                    .values(**update_data)
                )
                await session.execute(update_stmt)

        if not update_data:
            return UpdateMetaResponse(success=False, message="No fields provided for update")

        await session.commit()

        table_type = "network connector" if is_network_integration else "integration"
        logger.info(
            f"Updated {table_type} metadata for customer {update_request.customer_code}, {table_type} {update_request.integration_name}",
        )

        return UpdateMetaResponse(
            success=True,
            message=f"Successfully updated {table_type} metadata for {update_request.customer_code}/{update_request.integration_name}",
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
