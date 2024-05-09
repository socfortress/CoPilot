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
from app.db.db_session import get_db
from app.db.universal_models import Customers
from app.db.universal_models import CustomersMeta
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)
from app.network_connectors.models.network_connectors import AvailableNetworkConnectors
from app.network_connectors.models.network_connectors import CustomerNetworkConnectors
from app.network_connectors.models.network_connectors import (
    CustomerNetworkConnectorsMeta,
)
from app.network_connectors.models.network_connectors import NetworkConnectorsConfig
from app.network_connectors.models.network_connectors import NetworkConnectorsKeys
from app.network_connectors.models.network_connectors import NetworkConnectorsService
from app.network_connectors.models.network_connectors import (
    NetworkConnectorsSubscription,
)
from app.network_connectors.schema import AuthKey
from app.network_connectors.schema import AvailableNetworkConnectorsResponse
from app.network_connectors.schema import CreateNetworkConnectorsAuthKeys
from app.network_connectors.schema import CreateNetworkConnectorsService
from app.network_connectors.schema import CustomerNetworkConnectorsCreate
from app.network_connectors.schema import CustomerNetworkConnectorsCreateResponse
from app.network_connectors.schema import CustomerNetworkConnectorsDeleteResponse
from app.network_connectors.schema import CustomerNetworkConnectorsMetaResponse
from app.network_connectors.schema import CustomerNetworkConnectorsMetaSchema
from app.network_connectors.schema import CustomerNetworkConnectorsResponse
from app.network_connectors.schema import DeleteCustomerNetworkConnectors
from app.network_connectors.schema import NetworkConnectorsWithAuthKeys
from app.network_connectors.schema import UpdateCustomerNetworkConnectors

network_connector_settings_router = APIRouter()


async def fetch_available_network_connectors(session: AsyncSession):
    """
    Fetches available network_connectors and their auth keys from the database.

    Args:
        session (AsyncSession): The database session.

    Returns:
        List[NetworkConnectorsWithAuthKeys]: A list of available network_connectors with their auth keys.
    """
    stmt = select(AvailableNetworkConnectors).options(
        joinedload(AvailableNetworkConnectors.network_connector_keys),
    )
    result = await session.execute(stmt)

    # Use unique() to avoid duplicates caused by joined eager loading
    unique_network_connectors = result.unique().scalars().all()

    network_connectors_with_auth_keys = []
    for network_connector in unique_network_connectors:
        auth_keys = [AuthKey(auth_key_name=key.auth_key_name) for key in network_connector.network_connector_keys]
        network_connector_data = NetworkConnectorsWithAuthKeys(
            id=network_connector.id,
            network_connector_name=network_connector.network_connector_name,
            description=network_connector.description,
            network_connector_details=network_connector.network_connector_details,
            network_connector_keys=auth_keys,
        )
        network_connectors_with_auth_keys.append(network_connector_data)

    return network_connectors_with_auth_keys


async def validate_network_connector_name(network_connector_name: str, session: AsyncSession):
    """
    Validate if the network_connector name exists in available network_connectors.
    """
    available_network_connectors = await fetch_available_network_connectors(session)
    if network_connector_name not in [ai.network_connector_name for ai in available_network_connectors]:
        raise HTTPException(
            status_code=400,
            detail=f"NetworkConnectors {network_connector_name} is not a valid network_connector.",
        )


async def validate_network_connector_auth_keys(
    network_connector_name: str,
    network_connector_auth_keys: List[AuthKey],
    session: AsyncSession,
):
    """
    Validate if the network_connector auth keys are valid.
    """
    available_network_connectors = await fetch_available_network_connectors(session)
    network_connector = [ai for ai in available_network_connectors if ai.network_connector_name == network_connector_name][0]
    available_auth_keys = [ak.auth_key_name for ak in network_connector.network_connector_keys]
    # loop through the `available_auth_keys` and check if the `network_connector_auth_keys` contains the `auth_key_name`
    for auth_key in available_auth_keys:
        if auth_key not in [iak.auth_key_name for iak in network_connector_auth_keys]:
            raise HTTPException(
                status_code=400,
                detail=f"NetworkConnectors auth key {auth_key} does not exist.",
            )


async def validate_network_connector_auth_key_update(
    network_connector_name: str,
    network_connector_auth_key: List[AuthKey],
    session: AsyncSession,
):
    """
    Validate if the network_connector auth key is valid.
    """
    logger.info(f"network_connector_auth_key: {network_connector_auth_key}")
    available_network_connectors = await fetch_available_network_connectors(session)
    network_connector = [ai for ai in available_network_connectors if ai.network_connector_name == network_connector_name][0]
    available_auth_keys = [ak.auth_key_name for ak in network_connector.auth_keys]
    for auth_key in network_connector_auth_key:
        if auth_key.auth_key_name not in available_auth_keys:
            raise HTTPException(
                status_code=400,
                detail=f"NetworkConnectors auth key {auth_key.auth_key_name} does not exist.",
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
            detail=f"Customer {customer_code} meta does not exist. Please provision the customer before creating an network_connector.",
        )


async def check_existing_customer_network_connector(
    customer_code: str,
    network_connector_name: str,
    session: AsyncSession,
):
    """
    Check if the customer network_connector already exists.
    """
    # Assuming NetworkConnectorsService has an 'network_connector_name' field or similar
    stmt = (
        select(CustomerNetworkConnectors)
        .join(CustomerNetworkConnectors.network_connectors_subscriptions)
        .join(NetworkConnectorsSubscription.network_connectors_service)
        .where(
            CustomerNetworkConnectors.customer_code == customer_code,
            NetworkConnectorsService.service_name == network_connector_name,
        )
    )
    result = await session.execute(stmt)
    if result.scalars().first() is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Customer network_connector {customer_code} {network_connector_name} already exists.",
        )


async def check_existing_customer_network_connector_meta(
    customer_code: str,
    network_connector_name: str,
    session: AsyncSession,
):
    """
    Check if the customer network_connector meta already exists for the customer code and network_connector name.
    """
    stmt = select(CustomerNetworkConnectorsMeta).where(
        CustomerNetworkConnectorsMeta.customer_code == customer_code,
        CustomerNetworkConnectorsMeta.network_connector_name == network_connector_name,
    )
    result = await session.execute(stmt)
    if result.scalars().first() is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Customer network_connector meta {customer_code} {network_connector_name} already exists.",
        )


async def create_network_connector_service(
    network_connector_name: str,
    settings: CreateNetworkConnectorsService,
    session: AsyncSession,
) -> NetworkConnectorsService:
    """
    Create or fetch NetworkConnectorsService instance with custom configuration.
    """
    network_connector_service = NetworkConnectorsService(
        service_name=network_connector_name,
        auth_type=settings.auth_type,
        configs=[
            NetworkConnectorsConfig(
                config_key=settings.config_key,
                config_value=settings.config_value,
            ),
        ],
    )
    session.add(network_connector_service)
    await session.flush()
    return network_connector_service


async def create_customer_network_connectors(
    customer_code: str,
    customer_name: str,
    network_connector_service_id: int,
    network_connector_service_name: str,
    session: AsyncSession,
) -> CustomerNetworkConnectors:
    """
    Create CustomerNetworkConnectors instance.
    """
    customer_network_connectors = CustomerNetworkConnectors(
        customer_code=customer_code,
        customer_name=customer_name,
        network_connector_service_id=network_connector_service_id,
        network_connector_service_name=network_connector_service_name,
        deployed=False,
    )
    session.add(customer_network_connectors)
    await session.flush()
    return customer_network_connectors


async def create_network_connector_subscription(
    customer_network_connectors: CustomerNetworkConnectors,
    network_connector_service: NetworkConnectorsService,
    network_connector_auth_keys: List[CreateNetworkConnectorsAuthKeys],
    session: AsyncSession,
):
    """
    Create NetworkConnectorsSubscription instance.
    """
    for auth_key in network_connector_auth_keys:
        new_network_connector_subscription = NetworkConnectorsSubscription(
            customer_network_connectors=customer_network_connectors,
            network_connectors_service=network_connector_service,
            network_connectors_keys=[
                NetworkConnectorsKeys(
                    auth_key_name=auth_key.auth_key_name,
                    auth_value=auth_key.auth_value,
                ),
            ],
        )
        session.add(new_network_connector_subscription)
        await session.commit()


async def get_customer_and_service_ids(session, customer_code, network_connector_name):
    try:
        result = await session.execute(
            select(CustomerNetworkConnectors.id, NetworkConnectorsService.id)
            .join(
                NetworkConnectorsSubscription,
                CustomerNetworkConnectors.id == NetworkConnectorsSubscription.customer_id,
            )
            .join(
                NetworkConnectorsService,
                NetworkConnectorsSubscription.network_connectors_service_id == NetworkConnectorsService.id,
            )
            .where(
                CustomerNetworkConnectors.customer_code == customer_code,
                NetworkConnectorsService.service_name == network_connector_name,
            ),
        )
        return result.all()
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Customer network_connector not found")


async def get_subscription_ids(session, customer_id, network_connector_service_id):
    result = await session.execute(
        select(NetworkConnectorsSubscription.id).where(
            NetworkConnectorsSubscription.customer_id == customer_id,
            NetworkConnectorsSubscription.network_connectors_service_id == network_connector_service_id,
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
        delete(NetworkConnectorsKeys).where(
            NetworkConnectorsKeys.subscription_id.in_(subscription_ids),
        ),
    )


async def delete_subscriptions(session, subscription_ids):
    await session.execute(
        delete(NetworkConnectorsSubscription).where(
            NetworkConnectorsSubscription.id.in_(subscription_ids),
        ),
    )


async def delete_configs(session, network_connector_service_id):
    await session.execute(
        delete(NetworkConnectorsConfig).where(
            NetworkConnectorsConfig.network_connector_service_id == network_connector_service_id,
        ),
    )


async def delete_network_connector_service(session, network_connector_service_id):
    await session.execute(
        delete(NetworkConnectorsService).where(
            NetworkConnectorsService.id == network_connector_service_id,
        ),
    )


async def delete_customer_network_connector_record(session, customer_id):
    await session.execute(
        delete(CustomerNetworkConnectors).where(CustomerNetworkConnectors.id == customer_id),
    )


async def find_customer_network_connector(
    customer_code: str,
    network_connector_name: str,
    customer_network_connector_response,
) -> Optional[CustomerNetworkConnectors]:
    for ci in customer_network_connector_response.available_network_connectors:
        for subscription in ci.network_connectors_subscriptions:
            if subscription.network_connectors_service.service_name == network_connector_name:
                return ci
    return None


def get_subscription_id(
    customer_network_connector,
    network_connector_name: str,
    auth_key_name: str,
) -> Optional[int]:
    logger.info(f"Getting subscription id for {network_connector_name} {auth_key_name}")
    for subscription in customer_network_connector.network_connectors_subscriptions:
        if subscription.network_connectors_service.service_name == network_connector_name:
            for auth_key in subscription.network_connector_keys:
                if auth_key.auth_key_name == auth_key_name:
                    return subscription.id
    return None


async def get_tenant_id(
    customer_network_connector: CustomerNetworkConnectorsCreate,
    session: AsyncSession,
) -> str:
    """
    Retrieves the Tenant ID for a given customer network_connector. This is the Office365 organization ID and
    is used to create alerts for the customer in DFIR-IRIS.
    """
    stmt = (
        select(NetworkConnectorsKeys)
        .join(
            NetworkConnectorsSubscription,
            NetworkConnectorsKeys.subscription_id == NetworkConnectorsSubscription.id,
        )
        .join(
            CustomerNetworkConnectors,
            NetworkConnectorsSubscription.customer_id == CustomerNetworkConnectors.id,
        )
        .join(
            NetworkConnectorsService,
            NetworkConnectorsSubscription.network_connector_service_id == NetworkConnectorsService.id,
        )
        .where(
            CustomerNetworkConnectors.customer_code == customer_network_connector.customer_code,
            NetworkConnectorsService.service_name == customer_network_connector.network_connector_name,
            NetworkConnectorsKeys.auth_key_name == "TENANT_ID",
        )
    )

    result = await session.execute(stmt)
    tenant_id = result.scalars().first()
    if tenant_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tenant ID for customer {customer_network_connector.customer_code} not found.",
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


async def get_network_connector_service_id(
    network_connector_name: str,
    session: AsyncSession,
) -> int:
    """
    Retrieves the AvailableNetworkConnectorss ID for a given network_connector name.
    """
    stmt = select(AvailableNetworkConnectors).where(
        AvailableNetworkConnectors.network_connector_name == network_connector_name,
    )
    result = await session.execute(stmt)
    network_connector_service = result.scalars().first()
    if network_connector_service is None:
        raise HTTPException(
            status_code=404,
            detail=f"NetworkConnectors service {network_connector_name} not found.",
        )
    return network_connector_service.id


async def get_network_connector_service_name(
    network_connector_name: str,
    session: AsyncSession,
) -> str:
    """
    Retrieves the AvailableNetworkConnectors ID for a given network_connector name.
    """
    stmt = select(AvailableNetworkConnectors).where(
        AvailableNetworkConnectors.network_connector_name == network_connector_name,
    )
    result = await session.execute(stmt)
    network_connector_service = result.scalars().first()
    if network_connector_service is None:
        raise HTTPException(
            status_code=404,
            detail=f"NetworkConnectors service {network_connector_name} not found.",
        )
    return network_connector_service.network_connector_name


async def fetch_customer_network_connectors_data(session: AsyncSession):
    """
    Fetches customer network_connectors data from the database.
    """
    stmt = select(CustomerNetworkConnectors).options(
        joinedload(CustomerNetworkConnectors.network_connectors_subscriptions).joinedload(
            NetworkConnectorsSubscription.network_connectors_service,
        ),
        joinedload(CustomerNetworkConnectors.network_connectors_subscriptions).subqueryload(
            NetworkConnectorsSubscription.network_connectors_keys,
        ),
    )
    result = await session.execute(stmt)
    return result.scalars().unique().all()


def process_customer_network_connectors(customer_network_connectors_data):
    """
    Processes customer network_connectors data and returns a list of CustomerNetworkConnectors objects.
    """
    processed_customer_network_connectors = []
    for ci in customer_network_connectors_data:
        first_service_id = (
            ci.network_connectors_subscriptions[0].network_connectors_service_id if ci.network_connectors_subscriptions else None
        )
        customer_network_connector_obj = CustomerNetworkConnectors(
            id=ci.id,
            customer_code=ci.customer_code,
            customer_name=ci.customer_name,
            network_connectors_subscriptions=ci.network_connectors_subscriptions,
            network_connector_service_id=first_service_id,
            network_connector_service_name=ci.network_connectors_subscriptions[0].network_connectors_service.service_name
            if ci.network_connectors_subscriptions
            else None,
            deployed=ci.deployed,
        )
        processed_customer_network_connectors.append(customer_network_connector_obj)
    return processed_customer_network_connectors


@network_connector_settings_router.get(
    "/available_network_connectors",
    response_model=AvailableNetworkConnectorsResponse,
    description="Get a list of available network_connectors.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_available_network_connectors(
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to get a list of available network_connectors.
    """
    available_network_connectors = await fetch_available_network_connectors(session)
    return AvailableNetworkConnectorsResponse(
        network_connector_keys=available_network_connectors,
        message="Available network_connectors successfully retrieved.",
        success=True,
    )


@network_connector_settings_router.get(
    "/customer_network_connectors",
    response_model=CustomerNetworkConnectorsResponse,
    description="Get a list of customer network_connectors.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_network_connectors(session: AsyncSession = Depends(get_db)):
    """
    Endpoint to get a list of customer network_connectors.
    """
    customer_network_connectors_data = await fetch_customer_network_connectors_data(session)
    processed_customer_network_connectors = process_customer_network_connectors(
        customer_network_connectors_data,
    )

    return CustomerNetworkConnectorsResponse(
        available_network_connectors=processed_customer_network_connectors,
        message="Customer network_connectors successfully retrieved.",
        success=True,
    )


@network_connector_settings_router.get(
    "/customer_network_connectors_meta",
    response_model=CustomerNetworkConnectorsMetaResponse,
    description="Get a list of customer network_connectors metadata.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_network_connectors_meta(session: AsyncSession = Depends(get_db)):
    """
    Endpoint to get a list of customer network_connectors metadata.
    """
    try:
        stmt = select(CustomerNetworkConnectorsMeta)
        result = await session.execute(stmt)
        customer_network_connectors_meta = result.scalars().all()
    except Exception as e:
        logger.error(f"Error while fetching customer network_connectors metadata: {e}")
        customer_network_connectors_meta = []

    logger.info(f"customer_network_connectors_meta: {customer_network_connectors_meta}")
    return CustomerNetworkConnectorsMetaResponse(
        customer_network_connectors_meta=customer_network_connectors_meta,
        message="Customer network_connectors metadata successfully retrieved.",
        success=True,
    )


@network_connector_settings_router.get(
    "/customer_network_connectors/{customer_code}",
    response_model=CustomerNetworkConnectorsResponse,
    description="Get a list of customer network_connectors for a specific customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_network_connectors_by_customer_code(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to get a list of customer network_connectors for a specific customer.
    """
    stmt = (
        select(CustomerNetworkConnectors)
        .options(
            joinedload(CustomerNetworkConnectors.network_connectors_subscriptions).joinedload(
                NetworkConnectorsSubscription.network_connectors_service,
            ),
            joinedload(CustomerNetworkConnectors.network_connectors_subscriptions).subqueryload(
                NetworkConnectorsSubscription.network_connectors_keys,
            ),
        )
        .where(CustomerNetworkConnectors.customer_code == customer_code)
    )
    result = await session.execute(stmt)
    customer_network_connectors = result.scalars().unique().all()
    return CustomerNetworkConnectorsResponse(
        available_network_connectors=customer_network_connectors,
        message="Customer network_connectors successfully retrieved.",
        success=True,
    )


@network_connector_settings_router.get(
    "/customer_network_connectors_meta/{customer_code}",
    response_model=CustomerNetworkConnectorsMetaResponse,
    description="Get a list of customer network_connectors metadata for a specific customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_network_connectors_meta_by_customer_code(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to get a list of customer network_connectors metadata for a specific customer.
    """
    stmt = select(CustomerNetworkConnectorsMeta).where(
        CustomerNetworkConnectorsMeta.customer_code == customer_code,
    )
    result = await session.execute(stmt)
    customer_network_connectors_meta = result.scalars().all()
    logger.info(f"customer_network_connectors_meta: {customer_network_connectors_meta}")
    return CustomerNetworkConnectorsMetaResponse(
        customer_network_connectors_meta=customer_network_connectors_meta,
        message="Customer network_connectors metadata successfully retrieved.",
        success=True,
    )


@network_connector_settings_router.post(
    "/create_network_connector",
    response_model=CustomerNetworkConnectorsCreateResponse,
    description="Create a new customer network_connector.",
    # dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_network_connector(
    customer_network_connector_create: CustomerNetworkConnectorsCreate,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to create a new customer network_connector.
    """
    await validate_network_connector_name(
        customer_network_connector_create.network_connector_name,
        session,
    )
    await validate_network_connector_auth_keys(
        customer_network_connector_create.network_connector_name,
        customer_network_connector_create.network_connector_auth_keys,
        session,
    )
    await validate_customer_code(customer_network_connector_create.customer_code, session)
    await validate_customer_meta(customer_network_connector_create.customer_code, session)
    await check_existing_customer_network_connector(
        customer_network_connector_create.customer_code,
        customer_network_connector_create.network_connector_name,
        session,
    )
    network_connector_service_id = await get_network_connector_service_id(
        customer_network_connector_create.network_connector_name,
        session,
    )
    network_connector_service_name = await get_network_connector_service_name(
        customer_network_connector_create.network_connector_name,
        session,
    )

    network_connector_service = await create_network_connector_service(
        customer_network_connector_create.network_connector_name,
        settings=customer_network_connector_create.network_connector_config,
        session=session,
    )
    customer_network_connectors = await create_customer_network_connectors(
        customer_network_connector_create.customer_code,
        customer_network_connector_create.customer_name,
        network_connector_service_id=network_connector_service_id,
        network_connector_service_name=network_connector_service_name,
        session=session,
    )
    logger.info("Getting customer network_connector auth keys for subscription creation.")
    logger.info(f"Customer Network Connectors: {customer_network_connectors}")
    await create_network_connector_subscription(
        customer_network_connectors,
        network_connector_service,
        network_connector_auth_keys=customer_network_connector_create.network_connector_auth_keys,
        session=session,
    )

    return CustomerNetworkConnectorsCreateResponse(
        message=f"Customer network_connector {customer_network_connector_create.customer_code} {customer_network_connector_create.network_connector_name} successfully created.",
        success=True,
    )


@network_connector_settings_router.post(
    "/create_network_connector_meta",
    response_model=CustomerNetworkConnectorsMetaResponse,
    description="Create a new customer network_connector metadata.",
    # dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_network_connector_meta(
    customer_network_connector_meta: CustomerNetworkConnectorsMetaSchema,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to create a new customer network_connector metadata.
    """
    await validate_customer_code(customer_network_connector_meta.customer_code, session)
    await validate_customer_meta(customer_network_connector_meta.customer_code, session)
    await check_existing_customer_network_connector_meta(
        customer_network_connector_meta.customer_code,
        customer_network_connector_meta.network_connector_name,
        session,
    )
    try:
        new_customer_network_connector_meta = CustomerNetworkConnectorsMeta(
            **customer_network_connector_meta.dict(),
        )
        session.add(new_customer_network_connector_meta)
        await session.commit()
        return CustomerNetworkConnectorsMetaResponse(
            message="Customer network_connector metadata successfully created.",
            success=True,
        )
    except Exception as e:
        logger.error(f"Error while creating customer network_connector metadata: {e}")
        return CustomerNetworkConnectorsMetaResponse(
            customer_network_connectors_meta=None,
            message="Error while creating customer network_connector metadata.",
            success=False,
        )


@network_connector_settings_router.put(
    "/update_network_connector/{customer_code}",
    response_model=CustomerNetworkConnectorsCreateResponse,
    description="Update a customer network_connector.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_network_connector(
    customer_code: str,
    customer_network_connector_update: UpdateCustomerNetworkConnectors,
    session: AsyncSession = Depends(get_db),
):
    await validate_network_connector_name(
        customer_network_connector_update.network_connector_name,
        session,
    )
    customer_network_connector_response = await get_customer_network_connectors_by_customer_code(
        customer_code,
        session,
    )

    if not customer_network_connector_response:
        raise HTTPException(status_code=404, detail="Customer network_connectors not found")

    customer_network_connector = await find_customer_network_connector(
        customer_code,
        customer_network_connector_update.network_connector_name,
        customer_network_connector_response,
    )

    if not customer_network_connector:
        raise HTTPException(
            status_code=404,
            detail="Customer network_connector with specified service name not found.",
        )

    await validate_network_connector_auth_key_update(
        customer_network_connector_update.network_connector_name,
        customer_network_connector_update.network_connector_auth_keys,
        session,
    )

    subscription_id = get_subscription_id(
        customer_network_connector,
        customer_network_connector_update.network_connector_name,
        customer_network_connector_update.network_connector_auth_keys[0].auth_key_name,
    )

    if not subscription_id:
        raise HTTPException(
            status_code=404,
            detail=f"NetworkConnectors auth key {customer_network_connector_update.network_connector_auth_keys[0].auth_key_name} not found.",
        )

    await session.execute(
        update(NetworkConnectorsKeys)
        .where(NetworkConnectorsKeys.subscription_id == subscription_id)
        .values(
            auth_value=customer_network_connector_update.network_connector_auth_keys[0].auth_value,
        ),
    )

    await session.commit()

    return CustomerNetworkConnectorsCreateResponse(
        message=f"Customer network_connector {customer_code} {customer_network_connector_update.network_connector_name} successfully updated.",
        success=True,
    )


@network_connector_settings_router.put(
    "/available_network_connectors",
    response_model=AvailableNetworkConnectorsResponse,
    description="Update an available network_connector.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_available_network_connectors(
    available_network_connectors: List[AvailableNetworkConnectors],
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to update an available network_connector.
    """
    for network_connector in available_network_connectors:
        stmt = select(AvailableNetworkConnectors).where(
            AvailableNetworkConnectors.network_connector_name == network_connector.network_connector_name,
        )
        result = await session.execute(stmt)
        existing_network_connector = result.scalars().first()

        if existing_network_connector is None:
            raise HTTPException(
                status_code=404,
                detail=f"NetworkConnectors {network_connector.network_connector_name} not found.",
            )

        existing_network_connector.description = network_connector.description
        existing_network_connector.network_connector_details = network_connector.network_connector_details

    await session.commit()

    return AvailableNetworkConnectorsResponse(
        available_network_connectors=available_network_connectors,
        message="Available network_connectors successfully updated.",
        success=True,
    )


@network_connector_settings_router.delete(
    "/delete_network_connector",
    response_model=CustomerNetworkConnectorsDeleteResponse,
    description="Delete a customer network_connector.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_network_connector(
    delete_customer_network_connector: DeleteCustomerNetworkConnectors,
    session: AsyncSession = Depends(get_db),
):
    customer_code = delete_customer_network_connector.customer_code
    network_connector_name = delete_customer_network_connector.network_connector_name

    results = await get_customer_and_service_ids(
        session,
        customer_code,
        network_connector_name,
    )
    # Check if results is not empty
    if results:
        # Unpack the first tuple in results
        customer_id, network_connector_service_id = results[0]
    else:
        # Handle the case where results is empty
        raise HTTPException(status_code=404, detail="Customer network_connector not found")

    subscription_ids = await get_subscription_ids(
        session,
        customer_id,
        network_connector_service_id,
    )
    if not subscription_ids:
        raise HTTPException(
            status_code=404,
            detail="No subscriptions found for customer network_connector",
        )

    await delete_metadata(session, subscription_ids)
    await delete_subscriptions(session, subscription_ids)
    await delete_configs(session, network_connector_service_id)
    await delete_network_connector_service(session, network_connector_service_id)
    await delete_customer_network_connector_record(session, customer_id)

    await session.commit()

    return CustomerNetworkConnectorsDeleteResponse(
        message=f"Customer network_connector {customer_code} {network_connector_name} successfully deleted.",
        success=True,
    )


@network_connector_settings_router.delete(
    "/delete_network_connector_meta",
    response_model=CustomerNetworkConnectorsMetaResponse,
    description="Delete a customer network_connector metadata.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_network_connector_meta(
    customer_network_connector_meta: CustomerNetworkConnectorsMetaSchema,
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to delete a customer network_connector metadata.
    """
    try:
        stmt = delete(CustomerNetworkConnectorsMeta).where(
            CustomerNetworkConnectorsMeta.customer_code == customer_network_connector_meta.customer_code,
            CustomerNetworkConnectorsMeta.network_connector_name == customer_network_connector_meta.network_connector_name,
        )
        await session.execute(stmt)
        await session.commit()
        return CustomerNetworkConnectorsMetaResponse(
            message="Customer network_connector metadata successfully deleted.",
            success=True,
        )
    except Exception as e:
        logger.error(f"Error while deleting customer network_connector metadata: {e}")
        return CustomerNetworkConnectorsMetaResponse(
            customer_network_connectors_meta=None,
            message="Error while deleting customer network_connector metadata.",
            success=False,
        )
