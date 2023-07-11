from flask import Blueprint
from flask import jsonify

from app.services.WazuhIndexer.alerts import AlertsService

bp = Blueprint("alerts", __name__)


@bp.route("/alerts", methods=["GET"])
def get_alerts() -> jsonify:
    """
    Retrieves all alerts from the AlertsService.

    This endpoint retrieves all available alerts from the AlertsService. It does this by creating an instance of
    the AlertsService class and calling its `collect_alerts` method. The result is a list of all alerts currently
    available.

    Returns:
        jsonify: A JSON response containing a list of alerts. Each item in the list is a dictionary representing an alert,
        containing all its associated data.
    """
    service = AlertsService()
    alerts = service.collect_alerts()
    return jsonify(alerts)
