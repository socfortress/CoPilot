from typing import Dict

import requests
from loguru import logger

from app.services.Sublime.universal import UniversalService


class MessagesService:
    """
    A service class that encapsulates the logic for retrieving message details from Sublime.

    Attributes:
        connector_url (str): The URL of the Sublime instance.
        connector_api_key (str): The API key used for the Sublime instance.
        session (requests.Session): A requests session for making HTTP requests.

    Methods:
        _collect_sublime_details: Collects the details of the Sublime connector.
        _are_details_collected: Checks whether the details for the Sublime connector were successfully collected.
        _send_request: Sends a GET request to a provided URL.
        collect_messages: Collects the messages from Sublime.
        _handle_request_error: Handles any errors that occur during a request.
        _collect_messages: Collects the messages from Sublime.
    """

    def __init__(self):
        self._collect_sublime_details()
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {self.connector_api_key}", "Content-Type": "application/json"},
        )

    def _collect_sublime_details(self):
        """
        Collects the details of the Sublime connector.

        The details are collected from a universal service which pulls connector details from a database.

        Returns:
            tuple: A tuple containing the connection URL and API key of the Sublime connector.
        """
        (
            self.connector_url,
            self.connector_api_key,
        ) = UniversalService().collect_sublime_details("Sublime")

    def _are_details_collected(self) -> bool:
        """
        Checks whether the details for the Sublime connector were successfully collected.

        Returns:
            bool: True if all details were collected, False otherwise.
        """
        return all([self.connector_url, self.connector_api_key])

    def _send_request(self, url: str):
        """
        Sends a GET request to a provided URL.

        Args:
            url (str): The URL to send the GET request to.

        Returns:
            requests.Response: The response from the GET request.
        """
        return self.session.get(
            url,
            verify=False,
        )

    def collect_messages(self) -> Dict[str, object]:
        """
        Collects the messages from Sublime.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the workflows.
        """
        if not self._are_details_collected():
            return {
                "message": "Failed to collect Sublime details",
                "success": False,
            }

        messages = self._collect_messages()
        if not messages["success"]:
            return messages

        return {
            "message": "Successfully collected messages",
            "success": True,
            "messages": messages["messages"],
        }

    def _handle_request_error(self, err: Exception) -> Dict[str, object]:
        """
        Handles any errors that occur during a request.

        Args:
            err (Exception): The exception that occurred.

        Returns:
            dict: A dictionary containing the success status and an error message.
        """
        logger.error(f"Failed to collect messages from Sublime: {err}")
        return {
            "message": "Failed to collect messages from Sublime",
            "success": False,
        }

    def _collect_messages(self) -> Dict[str, object]:
        """
        Collects the messages from Sublime.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the workflows.
        """
        try:
            response = self._send_request(f"{self.connector_url}/v0/messages/groups")
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            return self._handle_request_error(err)

        return {
            "message": "Successfully collected messages from Sublime",
            "success": True,
            "messages": response.json(),
        }
