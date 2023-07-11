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


@bp.route("/connectors", methods=["GET"])
def list_connectors_available():
    """
    Endpoint to retrieve all available connectors.

    Returns:
        json: A JSON response containing the list of all available connectors along with their connection verification status.
    """
    connectors_service = ConnectorService(db)
    connectors = ConnectorsAvailable.query.all()
    result = connectors_available_schema.dump(connectors)

    instantiated_connectors = [
        connectors_service.process_connector(connector["connector_name"])
        for connector in result
        if connectors_service.process_connector(connector["connector_name"])
    ]

    return jsonify(instantiated_connectors)


@bp.route("/connectors/<id>", methods=["GET"])
def get_connector_details(id: str):
    """
    Endpoint to retrieve the details of a connector.

    Args:
        id (str): The ID of the connector to retrieve.

    Returns:
        json: A JSON response containing the details of the connector.
    """
    service = ConnectorService(db)
    connector = service.validate_connector_exists(int(id))

    if connector["success"]:
        connector = Connectors.query.get(id)
        instantiated_connector = service.process_connector(connector.connector_name)
        return jsonify(instantiated_connector)
    else:
        return jsonify(connector), 404


@bp.route("/connectors/<id>", methods=["PUT"])
def update_connector_route(id: str):
    """
    Endpoint to update the details of a connector.

    Args:
        id (str): The ID of the connector to update.

    Returns:
        json: A JSON response containing the success status of the update operation and a message indicating the status.
        If the update operation was successful, it returns the connector name and the status of the connection verification.
    """
    api_key_connector = ["Shuffle", "DFIR-IRIS", "Velociraptor"]

    request_data = request.get_json()
    service = ConnectorService(db)
    connector = service.validate_connector_exists(int(id))

    if connector["success"]:
        if connector["connector_name"] in api_key_connector:
            data_validated = service.validate_request_data_api_key(request_data)
            if data_validated["success"]:
                service.update_connector(int(id), request_data)
                return service.verify_connector_connection(int(id))
            else:
                return jsonify(data_validated), 400
        else:
            data_validated = service.validate_request_data(request_data)
            if data_validated["success"]:
                service.update_connector(int(id), request_data)
                return service.verify_connector_connection(int(id))
            else:
                return jsonify(data_validated), 400
    else:
        return jsonify(connector), 404
