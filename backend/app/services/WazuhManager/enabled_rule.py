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
            logger.info(f"GET request to {endpoint}")
            response = requests.get(
                f"{self.connector_url}/{endpoint}",
                headers=self.headers,
                params=params,
                verify=False,
            )
            response.raise_for_status()
            logger.info(f"Respones: {response.json()}")
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


class EnableRuleService:
    """
    A service class that encapsulates the logic for handling rule enabling related operations in Wazuh Manager.
    """
    def __init__(self, universal_service: UniversalService) -> None:
        """
        Args:
            universal_service (UniversalService): The UniversalService instance to use.
        """
        self.universal_service = universal_service
        self.auth_token = universal_service.get_auth_token()
        self.wazuh_http_requests = WazuhHttpRequests(self.universal_service.connector_url, self.auth_token)

    def enable_rule(self, request: Dict[str, str]) -> Dict[str, Union[str, bool]]:
        """
        Enable a rule in the Wazuh Manager.

        Args:
            request (Dict[str, str]): The request to enable a rule in Wazuh Manager.

        Returns:
            Dict[str, Union[str, bool]]: A dictionary containing status of the operation.
        """
        try:
            self._validate_request(request)
            rule_id = request["rule_id"]
            filename = self._fetch_filename(rule_id)
            logger.info(f"Getting file content of {filename}")
            file_content = self._fetch_file_content(filename)
            previous_level = self._get_previous_level(rule_id)
            updated_file_content = self._set_level_previous(file_content, rule_id, previous_level)
            xml_content = self._json_to_xml(updated_file_content)
            self._delete_rule_from_db(rule_id)
            self._put_updated_rule(filename, xml_content)
            UniversalService().restart_service()
            return {
                "message": f"Rule {rule_id} successfully enabled in file {filename}.",
                "success": True,
            }
        except Exception as e:
            return {"message": str(e), "success": False}

    def _validate_request(self, request: Dict[str, str]) -> str:
        """
        Validate the request to enable a rule in Wazuh Manager and return rule_id.

        Args:
            request (Dict[str, str]): The request to enable a rule in Wazuh Manager.

        Raises:
            ValueError: If the request is missing rule_id.

        Returns:
            str: rule_id.
        """
        logger.info(f"Validating enable rule request: {request}")
        if "rule_id" not in request:
            raise ValueError("Request missing rule_id")
        return request["rule_id"]

    def _fetch_filename(self, rule_id: str) -> str:
        """
        Get the filename of the rule to be enabled.

        Args:
            rule_id (str): The id of the rule to be enabled.

        Raises:
            RuntimeError: If the filename cannot be obtained.

        Returns:
            str: The filename of the rule to be enabled.
        """
        filename_data = self.wazuh_http_requests.get_request("rules", {"rule_ids": rule_id})
        if not filename_data["success"]:
            raise ValueError(filename_data["message"])
        return filename_data["data"]["data"]["affected_items"][0]["filename"]

    def _fetch_file_content(self, filename: str) -> Any:
        """
        Get the content of the rule file.

        Args:
            filename (str): The filename of the rule to be enabled.

        Raises:
            RuntimeError: If the file content cannot be obtained.

        Returns:
            Any: The content of the rule file.
        """
        file_content_data = self.wazuh_http_requests.get_request(f"rules/files/{filename}")
        if not file_content_data["success"]:
            raise ValueError(file_content_data["message"])
        return file_content_data["data"]["data"]["affected_items"][0]["group"]

    def _get_previous_level(self, rule_id: str) -> str:
        """
        Get the previous level of the rule from the `disabled_rules` table.

        Args:
            rule_id (str):The rule id to be enabled.

        Raises:
            ValueError: If the rule was not previously disabled.

        Returns:
            str: The previous level of the rule.
        """
        disabled_rule = DisabledRules.query.filter_by(rule_id=rule_id).first()
        if not disabled_rule:
            raise ValueError(f"Rule {rule_id} is not disabled.")
        return disabled_rule.previous_level

    def _set_level_previous(self, file_content: Any, rule_id: str, previous_level: str) -> Any:
        """
        Set the level of the rule to be enabled to the previous level.

        Args:
            file_content (Any): The content of the rule to be enabled.
            rule_id (str): The id of the rule to be enabled.
            previous_level (str): The previous level of the rule to be enabled.

        Returns:
            Any: The content of the rule with the level set to the previous level.
        """
        logger.info(
            f"Setting rule {rule_id} level to {previous_level} for file_content: {file_content}"
        )
        # If 'file_content' is a dictionary (representing a single group), make it a list of one group
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
                    # Set the rule level to the previous level.
                    rule["@level"] = previous_level
                    break

        return file_content

    def _json_to_xml(self, file_content: Any) -> str:
        """
        Convert the rule content from JSON to XML.

        Args:
            file_content (Any): The content of the rule to be enabled.

        Raises:
            Exception: If the JSON to XML conversion fails.

        Returns:
            str: The content of the rule to be enabled in XML format.
        """
        logger.info(f"Converting file_content to XML: {file_content}")

        xml_content_list = []
        for group in file_content:
            xml_dict = {"group": group}
            xml_content = xmltodict.unparse(xml_dict, pretty=True)
            # Remove the `<?xml version="1.0" encoding="utf-8"?>` from the
            # beginning of the XML string.
            xml_content = xml_content.replace(
                '<?xml version="1.0" encoding="utf-8"?>', ""
            )
            xml_content_list.append(xml_content)

        # Concatenate all XML strings
        xml_content = "\n".join(xml_content_list)
        # Remove top and bottom line breaks
        xml_content = xml_content.strip()

        return xml_content

    def _delete_rule_from_db(self, rule_id: str):
        """
        Delete the rule from the `disabled_rules` table.

        Args:
            rule_id (str): The rule id to be deleted.
        """
        disabled_rule = DisabledRules.query.filter_by(rule_id=rule_id).first()
        db.session.delete(disabled_rule)
        db.session.commit()

    def _put_updated_rule(self, filename: str, xml_content: str):
        """
        PUT the updated rule to the Wazuh Manager.

        Args:
            filename (str): The filename of the rule.
            xml_content (str): The XML content of the rule.

        Raises:
            RuntimeError: If the PUT operation fails.
        """
        response = self.wazuh_http_requests.put_request(f"rules/files/{filename}", xml_content, params={"overwrite": "true"})
        if not response["success"]:
            raise RuntimeError(f"Could not PUT rule {filename}")
