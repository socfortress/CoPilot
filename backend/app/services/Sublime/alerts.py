from typing import Dict

import requests
from loguru import logger

from app import db

from app.services.Sublime.universal import UniversalService
from app.models.sublime_alerts import SublimeAlerts


class SublimeAlertsService:
    """
    A service class that encapsulates the logic for receiving alerts from Sublime.

    First we verify the received payload contains `{data: {message: {"id"}}}`.

    Then we submit the payload to the database table `sublime_alerts`.
    """

    def verify_payload(self, data: Dict[str, object]) -> bool:
        """
        Verify the received payload contains `{data: {message: {"id"}}}`.

        Args:
            payload (Dict[str, object]): The payload received from Sublime.

        Returns:
            bool: True if the payload is valid, False otherwise.
        """
        try:
            data["data"]["message"]["id"]
        except KeyError:
            return {"success": False, "message": "Invalid payload."}
        return {"success": True, "message": "Valid payload.", "message_id": data["data"]["message"]["id"]}

    def store_sublime_alert(self, message_id: str) -> Dict[str, object]:
        """
        Store the received payload in the database table `sublime_alerts`.

        Args:
            message_id (str): The message ID of the payload received from Sublime.

        Returns:
            Dict[str, object]: A dictionary containing the success status and a message.
        """
        # Verify the payload is valid.
        sublime_alert = SublimeAlerts(
            message_id=message_id,

        )
        db.session.add(sublime_alert)
        db.session.commit()

        return {"success": True, "message": "Successfully stored payload."}

