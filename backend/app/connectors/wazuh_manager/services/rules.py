from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import requests
import xmltodict
from loguru import logger

from app.connectors.wazuh_manager.schema.rules import RuleDisable
from app.connectors.wazuh_manager.schema.rules import RuleDisableResponse
from app.connectors.wazuh_manager.schema.rules import RuleEnable
from app.connectors.wazuh_manager.schema.rules import RuleEnableResponse
from app.connectors.wazuh_manager.utils.universal import restart_service
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request


def fetch_filename(rule_id: str) -> str:
    endpoint = "rules"
    params = {"rule_ids": rule_id}
    filename_data = send_get_request(endpoint=endpoint, params=params)
    if not filename_data["success"]:
        raise ValueError(filename_data["message"])
    return filename_data["data"]["data"]["affected_items"][0]["filename"]


def fetch_file_content(filename: str) -> str:
    endpoint = f"rules/files/{filename}"
    file_content_data = send_get_request(endpoint=endpoint)
    if not file_content_data["success"]:
        raise ValueError(file_content_data["message"])
    return file_content_data["data"]["data"]["affected_items"][0]["group"]


def set_rule_level(file_content: Any, rule_id: str, new_level: str) -> Tuple[str, Any]:
    previous_level = None
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
    return previous_level, file_content


def convert_to_xml(updated_file_content: Union[Dict[str, str], List[Dict[str, str]]]) -> str:
    xml_content_list = []
    for group in updated_file_content:
        xml_dict = {"group": group}
        xml_content = xmltodict.unparse(xml_dict, pretty=True)
        xml_content = xml_content.replace('<?xml version="1.0" encoding="utf-8"?>', "")
        xml_content_list.append(xml_content)
    xml_content = "\n".join(xml_content_list)
    xml_content = xml_content.strip()
    return xml_content


def upload_updated_rule(filename: str, xml_content: str):
    response = send_put_request(
        endpoint=f"rules/files/{filename}",
        data=xml_content,
        params={"overwrite": "true"},
    )
    if not response["success"]:
        raise ValueError(response["message"])


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
