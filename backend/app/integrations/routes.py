from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

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
from app.integrations.schema import AvailableIntegrationsResponse, CustomerIntegrationCreate, CreateIntegrationService, CreateIntegrationMetadata, CustomerIntegrationCreateResponse, CustomerIntegrationsResponse

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
    stmt = select(CustomerIntegrations).options(joinedload(CustomerIntegrations.integration_subscriptions).joinedload(IntegrationSubscription.integration_service))
    result = await session.execute(stmt)
    customer_integrations = result.scalars().unique().all()
    logger.info(customer_integrations)
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
    stmt = select(CustomerIntegrations).options(joinedload(CustomerIntegrations.integration_subscriptions).joinedload(IntegrationSubscription.integration_service)).where(CustomerIntegrations.customer_code == customer_code)
    result = await session.execute(stmt)
    customer_integrations = result.scalars().unique().all()
    logger.info(customer_integrations)
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

    integration_service = await create_integration_service(customer_integration_create.integration_name, settings=customer_integration_create.integration_details, session=session)
    customer_integrations = await create_customer_integrations(customer_integration_create.customer_code, customer_integration_create.customer_name, session)
    await create_integration_subscription(customer_integrations, integration_service, integration_metadata=customer_integration_create.integration_metadata, session=session)

    return CustomerIntegrationCreateResponse(
        message=f"Customer integration {customer_integration_create.customer_code} {customer_integration_create.integration_name} successfully created.",
        success=True,
    )
