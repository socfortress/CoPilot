from flask import Blueprint, jsonify, request, Response
from loguru import logger
from typing import Tuple, Union

from app.services.Velociraptor.artifacts import ArtifactsService
from app.services.Velociraptor.universal import UniversalService

bp = Blueprint("velociraptor", __name__)

def get_client_info(client_name: str) -> Tuple[Union[str, None], Union[str, None], Union[Response, None]]:
    """
    Fetch client information based on client name.

    Args:
        client_name (str): The name of the client.

    Returns:
        tuple: Client ID, Client OS, and an error response if any.
    """
    service = UniversalService()
    client_info = service.get_client_id(client_name=client_name)["results"][0]
    if client_info is None:
        return None, None, jsonify(
            {
                "message": f"{client_name} has not been seen in the last 30 seconds and may not be online with the Velociraptor server.",
                "success": False,
            }
        ), 500
    return client_info["client_id"], client_info["os_info"]["system"], None

@bp.route("/velociraptor/artifacts/os/<filter_os>", methods=["GET"])
def get_artifacts(filter_os: str = None) -> Response:
    """
    Fetch artifacts based on the OS filter if provided.

    Args:
        filter_os (str, optional): The OS filter for artifacts.

    Returns:
        Response: A Flask JSON response containing the artifacts.
    """
    service = ArtifactsService()
    if filter_os:
        artifacts = service.collect_artifacts_filtered(filter_os)
    else:
        artifacts = service.collect_artifacts()
    return artifacts

@bp.route("/velociraptor/artifacts/hostname/<hostname>", methods=["GET"])
def get_artifacts_by_hostname(hostname: str) -> Response:
    """
    Fetch artifacts based on hostname.

    Args:
        hostname (str): The hostname for which to fetch artifacts.

    Returns:
        Response: A Flask JSON response containing the artifacts.
    """
    service = ArtifactsService()
    artifacts = service.collect_artifacts_by_hostname(hostname=hostname)
    return artifacts

@bp.route("/velociraptor/operation", methods=["POST"])
def execute_operation() -> Response:
    """
    Execute an operation like artifact collection, remote command execution, or quarantine.

    Returns:
        Response: A Flask JSON response containing the result of the operation.
    """
    req_data = request.get_json()
    client_name = req_data["client_name"]
    operation = req_data["operation"]
    action = req_data.get("action", None)
    command = req_data.get("command", None)

    client_id, client_os, error_response = get_client_info(client_name)
    if error_response:
        return error_response

    service = ArtifactsService()

    if operation == "collect_artifact":
        artifact_name = req_data["artifact_name"]
        return service.run_artifact_collection(client_id=client_id, artifact=artifact_name)

    elif operation == "run_command":
        artifact_name = req_data["artifact_name"]
        return service.run_remote_command(client_id=client_id, artifact=artifact_name, command=command)

    elif operation == "quarantine":
        if action is None:
            return jsonify({"message": "Action is required.", "success": False}), 500
        return service.quarantine_endpoint(client_id=client_id, client_os=client_os, action=action)

    else:
        return jsonify({"message": "Invalid operation", "success": False}), 400
