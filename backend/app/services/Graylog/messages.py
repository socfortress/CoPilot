# from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Union

import requests
from loguru import logger

from app.services.graylog.universal import UniversalService


class MessagesService:
    """
    A service class that encapsulates the logic for polling messages from Graylog.
    """

    def __init__(self):
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = UniversalService().collect_graylog_details("Graylog")

    def _get_messages_from_graylog(self, page_number: int) -> requests.Response:
        """Fetches messages from Graylog for a specific page number."""
        return requests.get(
            f"{self.connector_url}/api/system/messages?page={page_number}",
            auth=(self.connector_username, self.connector_password),
            verify=False,
        )

    def _handle_message_fetch_error(
        self,
        error: Exception,
    ) -> Dict[str, Union[str, bool]]:
        """Handles exceptions occurred while fetching messages."""
        logger.error(f"Failed to collect messages from Graylog: {error}")
        return {
            "message": "Failed to collect messages from Graylog",
            "success": False,
        }

    def collect_messages(self) -> Dict[str, Union[str, bool, List[Dict[str, Any]]]]:
        """
        Collects the latest 10 messages from Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of Graylog messages.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}
        else:
            try:
                page_number = 1
                graylog_messages = self._get_messages_from_graylog(page_number)

                if graylog_messages.status_code == 200:
                    logger.info(
                        f"Received {len(graylog_messages.json()['messages'])} messages from Graylog",
                    )
                    return {
                        "message": "Successfully retrieved messages",
                        "success": True,
                        "graylog_messages": graylog_messages.json()["messages"],
                    }
                else:
                    logger.error(
                        f"Failed to collect messages from Graylog: {graylog_messages.json()}",
                    )
                    return {
                        "message": "Failed to collect messages from Graylog",
                        "success": False,
                    }
            except Exception as e:
                return self._handle_message_fetch_error(e)
