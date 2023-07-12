from typing import Any
from typing import Dict

from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.services.Sublime.alerts import InvalidPayloadError
from app.services.Sublime.alerts import SublimeAlertsService
from app.services.Sublime.messages import MessagesService

bp = Blueprint("sublime", __name__)


@bp.route("/sublime/alert", methods=["POST"])
def get_alerts() -> jsonify:
    """
    Endpoint to store alert in the `sublime_alerts` table.

    Returns:
        jsonify: A JSON response containing if the alert was stored successfully.
    """
    logger.info("Received request to store Sublime alert")
    data: Dict[str, Any] = request.get_json()
    service = SublimeAlertsService()

    try:
        message_id = service.validate_payload(data=data)
        service.store_alert(message_id=message_id)
        return jsonify({"message": "Successfully stored payload.", "success": True}), 200
    except InvalidPayloadError:
        logger.error("Received invalid payload.")
        return jsonify({"message": "Invalid payload.", "success": False}), 400


@bp.route("/sublime/messages", methods=["GET"])
def get_messages() -> jsonify:
    """
    Endpoint to list all available messages from Sublime.

    Returns:
        jsonify: A JSON response containing the list of all messages from Sublime.
    """
    logger.info("Received request to get all Sublime messages")
    service = MessagesService()
    messages = service.collect_messages()
    return messages
