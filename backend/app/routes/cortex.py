from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.services.cortex.analyzers import AnalyzerService
from app.services.cortex.universal import UniversalService

bp = Blueprint("cortex", __name__)


@bp.route("/cortex/analyzers", methods=["GET"])
def receive_cortex_analyzers():
    """
    API Endpoint for receiving call to retrieve Cortex Analyzers.
    Accepts GET request.
    """
    logger.info(
        "Received request to invoke Cortex to list available analyzers.",
    )

    analyzers = AnalyzerService().get_analyzers()

    return jsonify(analyzers), 200


@bp.route("/cortex/analyzers/run", methods=["POST"])
def receive_cortex_analyzers_run():
    """
    API Endpoint for receiving call to run Cortex Analyzers.
    Accepts POST request with JSON body of `analyzer_name` and `artifact`.
    """
    logger.info(
        "Received request to invoke Cortex to run an analyzer.",
    )
    data = request.get_json()
    logger.debug(f"Data: {data}")
    if not data:
        return jsonify({"message": "No data received."}), 400
    if "analyzer_name" not in data:
        return (
            jsonify({"message": "Missing required data - analyzer_name.", "success": False}),
            400,
        )
    if "artifact" not in data:
        return (
            jsonify({"message": "Missing required data - artifact.", "success": False}),
            400,
        )

    # Check if the artifact is valid
    is_valid, data_type = UniversalService("Cortex").is_valid_datatype(value=data["artifact"])
    if not is_valid:
        return jsonify({"message": "Invalid artifact.", "success": False}), 400

    # Run the analyzer
    analyzer_service = AnalyzerService().run_and_wait_for_analyzer(
        analyzer_name=data["analyzer_name"],
        ioc_value=data["artifact"],
        data_type=data_type,
    )

    return jsonify(analyzer_service), 200
