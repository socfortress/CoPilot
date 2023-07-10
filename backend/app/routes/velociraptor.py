from flask import Blueprint
from flask import jsonify
from flask import request

# from app.models.connectors import Connector
# from app.models.connectors import WazuhManagerConnector
# from app.services.agents.agents import AgentService
# from app.services.agents.agents import AgentSyncService
from app.services.Velociraptor.artifacts import ArtifactsService
from app.services.Velociraptor.universal import UniversalService

# from loguru import logger


bp = Blueprint("velociraptor", __name__)


@bp.route("/velociraptor/artifacts", methods=["GET"])
def get_artifacts():
    """
    Endpoint to list all available artifacts.
    It processes each artifact to verify the connection and returns the results.

    Returns:
        json: A JSON response containing the list of all available artifacts along with their connection verification
        status.
    """
    service = ArtifactsService()
    artifacts = service.collect_artifacts()
    return artifacts


@bp.route("/velociraptor/artifacts/linux", methods=["GET"])
def get_artifacts_linux():
    """
    Endpoint to list all available artifacts.
    It processes each artifact to verify the connection and returns the results where the name
    begins with `Linux`.

    Returns:
        json: A JSON response containing the list of all available artifacts along with their connection verification
        status.
    """
    service = ArtifactsService()
    linux_artifacts = service.collect_artifacts_linux()
    return linux_artifacts


@bp.route("/velociraptor/artifacts/windows", methods=["GET"])
def get_artifacts_windows():
    """
    Endpoint to list all available artifacts.
    It processes each artifact to verify the connection and returns the results where the name
    begins with `Windows`.

    Returns:
        json: A JSON response containing the list of all available artifacts along with their connection verification
        status.
    """
    service = ArtifactsService()
    windows_artifacts = service.collect_artifacts_windows()
    return windows_artifacts


@bp.route("/velociraptor/artifacts/mac", methods=["GET"])
def get_artifacts_mac():
    """
    Endpoint to list all available artifacts.
    It processes each artifact to verify the connection and returns the results where the name
    begins with `MacOS`.

    Returns:
        json: A JSON response containing the list of all available artifacts along with their connection verification
        status.
    """
    service = ArtifactsService()
    mac_artifacts = service.collect_artifacts_macos()
    return mac_artifacts


@bp.route("/velociraptor/artifacts/collection", methods=["POST"])
def collect_artifact():
    """
    Endpoint to collect an artifact.
    It collects the artifact name and client name from the request body and returns the results.

    Returns:
        json: A JSON response containing the list of all available artifacts along with their connection verification
        status.
    """
    req_data = request.get_json()
    artifact_name = req_data["artifact_name"]
    client_name = req_data["client_name"]
    service = UniversalService()
    client_id = service.get_client_id(client_name=client_name)["results"][0][
        "client_id"
    ]
    if client_id is None:
        return (
            jsonify(
                {
                    "message": f"{client_name} has not been seen in the last 30 seconds and may not be online with the "
                    "Velociraptor server.",
                    "success": False,
                },
            ),
            500,
        )

    artifact_service = ArtifactsService()
    artifact_results = artifact_service.run_artifact_collection(
        client_id=client_id,
        artifact=artifact_name,
    )
    return artifact_results
