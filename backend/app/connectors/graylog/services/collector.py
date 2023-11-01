from typing import List
from typing import Tuple

from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.schema.collector import ConfiguredInput
from app.connectors.graylog.schema.collector import ConfiguredInputsResponse
from app.connectors.graylog.schema.collector import GraylogIndexItem
from app.connectors.graylog.schema.collector import GraylogIndicesResponse
from app.connectors.graylog.schema.collector import GraylogInputsResponse
from app.connectors.graylog.schema.collector import RunningInput
from app.connectors.graylog.schema.collector import RunningInputsResponse
from app.connectors.graylog.utils.universal import send_get_request


def get_indices_full() -> GraylogIndicesResponse:
    """Get indices from Graylog."""
    logger.info("Getting indices from Graylog")
    indices_collected = send_get_request(endpoint="/api/system/indexer/indices")
    if indices_collected["success"]:
        try:
            indices_data = indices_collected["data"]["all"]["indices"]
        except KeyError:
            raise HTTPException(status_code=500, detail="Failed to collect indices key")

        # Convert the dictionary to a list of GraylogIndexItem
        indices_list = [GraylogIndexItem(index_name=name, index_info=info) for name, info in indices_data.items()]

        return GraylogIndicesResponse(indices=indices_list, success=True, message="Indices collected successfully")
    else:
        return GraylogIndicesResponse(indices=[], success=False, message="Failed to collect indices")


def fetch_configured_inputs() -> Tuple[bool, List[ConfiguredInput]]:
    configured_inputs_collected = send_get_request(endpoint="/api/system/inputs")
    success = configured_inputs_collected.get("success", False)

    if success:
        return True, [ConfiguredInput(**input_data) for input_data in configured_inputs_collected["data"]["inputs"]]
    else:
        logger.error("Failed to fetch configured inputs")
        return False, []


def fetch_running_inputs() -> Tuple[bool, List[RunningInput]]:
    running_inputs_collected = send_get_request(endpoint="/api/system/inputstates")
    success = running_inputs_collected.get("success", False)

    if success:
        return True, [RunningInput(**input_data) for input_data in running_inputs_collected["data"]["states"]]
    else:
        logger.error("Failed to fetch running inputs")
        return False, []


def get_inputs() -> GraylogInputsResponse:
    """Get inputs from Graylog."""
    logger.info("Getting inputs from Graylog")

    config_success, configured_inputs_list = fetch_configured_inputs()
    run_success, running_inputs_list = fetch_running_inputs()

    if config_success and run_success:
        logger.info("Successfully fetched both configured and running inputs")
        return GraylogInputsResponse(
            configured_inputs=configured_inputs_list,
            running_inputs=running_inputs_list,
            success=True,
            message="Successfully retrieved inputs",
        )
    else:
        logger.error("Failed to fetch one or both types of inputs")
        return GraylogInputsResponse(configured_inputs=[], running_inputs=[], success=False, message="Failed to collect inputs")


def get_inputs_running() -> RunningInputsResponse:
    """Get running inputs from Graylog."""
    logger.info("Getting running inputs from Graylog")
    run_success, running_inputs_list = fetch_running_inputs()
    if run_success:
        return RunningInputsResponse(running_inputs=running_inputs_list, success=True, message="Successfully retrieved running inputs")


def get_inputs_configured() -> ConfiguredInputsResponse:
    """Get configured inputs from Graylog."""
    logger.info("Getting configured inputs from Graylog")
    config_success, configured_inputs_list = fetch_configured_inputs()
    if config_success:
        return ConfiguredInputsResponse(
            configured_inputs=configured_inputs_list,
            success=True,
            message="Successfully retrieved configured inputs",
        )


def get_index_names() -> List[str]:
    """
    Gets the names of all the indices in Graylog.

    Returns:
        List[str]: A list of all the index names.
    """
    logger.info("Getting index names from Graylog")

    indices_collected = get_indices_full()

    if indices_collected.success:
        # Access the index_name attribute directly
        return [index.index_name for index in indices_collected.indices]
    else:
        return []


def get_input_ids() -> List[str]:
    """
    Gets the IDs of all the inputs in Graylog.

    Returns:
        List[str]: A list of all the input IDs.
    """
    logger.info("Getting input IDs from Graylog")

    success, inputs_collected = fetch_configured_inputs()

    if success:
        # Access the input_id attribute directly
        return [input.id for input in inputs_collected]
    else:
        return []
