# from datetime import datetime

# import requests
# from loguru import logger

# from app.models.connectors import GraylogConnector
# from app import db
# from app.models.agents import AgentMetadata
# from app.models.agents import agent_metadata_schema
# from app.models.agents import agent_metadatas_schema
from app.models.connectors import Connector
from app.models.connectors import connector_factory


class UniversalService:
    """
    A service class that encapsulates the logic for polling messages from Graylog.
    """

    def __init__(self) -> None:
        self.collect_graylog_details("Graylog")

    def collect_graylog_details(self, connector_name: str):
        """
        Collects the details of the Graylog connector.

        Args:
            connector_name (str): The name of the Graylog connector.

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
