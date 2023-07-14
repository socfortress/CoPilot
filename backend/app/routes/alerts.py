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
    alerts = service.collect_alerts(size=1000)  # replace `collect_all_alerts` with `collect_alerts(size=1000)`
    return jsonify(alerts)


@bp.route("/alerts/top_10", methods=["GET"])
def get_top_10_alerts() -> jsonify:
    """
    Retrieves top 10 alerts from the AlertsService.

    This endpoint retrieves top 10 alerts from the AlertsService. It does this by creating an instance of
    the AlertsService class and calling its `collect_alerts` method. The result is a list of top 10 alerts currently
    available.

    Returns:
        jsonify: A JSON response containing a list of alerts. Each item in the list is a dictionary representing an alert,
        containing all its associated data.
    """
    service = AlertsService()
    alerts = service.collect_alerts(size=10)  # replace `collect_top_10_alerts` with `collect_alerts(size=10)`
    return jsonify(alerts)


@bp.route("/alerts/hosts", methods=["GET"])
def get_hosts() -> jsonify:
    """
    Retrieves all hosts from the AlertsService that have an alert.

    This endpoint retrieves all available hosts from the AlertsService. It does this by creating an instance of
    the AlertsService class and calling its `collect_alerts_by_host` method. The result is a list of all hosts currently
    available.

    Returns:
        jsonify: A JSON response containing a list of hosts. Each item in the list is a dictionary representing a host,
        containing all its associated data.
    """
    service = AlertsService()
    hosts = service.collect_alerts_by_host()
    return jsonify(hosts)
