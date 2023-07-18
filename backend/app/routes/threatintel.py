from typing import Any
from typing import Dict

from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.services.threat_intel.socfortress.universal import SocfortressThreatIntelService

bp = Blueprint("threatintel", __name__)


@bp.route("/threatintel/socfortress/<ioc_value>", methods=["GET"])
def get_socfortress_threatintel(ioc_value: str) -> jsonify:
    """
    Endpoint to check IoC in Socfortress Threat Intel.

    Returns:
        jsonify: A JSON response containing the list of all alerts from Socfortress.
    """
    ioc_enriched = SocfortressThreatIntelService("SocfortressThreatIntel").invoke_socfortress_threat_intel(data=ioc_value)
    return jsonify(ioc_enriched)
