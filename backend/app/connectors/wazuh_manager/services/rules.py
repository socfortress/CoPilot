import re
from enum import Enum
from typing import Any, Dict, List, Tuple, Union

# import pcre2
import xmltodict
from app.connectors.wazuh_manager.schema.rules import (
    RuleDisable,
    RuleDisableResponse,
    RuleEnable,
    RuleEnableResponse,
    RuleExclude,
    RuleExcludeResponse,
)
from app.connectors.wazuh_manager.utils.universal import (
    restart_service,
    send_get_request,
    send_put_request,
)
from fastapi import HTTPException
from loguru import logger


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


def make_pcre2_compatible(input_string: str) -> str:
    """
    Convert the input string to a PCRE2 compatible regex pattern.

    Parameters:
    - input_string (str): The input string to convert.

    Returns:
    - str: The PCRE2 compatible regex pattern.
    """
    # PCRE2 uses \\ to escape a backslash
    return input_string.replace("\\", "\\\\")


class RegexSpecialCharacters(Enum):
    DOT = (".", "\.")
    CARET = ("^", "\^")
    DOLLAR = ("$", "\$")
    STAR = ("*", "\*")
    PLUS = ("+", "\+")
    QUESTION = ("?", "\?")
    CURLY_OPEN = ("{", "\{")
    CURLY_CLOSE = ("}", "\}")
    SQUARE_OPEN = ("[", "\[")
    SQUARE_CLOSE = ("]", "\]")
    SINGLE_BACKSLASH = ("\\", "\\\\")
    DOUBLE_BACKSLASH = ("\\\\", "\\\\\\\\")
    PIPE = ("|", "\|")
    PAREN_OPEN = ("(", "\(")
    PAREN_CLOSE = (")", "\)")
    COLON = (":", "\:")
    DASH = ("-", "\-")


# Create a dictionary for easy lookup
REGEX_REPLACE_DICT = {char.value[0]: char.value[1] for char in RegexSpecialCharacters}


async def replace_special_chars(rule: RuleExclude):
    for char, replacement in REGEX_REPLACE_DICT.items():
        # Use Python's raw string notation for regular expressions
        pattern = re.compile(re.escape(char))
        input_string = pattern.sub(replacement, rule.input_value)
        logger.info(f"Input String: {input_string}")
    return input_string


async def exclude_rule(rule: RuleExclude) -> RuleExcludeResponse:
    """
    Exclude a rule based on the provided input value and rule value.

    Args:
        rule (RuleExclude): The rule to be excluded, containing the input value and rule value.

    Returns:
        RuleExcludeResponse: The response indicating the success or failure of excluding the rule, along with a recommended exclusion.

    Raises:
        Exception: If an error occurs while excluding the rule.
    """
    # Function to replace special characters
    # repr of the input string
    input_string = repr(rule.input_value)
    logger.info(f"Input String: {input_string}")
    excluded_string = await replace_special_chars(rule)
    logger.info(f"Excluded String: {excluded_string}")
    return None
    # try:
    #     # Convert rule_value to a PCRE2 compatible regex pattern
    #     pcre2_pattern = make_pcre2_compatible(rule.rule_value)

    #     compiled_pattern = pcre2.compile(pcre2_pattern)
    #     print(f"Compiled Pattern: {compiled_pattern}")  # Debugging line

    #     print(f"Input Value: {rule.input_value}")  # Debugging line

    #     match_data = compiled_pattern.match(rule.input_value)

    #     if match_data:
    #         return RuleExcludeResponse(success=True, message="Successfully excluded rule", recommended_exclusion=rule.input_value)
    #     else:
    #         return RuleExcludeResponse(success=False, message="Failed to exclude rule", recommended_exclusion="")

    # except Exception as e:
    #     print(f"Exception: {e}")  # Debugging line
    #     logger.error(f"Failed to exclude rule: {e}")
    #     return RuleExcludeResponse(success=False, message=f"Failed to exclude rule: {e}", recommended_exclusion="")
