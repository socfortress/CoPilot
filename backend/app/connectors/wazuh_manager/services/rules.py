from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import Union

import pcre2
import xmltodict
from fastapi import HTTPException
from loguru import logger

from app.connectors.wazuh_manager.schema.rules import RuleDisable
from app.connectors.wazuh_manager.schema.rules import RuleDisableResponse
from app.connectors.wazuh_manager.schema.rules import RuleEnable
from app.connectors.wazuh_manager.schema.rules import RuleEnableResponse
from app.connectors.wazuh_manager.schema.rules import RuleExclude
from app.connectors.wazuh_manager.schema.rules import RuleExcludeResponse
from app.connectors.wazuh_manager.utils.universal import restart_service
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request


def fetch_filename(rule_id: str) -> str:
    endpoint = "rules"
    params = {"rule_ids": rule_id}
    filename_data = send_get_request(endpoint=endpoint, params=params)
    if filename_data["data"]["data"]["total_affected_items"] == 0:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found. Make sure the rule ID is correct within the Wazuh Manager.")
    return filename_data["data"]["data"]["affected_items"][0]["filename"]


def fetch_file_content(filename: str) -> str:
    endpoint = f"rules/files/{filename}"
    file_content_data = send_get_request(endpoint=endpoint)
    if file_content_data["data"]["data"]["total_affected_items"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"File {filename} not found. Make sure the file name is correct within the Wazuh Manager.",
        )
    return file_content_data["data"]["data"]["affected_items"][0]["group"]


def set_rule_level(file_content: Any, rule_id: str, new_level: str) -> Tuple[str, Any]:
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


def convert_to_xml(updated_file_content: Union[Dict[str, str], List[Dict[str, str]]]) -> str:
    xml_content_list = []
    try:
        for group in updated_file_content:
            xml_dict = {"group": group}
            xml_content = xmltodict.unparse(xml_dict, pretty=True)
            xml_content = xml_content.replace('<?xml version="1.0" encoding="utf-8"?>', "")
            xml_content_list.append(xml_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert to XML: {e}")
    xml_content = "\n".join(xml_content_list)
    xml_content = xml_content.strip()
    return xml_content


def upload_updated_rule(filename: str, xml_content: str):
    response = send_put_request(
        endpoint=f"rules/files/{filename}",
        data=xml_content,
        params={"overwrite": "true"},
    )
    logger.info(response)
    if response["data"]["data"]["total_affected_items"] == 0:
        raise HTTPException(status_code=500, detail=f"Failed to upload updated rule to Wazuh Manager.")
    return response


def process_rule(rule, rule_action_func, ResponseModel):
    filename, file_content = fetch_filename_and_content(rule.rule_id)
    previous_level, updated_file_content = rule_action_func(file_content, rule.rule_id)
    xml_content = convert_to_xml(updated_file_content)
    upload_updated_rule(filename, xml_content)
    restart_service()
    return ResponseModel(
        previous_level=previous_level,
        success=True,
        message=f"Rule {rule.rule_id} successfully processed in file {filename}.",
    )


def fetch_filename_and_content(rule_id: str) -> Tuple[str, str]:
    filename = fetch_filename(rule_id)
    file_content = fetch_file_content(filename)
    return filename, file_content


def disable_rule(rule: RuleDisable) -> RuleDisableResponse:
    return process_rule(rule, lambda fc, rid: set_rule_level(fc, rid, "1"), RuleDisableResponse)


def enable_rule(rule: RuleEnable, previous_level: str) -> RuleEnableResponse:
    return process_rule(rule, lambda fc, rid: set_rule_level(fc, rid, previous_level), RuleEnableResponse)


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


def exclude_rule(rule: RuleExclude) -> RuleExcludeResponse:
    try:
        # Convert rule_value to a PCRE2 compatible regex pattern
        pcre2_pattern = make_pcre2_compatible(rule.rule_value)

        compiled_pattern = pcre2.compile(pcre2_pattern)
        print(f"Compiled Pattern: {compiled_pattern}")  # Debugging line

        print(f"Input Value: {rule.input_value}")  # Debugging line

        match_data = compiled_pattern.match(rule.input_value)

        if match_data:
            return RuleExcludeResponse(success=True, message="Successfully excluded rule", recommended_exclusion=rule.input_value)
        else:
            return RuleExcludeResponse(success=False, message="Failed to exclude rule", recommended_exclusion="")

    except Exception as e:
        print(f"Exception: {e}")  # Debugging line
        logger.error(f"Failed to exclude rule: {e}")
        return RuleExcludeResponse(success=False, message=f"Failed to exclude rule: {e}", recommended_exclusion="")
