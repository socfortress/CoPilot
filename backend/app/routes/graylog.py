from flask import Blueprint
from flask import jsonify
from loguru import logger

from app.services.graylog.events import EventsService
from app.services.graylog.index import IndexService
from app.services.graylog.inputs import InputsService
from app.services.graylog.messages import MessagesService
from app.services.graylog.metrics import MetricsService
from app.services.graylog.pipelines import PipelinesService
from app.services.graylog.streams import StreamsService

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


@bp.route("/graylog/inputs/<input_id>/state", methods=["GET"])
def get_inputstate(input_id: str) -> dict:
    """
    Endpoint to collect Graylog inputstate.

    Returns:
        dict: A JSON object containing the list of all running and configured inputs.
    """
    logger.info("Received request to get graylog inputstate")
    service = InputsService()
    inputstate = service.collect_inputstate(input_id)
    try:
        # If inputstate.inputstate.message starts with `No input state`, then set the state to STOPPED
        if inputstate["inputstate"]["message"].startswith("No input state"):
            inputstate["inputstate"]["state"] = "STOPPED"
            return inputstate
    except Exception:
        return inputstate


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
    try:
        for input in configured_inputs["configured_inputs"]:
            # Get the ID and invoke the get_inputstate function
            input_id = input["id"]
            inputstate = get_inputstate(input_id)
            # Add the inputstate to the configured_inputs
            input["inputstate"] = inputstate["inputstate"]["state"]
        return jsonify(
            {"configured_inputs": configured_inputs},
        )
    except Exception as e:
        logger.error(e)
        return jsonify(
            {"message": "Error getting inputstate. Make sure Graylog is running and has valid credentials.", "success": False},
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


@bp.route("/graylog/event/definitions", methods=["GET"])
def get_event_definitions() -> dict:
    """
    Endpoint to collect Graylog event definitions.

    Returns:
        dict: A JSON object containing the list of all event definitions.
    """
    logger.info("Received request to get graylog event definitions")
    service = EventsService()
    event_definitions = service.collect_event_definitions()
    return event_definitions


@bp.route("/graylog/event/alerts", methods=["GET"])
def get_alerts() -> dict:
    """
    Endpoint to collect Graylog alerts. Currently collects last 100 alerts.

    Returns:
        dict: A JSON object containing the list of all alerts.
    """
    logger.info("Received request to get graylog alerts")
    service = EventsService()
    alerts = service.collect_alerts()
    return alerts


@bp.route("/graylog/pipeline/rules", methods=["GET"])
def get_pipeline_rules() -> dict:
    """
    Endpoint to collect Graylog pipeline rules.

    Returns:
        dict: A JSON object containing the list of all pipeline rules.
    """
    logger.info("Received request to get graylog pipeline rules")
    service = PipelinesService()
    pipeline_rules = service.collect_pipeline_rules()
    return pipeline_rules


@bp.route("/graylog/pipeline/pipelines", methods=["GET"])
def get_pipelines() -> dict:
    """
    Endpoint to collect Graylog pipelines.

    Returns:
        dict: A JSON object containing the list of all pipelines.
    """
    logger.info("Received request to get graylog pipelines")
    service = PipelinesService()
    pipelines = service.collect_pipelines()
    return pipelines


@bp.route("/graylog/streams", methods=["GET"])
def get_streams() -> dict:
    """
    Endpoint to collect Graylog streams.

    Returns:
        dict: A JSON object containing the list of all streams.
    """
    logger.info("Received request to get graylog streams")
    service = StreamsService()
    try:
        streams = service.collect_streams()
        return streams
    except Exception as e:
        logger.error(e)
        return jsonify(
            {
                "message": "Error getting streams",
                "success": False,
            },
        )


@bp.route("/graylog/streams/<stream_id>/pause", methods=["POST"])
def pause_stream(stream_id: str) -> dict:
    """
    Endpoint to pause a Graylog stream.

    Args:
        stream_id (str): The ID of the stream to be paused.

    Returns:
        dict: A JSON object containing the result of the pause operation.
    """
    logger.info("Received request to pause stream")
    service = StreamsService()
    result = service.pause_stream(stream_id)
    return result


@bp.route("/graylog/streams/<stream_id>/resume", methods=["POST"])
def resume_stream(stream_id: str) -> dict:
    """
    Endpoint to resume a Graylog stream.

    Args:
        stream_id (str): The ID of the stream to be resumed.

    Returns:
        dict: A JSON object containing the result of the resume operation.
    """
    logger.info("Received request to resume stream")
    service = StreamsService()
    result = service.resume_stream(stream_id)
    return result
