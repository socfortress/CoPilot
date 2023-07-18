from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.models.connectors import SocfortressThreatIntelConnector
from app.services.threat_intel.socfortress.universal import (
    SocfortressThreatIntelService,
)
from app.services.WazuhIndexer.ioc_search import IocSearchService

bp = Blueprint("threatintel", __name__)


@bp.route("/threatintel/socfortress/<ioc_value>", methods=["GET"])
def get_socfortress_threatintel(ioc_value: str) -> jsonify:
    """
    Endpoint to check IoC in Socfortress Threat Intel.

    Returns:
        jsonify: A JSON response containing the list of all alerts from Socfortress.
    """
    logger.info("Received request to check IoC in Socfortress Threat Intel")
    ioc_enriched = SocfortressThreatIntelService("SocfortressThreatIntel").invoke_socfortress_threat_intel(data=ioc_value)
    return jsonify(ioc_enriched)


@bp.route("/threatintel/socfortress/search/wazuh", methods=["POST"])
def search_wazuh_threatintel() -> jsonify:
    """
    Endpoint to search IoC in Wazuh Threat Intel.

    Returns:
        jsonify: A JSON response containing the list of all alerts from Wazuh.
    """
    logger.info("Received request to search IoC in Wazuh Threat Intel")
    service = IocSearchService()
    field_name = request.json.get("field_name")
    time_range = request.json.get("time_range")
    # verify connection to SOCFortress Threat Intel
    verified_connection = SocfortressThreatIntelConnector("SocfortressThreatIntel").verify_connection()
    try:
        if verified_connection["response"] is None:
            message = {"message": "Connection to SOCFortress Threat Intel failed", "success": False}
            return jsonify(message)
    except Exception:
        ioc_searched = service.search_ioc(field_name=field_name, time_range=time_range)
        return jsonify(ioc_searched)
