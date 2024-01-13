from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import NoResultFound
from sqlalchemy import delete

from app.db.db_session import get_db
from app.integrations.models.customer_integration_settings import (
    CustomerIntegrations,
)
from app.integrations.models.customer_integration_settings import (
    IntegrationService,
)
from app.integrations.models.customer_integration_settings import (
    IntegrationSubscription,
)
from app.integrations.models.customer_integration_settings import (
    IntegrationConfig,
)
from app.integrations.models.customer_integration_settings import (
    IntegrationMetadata, AvailableIntegrations
)
from app.db.universal_models import Customers
from app.integrations.schema import AvailableIntegrationsResponse, CustomerIntegrationCreate, CreateIntegrationService, CreateIntegrationMetadata, CustomerIntegrationCreateResponse, CustomerIntegrationsResponse, DeleteCustomerIntegration, CustomerIntegrationDeleteResponse

integration_settings_router = APIRouter()

async def fetch_available_integrations(session: AsyncSession):
    """
    Fetches available integrations from the database.

    Args:
        session (AsyncSession): The database session.

    Returns:
        List[AvailableIntegrations]: A list of available integrations.
    """
    stmt = select(AvailableIntegrations)
    result = await session.execute(stmt)
    return result.scalars().all()

async def validate_integration_name(integration_name: str, session: AsyncSession):
    """
    Validate if the integration name exists in available integrations.
    """
    available_integrations = await fetch_available_integrations(session)
    if integration_name not in [ai.integration_name for ai in available_integrations]:
        raise HTTPException(status_code=400, detail=f"Integration {integration_name} does not exist.")

async def validate_customer_code(customer_code: str, session: AsyncSession):
    """
    Validate if the customer code exists in the customers table.
    """
    stmt = select(Customers).where(Customers.customer_code == customer_code)
    result = await session.execute(stmt)
    if result.scalars().first() is None:
        raise HTTPException(status_code=400, detail=f"Customer {customer_code} does not exist.")

async def check_existing_customer_integration(customer_code: str, integration_name: str, session: AsyncSession):
    """
    Check if the customer integration already exists.
    """
    # Assuming IntegrationService has an 'integration_name' field or similar
    stmt = select(CustomerIntegrations).join(CustomerIntegrations.integration_subscriptions).join(IntegrationSubscription.integration_service).where(
        CustomerIntegrations.customer_code == customer_code,
        IntegrationService.service_name == integration_name
    )
    result = await session.execute(stmt)
    if result.scalars().first() is not None:
        raise HTTPException(status_code=400, detail=f"Customer integration {customer_code} {integration_name} already exists.")

async def create_integration_service(integration_name: str, settings: CreateIntegrationService, session: AsyncSession) -> IntegrationService:
    """
    Create or fetch IntegrationService instance with custom configuration.
    """
    integration_service = IntegrationService(
        service_name=integration_name,
        auth_type=settings.auth_type,
        configs=[IntegrationConfig(config_key=settings.config_key, config_value=settings.config_value)]
    )
    session.add(integration_service)
    await session.flush()
    return integration_service

async def create_customer_integrations(customer_code: str, customer_name: str, session: AsyncSession) -> CustomerIntegrations:
    """
    Create CustomerIntegrations instance.
    """
    customer_integrations = CustomerIntegrations(
        customer_code=customer_code,
        customer_name=customer_name,
    )
    session.add(customer_integrations)
    await session.flush()
    return customer_integrations

async def create_integration_subscription(customer_integrations: CustomerIntegrations, integration_service: IntegrationService, integration_metadata: CreateIntegrationMetadata, session: AsyncSession):
    """
    Create IntegrationSubscription instance.
    """
    new_integration_subscription = IntegrationSubscription(
        customer_integrations=customer_integrations,
        integration_service=integration_service,
        integration_metadata=[IntegrationMetadata(metadata_key=integration_metadata.metadata_key, metadata_value=integration_metadata.metadata_value)]
    )
    session.add(new_integration_subscription)
    await session.commit()

async def get_customer_and_service_ids(session, customer_code, integration_name):
    try:
        result = await session.execute(
            select(CustomerIntegrations.id, IntegrationService.id)
            .join(IntegrationSubscription, CustomerIntegrations.id == IntegrationSubscription.customer_id)
            .join(IntegrationService, IntegrationSubscription.integration_service_id == IntegrationService.id)
            .where(CustomerIntegrations.customer_code == customer_code,
                   IntegrationService.service_name == integration_name)
        )
        return result.one()
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Customer integration not found")

async def get_subscription_ids(session, customer_id, integration_service_id):
    result = await session.execute(
        select(IntegrationSubscription.id)
        .where(IntegrationSubscription.customer_id == customer_id,
               IntegrationSubscription.integration_service_id == integration_service_id)
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
        delete(IntegrationMetadata)
        .where(IntegrationMetadata.subscription_id.in_(subscription_ids))
    )

async def delete_subscriptions(session, subscription_ids):
    await session.execute(
        delete(IntegrationSubscription)
        .where(IntegrationSubscription.id.in_(subscription_ids))
    )

async def delete_configs(session, integration_service_id):
    await session.execute(
        delete(IntegrationConfig)
        .where(IntegrationConfig.integration_service_id == integration_service_id)
    )

async def delete_integration_service(session, integration_service_id):
    await session.execute(
        delete(IntegrationService)
        .where(IntegrationService.id == integration_service_id)
    )

async def delete_customer_integration_record(session, customer_id):
    await session.execute(
        delete(CustomerIntegrations)
        .where(CustomerIntegrations.id == customer_id)
    )

@integration_settings_router.get(
    "/available_integrations",
    response_model=AvailableIntegrationsResponse,
    description="Get a list of available integrations."
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
    description="Get a list of customer integrations."
)
async def get_customer_integrations(
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to get a list of customer integrations.
    """
    stmt = (
        select(CustomerIntegrations)
        .options(
            joinedload(CustomerIntegrations.integration_subscriptions)
            .joinedload(IntegrationSubscription.integration_service),
            joinedload(CustomerIntegrations.integration_subscriptions)
            .subqueryload(IntegrationSubscription.integration_metadata)  # Load IntegrationMetadata
        )
    )
    result = await session.execute(stmt)
    customer_integrations = result.scalars().unique().all()
    return CustomerIntegrationsResponse(
        available_integrations=customer_integrations,
        message="Customer integrations successfully retrieved.",
        success=True,
    )

@integration_settings_router.get(
    "/customer_integrations/{customer_code}",
    response_model=CustomerIntegrationsResponse,
    description="Get a list of customer integrations for a specific customer."
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
            joinedload(CustomerIntegrations.integration_subscriptions)
            .joinedload(IntegrationSubscription.integration_service),
            joinedload(CustomerIntegrations.integration_subscriptions)
            .subqueryload(IntegrationSubscription.integration_metadata)  # Load IntegrationMetadata
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

@integration_settings_router.post(
    "/create_integration",
    response_model=CustomerIntegrationCreateResponse,
    description="Create a new customer integration."
)
async def create_integration(
    customer_integration_create: CustomerIntegrationCreate,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to create a new customer integration.
    """

    await validate_integration_name(customer_integration_create.integration_name, session)
    await validate_customer_code(customer_integration_create.customer_code, session)
    await check_existing_customer_integration(customer_integration_create.customer_code, customer_integration_create.integration_name, session)

    integration_service = await create_integration_service(customer_integration_create.integration_name, settings=customer_integration_create.integration_config, session=session)
    customer_integrations = await create_customer_integrations(customer_integration_create.customer_code, customer_integration_create.customer_name, session)
    await create_integration_subscription(customer_integrations, integration_service, integration_metadata=customer_integration_create.integration_metadata, session=session)

    return CustomerIntegrationCreateResponse(
        message=f"Customer integration {customer_integration_create.customer_code} {customer_integration_create.integration_name} successfully created.",
        success=True,
    )


@integration_settings_router.delete(
    "/delete_integration",
    response_model=CustomerIntegrationDeleteResponse,
    description="Delete a customer integration."
)
async def delete_integration(
    delete_customer_integration: DeleteCustomerIntegration,
    session: AsyncSession = Depends(get_db),
):
    customer_code = delete_customer_integration.customer_code
    integration_name = delete_customer_integration.integration_name

    customer_id, integration_service_id = await get_customer_and_service_ids(
        session, customer_code, integration_name
    )

    subscription_ids = await get_subscription_ids(session, customer_id, integration_service_id)
    if not subscription_ids:
        raise HTTPException(status_code=404, detail="No subscriptions found for customer integration")

    await delete_metadata(session, subscription_ids)
    await delete_subscriptions(session, subscription_ids)
    await delete_configs(session, integration_service_id)
    await delete_integration_service(session, integration_service_id)
    await delete_customer_integration_record(session, customer_id)

    await session.commit()

    return CustomerIntegrationDeleteResponse(
        message=f"Customer integration {customer_code} {integration_name} successfully deleted.",
        success=True,
    )

