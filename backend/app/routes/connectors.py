from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app import db
from app.models.models import Connectors
from app.models.models import ConnectorsAvailable
from app.models.models import connectors_available_schema
from app.services.connectors.connectors import ConnectorService

bp = Blueprint("connectors", __name__)

api_key_connector = ["Shuffle", "DFIR-IRIS", "Velociraptor", "Sublime"]


def validate_and_update_connector(id, request_data, service, api_key=False):
    if api_key:
        data_validated = service.validate_request_data_api_key(request_data)
    else:
        data_validated = service.validate_request_data(request_data)

    if data_validated["success"]:
        service.update_connector(int(id), request_data)
        return service.verify_connector_connection(int(id))
    else:
        return jsonify(data_validated), 400


@bp.route("/connectors", methods=["GET"])
def list_connectors_available():
    try:
        logger.info("Received request to get all available connectors")
        connectors_service = ConnectorService(db)
        connectors = ConnectorsAvailable.query.all()
        result = connectors_available_schema.dump(connectors)

        instantiated_connectors = [
            connectors_service.process_connector(connector["connector_name"])
            for connector in result
            if connectors_service.process_connector(connector["connector_name"])
        ]

        return {"message": "All available connectors", "connectors": instantiated_connectors, "success": True}
    except Exception as e:
        logger.error(f"Error while getting all available connectors: {e}")
        return {"message": "Error while getting all available connectors", "success": False}, 500


@bp.route("/connectors/<id>", methods=["GET"])
def get_connector_details(id: str):
    logger.info("Received request to get a connector details")
    service = ConnectorService(db)
    connector = service.validate_connector_exists(int(id))

    if connector["success"]:
        connector = Connectors.query.get(id)
        instantiated_connector = service.process_connector(connector.connector_name)
        return {"message": "Connector details", "connector": instantiated_connector, "success": True}
    else:
        return {"message": "Connector not found", "success": False}, 404


@bp.route("/connectors/<id>", methods=["PUT"])
def update_connector_route(id: str):
    logger.info("Received request to update connector")

    request_data = request.get_json()
    service = ConnectorService(db)
    connector = service.validate_connector_exists(int(id))

    if connector["success"]:
        if connector["connector_name"] in api_key_connector:
            return validate_and_update_connector(id, request_data, service, api_key=True)
        else:
            return validate_and_update_connector(id, request_data, service)
    else:
        return jsonify(connector), 404


@bp.route("/connectors/upload", methods=["POST"])
def upload_file():
    logger.info("Received request to upload a file")
    # check if the post request has the file part
    if "file" not in request.files:
        logger.error("No file part in the request")
        return {"message": "No file part in the request", "success": False}, 400
    file = request.files["file"]
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == "":
        logger.error("No selected file")
        return {"message": "No selected file", "success": False}, 400

    service = ConnectorService(db)
    return service.save_file(file)
