from flask import Blueprint, jsonify, request
from loguru import logger
from app.models.connectors import Connector, WazuhManagerConnector

from app.services.Graylog.messages import MessagesService
from app.services.Graylog.metrics import MetricsService
from app.services.Graylog.index import IndexService
from app.services.Graylog.inputs import InputsService
from app.services.WazuhManager.wazuhmanager import WazuhManagerService

bp = Blueprint("graylog", __name__)


@bp.route("/graylog/messages", methods=["GET"])
def get_messages():
    """
    Endpoint to collect the latest 10 messages from Graylog.

    Returns:
        json: A JSON response containing the list of all the messages.
    """
    service = MessagesService()
    messages = service.collect_messages()
    return messages


@bp.route("/graylog/metrics", methods=["GET"])
def get_metrics():
    """
    Endpoint to collect Graylog metrics.

    Returns:
        json: A JSON response containing the list of all metrics
    """
    service = MetricsService()
    uncommitted_journal_size = service.collect_uncommitted_journal_size()
    metrics = service.collect_throughput_metrics()
    return jsonify(
        {"uncommitted_journal_size": uncommitted_journal_size, "metrics": metrics}
    )


@bp.route("/graylog/indices", methods=["GET"])
def get_indices():
    """
    Endpoint to collect Graylog indices.

    Returns:
        json: A JSON response containing the list of all indices
    """
    service = IndexService()
    indices = service.collect_indices()
    return indices


@bp.route("/graylog/indices/<index_name>/delete", methods=["DELETE"])
def delete_index(index_name):
    """
    Endpoint to delete a Graylog index.

    Args:
        index_name (str): The name of the index to be deleted.

    Returns:
        json: A JSON response containing the result of the deletion.
    """
    service = IndexService()
    result = service.delete_index(index_name)
    return result


@bp.route("/graylog/inputs", methods=["GET"])
def get_inputs():
    """
    Endpoint to collect Graylog inputs.

    Returns:
        json: A JSON response containing the list of all inputs
    """
    service = InputsService()
    running_inputs = service.collect_running_inputs()
    configured_inputs = service.collect_configured_inputs()
    return jsonify(
        {"running_inputs": running_inputs, "configured_inputs": configured_inputs}
    )
