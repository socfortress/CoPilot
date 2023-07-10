from typing import Dict, Optional, Union, List, Any, Tuple
from loguru import logger
from app.services.WazuhManager.universal import UniversalService
import requests
from app.models.rules import DisabledRules
from app.models.connectors import connector_factory, Connector
from app import db
import xmltodict
import xml.etree.ElementTree as ET
import json

class WazuhHttpRequests:
    """
    Class to handle HTTP requests to the Wazuh API.
    """
    def __init__(self, connector_url: str, wazuh_auth_token: str) -> None:
        """
        Args:
            connector_url (str): The URL of the Wazuh Manager.
            wazuh_auth_token (str): The Wazuh API authentication token.
        """
        self.connector_url = connector_url
        self.wazuh_auth_token = wazuh_auth_token
        self.headers = {"Authorization": f"Bearer {wazuh_auth_token}"}

    def get_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Union[str, bool]]:
        """
        Function to handle GET requests.

        Args:
            endpoint (str): The endpoint to make a GET request to.
            params (Optional[Dict[str, str]]): Any parameters to pass in the GET request.

        Returns:
            Dict[str, Union[str, bool]]: A dictionary with the requested data or error message.
        """
        try:
            response = requests.get(
                f"{self.connector_url}/{endpoint}",
                headers=self.headers,
                params=params,
                verify=False,
            )
            response.raise_for_status()
            return {"data": response.json(), "success": True}

        except Exception as e:
            logger.error(f"GET request to {endpoint} failed: {e}")
            return {"message": f"GET request to {endpoint} failed: {e}", "success": False}

    def put_request(self, endpoint: str, data: str, params: Optional[Dict[str, str]] = None) -> Dict[str, bool]:
        """
        Function to handle PUT requests.

        Args:
            endpoint (str): The endpoint to make a PUT request to.
            data (str): Data to be updated on the PUT request.
            params (Optional[Dict[str, str]]): Any parameters to pass in the PUT request.

        Returns:
            Dict[str, bool]: A dictionary indicating the success of the operation.
        """
        try:
            headers = self.headers.copy()
            headers.update({"Content-Type": "application/octet-stream"})

            response = requests.put(
                f"{self.connector_url}/{endpoint}",
                headers=headers,
                params=params,
                data=data,
                verify=False,
            )
            response.raise_for_status()
            return {"message": f"Successfully updated {endpoint}", "success": True}

        except Exception as e:
            logger.error(f"Failed to update {endpoint}: {e}")
            return {"message": f"Failed to update {endpoint}: {e}", "success": False}


class DisableRuleService:
    """
    A service class that encapsulates the logic for handling rule disabling related operations in Wazuh Manager.
    """
    def __init__(self, universal_service: UniversalService) -> None:
        """
        Args:
            universal_service (UniversalService): The UniversalService instance to use.
        """
        self.universal_service = universal_service
        self.auth_token = universal_service.get_auth_token()
        self.wazuh_http_requests = WazuhHttpRequests(self.universal_service.connector_url, self.auth_token)

    def disable_rule(self, request: Dict[str, Union[str, int]]) -> Dict[str, Union[str, bool]]:
        try:
            self._validate_request(request)
            rule_id = request["rule_id"]
            filename = self._fetch_filename(rule_id)
            file_content = self._fetch_file_content(filename)
            previous_level, updated_file_content = self._set_level_1(file_content, rule_id)
            xml_content = self._convert_to_xml(updated_file_content)
            self._store_disabled_rule_info(rule_id, previous_level, request["reason"], request["length_of_time"])
            self._upload_updated_rule(filename, xml_content)
            UniversalService().restart_service()
            return {"message": f"Rule {rule_id} successfully disabled in file {filename}.", "success": True}

        except Exception as e:
            logger.error(str(e))
            return {"message": str(e), "success": False}

    def _validate_request(self, request: Dict[str, Union[str, int]]):
        logger.info(f"Validating disable rule request: {request}")
        if "rule_id" not in request:
            raise ValueError("Request missing rule_id")
        if "reason" not in request:
            raise ValueError("Request missing reason")
        if "length_of_time" not in request:
            raise ValueError("Request missing length_of_time")
        request["length_of_time"] = int(request["length_of_time"])
    
    def _fetch_filename(self, rule_id: str) -> str:
        filename_data = self.wazuh_http_requests.get_request("rules", {"rule_ids": rule_id})
        if not filename_data["success"]:
            raise ValueError(filename_data["message"])
        return filename_data["data"]["data"]["affected_items"][0]["filename"]

    def _fetch_file_content(self, filename: str) -> Union[Dict[str, str], List[Dict[str, str]]]:
        file_content_data = self.wazuh_http_requests.get_request(f"rules/files/{filename}")
        if not file_content_data["success"]:
            raise ValueError(file_content_data["message"])
        return file_content_data["data"]["data"]["affected_items"][0]["group"]

    def _set_level_1(self, file_content: Union[Dict[str, str], List[Dict[str, str]]], rule_id: str) -> Tuple[str, Union[Dict[str, str], List[Dict[str, str]]]]:
        logger.info(f"Setting rule {rule_id} level to 1 for file_content: {file_content}")
        previous_level = None
        if isinstance(file_content, dict):
            file_content = [file_content]
        for group_block in file_content:
            rule_block = group_block.get("rule", None)
            if not rule_block:
                continue
            if isinstance(rule_block, dict):
                rule_block = [rule_block]
            for rule in rule_block:
                if rule["@id"] == rule_id:
                    previous_level = rule["@level"]
                    rule["@level"] = "1"
                    break
        return previous_level, file_content

    def _convert_to_xml(self, updated_file_content: Union[Dict[str, str], List[Dict[str, str]]]) -> str:
        logger.info(f"Received updated_file_content: {updated_file_content}")
        xml_content_list = []
        for group in updated_file_content:
            xml_dict = {"group": group}
            xml_content = xmltodict.unparse(xml_dict, pretty=True)
            xml_content = xml_content.replace('<?xml version="1.0" encoding="utf-8"?>', "")
            xml_content_list.append(xml_content)
        xml_content = "\n".join(xml_content_list)
        xml_content = xml_content.strip()
        return xml_content

    def _store_disabled_rule_info(self, rule_id: str, previous_level: str, reason: str, length_of_time: str):
        disabled_rule = DisabledRules(
            rule_id=rule_id,
            previous_level=previous_level,
            new_level="1",
            reason_for_disabling=reason,
            length_of_time=length_of_time,
        )
        db.session.add(disabled_rule)
        db.session.commit()

    def _upload_updated_rule(self, filename: str, xml_content: str):
        response = self.wazuh_http_requests.put_request(f"rules/files/{filename}", xml_content, {"overwrite": "true"})
        if not response["success"]:
            raise ValueError(response["message"])
        
