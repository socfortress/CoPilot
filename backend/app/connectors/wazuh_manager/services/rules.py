from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import httpx

# import pcre2
import xmltodict
from fastapi import HTTPException
from loguru import logger

from app.connectors.wazuh_manager.schema.rules import RuleDisable
from app.connectors.wazuh_manager.schema.rules import RuleDisableResponse
from app.connectors.wazuh_manager.schema.rules import RuleEnable
from app.connectors.wazuh_manager.schema.rules import RuleEnableResponse
from app.connectors.wazuh_manager.schema.rules import RuleExcludeRequest
from app.connectors.wazuh_manager.schema.rules import RuleExcludeResponse
from app.connectors.wazuh_manager.schema.rules import WazuhRuleFileContentResponse
from app.connectors.wazuh_manager.schema.rules import WazuhRuleFilesResponse
from app.connectors.wazuh_manager.schema.rules import WazuhRuleFileUploadResponse
from app.connectors.wazuh_manager.schema.rules import WazuhRulesResponse
from app.connectors.wazuh_manager.utils.universal import restart_service
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request


async def get_wazuh_rules(**params) -> WazuhRulesResponse:
    """
    Fetch Wazuh rules from the Wazuh Manager API.

    Args:
        **params: All query parameters passed directly to the API

    Returns:
        WazuhRulesResponse: Structured response with rules data
    """
    # Filter out None values
    clean_params = {k: v for k, v in params.items() if v is not None}

    # Handle list parameters
    if "rule_ids" in clean_params and isinstance(clean_params["rule_ids"], list):
        clean_params["rule_ids"] = ",".join(map(str, clean_params["rule_ids"]))
    if "select" in clean_params and isinstance(clean_params["select"], list):
        clean_params["select"] = ",".join(clean_params["select"])
    if "filename" in clean_params and isinstance(clean_params["filename"], list):
        clean_params["filename"] = ",".join(clean_params["filename"])

    try:
        response = await send_get_request(endpoint="/rules", params=clean_params)

        if not response.get("success"):
            raise HTTPException(status_code=500, detail="Failed to fetch rules from Wazuh API")

        # Extract data from nested response structure
        wazuh_data = response.get("data", {}).get("data", {})
        rules = wazuh_data.get("affected_items", [])
        total_items = wazuh_data.get("total_affected_items", len(rules))

        logger.info(f"Retrieved {len(rules)} of {total_items} Wazuh rules")

        return WazuhRulesResponse(
            success=True,
            message=f"Successfully retrieved {len(rules)} rules",
            results=rules,
            total_items=total_items,
        )

    except Exception as e:
        logger.error(f"Error fetching Wazuh rules: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching rules: {str(e)}")


async def get_wazuh_rule_files(**params) -> WazuhRuleFilesResponse:
    """
    Fetch Wazuh rule files from the Wazuh Manager API.

    Args:
        **params: All query parameters passed directly to the API

    Returns:
        WazuhRuleFilesResponse: Structured response with rule files data

    Raises:
        HTTPException: If there's an error fetching the rule files
    """
    # Filter out None values and prepare parameters
    clean_params = {k: v for k, v in params.items() if v is not None}

    # Handle list parameters that need to be joined as comma-separated strings
    if "filename" in clean_params and isinstance(clean_params["filename"], list):
        clean_params["filename"] = ",".join(clean_params["filename"])
    if "select" in clean_params and isinstance(clean_params["select"], list):
        clean_params["select"] = ",".join(clean_params["select"])

    logger.debug(f"Requesting Wazuh rule files with params: {clean_params}")

    try:
        response = await send_get_request(endpoint="/rules/files", params=clean_params)

        # Check if the API request was successful
        if not response.get("success"):
            error_detail = response.get("message", "Failed to fetch rule files from Wazuh API")
            logger.error(f"Wazuh API error: {error_detail}")
            raise HTTPException(status_code=500, detail=error_detail)

        # Extract data from nested response structure
        wazuh_data = response.get("data", {}).get("data", {})
        rule_files = wazuh_data.get("affected_items", [])
        total_items = wazuh_data.get("total_affected_items", len(rule_files))

        logger.info(f"Retrieved {len(rule_files)} of {total_items} Wazuh rule files")

        return WazuhRuleFilesResponse(
            success=True,
            message=f"Successfully retrieved {len(rule_files)} rule files",
            results=rule_files,
            total_items=total_items,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error fetching Wazuh rule files: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching rule files: {str(e)}")


async def get_wazuh_rule_file_content(filename: str, **params) -> WazuhRuleFileContentResponse:
    """
    Fetch the content of a specific Wazuh rule file from the Wazuh Manager API.

    Args:
        filename: The name of the rule file to fetch content for
        **params: All query parameters passed directly to the API

    Returns:
        WazuhRuleFileContentResponse: Structured response with rule file content

    Raises:
        HTTPException: If there's an error fetching the rule file content
    """
    # Filter out None values and prepare parameters
    clean_params = {k: v for k, v in params.items() if v is not None}

    # Check if raw content is requested
    is_raw = clean_params.get("raw", False)

    logger.debug(f"Requesting Wazuh rule file content for '{filename}' with params: {clean_params}")

    try:
        # Handle raw response differently
        if is_raw:
            # For raw requests, we need to use a modified approach
            # Use only the raw parameter to trigger the special handling in send_get_request
            raw_params = {"raw": True}
            response = await send_get_request(endpoint=f"/rules/files/{filename}", params=raw_params)

            # Check if the API request was successful
            if not response.get("success"):
                error_detail = response.get("message", f"Failed to fetch raw rule file content for {filename}")
                logger.error(f"Wazuh API error: {error_detail}")

                # Handle specific errors
                if "not found" in error_detail.lower():
                    raise HTTPException(status_code=404, detail=f"Rule file '{filename}' not found")
                else:
                    raise HTTPException(status_code=500, detail=error_detail)

            # For raw responses, the content is in response["data"]
            content = response.get("data", "")
            logger.info(f"Retrieved raw content for rule file '{filename}' ({len(content)} characters)")

            return WazuhRuleFileContentResponse(
                success=True,
                message=f"Successfully retrieved raw content for rule file '{filename}'",
                filename=filename,
                content=content,
                is_raw=True,
                total_items=None,
            )

        # Handle structured response (non-raw)
        response = await send_get_request(endpoint=f"/rules/files/{filename}", params=clean_params)

        # Check if the API request was successful
        if not response.get("success"):
            error_detail = response.get("message", f"Failed to fetch rule file content for {filename}")
            logger.error(f"Wazuh API error: {error_detail}")

            # Handle specific errors
            if "not found" in error_detail.lower():
                raise HTTPException(status_code=404, detail=f"Rule file '{filename}' not found")
            else:
                raise HTTPException(status_code=500, detail=error_detail)

        # Handle structured response
        wazuh_data = response.get("data", {}).get("data", {})
        affected_items = wazuh_data.get("affected_items", [])
        total_items = wazuh_data.get("total_affected_items", len(affected_items))

        if not affected_items:
            raise HTTPException(status_code=404, detail=f"No content found for rule file '{filename}'")

        # Extract the content from the first affected item
        content = affected_items[0] if affected_items else {}

        logger.info(f"Retrieved structured content for rule file '{filename}' with {total_items} affected items")

        return WazuhRuleFileContentResponse(
            success=True,
            message=f"Successfully retrieved content for rule file '{filename}'",
            filename=filename,
            content=content,
            is_raw=False,
            total_items=total_items,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error fetching Wazuh rule file content for '{filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching rule file content: {str(e)}")


async def update_wazuh_rule_file(
    filename: str,
    file_content: bytes,
    pretty: Optional[bool] = False,
    wait_for_complete: Optional[bool] = False,
    overwrite: Optional[bool] = False,
    relative_dirname: Optional[str] = None,
) -> WazuhRuleFileUploadResponse:
    """
    Upload or update a Wazuh rule file.

    Args:
        filename: Name of the rule file
        file_content: Binary content of the rule file
        pretty: Show results in human-readable format
        wait_for_complete: Disable timeout response
        overwrite: Whether to overwrite the file if it exists
        relative_dirname: Relative directory name

    Returns:
        WazuhRuleFileUploadResponse: Response indicating success/failure

    Raises:
        HTTPException: If there's an error uploading the file
    """
    # Prepare parameters
    params = {}
    if pretty is not None:
        params["pretty"] = str(pretty).lower()
    if wait_for_complete is not None:
        params["wait_for_complete"] = str(wait_for_complete).lower()
    if overwrite is not None:
        params["overwrite"] = str(overwrite).lower()
    if relative_dirname is not None:
        params["relative_dirname"] = relative_dirname

    logger.info(f"Uploading/updating rule file: {filename}")
    logger.debug(f"Request params: {params}")

    try:
        # Send PUT request with binary data
        response = await send_put_request(
            endpoint=f"/rules/files/{filename}",
            data=file_content,
            params=params,
            binary_data=True,
            debug=True,
        )

        # Check if the API request was successful
        if not response.get("success"):
            error_detail = response.get("message", "Failed to upload rule file to Wazuh API")
            status_code = response.get("status_code", 500)
            logger.error(f"Wazuh API error: {error_detail}")
            raise HTTPException(status_code=status_code, detail=error_detail)

        # Extract data from response
        wazuh_data = response.get("data", {}).get("data", {})
        total_items = wazuh_data.get("total_affected_items", 1)

        logger.info(f"Successfully uploaded/updated rule file: {filename}")

        return WazuhRuleFileUploadResponse(
            success=True,
            message=f"Successfully uploaded/updated rule file: {filename}",
            filename=filename,
            details=wazuh_data,
            total_items=total_items,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error uploading rule file {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading rule file: {str(e)}")


async def fetch_filename(rule_id: str) -> str:
    """
    Fetches the filename associated with a given rule ID from the Wazuh Manager.

    Args:
        rule_id (str): The ID of the rule.

    Returns:
        str: The filename associated with the rule ID.

    Raises:
        HTTPException: If the rule ID is not found in the Wazuh Manager.
    """
    endpoint = "rules"
    params = {"rule_ids": rule_id}
    filename_data = await send_get_request(endpoint=endpoint, params=params)
    if filename_data["data"]["data"]["total_affected_items"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Rule {rule_id} not found. Make sure the rule ID is correct within the Wazuh Manager.",
        )
    return filename_data["data"]["data"]["affected_items"][0]["filename"]


async def fetch_file_content(filename: str) -> str:
    """
    Fetches the content of a file from the Wazuh Manager.

    Args:
        filename (str): The name of the file to fetch.

    Returns:
        str: The content of the file.

    Raises:
        HTTPException: If the file is not found in the Wazuh Manager.
    """
    endpoint = f"rules/files/{filename}"
    file_content_data = await send_get_request(endpoint=endpoint)
    if file_content_data["data"]["data"]["total_affected_items"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"File {filename} not found. Make sure the file name is correct within the Wazuh Manager.",
        )
    return file_content_data["data"]["data"]["affected_items"][0]["group"]


async def set_rule_level(
    file_content: Any,
    rule_id: str,
    new_level: str,
) -> Tuple[str, Any]:
    """
    Sets the level of a rule identified by its ID in the given file content.

    Args:
        file_content (Any): The content of the file containing the rules.
        rule_id (str): The ID of the rule to set the level for.
        new_level (str): The new level to set for the rule.

    Returns:
        Tuple[str, Any]: A tuple containing the previous level of the rule and the modified file content.
    """
    previous_level = None
    try:
        if isinstance(file_content, dict):
            file_content = [file_content]
        for group_block in file_content:
            rule_block = group_block.get("rule", None)
            if rule_block:
                if isinstance(rule_block, dict):
                    rule_block = [rule_block]
                for rule in rule_block:
                    if rule["@id"] == rule_id:
                        previous_level = rule["@level"]
                        rule["@level"] = new_level
                        break
    except (KeyError, TypeError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to set rule level: {e}")
    return previous_level, file_content


async def convert_to_xml(
    updated_file_content: Union[Dict[str, str], List[Dict[str, str]]],
) -> str:
    """
    Converts the updated file content to XML format.

    Args:
        updated_file_content (Union[Dict[str, str], List[Dict[str, str]]]): The updated file content.

    Returns:
        str: The XML content.

    Raises:
        HTTPException: If there is an error converting to XML.
    """
    xml_content_list = []
    try:
        for group in updated_file_content:
            xml_dict = {"group": group}
            xml_content = xmltodict.unparse(xml_dict, pretty=True)
            xml_content = xml_content.replace(
                '<?xml version="1.0" encoding="utf-8"?>',
                "",
            )
            xml_content_list.append(xml_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert to XML: {e}")
    xml_content = "\n".join(xml_content_list)
    xml_content = xml_content.strip()
    return xml_content


async def upload_updated_rule(filename: str, xml_content: str):
    """
    Uploads an updated rule to the Wazuh Manager.

    Args:
        filename (str): The name of the rule file.
        xml_content (str): The content of the rule file in XML format.

    Returns:
        dict: The response from the Wazuh Manager API.

    Raises:
        HTTPException: If the upload fails.
    """
    response = await send_put_request(
        endpoint=f"rules/files/{filename}",
        data=xml_content,
        params={"overwrite": "true"},
    )
    logger.info(response)
    if response["data"]["data"]["total_affected_items"] == 0:
        raise HTTPException(
            status_code=500,
            detail="Failed to upload updated rule to Wazuh Manager.",
        )
    return response


async def process_rule(rule, rule_action_func, ResponseModel):
    """
    Process a rule by fetching its filename and content, applying a rule action function,
    converting the updated content to XML, uploading the updated rule, and restarting the service.

    Args:
        rule: The rule to be processed.
        rule_action_func: The function to apply to the rule's content.
        ResponseModel: The response model class.

    Returns:
        An instance of ResponseModel with the previous level, success status, and a message.
    """
    filename, file_content = await fetch_filename_and_content(rule.rule_id)
    previous_level, updated_file_content = await rule_action_func(
        file_content,
        rule.rule_id,
    )
    xml_content = await convert_to_xml(updated_file_content)
    await upload_updated_rule(filename, xml_content)
    await restart_service()
    return ResponseModel(
        previous_level=previous_level,
        success=True,
        message=f"Rule {rule.rule_id} successfully processed in file {filename}.",
    )


async def fetch_filename_and_content(rule_id: str) -> Tuple[str, str]:
    """
    Fetches the filename and content of a rule based on the given rule ID.

    Args:
        rule_id (str): The ID of the rule.

    Returns:
        Tuple[str, str]: A tuple containing the filename and content of the rule.
    """
    filename = await fetch_filename(rule_id)
    file_content = await fetch_file_content(filename)
    return filename, file_content


async def disable_rule(rule: RuleDisable) -> RuleDisableResponse:
    """
    Disable a rule by setting its level to "1".

    Args:
        rule (RuleDisable): The rule to be disabled.

    Returns:
        RuleDisableResponse: The response indicating the success or failure of the operation.
    """

    async def process(fc, rid):
        return await set_rule_level(fc, rid, "1")

    return await process_rule(rule, process, RuleDisableResponse)


async def enable_rule(rule: RuleEnable, previous_level: str) -> RuleEnableResponse:
    """
    Enable a rule with the given parameters.

    Args:
        rule (RuleEnable): The rule to enable.
        previous_level (str): The previous level of the rule.

    Returns:
        RuleEnableResponse: The response indicating the success or failure of enabling the rule.
    """

    async def process(fc, rid):
        return await set_rule_level(fc, rid, previous_level)

    return await process_rule(rule, process, RuleEnableResponse)


################# ! EXCLUDE RULE ! #################
async def post_to_copilot_ai_module(data: RuleExcludeRequest) -> RuleExcludeResponse:
    """
    Send a POST request to the copilot-ai-module Docker container.

    Args:
        data (CollectHuntress): The data to send to the copilot-ai-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-ai-module/wazuh-rule-exclusion with data: {data.dict()}")
    # raise HTTPException(status_code=501, detail="Not Implemented Yet")
    async with httpx.AsyncClient() as client:
        data = await client.post(
            "http://copilot-ai-module/wazuh-rule-exclusion",
            json=data.dict(),
            timeout=120,
        )
    return RuleExcludeResponse(**data.json())
