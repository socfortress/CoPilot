# import json
# import xml.etree.ElementTree as ET
# from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import requests
import xmltodict
from loguru import logger

from app import db
from app.models.rules import DisabledRules
from app.services.wazuh_manager.universal import UniversalService


class WazuhHttpRequests:
    """
    This class helps to send HTTP requests to the Wazuh API.

    Attributes:
        connector_url (str): The URL of the Wazuh Manager.
        wazuh_auth_token (str): The Wazuh API authentication token.
        headers (Dict[str, str]): The headers for HTTP requests.
    """

    def __init__(self, connector_url: str, wazuh_auth_token: str) -> None:
        """
        Initialize a WazuhHttpRequests instance.

        Args:
            connector_url (str): The URL of the Wazuh Manager.
            wazuh_auth_token (str): The Wazuh API authentication token.
        """
        self.connector_url = connector_url
        self.wazuh_auth_token = wazuh_auth_token
        self.headers = {"Authorization": f"Bearer {wazuh_auth_token}"}

    def get_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Union[str, bool]]:
        """
        Send a GET request to the specified endpoint.

        Args:
            endpoint (str): The endpoint to send the GET request to.
            params (Optional[Dict[str, str]]): Additional parameters to include in the request.

        Returns:
            Dict[str, Union[str, bool]]: The response from the endpoint. It contains the data from the response or an error message.
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
            return {
                "message": f"GET request to {endpoint} failed: {e}",
                "success": False,
            }

    def put_request(
        self,
        endpoint: str,
        data: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, bool]:
        """
        Send a PUT request to the specified endpoint.

        Args:
            endpoint (str): The endpoint to send the PUT request to.
            data (str): The data to be updated in the PUT request.
            params (Optional[Dict[str, str]]): Additional parameters to include in the request.

        Returns:
            Dict[str, bool]: A dictionary indicating the success or failure of the operation.
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
    This class handles rule disabling related operations in Wazuh Manager.

    Attributes:
        universal_service (UniversalService): An instance of UniversalService.
        auth_token (str): The Wazuh API authentication token.
        wazuh_http_requests (WazuhHttpRequests): An instance of WazuhHttpRequests.
    """

    def __init__(self, universal_service: UniversalService) -> None:
        """
        Initialize a DisableRuleService instance.

        Args:
            universal_service (UniversalService): The UniversalService instance to use.
        """
        self.universal_service = universal_service
        self.auth_token = universal_service.get_auth_token()
        self.wazuh_http_requests = WazuhHttpRequests(
            self.universal_service.connector_url,
            self.auth_token,
        )

    def disable_rule(
        self,
        request: Dict[str, Union[str, int]],
    ) -> Dict[str, Union[str, bool]]:
        """
        Disable a rule in Wazuh Manager.

        Args:
            request (Dict[str, Union[str, int]]): The request to disable a rule. It should contain 'rule_id', 'reason', and
            'length_of_time'.

        Returns:
            Dict[str, Union[str, bool]]: A dictionary indicating the success or failure of the operation.
        """
        try:
            self._validate_request(request)
            rule_id = request["rule_id"]
            filename = self._fetch_filename(rule_id)
            file_content = self._fetch_file_content(filename)
            previous_level, updated_file_content = self._set_level_1(
                file_content,
                rule_id,
            )
            xml_content = self._convert_to_xml(updated_file_content)
            self._store_disabled_rule_info(
                rule_id,
                previous_level,
                request["reason"],
                request["length_of_time"],
            )
            self._upload_updated_rule(filename, xml_content)
            UniversalService().restart_service()
            return {
                "message": f"Rule {rule_id} successfully disabled in file {filename}.",
                "success": True,
            }

        except Exception as e:
            logger.error(str(e))
            return {"message": str(e), "success": False}

    def _validate_request(self, request: Dict[str, Union[str, int]]) -> None:
        """
        Validate the request to disable a rule.

        Args:
            request (Dict[str, Union[str, int]]): The request to disable a rule.

        Raises:
            ValueError: If any of the required fields ('rule_id', 'reason', 'length_of_time') are missing in the request.
        """
        logger.info(f"Validating disable rule request: {request}")
        if "rule_id" not in request:
            raise ValueError("Request missing rule_id")
        if "reason" not in request:
            raise ValueError("Request missing reason")
        if "length_of_time" not in request:
            raise ValueError("Request missing length_of_time")
        request["length_of_time"] = int(request["length_of_time"])

    def _fetch_filename(self, rule_id: str) -> str:
        """
        Fetch the filename from the Wazuh-Manager that contains the rule to be disabled.

        Args:
            rule_id (str): The id of the rule to be disabled.

        Returns:
            str: The filename that contains the rule.

        Raises:
            ValueError: If the filename could not be fetched successfully.
        """
        filename_data = self.wazuh_http_requests.get_request(
            "rules",
            {"rule_ids": rule_id},
        )
        if not filename_data["success"]:
            raise ValueError(filename_data["message"])
        return filename_data["data"]["data"]["affected_items"][0]["filename"]

    def _fetch_file_content(
        self,
        filename: str,
    ) -> Union[Dict[str, str], List[Dict[str, str]]]:
        """
        Fetch the content of the file that contains the rule to be disabled.

        Args:
            filename (str): The filename that contains the rule.

        Returns:
            Union[Dict[str, str], List[Dict[str, str]]]: The content of the file.

        Raises:
            ValueError: If the file content could not be fetched successfully.
        """
        file_content_data = self.wazuh_http_requests.get_request(
            f"rules/files/{filename}",
        )
        if not file_content_data["success"]:
            raise ValueError(file_content_data["message"])
        return file_content_data["data"]["data"]["affected_items"][0]["group"]

    def _set_level_1(
        self,
        file_content: Union[Dict[str, str], List[Dict[str, str]]],
        rule_id: str,
    ) -> Tuple[str, Union[Dict[str, str], List[Dict[str, str]]]]:
        """
        Set the level of the rule to 1.

        Args:
            file_content (Union[Dict[str, str], List[Dict[str, str]]]): The content of the file that contains the rule.
            rule_id (str): The id of the rule to be disabled.

        Returns:
            Tuple[str, Union[Dict[str, str], List[Dict[str, str]]]]: A tuple containing the previous level of the rule and the updated file
            content.
        """
        logger.info(
            f"Setting rule {rule_id} level to 1 for file_content: {file_content}",
        )
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

    def _convert_to_xml(
        self,
        updated_file_content: Union[Dict[str, str], List[Dict[str, str]]],
    ) -> str:
        """
        Convert the updated file content to XML format.

        Args:
            updated_file_content (Union[Dict[str, str], List[Dict[str, str]]]): The updated file content.

        Returns:
            str: The updated file content in XML format.
        """
        logger.info(f"Received updated_file_content: {updated_file_content}")
        xml_content_list = []
        for group in updated_file_content:
            xml_dict = {"group": group}
            xml_content = xmltodict.unparse(xml_dict, pretty=True)
            xml_content = xml_content.replace(
                '<?xml version="1.0" encoding="utf-8"?>',
                "",
            )
            xml_content_list.append(xml_content)
        xml_content = "\n".join(xml_content_list)
        xml_content = xml_content.strip()
        return xml_content

    def _store_disabled_rule_info(
        self,
        rule_id: str,
        previous_level: str,
        reason: str,
        length_of_time: str,
    ) -> None:
        """
        Store information about the disabled rule in the database.

        Args:
            rule_id (str): The id of the rule.
            previous_level (str): The previous level of the rule before it was disabled.
            reason (str): The reason for disabling the rule.
            length_of_time (str): The length of time for which the rule will be disabled.
        """
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
        """
        Upload the updated rule to the Wazuh Manager.

        Args:
            filename (str): The filename that contains the rule.
            xml_content (str): The updated rule in XML format.

        Raises:
            ValueError: If the updated rule could not be uploaded successfully.
        """
        response = self.wazuh_http_requests.put_request(
            f"rules/files/{filename}",
            xml_content,
            {"overwrite": "true"},
        )
        if not response["success"]:
            raise ValueError(response["message"])
