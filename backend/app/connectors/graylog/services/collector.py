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
from app.connectors.graylog.schema.management import UrlWhitelistEntryResponse
from app.connectors.graylog.utils.universal import send_get_request


async def get_indices_full() -> GraylogIndicesResponse:
    """Get indices from Graylog.

    Returns:
        GraylogIndicesResponse: The response object containing the collected indices.

    Raises:
        HTTPException: If there is an error collecting the indices.
    """
    logger.info("Getting indices from Graylog")
    indices_collected = await send_get_request(endpoint="/api/system/indexer/indices")
    if indices_collected["success"]:
        try:
            indices_data = indices_collected["data"]["all"]["indices"]
        except KeyError:
            raise HTTPException(status_code=500, detail="Failed to collect indices key")

        # Convert the dictionary to a list of GraylogIndexItem
        indices_list = [GraylogIndexItem(index_name=name, index_info=info) for name, info in indices_data.items()]

        return GraylogIndicesResponse(
            indices=indices_list,
            success=True,
            message="Indices collected successfully",
        )
    else:
        return GraylogIndicesResponse(
            indices=[],
            success=False,
            message="Failed to collect indices",
        )


async def fetch_configured_inputs() -> Tuple[bool, List[ConfiguredInput]]:
    """
    Fetches the configured inputs from the Graylog server.

    Returns:
        A tuple containing a boolean indicating the success of the request and a list of ConfiguredInput objects.
    """
    configured_inputs_collected = await send_get_request(endpoint="/api/system/inputs")
    success = configured_inputs_collected.get("success", False)

    if success:
        return True, [ConfiguredInput(**input_data) for input_data in configured_inputs_collected["data"]["inputs"]]
    else:
        logger.error("Failed to fetch configured inputs")
        return False, []


async def fetch_running_inputs() -> Tuple[bool, List[RunningInput]]:
    """
    Fetches the running inputs from the Graylog API.

    Returns:
        A tuple containing a boolean indicating the success of the request and a list of RunningInput objects.
    """
    running_inputs_collected = await send_get_request(
        endpoint="/api/system/inputstates",
    )
    success = running_inputs_collected.get("success", False)

    if success:
        return True, [RunningInput(**input_data) for input_data in running_inputs_collected["data"]["states"]]
    else:
        logger.error("Failed to fetch running inputs")
        return False, []


async def get_inputs() -> GraylogInputsResponse:
    """Get inputs from Graylog.

    This function retrieves both configured and running inputs from Graylog.
    It first fetches the configured inputs using the `fetch_configured_inputs` function,
    and then fetches the running inputs using the `fetch_running_inputs` function.
    If both fetch operations are successful, it returns a `GraylogInputsResponse` object
    containing the configured and running inputs, along with a success message.
    If either of the fetch operations fails, it returns a `GraylogInputsResponse` object
    with empty input lists and a failure message.

    Returns:
        GraylogInputsResponse: An object containing the configured and running inputs,
        along with a success or failure message.
    """
    logger.info("Getting inputs from Graylog")

    config_success, configured_inputs_list = await fetch_configured_inputs()
    run_success, running_inputs_list = await fetch_running_inputs()

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
        return GraylogInputsResponse(
            configured_inputs=[],
            running_inputs=[],
            success=False,
            message="Failed to collect inputs",
        )


async def get_inputs_running() -> RunningInputsResponse:
    """Get running inputs from Graylog.

    Returns:
        RunningInputsResponse: The response object containing the running inputs, success status, and message.
    """
    logger.info("Getting running inputs from Graylog")
    run_success, running_inputs_list = await fetch_running_inputs()
    if run_success:
        return RunningInputsResponse(
            running_inputs=running_inputs_list,
            success=True,
            message="Successfully retrieved running inputs",
        )


async def get_inputs_configured() -> ConfiguredInputsResponse:
    """Get configured inputs from Graylog.

    Returns:
        ConfiguredInputsResponse: The response object containing the configured inputs, success status, and message.
    """
    logger.info("Getting configured inputs from Graylog")
    config_success, configured_inputs_list = await fetch_configured_inputs()
    if config_success:
        return ConfiguredInputsResponse(
            configured_inputs=configured_inputs_list,
            success=True,
            message="Successfully retrieved configured inputs",
        )


async def get_index_names() -> List[str]:
    """
    Gets the names of all the indices in Graylog.

    Returns:
        List[str]: A list of all the index names.
    """
    logger.info("Getting index names from Graylog")

    indices_collected = await get_indices_full()

    if indices_collected.success:
        # Access the index_name attribute directly
        return [index.index_name for index in indices_collected.indices]
    else:
        return []


async def get_input_ids() -> List[str]:
    """
    Gets the IDs of all the inputs in Graylog.

    Returns:
        List[str]: A list of all the input IDs.
    """
    logger.info("Getting input IDs from Graylog")

    success, inputs_collected = await fetch_configured_inputs()

    if success:
        # Access the input_id attribute directly
        return [input.id for input in inputs_collected]
    else:
        return []


async def get_url_whitelist_entries() -> UrlWhitelistEntryResponse:
    """
    Retrieves the URL whitelist entries from Graylog.

    Returns:
        UrlWhitelistEntryResponse: The response object containing the URL whitelist entries.
    """
    logger.info("Getting URL whitelist entries from Graylog")
    response = await send_get_request(endpoint="/api/system/urlwhitelist")
    logger.info(f"URL whitelist entries response: {response}")
    if response["success"]:
        try:
            url_whitelist_entries = response["data"]
        except KeyError:
            raise HTTPException(
                status_code=500,
                detail="Failed to collect URL whitelist entries",
            )
        return UrlWhitelistEntryResponse(
            url_whitelist_entries=url_whitelist_entries,
            success=True,
            message="URL whitelist entries collected successfully",
        )
    else:
        return UrlWhitelistEntryResponse(
            url_whitelist_entries=[],
            success=False,
            message="Failed to collect URL whitelist entries",
        )


async def get_stream_id_by_stream_name(stream_name: str) -> str:
    """Get stream ID from Graylog by stream name.

    Args:
        stream_name (str): The name of the stream.

    Returns:
        str: The ID of the stream.

    Raises:
        HTTPException: If there is an error collecting the stream ID.
    """
    logger.info(f"Getting stream ID from Graylog for stream {stream_name}")
    streams_collected = await send_get_request(endpoint="/api/streams")
    try:
        if streams_collected["success"]:
            for stream in streams_collected["data"]["streams"]:
                if stream["title"] == stream_name:
                    return stream["id"]
        else:
            return ""
    except KeyError as e:
        logger.error(f"Failed to collect stream ID key: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect stream ID key: {e}",
        )


async def get_input_id_by_input_name(input_name: str) -> str:
    """Get input ID from Graylog by input name.

    Args:
        input_name (str): The name of the input.

    Returns:
        str: The ID of the input.

    Raises:
        HTTPException: If there is an error collecting the input ID.
    """
    logger.info(f"Getting input ID from Graylog for input {input_name}")
    inputs_collected = await send_get_request(endpoint="/api/system/inputs")
    try:
        if inputs_collected["success"]:
            for input in inputs_collected["data"]["inputs"]:
                if input["title"] == input_name:
                    return input["id"]
        else:
            return ""
    except KeyError as e:
        logger.error(f"Failed to collect input ID key: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect input ID key: {e}",
        )


async def get_content_pack_id_by_content_pack_name(content_pack_name: str) -> str:
    """Get content pack ID from Graylog by content pack name.

    Args:
        content_pack_name (str): The name of the content pack.

    Returns:
        str: The ID of the content pack.

    Raises:
        HTTPException: If there is an error collecting the content pack ID.
    """
    logger.info(f"Getting content pack ID from Graylog for content pack {content_pack_name}")
    content_packs_collected = await send_get_request(endpoint="/api/system/content_packs")
    try:
        if content_packs_collected["success"]:
            for content_pack in content_packs_collected["data"]["content_packs"]:
                if content_pack["name"] == content_pack_name:
                    return content_pack["id"]
        else:
            return ""
    except KeyError as e:
        logger.error(f"Failed to collect content pack ID key: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect content pack ID key: {e}",
        )
