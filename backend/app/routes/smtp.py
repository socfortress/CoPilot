from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.services.smtp.send_report import EmailReportSender
from app.services.smtp.universal import UniversalEmailCredentials

bp = Blueprint("smtp", __name__)


@bp.route("/smtp/credential", methods=["POST"])
def put_credentials() -> jsonify:
    """
    Endpoint to store credentials into `smtp_credentials` table.

    Returns:
        Tuple[jsonify, int]: A Tuple where the first element is a JSON response
        indicating if the credentials were stored successfully and the second element
        is the HTTP status code.
    """
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400

    email = request.json.get("email", None)
    password = request.json.get("password", None)
    smtp_server = request.json.get("smtp_server", None)
    smtp_port = request.json.get("smtp_port", None)

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


@bp.route("/smtp/report", methods=["POST"])
def send_report() -> jsonify:
    """
    Endpoint to send a report via email.

    Returns:
        Tuple[jsonify, int]: A Tuple where the first element is a JSON response
        indicating if the report was sent successfully and the second element
        is the HTTP status code.
    """
    logger.info("Received request to send a report via email")
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400

    to_email = request.json.get("to_email", None)
    if not to_email:
        return jsonify({"message": "Missing 'to_email' in request", "success": False}), 400

    send_report = EmailReportSender(to_email).send_email_with_pdf()
    return jsonify(send_report), 201
