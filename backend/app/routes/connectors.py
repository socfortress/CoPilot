from flask import Blueprint, jsonify, request
from loguru import logger
from app.models.models import (
    ConnectorsAvailable,
    Connectors,
    connectors_available_schema,
)

from app.services.connectors.connectors import ConnectorService
from app import db

bp = Blueprint("connectors", __name__)


@bp.route("/connectors", methods=["GET"])
def list_connectors_available():
    """
    Endpoint to list all available connectors.
    It processes each connector to verify the connection and returns the results.

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
def get_connector_details(id):
    """
    Endpoint to get the details of a connector.

    Args:
        id (str): The id of the connector to be fetched.

    Returns:
        json: A JSON response containing the details of the connector.
    """
    # Call service function instead of direct function call
    service = ConnectorService(db)
    connector_validated = service.validate_connector_exists(
        int(id)
    )  # convert id to integer
    logger.info(connector_validated)
    if connector_validated["success"] == False:
        return jsonify(connector_validated), 404

    # Fetch connector using the ID
    connector = Connectors.query.get(id)
    # Call service function instead of direct function call
    instantiated_connector = service.process_connector(connector.connector_name)
    return jsonify(instantiated_connector)


@bp.route("/connectors/<id>", methods=["PUT"])
def update_connector_route(id):
    """
    Endpoint to update a connector.

    Args:
        id (str): The id of the connector to be updated.

    Returns:
        json: A JSON response containing the success status of the update operation and a message indicating the status. If the update operation was successful, it returns the connector name and the status of the connection verification.
    """
    api_key_connector = ["Shuffle", "DFIR-IRIS", "Velociraptor"]

    request_data = request.get_json()
    service = ConnectorService(db)
    connector_validated = service.validate_connector_exists(
        int(id)
    )  # convert id to integer
    logger.info(connector_validated)
    if connector_validated["success"] == False:
        return jsonify(connector_validated), 404

    if connector_validated["connector_name"] in api_key_connector:
        data_validated = service.validate_request_data_api_key(request_data)
        if data_validated["success"] == False:
            return jsonify(data_validated), 400
        else:
            service.update_connector(int(id), request_data)
            return service.verify_connector_connection(int(id))

    data_validated = service.validate_request_data(request_data)
    if data_validated["success"] == False:
        return jsonify(data_validated), 400

    service.update_connector(int(id), request_data)
    return service.verify_connector_connection(int(id))
