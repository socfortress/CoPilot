from typing import Any
from typing import Dict

from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.services.Sublime.alerts import InvalidPayloadError
from app.services.Sublime.alerts import SublimeAlertsService

bp = Blueprint("sublime", __name__)


@bp.route("/sublime/alert", methods=["POST"])
def put_alert() -> jsonify:
    """
    Endpoint to store alert in the `sublime_alerts` table.
    Invoked by the Sublime alert webhook which is configured in the Sublime UI.

    Returns:
        jsonify: A JSON response containing if the alert was stored successfully.
    """
    logger.info("Received request to store Sublime alert")
    data: Dict[str, Any] = request.get_json()
    service = SublimeAlertsService.from_connector_details("Sublime")

    try:
        message_id = service.validate_payload(data=data)
        service.store_alert(message_id=message_id)
        return jsonify({"message": "Successfully stored payload.", "success": True}), 200
    except InvalidPayloadError:
        logger.error("Received invalid payload.")
        return jsonify({"message": "Invalid payload.", "success": False}), 400


@bp.route("/sublime/alerts", methods=["GET"])
def get_alerts() -> jsonify:
    """
    Endpoint to list all alerts from the `sublime_alerts` table.

    Returns:
        jsonify: A JSON response containing the list of all alerts from Sublime.
    """
    logger.info("Received request to get all Sublime alerts")
    service = SublimeAlertsService.from_connector_details("Sublime")
    alerts = service.collect_alerts()
    return jsonify(alerts)
