from app.models.agents import (
    AgentMetadata,
    agent_metadata_schema,
    agent_metadatas_schema,
)
from typing import Dict, List
from app import db
from datetime import datetime
import requests
from loguru import logger
from elasticsearch7 import Elasticsearch
from app.models.connectors import connector_factory, Connector


class UniversalService:
    """
    A service class that encapsulates the logic for polling messages from the Wazuh-Indexer.
    """

    def __init__(self) -> None:
        self.collect_shuffle_details("Shuffle")
        (
            self.connector_url,
            self.connector_api_key,
        ) = self.collect_shuffle_details("Shuffle")

    def collect_shuffle_details(self, connector_name: str):
        """
        Collects the details of the Shuffle connector.

        Args:
            connector_name (str): The name of the Shuffle connector.

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
