from typing import Dict

import requests
from loguru import logger

from app import db
from app.models.sublime_alerts import SublimeAlerts
from app.services.Sublime.universal import UniversalService


class InvalidPayloadError(Exception):
    """Exception to be raised when the payload is invalid."""

    pass


class SublimeAlertsService:
    """
    A service class that encapsulates the logic for receiving alerts from Sublime.

    The service verifies the received payload contains `{data: {message: {"id"}}}`.
    Then it submits the payload to the database table `sublime_alerts`.
    """

    def validate_payload(self, data: Dict[str, object]) -> str:
        """
        Validate the received payload contains `{data: {message: {"id"}}}`.

        Args:
            data (Dict[str, object]): The payload received from Sublime.

        Returns:
            str: The message ID if the payload is valid.

        Raises:
            InvalidPayloadError: If the payload is not valid.
        """
        try:
            message_id = data["data"]["message"]["id"]
        except KeyError:
            raise InvalidPayloadError("Invalid payload.")

        return message_id

    def store_alert(self, message_id: str):
        """
        Store the received payload in the database table `sublime_alerts`.

        Args:
            message_id (str): The message ID of the payload received from Sublime.
        """
        sublime_alert = SublimeAlerts(message_id=message_id)
        db.session.add(sublime_alert)
        db.session.commit()

        logger.info(f"Successfully stored payload with message ID {message_id}.")
