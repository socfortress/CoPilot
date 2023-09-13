from flask import Blueprint
from flask import jsonify
from loguru import logger

from app.services.Graylog.index import IndexService
from app.services.Graylog.inputs import InputsService
from app.services.Graylog.messages import MessagesService
from app.services.Graylog.metrics import MetricsService

bp = Blueprint("graylog", __name__)


@bp.route("/graylog/messages", methods=["GET"])
def get_messages() -> dict:
    """
    Endpoint to collect the latest 10 messages from Graylog.

    Returns:
        dict: A JSON object containing the list of all the messages.
    """
    logger.info("Received request to get graylog messages")
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
    logger.info("Received request to get graylog metrics")
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
    logger.info("Received request to get graylog indexes")
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
    logger.info("Received request to delete index")
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
    logger.info("Received request to get graylog inputs")
    service = InputsService()
    running_inputs = service.collect_running_inputs()
    configured_inputs = service.collect_configured_inputs()
    return jsonify(
        {"running_inputs": running_inputs, "configured_inputs": configured_inputs},
    )


@bp.route("/graylog/inputs/running", methods=["GET"])
def get_inputs_running() -> dict:
    """
    Endpoint to collect running Graylog inputs.

    Returns:
        dict: A JSON object containing the list of all running and configured inputs.
    """
    logger.info("Received request to get runnning graylog inputs")
    service = InputsService()
    running_inputs = service.collect_running_inputs()
    return jsonify(
        {"running_inputs": running_inputs},
    )

@bp.route("/graylog/inputs/configured", methods=["GET"])
def get_inputs_configured() -> dict:
    """
    Endpoint to collect configured Graylog inputs.

    Returns:
        dict: A JSON object containing the list of all running and configured inputs.
    """
    logger.info("Received request to get configured graylog inputs")
    service = InputsService()
    configured_inputs = service.collect_configured_inputs()
    return jsonify(
        {"configured_inputs": configured_inputs},
    )

@bp.route("/graylog/inputs/<input_id>/stop", methods=["DELETE"])
def stop_input(input_id: str) -> dict:
    """
    Endpoint to stop a Graylog input.

    Args:
        input_id (str): The ID of the input to be stopped.

    Returns:
        dict: A JSON object containing the result of the stop operation.
    """
    logger.info("Received request to stop input")
    service = InputsService()
    result = service.stop_input(input_id)
    return result


@bp.route("/graylog/inputs/<input_id>/start", methods=["PUT"])
def start_input(input_id: str) -> dict:
    """
    Endpoint to start a Graylog input.

    Args:
        input_id (str): The ID of the input to be started.

    Returns:
        dict: A JSON object containing the result of the start operation.
    """
    logger.info("Received request to start input")
    service = InputsService()
    result = service.start_input(input_id)
    return result
