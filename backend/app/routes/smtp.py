from typing import Any
from typing import Dict

from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.services.smtp.universal import UniversalEmailCredentials

bp = Blueprint("smtp", __name__)


@bp.route("/smtp/credential", methods=["POST"])
def put_credentials() -> jsonify:
    """
    Endpoint to store credentials into `smtp_credentials` table.

    Returns:
        jsonify: A JSON response containing if the credentials were stored successfully.
    """
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400

    email = request.json.get('email', None)
    password = request.json.get('password', None)
    smtp_server = request.json.get('smtp_server', None)
    smtp_port = request.json.get('smtp_port', None)

    if not all([email, password, smtp_server, smtp_port]):
        return jsonify({"message": "Missing JSON in request", "success": False}), 400

    new_credential = UniversalEmailCredentials.create(email, password, smtp_server, smtp_port)

    return jsonify(new_credential), 201

@bp.route("/smtp/credentials", methods=["GET"])
def get_credentials() -> jsonify:
    """
    Endpoint to list all credentials from the `smtp_credentials` table.

    Returns:
        jsonify: A JSON response containing the list of all credentials from SMTP.
    """
    logger.info("Received request to get all SMTP credentials")
    credentials = UniversalEmailCredentials.read_all()
    return jsonify(credentials)
