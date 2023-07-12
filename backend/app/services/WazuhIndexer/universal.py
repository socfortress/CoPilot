# from datetime import datetime
from typing import Dict

# import requests
from elasticsearch7 import Elasticsearch
from loguru import logger

# from app.models.agents import AgentMetadata
# from app.models.agents import agent_metadata_schema
# from app.models.agents import agent_metadatas_schema
from app.models.connectors import Connector
from app.models.connectors import connector_factory

# from typing import List


# from app import db


class UniversalService:
    """
    A service class that encapsulates the logic for polling messages from the Wazuh-Indexer.
    """

    def __init__(self) -> None:
        self.collect_wazuhindexer_details("Wazuh-Indexer")
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = self.collect_wazuhindexer_details("Wazuh-Indexer")
        self.es = Elasticsearch(
            [self.connector_url],
            http_auth=(self.connector_username, self.connector_password),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )

    def collect_wazuhindexer_details(self, connector_name: str):
        """
        Collects the details of the Wazuh-Indexer connector.

        Args:
            connector_name (str): The name of the Wazuh-Indexer connector.

        Returns:
            tuple: A tuple containing the connection URL, username, and password.
        """
        connector_instance = connector_factory.create(connector_name, connector_name)
        connection_successful = connector_instance.verify_connection()
        if connection_successful:
            connection_details = Connector.get_connector_info_from_db(connector_name)
            return (
                connection_details.get("connector_url"),
                connection_details.get("connector_username"),
                connection_details.get("connector_password"),
            )
        else:
            return None, None, None

    def collect_indices(self):
        """
        Collects the indices from the Wazuh-Indexer.

        Returns:
            list: A list containing the indices.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {
                "message": "Failed to collect Wazuh-Indexer details",
                "success": False,
            }

        indices = self._collect_indices()

        if indices["success"]:
            return indices

        return {"message": "Failed to collect indices", "success": False}

    def _collect_indices(self) -> Dict[str, object]:
        """
        Wazuh-Indexer query to retrievce all indices.

        Returns:
            Dict[str, object]: _description_
        """
        try:
            indices_dict = self.es.indices.get_alias("*")
            indices_list = list(indices_dict.keys())
            return {
                "message": "Successfully collected indices",
                "success": True,
                "indices_list": indices_list,
            }
        except Exception as e:
            logger.error(f"Failed to collect indices: {e}")
            return {"message": "Failed to collect indices", "success": False}
