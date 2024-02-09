import os

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models.users import Role
from app.connectors.models import Connectors
from app.integrations.models.customer_integration_settings import AvailableIntegrations
from app.integrations.models.customer_integration_settings import (
    AvailableIntegrationsAuthKeys,
)

load_dotenv()


def load_connector_data(
    connector_name,
    connector_type,
    accepts_key,
    description,
    extra_data_key=None,
):
    """
    Load connector data from environment variables.

    Args:
        connector_name (str): The name of the connector.
        connector_type (str): The type of the connector.
        accepts_key (str): The type of key the connector accepts.
        description (str): The description of the connector.
        extra_data_key (str, optional): The key for extra data. Defaults to None.

    Returns:
        dict: A dictionary containing the connector data.
    """
    env_prefix = connector_name.upper().replace("-", "_").replace(" ", "_")
    url = os.getenv(f"{env_prefix}_URL")
    logger.info(
        f"Loading connector data for {connector_name} from environment variables with URL: {url}",
    )
    return {
        "connector_name": connector_name,
        "connector_type": connector_type,
        "connector_url": os.getenv(f"{env_prefix}_URL"),
        "connector_username": os.getenv(f"{env_prefix}_USERNAME"),
        "connector_password": os.getenv(f"{env_prefix}_PASSWORD"),
        "connector_api_key": os.getenv(f"{env_prefix}_API_KEY"),
        "connector_description": description,
        "connector_supports": os.getenv(f"{env_prefix}_SUPPORTS", "Not specified."),
        "connector_configured": True,
        "connector_verified": bool(os.getenv(f"{env_prefix}_VERIFIED", False)),
        "connector_accepts_host_only": accepts_key == "host_only",
        "connector_accepts_api_key": accepts_key == "api_key",
        "connector_accepts_username_password": accepts_key == "username_password",
        "connector_accepts_file": accepts_key == "file",
        "connector_accepts_extra_data": True if extra_data_key else False,
        "connector_extra_data": os.getenv(extra_data_key) if extra_data_key else None,
    }


def get_connectors_list():
    """
    Get a list of connectors with their respective versions and authentication methods.

    Returns:
        list: A list of connector data, where each item contains the connector name, version, and authentication method.
    """
    connectors = [
        ("Wazuh-Indexer", "4.4.1", "username_password", "Connection to Wazuh-Indexer."),
        (
            "Wazuh-Manager",
            "4.4.1",
            "username_password",
            "Connection to Wazuh-Manager. Default is wazuh-wui:wazuh-wui",
        ),
        ("Graylog", "5.0.7", "username_password", "Connection to Graylog."),
        ("Shuffle", "1.1.0", "api_key", "Connection to Shuffle."),
        ("DFIR-IRIS", "2.0", "api_key", "Connection to DFIR-IRIS."),
        (
            "Velociraptor",
            "0.6.8",
            "file",
            "Connection to Velociraptor. Make sure you have generated the api file first.",
        ),
        ("Sublime", "3", "api_key", "Connection to Sublime."),
        (
            "InfluxDB",
            "3",
            "api_key",
            "Connection to InfluxDB.",
            "INFLUXDB_ORG_AND_BUCKET",
        ),
        (
            "AskSocfortress",
            "3",
            "api_key",
            "Connection to AskSocfortress. Make sure you have requested an API key.",
        ),
        (
            "SocfortressThreatIntel",
            "3",
            "api_key",
            "Connection to Socfortress Threat Intel. Make sure you have requested an API key.",
        ),
        (
            "Cortex",
            "3",
            "api_key",
            "Connection to Cortex. Make sure you have created an API key.",
        ),
        ("Grafana", "3", "username_password", "Connection to Grafana."),
        (
            "Wazuh Worker Provisioning",
            "3",
            "host_only",
            (
                "Connection to Wazuh Worker Provisioning. Make sure you have "
                "deployed the Wazuh Worker Provisioning Application provided by "
                "SOCFortress: https://github.com/socfortress/Customer-Provisioning-Worker"
            ),
        ),
        (
            "Event Shipper",
            "3",
            "host_only",
            "Connection to Graylog GELF Input to receive events from integrations. Make sure you have created a GELF Input in Graylog.",
            "GELF_INPUT_PORT",
        ),
        (
            "Alert Creation Provisioning",
            "3",
            "host_only",
            (
                "Connection to Alert Creation Provisioning. Make sure you have "
                "deployed the Alert Creation Provisioning Application provided by "
                "SOCFortress: https://github.com/socfortress/Customer-Provisioning-Alert"
            ),
        ),
        # ... Add more connectors as needed ...
    ]

    return [load_connector_data(*connector) for connector in connectors]


async def add_connectors_if_not_exist(session: AsyncSession):
    """
    Adds connectors to the database if they do not already exist.

    Args:
        session (AsyncSession): The database session.

    Returns:
        None
    """
    connector_list = get_connectors_list()

    for connector_data in connector_list:
        query = select(Connectors).where(
            Connectors.connector_name == connector_data["connector_name"],
        )
        result = await session.execute(query)
        existing_connector = result.scalars().first()

        if existing_connector is None:
            new_connector = Connectors(**connector_data)
            session.add(new_connector)
            logger.info(f"Added new connector: {connector_data['connector_name']}")

    await session.commit()


async def add_roles_if_not_exist(session: AsyncSession) -> None:
    """
    Adds roles to the database if they do not already exist.

    Args:
        session (AsyncSession): The database session.

    Returns:
        None
    """
    # List of roles to add
    role_list = [
        {"name": "admin", "description": "Administrator"},
        {"name": "analyst", "description": "SOC Analyst"},
        {"name": "scheduler", "description": "Scheduler for automated tasks"},
    ]

    for role_data in role_list:
        logger.info(f"Checking for existence of role {role_data['name']}")
        query = select(Role).where(Role.name == role_data["name"])
        result = await session.execute(query)
        existing_role = result.scalars().first()

        if existing_role is None:
            new_role = Role(**role_data)
            session.add(new_role)  # Use session.add() to add new objects
            logger.info(f"Added new role: {role_data['name']}")

    await session.commit()  # Commit the transaction
    logger.info("Role check and addition completed.")


def load_available_integrations_data(
    integration_name: str,
    description: str,
    integration_details: str,
):
    """
    Load available integrations data from environment variables.

    Args:
        integration_name (str): The name of the integration.
        description (str): The description of the integration.

    Returns:
        dict: A dictionary containing the integration data.
    """
    logger.info(f"Loading available integrations data for {integration_name}.")
    return {
        "integration_name": integration_name,
        "description": description,
        "integration_details": integration_details,
    }


def load_markdown_for_integration(integration_name: str) -> str:
    """
    Load markdown content for a given integration from a file.

    Args:
        integration_name (str): The name of the integration.

    Returns:
        str: The content of the markdown file.
    """
    # file_path = os.path.join("integrations_markdown", f"{integration_name.lower()}.md")
    file_path = os.path.join(
        "app",
        "integrations",
        "markdown",
        f"{integration_name.lower()}.md",
    )
    try:
        with open(file_path, "r") as file:
            return file.read()
    except FileNotFoundError:
        return "No deployment intrusctions available."


def get_available_integrations_list():
    """
    Get a list of available integrations.

    Returns:
        list: A list of available integrations data, where each item contains the integration name, description, and markdown details.
    """
    available_integrations = [
        ("Office365", "Integrate Office365 with SOCFortress."),
        ("Mimecast", "Integrate Mimecast with SOCFortress."),
        # ... Add more available integrations as needed ...
    ]

    return [
        load_available_integrations_data(
            integration_name,
            description,
            load_markdown_for_integration(integration_name),
        )
        for integration_name, description in available_integrations
    ]


async def add_available_integrations_if_not_exist(session: AsyncSession):
    """
    Adds available integrations to the database if they do not already exist.

    Args:
        session (AsyncSession): The database session.

    Returns:
        None
    """
    available_integrations_list = get_available_integrations_list()

    for available_integration_data in available_integrations_list:
        query = select(AvailableIntegrations).where(
            AvailableIntegrations.integration_name == available_integration_data["integration_name"],
        )
        result = await session.execute(query)
        existing_available_integration = result.scalars().first()

        if existing_available_integration is None:
            new_available_integration = AvailableIntegrations(
                **available_integration_data,
            )
            session.add(new_available_integration)
            logger.info(
                f"Added new available integration: {available_integration_data['integration_name']}",
            )


def load_available_integrations_auth_keys(
    integration_id: int,
    integration_name: str,
    auth_key_name: str,
):
    """
    Load available integrations auth keys from environment variables.

    Args:
        integration_id (int): The ID of the integration.
        integration_name (str): The name of the integration.
        auth_key_name (str): The name of the auth key.

    Returns:
        dict: A dictionary containing the auth key data.
    """
    logger.info(
        f"Loading available integrations auth keys data for {integration_name}.",
    )
    return {
        "integration_id": integration_id,
        "integration_name": integration_name,
        "auth_key_name": auth_key_name,
    }


async def get_available_integrations_auth_keys_list(session: AsyncSession):
    """
    Get a list of available integrations auth keys with their corresponding integration IDs.

    Args:
        session (AsyncSession): The database session.

    Returns:
        list: A list of available integrations auth keys data, where each item contains the integration ID, integration name, and auth key name.
    """
    available_integrations_auth_keys = []
    available_integrations = [
        ("Office365", "TENANT_ID"),
        ("Office365", "CLIENT_ID"),
        ("Office365", "CLIENT_SECRET"),
        ("Office365", "API_TYPE"),
        ("Mimecast", "APP_ID"),
        ("Mimecast", "APP_KEY"),
        ("Mimecast", "EMAIL_ADDRESS"),
        ("Mimecast", "ACCESS_KEY"),
        ("Mimecast", "SECRET_KEY"),
        # ... Add more available integrations auth keys as needed ...
    ]

    for integration_name, auth_key_name in available_integrations:
        query = select(AvailableIntegrations.id).where(
            AvailableIntegrations.integration_name == integration_name,
        )
        result = await session.execute(query)
        integration_id = result.scalars().first()

        if integration_id:
            available_integrations_auth_keys.append(
                load_available_integrations_auth_keys(
                    integration_id,
                    integration_name,
                    auth_key_name,
                ),
            )

    return available_integrations_auth_keys


async def add_available_integrations_auth_keys_if_not_exist(session: AsyncSession):
    """
    Adds available integrations auth keys to the database if they do not already exist.

    Args:
        session (AsyncSession): The database session.

    Returns:
        None
    """
    available_integrations_auth_keys_list = await get_available_integrations_auth_keys_list(session=session)

    for available_integration_auth_keys_data in available_integrations_auth_keys_list:
        query = select(AvailableIntegrations).where(
            AvailableIntegrations.integration_name == available_integration_auth_keys_data["integration_name"],
        )
        result = await session.execute(query)
        existing_integration = result.scalars().first()

        if existing_integration:
            available_integration_auth_keys_data["integration_id"] = existing_integration.id
            auth_key_query = select(AvailableIntegrationsAuthKeys).where(
                and_(
                    AvailableIntegrationsAuthKeys.integration_id == existing_integration.id,
                    AvailableIntegrationsAuthKeys.auth_key_name == available_integration_auth_keys_data["auth_key_name"],
                ),
            )
            auth_key_result = await session.execute(auth_key_query)
            existing_auth_key = auth_key_result.scalars().first()

            if existing_auth_key is None:
                new_auth_key = AvailableIntegrationsAuthKeys(
                    **available_integration_auth_keys_data,
                )
                session.add(new_auth_key)
                logger.info(
                    f"Added new available integration auth keys: "
                    f"{available_integration_auth_keys_data['auth_key_name']} for "
                    f"{available_integration_auth_keys_data['integration_name']}",
                )
