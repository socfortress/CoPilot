from flask import Blueprint
from flask import jsonify
from loguru import logger

from app.services.InfluxDB.checks import InfluxDBChecksService

bp = Blueprint("influxdb", __name__)


@bp.route("/influxdb/checks", methods=["GET"])
def get_checks() -> jsonify:
    """
    Endpoint to retrive list of InfluxDB checks.
    Requires API token of `admin` user.

    Returns:
        jsonify: A JSON response containing the list of all checks from InfluxDB.

    """
    logger.info("Received request to get all InfluxDB checks")
    service = InfluxDBChecksService.from_connector_details("InfluxDB")
    checks = service.collect_checks()
    return jsonify(checks)
