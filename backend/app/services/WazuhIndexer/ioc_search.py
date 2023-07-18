import ipaddress
import re
from typing import Any
from typing import Dict

from elasticsearch7 import Elasticsearch
from loguru import logger

from app.services.threat_intel.socfortress.universal import (
    SocfortressThreatIntelService,
)
from app.services.WazuhIndexer.universal import UniversalService


class IocSearchService:
    """
    A service class that encapsulates the logic for searching the Wazuh Indexer for IoCs.
    """

    SKIP_INDEX_NAMES: Dict[str, bool] = {
        "wazuh-statistics": True,
        "wazuh-monitoring": True,
    }

    INVALID_DOMAINS = [
        ".internal",
        ".home",
        ".local",
        ".lan",
        ".corp",
        ".localdomain",
        ".intranet",
        ".localnet",
        ".priv",
    ]

    def __init__(self):
        """
        Initializes the service by collecting Wazuh-Indexer details and creating an Elasticsearch client.
        """
        self.universal_service = UniversalService()
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = self.universal_service.collect_wazuhindexer_details("Wazuh-Indexer")
        self.es = Elasticsearch(
            [self.connector_url],
            http_auth=(self.connector_username, self.connector_password),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )
        self.socfortress_threat_intel_service = SocfortressThreatIntelService("SocfortressThreatIntel")

    def is_index_skipped(self, index_name: str) -> bool:
        """
        Checks whether the given index name should be skipped.
        """
        return any(index_name.startswith(skipped) for skipped in self.SKIP_INDEX_NAMES)

    def is_valid_index(self, index_name: str) -> bool:
        """
        Checks if the index name starts with "wazuh_" and is not in the SKIP_INDEX_NAMES list.
        """
        return index_name.startswith("wazuh_") and not self.is_index_skipped(index_name)

    def _collect_indices_and_validate(self) -> Dict[str, Any]:
        """
        Collect indices and validate connector details.
        """
        if not all([self.connector_url, self.connector_username, self.connector_password]):
            return self._error_response("Failed to collect Wazuh-Indexer details")

        indices_list = self.universal_service.collect_indices()
        if not indices_list["success"]:
            return self._error_response("Failed to collect indices")

        valid_indices = [index for index in indices_list["indices_list"] if self.is_valid_index(index)]

        return {"success": True, "indices": valid_indices}

    def search_ioc(self, field_name: str, time_range: str) -> Dict[str, object]:
        """
        Search for IoCs from the given field name.

        Args:
            field_name (str): The field name to search for IoCs.
            time_range (str): The time range to search for IoCs. I.E: 24h

        Returns:
            Dict[str, object]: A dictionary containing the list of all alerts from Wazuh.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_summary = []
        for index_name in indices_validation["indices"]:
            alerts = self._collect_iocs(index_name, field_name=field_name, time_range=time_range)
            if alerts["success"] and len(alerts["alerts"]) > 0:
                alerts_summary.append(
                    {
                        "index_name": index_name,
                        "total_alerts": len(alerts["alerts"]),
                        "alerts": alerts["alerts"],
                    },
                )
        return {
            "message": f"Successfully collected alerts with discovered IoCs from {field_name}",
            "success": True,
            "alerts_summary": alerts_summary,
        }

    @staticmethod
    def _error_response(message: str) -> Dict[str, bool]:
        """
        Standardizes the error response format.
        """
        return {"message": message, "success": False}

    @staticmethod
    def is_invalid_domain_name(field_value: str) -> bool:
        """
        Checks if the given field value is an internal domain name.

        Args:
            field_value (str): The field value to check.

        Returns:
            bool: True if the field value is an internal domain name, False otherwise.
        """
        return any(field_value.endswith(domain) for domain in IocSearchService.INVALID_DOMAINS)

    @staticmethod
    def is_valid_domain_name(domain: str) -> bool:
        """
        Checks if the given domain name is valid.

        Args:
            domain (str): The domain name to check.

        Returns:
            bool: True if the domain name is valid, False otherwise.
        """
        pattern = r"(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9\-]{0,61}[a-z0-9]"
        return re.fullmatch(pattern, domain) is not None

    @staticmethod
    def is_valid_ipv4(field_value: str) -> bool:
        """
        Checks if the given field value is a valid IPv4 address.

        Args:
            field_value (str): The field value to check.

        Returns:
            bool: True if the field value is a valid IPv4 address, False otherwise.
        """
        try:
            ipaddress.IPv4Address(field_value)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_md5(field_value: str) -> bool:
        """
        Checks if the given field value is a valid MD5 hash.

        Args:
            field_value (str): The field value to check.

        Returns:
            bool: True if the field value is a valid MD5 hash, False otherwise.
        """
        return bool(re.fullmatch(r"[a-fA-F0-9]{32}", field_value))

    @staticmethod
    def is_valid_sha256(field_value: str) -> bool:
        """
        Checks if the given field value is a valid SHA256 hash.

        Args:
            field_value (str): The field value to check.

        Returns:
            bool: True if the field value is a valid SHA256 hash, False otherwise.
        """
        return bool(re.fullmatch(r"[a-fA-F0-9]{64}", field_value))

    def is_valid_field_value(self, field_value: str) -> bool:
        """
        Validates the field value as per different conditions.

        Args:
            field_value (str): The field value to check.

        Returns:
            bool: True if the field value is valid, False otherwise.
        """
        if self.is_invalid_domain_name(field_value):
            logger.info(f"Skipping invalid domain name: {field_value}")
            return False

        if not (
            self.is_valid_ipv4(field_value)
            or self.is_valid_md5(field_value)
            or self.is_valid_sha256(field_value)
            or self.is_valid_domain_name(field_value)
        ):
            logger.info(f"Skipping invalid field value: {field_value}")
            return False

        return True

    def _collect_iocs(self, index_name: str, field_name: str, time_range: str) -> Dict[str, object]:
        """
        Elasticsearch query to retrieve all values of a given field and index to
        invoke the IOC service to discover if the value is malicious or not.
        I.E: `data_srcip` field in `wazuh-*` index.

        Args:
            index_name (str): The index name to query.
            field_name (str): The field name to query.
            time_range (str): The time range to query. I.E: 24h

        Returns:
            Dict[str, object]: The response from the IOC service.
        """
        logger.info(f"Collecting alerts from {index_name}")
        query = self._build_query(field_name=field_name, time_range=time_range)
        try:
            alerts = self.es.search(index=index_name, body=query)
            alerts_list = self._filter_and_enrich_alerts(alerts["hits"]["hits"], field_name)
            return {
                "message": "Successfully collected alerts",
                "success": True,
                "alerts": alerts_list,
            }
        except Exception as e:
            logger.error(f"Failed to collect alerts: {e}")
            return {"message": "Failed to collect alerts", "success": False}

    def _filter_and_enrich_alerts(self, alerts_list, field_name):
        """
        Filters out invalid domain names and enriches the alerts with socfortress_threat_intel.
        """
        alerts_list_with_response = []  # Create a new list to store alerts with responses
        for alert in alerts_list:
            field_value = alert["_source"][field_name]
            # Skip if field value is invalid
            if not self.is_valid_field_value(field_value):
                continue

            socfortress_threat_intel = self.socfortress_threat_intel_service.invoke_socfortress_threat_intel(data=field_value)
            logger.info(f"Socfortress threat intel response: {socfortress_threat_intel}")
            # if `response` is not empty, add it to the alert
            if socfortress_threat_intel["response"]:
                alert["_source"]["socfortress_threat_intel"] = socfortress_threat_intel["response"]
                alerts_list_with_response.append(alert)  # Add the alert to the new list
        return alerts_list_with_response

    @staticmethod
    def _build_query(field_name: str, time_range: str) -> Dict[str, Any]:
        """
        Builds the Elasticsearch query to retrieve all values of a given field.

        Args:
            field_name (str): The field name to query.
            time_range (str): The time range to query. I.E: 24h

        Returns:
            Dict[str, Any]: The Elasticsearch query.
        """
        return {
            "query": {
                "bool": {
                    "must": [
                        {
                            "exists": {
                                "field": field_name,
                            },
                        },
                        {
                            "range": {
                                "timestamp": {
                                    "gte": f"now-{time_range}",
                                },
                            },
                        },
                    ],
                },
            },
        }
