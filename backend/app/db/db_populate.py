from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import Session

from app.auth.models.users import Role
from app.connectors.models import Connectors

from dotenv import load_dotenv
import os

load_dotenv()


async def add_connectors_if_not_exist(session: AsyncSession):
    # List of connectors to add
    connector_list = [
        {
            "connector_name": "Wazuh-Indexer",
            "connector_type": "4.4.1",
            "connector_url": os.getenv("WAZUH_INDEXER_URL"),
            "connector_username": os.getenv("WAZUH_INDEXER_USERNAME"),
            "connector_password": os.getenv("WAZUH_INDEXER_PASSWORD"),
            "connector_api_key": None,
            "connector_configured": True,
            "connector_accepts_username_password": True,
        },
        {
            "connector_name": "Wazuh-Manager",
            "connector_type": "4.4.1",
            "connector_url": os.getenv("WAZUH_MANAGER_URL"),
            "connector_username": os.getenv("WAZUH_MANAGER_USERNAME"),
            "connector_password": os.getenv("WAZUH_MANAGER_PASSWORD"),
            "connector_api_key": None,
            "connector_configured": True,
            "connector_accepts_username_password": True,
        },
        {
            "connector_name": "Graylog",
            "connector_type": "5.0.7",
            "connector_url": os.getenv("GRAYLOG_URL"),
            "connector_username": os.getenv("GRAYLOG_USERNAME"),
            "connector_password": os.getenv("GRAYLOG_PASSWORD"),
            "connector_api_key": None,
            "connector_configured": True,
            "connector_accepts_username_password": True,
        },
        {
            "connector_name": "Shuffle",
            "connector_type": "1.1.0",
            "connector_url": os.getenv("SHUFFLE_URL"),
            "connector_username": "sting",
            "connector_password": "string",
            "connector_api_key": os.getenv("SHUFFLE_API_KEY"),
            "connector_configured": True,
            "connector_accepts_api_key": True,
        },
        {
            "connector_name": "DFIR-IRIS",
            "connector_type": "2.0",
            "connector_url": os.getenv("DFIR_IRIS_URL"),
            "connector_username": None,
            "connector_password": None,
            "connector_api_key": os.getenv("DFIR_IRIS_API_KEY"),
            "connector_configured": True,
            "connector_accepts_api_key": True,
        },
        {
            "connector_name": "Velociraptor",
            "connector_type": "0.6.8",
            "connector_url": os.getenv("VELOCIRAPTOR_URL"),
            "connector_username": None,
            "connector_password": None,
            "connector_api_key": os.getenv("VELOCIRAPTOR_API_KEY_PATH"),
            "connector_configured": True,
            "connector_accepts_file": True,
        },
        # {
        #     "connector_name": "RabbitMQ",
        #     "connector_type": "3",
        #     "connector_url": "ashdkr02.socfortress.local:5672",
        #     "connector_username": "guest",
        #     "connector_password": "guest",
        #     "connector_api_key": None,
        #     "connector_configured": True,
        #     "connector_accepts_username_password": True,
        # },
        {
            "connector_name": "Sublime",
            "connector_type": "3",
            "connector_url": os.getenv("SUBLIME_URL"),
            "connector_username": None,
            "connector_password": None,
            "connector_api_key": os.getenv("SUBLIME_API_KEY"),
            "connector_configured": True,
            "connector_accepts_api_key": True,
        },
        {
            "connector_name": "InfluxDB",
            "connector_type": "3",
            "connector_url": os.getenv("INFLUXDB_URL"),
            "connector_username": None,
            "connector_password": None,
            "connector_api_key": os.getenv("INFLUXDB_API_KEY"),
            "connector_configured": True,
            "connector_accepts_api_key": True,
            "connector_extra_data": os.getenv("INFLUXDB_ORG_AND_BUCKET"),
        },
        {
            "connector_name": "AskSocfortress",
            "connector_type": "3",
            "connector_url": os.getenv("ASK_SOCFORTRESS_URL"),
            "connector_username": None,
            "connector_password": None,
            "connector_api_key": os.getenv("ASK_SOCFORTRESS_API_KEY"),
            "connector_configured": True,
            "connector_accepts_api_key": True,
        },
        {
            "connector_name": "SocfortressThreatIntel",
            "connector_type": "3",
            "connector_url": os.getenv("SOCFORTRESS_THREAT_INTEL_URL"),
            "connector_username": None,
            "connector_password": None,
            "connector_api_key": os.getenv("SOCFORTRESS_THREAT_INTEL_API_KEY"),
            "connector_configured": True,
            "connector_accepts_api_key": True,
        },
        {
            "connector_name": "Cortex",
            "connector_type": "3",
            "connector_url": os.getenv("CORTEX_URL"),
            "connector_username": None,
            "connector_password": None,
            "connector_api_key": os.getenv("CORTEX_API_KEY"),
            "connector_configured": True,
            "connector_accepts_api_key": True,
        },
        {
            "connector_name": "Grafana",
            "connector_type": "3",
            "connector_url": os.getenv("GRAFANA_URL"),
            "connector_username": os.getenv("GRAFANA_USERNAME"),
            "connector_password": os.getenv("GRAFANA_PASSWORD"),
            "connector_api_key": None,
            "connector_configured": True,
            "connector_accepts_username_password": True,
        },
        {
            "connector_name": "Wazuh Worker Provisioning",
            "connector_type": "3",
            "connector_url": os.getenv("WAZUH_WORKER_PROVISIONING_URL"),
            "connector_username": None,
            "connector_password": None,
            "connector_api_key": None,
            "connector_configured": True,
            "connector_accepts_api_key": False,
        },
    ]

    for connector_data in connector_list:
        # Asynchronously check if connector already exists in the database
        query = select(Connectors).where(Connectors.connector_name == connector_data["connector_name"])
        result = await session.execute(query)
        existing_connector = result.scalars().first()

        if existing_connector is None:
            new_connector = Connectors(**connector_data)
            session.add(new_connector)  # Use session.add() to add new objects
            logger.info(f"Added new connector: {connector_data['connector_name']}")

    # Commit the changes if any new connectors were added
    await session.commit()


async def add_roles_if_not_exist(session: AsyncSession) -> None:
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
