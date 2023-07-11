from flask import Blueprint
from flask import jsonify

from app.services.Graylog.index import IndexService
from app.services.Graylog.inputs import InputsService
from app.services.Graylog.messages import MessagesService
from app.services.Graylog.metrics import MetricsService

# from loguru import logger


bp = Blueprint("graylog", __name__)


@bp.route("/graylog/messages", methods=["GET"])
def get_messages() -> dict:
    """
    Endpoint to collect the latest 10 messages from Graylog.

    Returns:
        dict: A JSON object containing the list of all the messages.
    """
    service = MessagesService()
    messages = service.collect_messages()
    return messages


@bp.route("/graylog/metrics", methods=["GET"])
def get_metrics() -> dict:
    """
    Endpoint to collect Graylog metrics.

    Returns:
        dict: A JSON object containing the list of all metrics,
              including the uncommitted journal size.
    """
    service = MetricsService()
    uncommitted_journal_size = service.collect_uncommitted_journal_size()
    metrics = service.collect_throughput_metrics()
    return jsonify(
        {"uncommitted_journal_size": uncommitted_journal_size, "metrics": metrics},
    )


@bp.route("/graylog/indices", methods=["GET"])
def get_indices() -> dict:
    """
    Endpoint to collect Graylog indices.

    Returns:
        dict: A JSON object containing the list of all indices.
    """
    service = IndexService()
    indices = service.collect_indices()
    return indices


@bp.route("/graylog/indices/<index_name>/delete", methods=["DELETE"])
def delete_index(index_name: str) -> dict:
    """
    Endpoint to delete a Graylog index.

    Args:
        index_name (str): The name of the index to be deleted.

    Returns:
        dict: A JSON object containing the result of the deletion operation.
    """
    service = IndexService()
    result = service.delete_index(index_name)
    return result


@bp.route("/graylog/inputs", methods=["GET"])
def get_inputs() -> dict:
    """
    Endpoint to collect Graylog inputs.

    Returns:
        dict: A JSON object containing the list of all running and configured inputs.
    """
    service = InputsService()
    running_inputs = service.collect_running_inputs()
    configured_inputs = service.collect_configured_inputs()
    return jsonify(
        {"running_inputs": running_inputs, "configured_inputs": configured_inputs},
    )
