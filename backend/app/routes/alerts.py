from flask import Blueprint, jsonify, request
from loguru import logger
from app.models.connectors import Connector, WazuhManagerConnector

from app.services.agents.agents import AgentService, AgentSyncService
from app.services.WazuhIndexer.alerts import AlertsService

bp = Blueprint("alerts", __name__)


@bp.route("/alerts", methods=["GET"])
def get_alerts():
    """
    Endpoint to list all available alerts.
    It processes each alert to verify the connection and returns the results.

    Returns:
        json: A JSON response containing the list of all available alerts along with their connection verification status.
    """
    service = AlertsService()
    alerts = service.collect_alerts()
    return alerts
