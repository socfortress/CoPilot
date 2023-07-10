from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import dfir_iris_client
import requests
from dfir_iris_client.case import Case
from dfir_iris_client.helper.utils import assert_api_resp
from dfir_iris_client.helper.utils import get_data_from_resp
from dfir_iris_client.session import ClientSession
from elasticsearch7 import Elasticsearch
from loguru import logger

from app import db
from app.models.agents import AgentMetadata
from app.models.agents import agent_metadata_schema
from app.models.agents import agent_metadatas_schema
from app.models.connectors import Connector
from app.models.connectors import connector_factory


class UniversalService:
    """
    A service class that encapsulates the logic for polling messages from DFIR-IRIS.
    """

    def __init__(self, connector_name: str) -> None:
        self.connector_url, self.connector_api_key = self.collect_iris_details(
            connector_name,
        )

    def collect_iris_details(self, connector_name: str):
        """
        Collects the details of the DFIR-IRIS connector.

        Args:
            connector_name (str): The name of the DFIR-IRIS connector.

        Returns:
            tuple: A tuple containing the connection URL, and api key.
        """
        connector_instance = connector_factory.create(connector_name, connector_name)
        connection_successful = connector_instance.verify_connection()
        if connection_successful:
            connection_details = Connector.get_connector_info_from_db(connector_name)
            return (
                connection_details.get("connector_url"),
                connection_details.get("connector_api_key"),
            )
        else:
            return None, None

    def create_session(self) -> Optional[ClientSession]:
        """
        Create a session with DFIR-IRIS.

        This method creates a session with DFIR-IRIS and returns the session object.
        If a session cannot be established, an error is logged and None is returned.

        Returns:
            session: A session object for DFIR-IRIS.
        """
        try:
            logger.info("Creating session with DFIR-IRIS.")
            session = ClientSession(
                host=self.connector_url,
                apikey=self.connector_api_key,
                agent="iris-client",
                ssl_verify=False,
                timeout=120,
                proxy=None,
            )
            logger.info("Session created.")
            return {"success": True, "session": session}
        except Exception as e:
            logger.error(f"Error creating session with DFIR-IRIS: {e}")
            return {
                "success": False,
                "message": "Connection to DFIR-IRIS unsuccessful.",
            }

    def fetch_and_parse_data(self, session, action, *args):
        """
        General method to fetch and parse data from DFIR-IRIS.

        Args:
            session: ClientSession object.
            action: callable, the action to be performed (e.g., list_cases or get_case)
            args: arguments for the action callable

        Returns:
            dict: A dictionary containing the data and a success status.
        """
        try:
            logger.info(f"Executing {action.__name__}... on args: {args}")
            status = action(*args)
            assert_api_resp(status, soft_fail=False)
            data = get_data_from_resp(status)
            logger.info(f"Successfully executed {action.__name__}")
            return {"success": True, "data": data}
        except Exception as err:
            logger.error(f"Failed to execute {action.__name__}: {err}")
            return {"success": False}
