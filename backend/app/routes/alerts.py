from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.models.connectors import Connector
from app.models.connectors import WazuhManagerConnector
from app.services.agents.agents import AgentService
from app.services.agents.agents import AgentSyncService
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
