from datetime import datetime

import requests
from loguru import logger

from app import db
from app.models.agents import AgentMetadata
from app.models.agents import agent_metadata_schema
from app.models.agents import agent_metadatas_schema
from app.models.connectors import Connector
from app.models.connectors import GraylogConnector
from app.models.connectors import connector_factory
from app.services.Graylog.universal import UniversalService


class MessagesService:
    """
    A service class that encapsulates the logic for polling messages from Graylog.
    """

    def collect_messages(self):
        """
        Collects the latest 10 messages from Graylog.

        Returns:
            list: A list containing the messages.
        """
        (
            connector_url,
            connector_username,
            connector_password,
        ) = UniversalService().collect_graylog_details("Graylog")
        if (
            connector_url is None
            or connector_username is None
            or connector_password is None
        ):
            return {"message": "Failed to collect Graylog details", "success": False}
        else:
            try:
                # Get the Graylog Journal Messages where a parameter of `page` is passed with an integer value of `1`
                page_number = 1
                graylog_messages = requests.get(
                    f"{connector_url}/api/system/messages?page={page_number}",
                    auth=(connector_username, connector_password),
                    verify=False,
                )
                # If the response is successful, return the messages as a list
                if graylog_messages.status_code == 200:
                    logger.info(
                        f"Received {len(graylog_messages.json()['messages'])} messages from Graylog",
                    )
                    return {
                        "message": "Successfully retrieved messages",
                        "success": True,
                        "graylog_messages": graylog_messages.json()["messages"],
                    }
                # Otherwise, return an error message
                else:
                    logger.error(
                        f"Failed to collect messages from Graylog: {graylog_messages.json()}",
                    )
                    return {
                        "message": "Failed to collect messages from Graylog",
                        "success": False,
                    }
            except Exception as e:
                logger.error(f"Failed to collect messages from Graylog: {e}")
                return {
                    "message": "Failed to collect messages from Graylog",
                    "success": False,
                }
