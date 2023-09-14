from typing import Dict
from typing import List
from typing import Union

import requests
from loguru import logger

from app import db
from app.models.sublime_alerts import SublimeAlerts
from app.services.sublime.universal import UniversalService


class InvalidPayloadError(Exception):
    """
    Exception to be raised when the payload is invalid.
    """

    pass


class SublimeSession:
    """
    Handles the session and connection to the Sublime server.

    Attributes:
        session (requests.Session): The session object for making HTTP requests.
        connector_url (str): The base URL for the Sublime API.
    """

    def __init__(self, connector_url: str, connector_api_key: str):
        """
        The constructor for SublimeSession class.

        Args:
            connector_url (str): The base URL for the Sublime API.
            connector_api_key (str): The API key for the Sublime API.
        """
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {connector_api_key}", "Content-Type": "application/json"},
        )
        self.connector_url = connector_url

    def send_request(self, url: str) -> requests.Response:
        """
        Sends a GET request to a specific URL.

        Args:
            url (str): The URL to send the GET request to.

        Returns:
            requests.Response: The response object from the GET request.
        """
        return self.session.get(url, verify=False)


class SublimeAlertsService:
    """
    Handles operations related to Sublime alerts.

    Attributes:
        session (SublimeSession): The session object for making HTTP requests.
        connector_url (str): The base URL for the Sublime API.
        connector_api_key (str): The API key for the Sublime API.
    """

    def __init__(self, session: SublimeSession, connector_url: str, connector_api_key: str):
        """
        The constructor for SublimeAlertsService class.

        Args:
            session (SublimeSession): The session object for making HTTP requests.
            connector_url (str): The base URL for the Sublime API.
            connector_api_key (str): The API key for the Sublime API.
        """
        self.session = session
        self.connector_url = connector_url
        self.connector_api_key = connector_api_key

    @classmethod
    def from_connector_details(cls, connector_name: str) -> "SublimeAlertsService":
        """
        Creates an instance of SublimeAlertsService using connector details.

        Args:
            connector_name (str): The name of the connector.

        Returns:
            SublimeAlertsService: An instance of the class.
        """
        connector_url, connector_api_key = UniversalService().collect_sublime_details(connector_name)
        session = SublimeSession(connector_url, connector_api_key)
        return cls(session, connector_url, connector_api_key)

    def validate_payload(self, data: Dict[str, object]) -> str:
        """
        Validates the payload received from the Sublime alert webhook.

        Args:
            data (Dict[str, object]): The data received from the webhook.

        Returns:
            str: The message ID from the payload.

        Raises:
            InvalidPayloadError: If the payload is invalid.
        """
        try:
            return data["data"]["message"]["id"]
        except KeyError:
            raise InvalidPayloadError("Invalid payload.")

    def store_alert(self, message_id: str) -> None:
        """
        Stores a Sublime alert in the database.

        Args:
            message_id (str): The ID of the message to be stored.
        """
        sublime_alert = SublimeAlerts(message_id=message_id)
        db.session.add(sublime_alert)
        db.session.commit()
        logger.info(f"Successfully stored payload with message ID {message_id}.")

    def collect_alerts(self) -> Dict[str, Union[bool, str, List[Dict[str, str]]]]:
        """
        Collects alerts from Sublime and the database.

        Returns:
            Dict[str, Union[bool, str, List[Dict[str, str]]]]: A dictionary containing the success status,
                a message, and potentially the message details.
        """
        if not self._are_sublime_details_collected():
            return {
                "message": "Failed to collect Sublime details",
                "success": False,
            }

        alerts = self._collect_alerts_from_db()
        if alerts["success"] is False:
            return alerts

        messages = self._collect_alerts_from_sublime(message_ids=alerts["message_ids"])
        if messages["success"] is False:
            return messages

        return {
            "message": "Successfully collected alerts",
            "success": True,
            "message_details": messages["message_details"],
        }

    def _are_sublime_details_collected(self) -> bool:
        """
        Checks whether the details for the Sublime connector were successfully collected.

        Returns:
            bool: True if all details were collected, False otherwise.
        """
        return all([self.connector_url, self.connector_api_key])

    def _collect_alerts_from_db(self) -> Dict[str, Union[bool, str, List[str]]]:
        """
        Collects alerts from the database.

        Returns:
            Dict[str, Union[bool, str, List[str]]]: A dictionary containing the success status,
                a message, and potentially the message IDs.
        """
        try:
            message_ids = [alert.message_id for alert in SublimeAlerts.query.all()]
        except Exception as err:
            logger.error(f"Failed to collect message ids from database: {err}")
            return {
                "message": "Failed to collect message ids from database",
                "success": False,
            }

        return {
            "message": "Successfully collected message ids from database",
            "success": True,
            "message_ids": message_ids,
        }

    def _collect_alerts_from_sublime(self, message_ids: List[str]) -> Dict[str, Union[bool, str, List[Dict[str, str]]]]:
        """
        Collects alerts from Sublime.

        Args:
            message_ids (List[str]): A list of message IDs to collect.

        Returns:
            Dict[str, Union[bool, str, List[Dict[str, str]]]]: A dictionary containing the success status,
                a message, and potentially the message details.
        """
        try:
            message_details = []
            for message_id in message_ids:
                response = self.session.send_request(f"{self.connector_url}/v0/messages/{message_id}")
                response.raise_for_status()
                message_details.append(response.json())

            return {
                "message": "Successfully collected messages from Sublime",
                "success": True,
                "message_details": message_details,
            }
        except requests.exceptions.HTTPError as err:
            return self._handle_request_error(err)

    def _handle_request_error(self, err: Exception) -> Dict[str, Union[bool, str]]:
        """
        Handles a request error.

        Args:
            err (Exception): The exception that was raised.

        Returns:
            Dict[str, Union[bool, str]]: A dictionary containing the success status and a message.
        """
        logger.error(f"Failed to collect messages from Sublime: {err}")
        return {
            "message": "Failed to collect messages from Sublime",
            "success": False,
        }

    def _collect_messages(self) -> Dict[str, Union[bool, str, Dict[str, str]]]:
        """
        Collects messages from Sublime.

        Returns:
            Dict[str, Union[bool, str, Dict[str, str]]]: A dictionary containing the success status,
                a message, and potentially the messages.
        """
        try:
            response = self.session.send_request(f"{self.connector_url}/v0/messages/groups")
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            return self._handle_request_error(err)

        return {
            "message": "Successfully collected messages from Sublime",
            "success": True,
            "messages": response.json(),
        }
