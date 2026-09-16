from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import or_
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
from app.integrations.office365.services.decommission import (
    decommission_office365_tenant,
)
from app.integrations.office365.services.decommission import get_office365_tenant_id
from app.integrations.schema import AuthKey
from app.integrations.schema import AvailableIntegrationDetailResponse
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
from app.middleware.customer_access import verify_customer_code_access
from app.network_connectors.models.network_connectors import (
    CustomerNetworkConnectorsMeta,
)

integration_settings_router = APIRouter()

# Shown whenever a deployed integration has no metadata row — usually the result of a
# deployment that failed after the infrastructure was provisioned.
MISSING_META_RECOVERY_HINT = (
    "This usually means the deployment did not finish. You can record the metadata manually from the "
    "Meta Details panel, or delete the integration and deploy it again."
)

# Integrations a customer may configure more than once, each configuration distinguished by
# `CustomerIntegrations.instance_name`. The column and every lookup below are generic, but an
# integration only becomes multi-instance once its provisioning and decommission paths can cope
# with sharing a customer's infrastructure between instances — so opting one in is a deliberate
# act, not a default.
MULTI_INSTANCE_INTEGRATIONS = {
    "Office365",
}

NETWORK_INTEGRATIONS = [
    "DefenderForEndpoint",
    "BITDEFENDER",
    "CROWDSTRIKE",
    "FORTINET",
    "Fortinet",
    "Sonicwall",
    # Add other network integrations as needed
]


def _to_integration_with_auth_keys(integration: AvailableIntegrations) -> IntegrationWithAuthKeys:
    """Map an AvailableIntegrations ORM row (with auth_keys loaded) to its response schema."""
    return IntegrationWithAuthKeys(
        id=integration.id,
        integration_name=integration.integration_name,
        description=integration.description,
        integration_details=integration.integration_details,
        auth_keys=[AuthKey(auth_key_name=key.auth_key_name) for key in integration.auth_keys],
    )


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

    return [_to_integration_with_auth_keys(integration) for integration in unique_integrations]


async def fetch_available_integration_by_id(session: AsyncSession, integration_id: int) -> IntegrationWithAuthKeys:
    stmt = (
        select(AvailableIntegrations).options(joinedload(AvailableIntegrations.auth_keys)).where(AvailableIntegrations.id == integration_id)
    )
    result = await session.execute(stmt)
    integration = result.unique().scalar_one_or_none()
    if integration is None:
        raise HTTPException(status_code=404, detail=f"Integration {integration_id} not found")

    return _to_integration_with_auth_keys(integration)


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


def normalize_instance_name(instance_name: Optional[str]) -> Optional[str]:
    """
    Collapse an absent, empty or whitespace-only instance label to ``None``.

    ``None`` is the single unnamed instance every pre-existing row carries, so a form that posts
    an empty string must resolve to the same thing rather than creating a second, "" -named
    instance that no lookup would ever find again.
    """
    if instance_name is None:
        return None
    stripped = instance_name.strip()
    return stripped or None


def instance_name_matches(column, instance_name: Optional[str]):
    """
    Build a WHERE clause for an instance label, using ``IS NULL`` for the unnamed instance.

    ``column == None`` renders as ``= NULL`` under some drivers, which matches nothing. Route every
    instance comparison through here so the default instance stays selectable.
    """
    return column.is_(None) if instance_name is None else column == instance_name


def instance_name_differs(column, instance_name: Optional[str]):
    """
    The negation of :func:`instance_name_matches`, written so NULL rows are not swallowed.

    SQL's ``column != 'x'`` evaluates to NULL — and therefore false — for a NULL column, so the
    plain negation would hide a customer's unnamed instance from "are there any others?" questions
    and let the delete path tear down infrastructure that instance is still using.
    """
    if instance_name is None:
        return column.isnot(None)
    return or_(column.is_(None), column != instance_name)


async def check_existing_customer_integration(
    customer_code: str,
    integration_name: str,
    session: AsyncSession,
    instance_name: Optional[str] = None,
):
    """
    Check if the customer integration already exists.

    For a single-instance integration any existing row is a conflict, exactly as before. For a
    multi-instance one (see ``MULTI_INSTANCE_INTEGRATIONS``) only a clash on the same instance label
    is. An unlabelled *second* instance is still rejected: two NULL instances would be
    indistinguishable to every lookup, provisioning and decommission path downstream. A customer
    provisioned before this feature keeps its unnamed instance and can have named ones added
    alongside it.
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
    existing = result.scalars().unique().all()

    if not existing:
        return

    if integration_name not in MULTI_INSTANCE_INTEGRATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Customer integration {customer_code} {integration_name} already exists.",
        )

    if instance_name is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Customer {customer_code} already has a {integration_name} integration. " f"Provide an instance name to add another one."
            ),
        )

    if any(ci.instance_name == instance_name for ci in existing):
        raise HTTPException(
            status_code=400,
            detail=f"Customer integration {customer_code} {integration_name} '{instance_name}' already exists.",
        )


async def check_existing_customer_integration_meta(
    customer_code: str,
    integration_name: str,
    session: AsyncSession,
    instance_name: Optional[str] = None,
):
    """
    Check if the customer integration meta already exists for the customer code, integration name
    and instance. Each provisioned instance has its own Graylog and Grafana resources, so each gets
    its own metadata row.
    """
    stmt = select(CustomerIntegrationsMeta).where(
        CustomerIntegrationsMeta.customer_code == customer_code,
        CustomerIntegrationsMeta.integration_name == integration_name,
        instance_name_matches(CustomerIntegrationsMeta.instance_name, instance_name),
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
    instance_name: Optional[str] = None,
) -> CustomerIntegrations:
    """
    Create CustomerIntegrations instance.
    """
    customer_integrations = CustomerIntegrations(
        customer_code=customer_code,
        customer_name=customer_name,
        integration_service_id=integration_service_id,
        integration_service_name=integration_service_name,
        instance_name=instance_name,
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


async def get_customer_and_service_ids(session, customer_code, integration_name, instance_name=None, match_instance=False):
    """
    Resolve the `(customer_integrations.id, integration_services.id)` pairs backing an integration.

    ``create_integration_service`` mints a fresh ``integration_services`` row per instance, so each
    instance owns its own service id and the two can be deleted together. Pass
    ``match_instance=True`` to narrow to a single instance; without it the behaviour is unchanged
    and every instance of the integration comes back.
    """
    try:
        stmt = (
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
            )
        )
        if match_instance:
            stmt = stmt.where(instance_name_matches(CustomerIntegrations.instance_name, instance_name))
        result = await session.execute(stmt)
        return result.all()
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Customer integration not found")


async def count_other_integration_instances(
    session,
    customer_code: str,
    integration_name: str,
    instance_name: Optional[str],
) -> int:
    """
    How many *other* instances of this integration the customer still has.

    The delete path uses this to decide whether the customer's shared infrastructure may be torn
    down. A multi-instance integration provisions some resources once per customer — for Office365
    the Graylog index set every tenant writes into, and the Grafana datasource, folder and
    dashboards that read it — so removing one tenant must not take them with it.
    """
    result = await session.execute(
        select(CustomerIntegrations.id)
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
            instance_name_differs(CustomerIntegrations.instance_name, instance_name),
        )
        .distinct(),
    )
    return len(result.scalars().all())


async def resolve_integration_instance(
    session,
    customer_code: str,
    integration_name: str,
    instance_name: Optional[str],
) -> Optional[str]:
    """
    Work out which instance a caller means when they did not name one.

    Callers that predate multi-instance support (and every single-instance integration) send only a
    customer code and an integration name. When the customer has exactly one instance that is
    unambiguous, so return its label; when they have several, refuse rather than silently acting on
    an arbitrary one.
    """
    if instance_name is not None:
        return instance_name

    result = await session.execute(
        select(CustomerIntegrations.instance_name)
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
        )
        .distinct(),
    )
    instances = list(result.scalars().all())

    if len(instances) > 1:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Customer {customer_code} has {len(instances)} {integration_name} instances "
                f"({', '.join(sorted(i or 'unnamed' for i in instances))}). Specify which one."
            ),
        )

    return instances[0] if instances else None


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
    instance_name: Optional[str] = None,
    match_instance: bool = False,
) -> Optional[CustomerIntegrations]:
    """
    Pick a customer's integration out of a ``CustomerIntegrationsResponse``.

    With ``match_instance`` the search is narrowed to one instance label; without it the first
    matching instance wins, which is what every single-instance caller has always got.
    """
    for ci in customer_integration_response.available_integrations:
        if match_instance and ci.instance_name != instance_name:
            continue
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
    instance_name: Optional[str] = None,
    match_instance: bool = False,
) -> str:
    """
    Retrieves the Tenant ID for a given customer integration. This is the Office365 organization ID and
    is used to create alerts for the customer in DFIR-IRIS.

    With ``match_instance`` the lookup is pinned to one instance, which is what a customer holding
    several Microsoft 365 tenants needs; without it the customer's first tenant comes back, as before.
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
    if match_instance:
        stmt = stmt.where(instance_name_matches(CustomerIntegrations.instance_name, instance_name))

    result = await session.execute(stmt)
    tenant_id = result.scalars().first()
    if tenant_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tenant ID for customer {customer_integration.customer_code} not found.",
        )
    logger.info(f"tenant_id: {tenant_id.auth_value}")
    return tenant_id.auth_value


async def clear_office365_organization_id(
    tenant_id: str,
    session: AsyncSession,
):
    """
    Forget a deleted tenant in the two legacy single-tenant columns.

    Both are matched on the tenant ID rather than the customer, so only rows naming this exact
    tenant are touched — a customer's remaining tenants are unaffected. Without this a deleted
    tenant keeps pointing at its old customer, and re-registering it under a different customer
    would route its alerts to the previous one, since the legacy columns are consulted first.
    """
    await session.execute(
        update(AlertCreationSettings)
        .where(AlertCreationSettings.office365_organization_id == tenant_id)
        .values(office365_organization_id=None),
    )
    await session.execute(
        update(CustomersMeta)
        .where(CustomersMeta.customer_meta_office365_organization_id == tenant_id)
        .values(customer_meta_office365_organization_id=None),
    )
    await session.commit()


async def update_office365_organization_id(
    customer_code: str,
    tenant_id: str,
    session: AsyncSession,
):
    """
    Record the customer's Microsoft 365 tenant in `custom_alert_creation_settings`.

    This column holds a single tenant and predates multi-tenant support, so it is only ever written
    for the *first* tenant a customer gets; alerts from any later tenant are routed by
    `resolve_customer_code_from_office365_tenant` instead, which reads the stored TENANT_ID auth
    keys. Overwriting it here would silently repoint the legacy lookup at whichever tenant was added
    last.
    """
    stmt = (
        update(AlertCreationSettings)
        .where(
            AlertCreationSettings.customer_code == customer_code,
            (AlertCreationSettings.office365_organization_id.is_(None)) | (AlertCreationSettings.office365_organization_id == ""),
        )
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
            instance_name=ci.instance_name,
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


def generate_decommission_response(
    customer_code: str,
    integration_name: str,
    cleanup_warnings: Optional[List[str]] = None,
) -> CustomerIntegrationDeleteResponse:
    additional_info_map = {
        # The tenant's <api_auth> block and the manager restart are handled automatically by
        # `decommission_office365_tenant`; anything it could not do arrives as a cleanup warning.
        "Office365": "",
        "Crowdstrike": ("Make sure to remove the Crowdstrike docker application."),
        "BitDefender": ("Make sure to remove the BitDefender docker application."),
    }

    additional_info = additional_info_map.get(integration_name, "")

    # Anything the infrastructure cleanup could not remove is reported alongside the manual
    # steps so the operator knows exactly what is left over.
    if cleanup_warnings:
        additional_info = " ".join([additional_info, *cleanup_warnings]).strip()

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
    "/available_integrations/{integration_id}",
    response_model=AvailableIntegrationDetailResponse,
    description="Get a single available integration by id.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_available_integration(
    integration_id: int,
    session: AsyncSession = Depends(get_db),
) -> AvailableIntegrationDetailResponse:
    integration = await fetch_available_integration_by_id(session, integration_id)
    return AvailableIntegrationDetailResponse(
        available_integration=integration,
        message="Available integration successfully retrieved.",
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
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

    instance_name = normalize_instance_name(customer_integration_create.instance_name)
    if instance_name and customer_integration_create.integration_name not in MULTI_INSTANCE_INTEGRATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"{customer_integration_create.integration_name} does not support multiple instances per customer.",
        )

    await check_existing_customer_integration(
        customer_integration_create.customer_code,
        customer_integration_create.integration_name,
        session,
        instance_name=instance_name,
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
        instance_name=instance_name,
    )
    await create_integration_subscription(
        customer_integrations,
        integration_service,
        integration_auth_keys=customer_integration_create.integration_auth_keys,
        session=session,
    )

    # Office365 specific integration handling
    if customer_integration_create.integration_name == "Office365":
        tenant_id = await get_tenant_id(
            customer_integration_create,
            session,
            instance_name=instance_name,
            match_instance=True,
        )
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
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
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
        instance_name=normalize_instance_name(customer_integration_meta.instance_name),
    )
    try:
        new_customer_integration_meta = CustomerIntegrationsMeta(
            **customer_integration_meta.model_dump(),
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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
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

    instance_name = await resolve_integration_instance(
        session,
        customer_code,
        customer_integration_update.integration_name,
        normalize_instance_name(customer_integration_update.instance_name),
    )

    customer_integration = await find_customer_integration(
        customer_code,
        customer_integration_update.integration_name,
        customer_integration_response,
        instance_name=instance_name,
        match_instance=True,
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


async def fetch_customer_integration_meta(
    session: AsyncSession,
    customer_code: str,
    integration_name: str,
    instance_name: Optional[str] = None,
    match_instance: bool = False,
):
    """
    Fetches customer integrations metadata from the database.
    """
    stmt = select(CustomerIntegrationsMeta).where(
        CustomerIntegrationsMeta.customer_code == customer_code,
        CustomerIntegrationsMeta.integration_name == integration_name,
    )
    if match_instance:
        stmt = stmt.where(instance_name_matches(CustomerIntegrationsMeta.instance_name, instance_name))
    result = await session.execute(stmt)
    return result.scalars().first()


async def delete_customer_integration_meta(
    session: AsyncSession,
    customer_code: str,
    integration_name: str,
    instance_name: Optional[str] = None,
    match_instance: bool = False,
):
    """
    Deletes customer integrations metadata from the database.
    """
    stmt = delete(CustomerIntegrationsMeta).where(
        CustomerIntegrationsMeta.customer_code == customer_code,
        CustomerIntegrationsMeta.integration_name == integration_name,
    )
    if match_instance:
        stmt = stmt.where(instance_name_matches(CustomerIntegrationsMeta.instance_name, instance_name))
    await session.execute(stmt)


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


async def _cleanup_integration_infrastructure(
    meta_data,
    customer_code: str,
    integration_name: str,
    cleanup_warnings: List[str],
    stream_only: bool = False,
) -> None:
    """
    Remove the Graylog and Grafana resources recorded in an integration's metadata.

    Each resource is removed independently: a resource that is already gone (or a metadata
    field that was never populated because provisioning failed partway) must not block the
    removal of the others, otherwise the integration becomes undeletable from the UI. Every
    failure is logged and appended to `cleanup_warnings` for the caller to surface.

    `stream_only` is for a multi-instance integration whose other instances are still deployed.
    Each instance owns its Graylog stream, but the index set and the Grafana folder, datasource and
    dashboards are provisioned once per customer and shared — for Office365 every tenant writes
    into the one `office365-<customer_code>` index set — so tearing those down here would blind the
    tenants that remain.
    """

    async def _attempt(description: str, coroutine_factory):
        try:
            await coroutine_factory()
        except Exception as e:
            logger.warning(f"Failed to delete {description} for {integration_name} / {customer_code}: {e}")
            cleanup_warnings.append(f"Could not delete {description}: {e}. Remove it manually if it still exists.")

    # Delete stream and index using metadata
    stream_id = meta_data.graylog_stream_id
    logger.info(f"stream_id: {stream_id}")
    if stream_id:
        await _attempt(f"Graylog stream {stream_id}", lambda: delete_stream(stream_id=stream_id))

    if stream_only:
        logger.info(
            f"Other instances of {integration_name} are still deployed for {customer_code}; "
            "keeping the shared index set, Grafana folder and datasource.",
        )
        return

    index_id = meta_data.graylog_index_id
    logger.info(f"index_id: {index_id}")
    if index_id:
        await _attempt(f"Graylog index {index_id}", lambda: delete_index_by_id(index_id=index_id))

    # Delete the folder in Grafana
    grafana_org_id = meta_data.grafana_org_id
    grafana_dashboard_folder_id = meta_data.grafana_dashboard_folder_id

    if grafana_org_id and grafana_dashboard_folder_id:
        await _attempt(
            f"Grafana dashboard folder {grafana_dashboard_folder_id}",
            lambda: delete_folder(grafana_org_id, grafana_dashboard_folder_id),
        )
    else:
        logger.info("No Grafana org ID or dashboard folder ID found, skipping folder deletion.")

    # Delete the grafana datasource
    grafana_datasource_uid = getattr(meta_data, "grafana_datasource_uid", None)
    if grafana_org_id and grafana_datasource_uid:
        logger.info(f"Deleting Grafana datasource with UID: {grafana_datasource_uid}")
        await _attempt(
            f"Grafana datasource {grafana_datasource_uid}",
            lambda: delete_grafana_datasource(
                organization_id=grafana_org_id,
                datasource_uid=grafana_datasource_uid,
            ),
        )
    else:
        logger.info("No Grafana datasource UID found, skipping deletion.")


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

    instance_name = await resolve_integration_instance(
        session,
        customer_code,
        integration_name,
        normalize_instance_name(delete_customer_integration.instance_name),
    )

    # Instances of the same integration share the customer's index set and Grafana resources, so
    # only the last one out may take the infrastructure with it.
    remaining_instances = await count_other_integration_instances(
        session,
        customer_code,
        integration_name,
        instance_name,
    )

    results = await get_customer_and_service_ids(
        session,
        customer_code,
        integration_name,
        instance_name=instance_name,
        match_instance=True,
    )
    # Check if results is not empty
    if results:
        # Unpack the first tuple in results
        customer_id, integration_service_id = results[0]
    else:
        # Handle the case where results is empty
        raise HTTPException(status_code=404, detail="Customer integration not found")

    # Check if the integration is deployed before proceeding with metadata cleanup
    stmt = select(CustomerIntegrations.deployed).where(CustomerIntegrations.id == customer_id)
    result = await session.execute(stmt)
    is_deployed = result.scalar()

    logger.info(f"Integration {integration_name} for customer {customer_code} deployment status: {is_deployed}")

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

    # Collected non-fatal problems, surfaced to the caller so they know what was left behind
    cleanup_warnings: List[str] = []

    # Read before the auth keys are deleted, since it is the only record of which Microsoft 365
    # tenant the Wazuh manager should stop polling for this instance.
    office365_tenant_id = None
    if integration_name == "Office365":
        office365_tenant_id = await get_office365_tenant_id(customer_code, session, instance_name=instance_name)

    # Only proceed with infrastructure cleanup if the integration is deployed
    if is_deployed:
        logger.info("Integration is deployed, proceeding with full cleanup including infrastructure components")

        # Fetch metadata from appropriate table based on integration type
        if is_network_integration:
            meta_data = await fetch_customer_network_connectors_meta(session, customer_code, integration_name)
        else:
            meta_data = await fetch_customer_integration_meta(
                session,
                customer_code,
                integration_name,
                instance_name=instance_name,
                match_instance=True,
            )

        if not meta_data:
            # A deployment that failed partway (or predates metadata tracking) leaves the
            # integration flagged as deployed with no metadata row. Refusing to delete here
            # used to make the integration permanently undeletable from the UI, so continue
            # with the settings cleanup and tell the caller what could not be reached.
            logger.warning(
                f"No metadata found for {integration_name} / {customer_code}; "
                "skipping infrastructure cleanup and removing the integration settings only",
            )
            cleanup_warnings.append(
                f"No metadata record was found for {integration_name}, so the Graylog stream/index and Grafana folder/datasource "
                "could not be removed automatically. Delete any leftover Graylog and Grafana resources for this customer manually.",
            )
        else:
            await _cleanup_integration_infrastructure(
                meta_data=meta_data,
                customer_code=customer_code,
                integration_name=integration_name,
                cleanup_warnings=cleanup_warnings,
                stream_only=remaining_instances > 0,
            )

            # Delete metadata from appropriate table
            if is_network_integration:
                await delete_customer_network_connectors_meta(session, customer_code, integration_name)
            else:
                await delete_customer_integration_meta(
                    session,
                    customer_code,
                    integration_name,
                    instance_name=instance_name,
                    match_instance=True,
                )

    else:
        logger.info(
            "Integration is not deployed, skipping infrastructure cleanup (Graylog streams/indexes, Grafana folders/datasources, metadata)",
        )

    # Always delete the integration settings (auth keys, configs, subscriptions, etc.)
    logger.info(f"Deleting integration settings for {integration_name}")
    await delete_metadata(session, subscription_ids)  # This deletes auth keys
    await delete_subscriptions(session, subscription_ids)
    await delete_configs(session, integration_service_id)
    await delete_integration_service(session, integration_service_id)
    await delete_customer_integration_record(session, customer_id)

    await session.commit()

    # The Wazuh manager keeps collecting from a tenant whose <api_auth> block is still in ossec.conf,
    # so this runs even when the integration was never marked deployed. A failure here is reported
    # rather than raised: the CoPilot-side records are already gone and re-running the delete would
    # 404 before it ever reached this point.
    if office365_tenant_id:
        await clear_office365_organization_id(office365_tenant_id, session)
        try:
            await decommission_office365_tenant(customer_code, office365_tenant_id)
        except Exception as e:
            logger.warning(f"Failed to remove the Office365 api_auth block for tenant {office365_tenant_id}: {e}")
            cleanup_warnings.append(
                f"Could not remove the Office365 api_auth block for tenant {office365_tenant_id} from the Wazuh "
                f"manager ({e}). Remove it from ossec.conf and restart the manager.",
            )

    return generate_decommission_response(customer_code, integration_name, cleanup_warnings)


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
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def get_meta_auto(
    customer_code: str,
    integration_name: str,
    instance_name: Optional[str] = None,
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
                    detail=(
                        f"Network connector metadata not found for customer {customer_code} and connector {integration_name}. "
                        f"{MISSING_META_RECOVERY_HINT}"
                    ),
                )

            logger.info(f"Successfully retrieved network connector metadata for {customer_code}/{integration_name}")

        else:
            # Fetch from regular integrations table
            stmt = select(CustomerIntegrationsMeta).where(
                CustomerIntegrationsMeta.customer_code == customer_code,
                CustomerIntegrationsMeta.integration_name == integration_name,
            )
            # Only narrow when the caller named an instance: an omitted instance keeps the
            # pre-multi-instance behaviour of returning the customer's single metadata row.
            normalized_instance = normalize_instance_name(instance_name)
            if normalized_instance is not None:
                stmt = stmt.where(instance_name_matches(CustomerIntegrationsMeta.instance_name, normalized_instance))
            result = await session.execute(stmt)
            meta_record = result.scalars().first()

            if not meta_record:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Integration metadata not found for customer {customer_code} and integration {integration_name}. "
                        f"{MISSING_META_RECOVERY_HINT}"
                    ),
                )

            logger.info(f"Successfully retrieved integration metadata for {customer_code}/{integration_name}")

        # Convert SQLModel to dict for response
        return {
            "success": True,
            "message": f"Successfully retrieved metadata for {customer_code}/{integration_name}",
            "data": meta_record.model_dump() if hasattr(meta_record, "dict") else meta_record.__dict__,
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
    updates the appropriate table accordingly. When no metadata row exists yet — the state a
    deployment that failed partway leaves behind — the row is created instead of returning a
    404, so a broken integration can be repaired from the UI.
    """
    is_network_integration = update_request.integration_name in NETWORK_INTEGRATIONS

    if is_network_integration:
        meta_model = CustomerNetworkConnectorsMeta
        name_field = "network_connector_name"
        editable_fields = [
            "graylog_input_id",
            "graylog_index_id",
            "graylog_stream_id",
            "graylog_pipeline_id",
            "graylog_content_pack_input_id",
            "graylog_content_pack_stream_id",
            "grafana_org_id",
            "grafana_dashboard_folder_id",
            "grafana_datasource_uid",
        ]
    else:
        meta_model = CustomerIntegrationsMeta
        name_field = "integration_name"
        editable_fields = [
            "graylog_input_id",
            "graylog_index_id",
            "graylog_stream_id",
            "grafana_org_id",
            "grafana_dashboard_folder_id",
            "grafana_datasource_uid",
        ]

    table_type = "network connector" if is_network_integration else "integration"
    name_column = getattr(meta_model, name_field)

    # Network connectors have no instance column; for integrations an omitted instance keeps the
    # pre-multi-instance behaviour of addressing the customer's single metadata row.
    normalized_instance = None if is_network_integration else normalize_instance_name(update_request.instance_name)

    def _scope(statement):
        if normalized_instance is not None:
            return statement.where(instance_name_matches(meta_model.instance_name, normalized_instance))
        return statement

    try:
        stmt = _scope(
            select(meta_model).where(
                meta_model.customer_code == update_request.customer_code,
                name_column == update_request.integration_name,
            ),
        )
        result = await session.execute(stmt)
        existing_record = result.scalars().first()

        update_data = {field: getattr(update_request, field) for field in editable_fields if getattr(update_request, field) is not None}

        if not update_data:
            return UpdateMetaResponse(success=False, message="No fields provided for update")

        if existing_record:
            update_stmt = _scope(
                update(meta_model).where(
                    meta_model.customer_code == update_request.customer_code,
                    name_column == update_request.integration_name,
                ),
            ).values(**update_data)
            await session.execute(update_stmt)
            action = "Updated"
        else:
            # Every ID column is NOT NULL, so anything the caller left out is stored as an
            # empty string rather than blocking the repair of a partially deployed integration.
            record_values = {field: "" for field in editable_fields}
            record_values.update(update_data)
            record_values["customer_code"] = update_request.customer_code
            record_values[name_field] = update_request.integration_name
            if not is_network_integration:
                record_values["instance_name"] = normalized_instance
            session.add(meta_model(**record_values))
            action = "Created"

        await session.commit()

        logger.info(
            f"{action} {table_type} metadata for customer {update_request.customer_code}, {table_type} {update_request.integration_name}",
        )

        return UpdateMetaResponse(
            success=True,
            message=(
                f"Successfully {action.lower()} {table_type} metadata for "
                f"{update_request.customer_code}/{update_request.integration_name}"
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
