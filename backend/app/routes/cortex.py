from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.services.cortex.analyzers import AnalyzerService

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
