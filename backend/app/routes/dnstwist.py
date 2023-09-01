import json

from app.services.dnstwist.analyze import DNSTwistService
from app.services.dnstwist.universal import UniversalService
from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

bp = Blueprint("dnstwist", __name__)


@bp.route("/dnstwist/registered", methods=["POST"])
def receive_dnstwist_registered():
    """
    API Endpoint for receiving call to run dnstwist.
    Accepts POST request with JSON body of `domain`.
    """
    logger.info(
        "Received request to invoke DNStwist to detect similar registered domains.",
    )
    data = request.get_json()
    logger.debug(f"Data: {data}")
    if not data:
        return jsonify({"message": "No data received."}), 400
    if "domain" not in data:
        return (
            jsonify({"message": "Missing required data - domain.", "success": False}),
            400,
        )

    # Check if the domain is valid
    if not UniversalService.is_domain(data["domain"]):
        return jsonify({"message": "Invalid domain.", "success": False}), 400

    # Invoke dnstwist service
    dnstwist_service = DNSTwistService(data["domain"])
    results = dnstwist_service.analyze_domain_registered()

    # Return the results to the client
    return jsonify(results), 200


@bp.route("/dnstwist/phishing", methods=["POST"])
def receive_dnstwist_phishing():
    """
    API Endpoint for receiving call to run dnstwist.
    Accepts POST request with JSON body of `domain`.
    """
    logger.info("Received request to invoke DNStwist to detect potential Phishing.")
    data = request.get_json()
    logger.debug(f"Data: {data}")
    if not data:
        return jsonify({"message": "No data received."}), 400
    if "domain" not in data:
        return (
            jsonify({"message": "Missing required data - domain.", "success": False}),
            400,
        )

    # Check if the domain is valid
    if not UniversalService.is_domain(data["domain"]):
        return jsonify({"message": "Invalid domain.", "success": False}), 400

    # Invoke dnstwist service
    dnstwist_service = DNSTwistService(data["domain"])
    results = dnstwist_service.analyze_domain_phishing()

    # Return the results to the client
    return jsonify(results), 200
