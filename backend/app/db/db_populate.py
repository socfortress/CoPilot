from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models.users import Role
from app.connectors.models import Connectors

from dotenv import load_dotenv
import os

load_dotenv()

def load_connector_data(connector_name, connector_type, accepts_key, extra_data_key=None):
    """
    Load connector data from environment variables.

    Args:
        connector_name (str): The name of the connector.
        connector_type (str): The type of the connector.
        accepts_key (str): The type of key the connector accepts.
        extra_data_key (str, optional): The key for extra data. Defaults to None.

    Returns:
        dict: A dictionary containing the connector data.
    """
    env_prefix = connector_name.upper().replace("-", "_").replace(" ", "_")
    url = os.getenv(f"{env_prefix}_URL")
    logger.info(f"Loading connector data for {connector_name} from environment variables with URL: {url}")
    return {
        "connector_name": connector_name,
        "connector_type": connector_type,
        "connector_url": os.getenv(f"{env_prefix}_URL"),
        "connector_username": os.getenv(f"{env_prefix}_USERNAME"),
        "connector_password": os.getenv(f"{env_prefix}_PASSWORD"),
        "connector_api_key": os.getenv(f"{env_prefix}_API_KEY"),
        "connector_description": os.getenv(f"{env_prefix}_DESCRIPTION", "No description available."),
        "connector_supports": os.getenv(f"{env_prefix}_SUPPORTS", "Not specified."),
        "connector_configured": True,
        "connector_verified": bool(os.getenv(f"{env_prefix}_VERIFIED", False)),
        "connector_accepts_api_key": accepts_key == "api_key",
        "connector_accepts_username_password": accepts_key == "username_password",
        "connector_accepts_file": accepts_key == "file",
        "connector_extra_data": os.getenv(extra_data_key) if extra_data_key else None,
    }


def get_connectors_list():
    """
    Get a list of connectors with their respective versions and authentication methods.

    Returns:
        list: A list of connector data, where each item contains the connector name, version, and authentication method.
    """
    connectors = [
        ("Wazuh-Indexer", "4.4.1", "username_password"),
        ("Wazuh-Manager", "4.4.1", "username_password"),
        ("Graylog", "5.0.7", "username_password"),
        ("Shuffle", "1.1.0", "api_key"),
        ("DFIR-IRIS", "2.0", "api_key"),
        ("Velociraptor", "0.6.8", "file"),
        ("Sublime", "3", "api_key"),
        ("InfluxDB", "3", "api_key", "INFLUXDB_ORG_AND_BUCKET"),
        ("AskSocfortress", "3", "api_key"),
        ("SocfortressThreatIntel", "3", "api_key"),
        ("Cortex", "3", "api_key"),
        ("Grafana", "3", "username_password"),
        ("Wazuh Worker Provisioning", "3", "api_key"),
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
        query = select(Connectors).where(Connectors.connector_name == connector_data["connector_name"])
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
