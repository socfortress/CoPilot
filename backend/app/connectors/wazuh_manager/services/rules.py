from typing import Any
from typing import Dict
from typing import List
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
from app.connectors.wazuh_manager.utils.universal import restart_service
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request


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
