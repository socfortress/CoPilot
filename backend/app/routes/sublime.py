from flask import Blueprint
from flask import jsonify
from loguru import logger
from flask import request
from typing import Any
from typing import Dict

from app.services.Sublime.messages import MessagesService
from app.services.Sublime.alerts import SublimeAlertsService

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
    verify_payload = service.verify_payload(data=data)
    if verify_payload["success"] is False:
        return jsonify(verify_payload)
    alert_stored = service.store_sublime_alert(message_id=verify_payload["message_id"])
    return alert_stored

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
