from typing import Any
from typing import Dict
from typing import Iterable
from typing import Tuple

from elasticsearch7 import Elasticsearch
from loguru import logger

from app.services.ask_socfortress.universal import AskSocfortressService
from app.services.DFIR_IRIS.alerts import IRISAlertsService
from app.services.WazuhIndexer.universal import QueryBuilder
from app.services.WazuhIndexer.universal import UniversalService


class AlertsService:
    """
    A service class that encapsulates the logic for pulling alerts from the Wazuh-Indexer.
    """

    SKIP_INDEX_NAMES: Dict[str, bool] = {
        "wazuh-statistics": True,
        "wazuh-monitoring": True,
    }

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
        self.asksocfortress_service = AskSocfortressService("AskSocfortress")
        (
            self.connector_url,
            self.connector_api_key,
        ) = self.asksocfortress_service.collect_asksocfortress_details("AskSocfortress")

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

    def collect_alerts(self, size: int, timerange: str, alert_field: str, alert_value: str) -> Dict[str, object]:
        """
        Collects alerts from the Wazuh-Indexer.

        Args:
            size (int): The maximum number of alerts to return.
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.
            alert_field (str): The field to match.
            alert_value (str): The value to match.
        Returns:
            Dict[str, object]: A dictionary containing success status and alerts or an error message.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_summary = []
        # matches = [("syslog_level", "ALERT"), ("agent_name", "WIN-39O01J5F7G5")]
        # matches = [("syslog_level", "ALERT")]
        matches = [(alert_field, alert_value)]
        for index_name in indices_validation["indices"]:
            alerts = self._collect_alerts(index_name, size=size, timerange=timerange, matches=matches)
            if alerts["success"] and len(alerts["alerts"]) > 0:
                alerts_summary.append(
                    {
                        "index_name": index_name,
                        "total_alerts": len(alerts["alerts"]),
                        "alerts": alerts["alerts"],
                    },
                )
        return {
            "message": f"Successfully collected top {size} alerts from the last {timerange}",
            "success": True,
            "alerts_summary": alerts_summary,
        }

    def collect_alerts_last_24_hours(self, size: int) -> Dict[str, object]:
        """
        Collects alerts from the last 24 hours from the Wazuh-Indexer.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_summary = []
        for index_name in indices_validation["indices"]:
            alerts = self._collect_alerts(index_name, size=size, query=self._build_query_last_24_hours())
            if alerts["success"] and len(alerts["alerts"]) > 0:
                alerts_summary.append(
                    {
                        "index_name": index_name,
                        "total_alerts": len(alerts["alerts"]),
                        "alerts": alerts["alerts"],
                    },
                )
        return {
            "message": f"Successfully collected top {size} alerts from the last 24 hours",
            "success": True,
            "alerts_summary": alerts_summary,
        }

    def collect_alerts_by_index(self, index_name: str, size: int, timerange: str, alert_field: str, alert_value: str) -> Dict[str, Any]:
        """
        Collects alerts from the given index.

        Args:
            index_name (str): The name of the index to query.
            size (int): The maximum number of alerts to return.
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.
            alert_field (str): The field to match.
            alert_value (str): The value to match.

        Returns:
            Dict[str, Any]: A dictionary containing success status, a message, and potentially the alerts from the given index.
        """
        if not self.is_valid_index(index_name):
            return self._error_response("Invalid index name")

        matches = [(alert_field, alert_value)]
        alerts = self._collect_alerts(index_name=index_name, size=size, timerange=timerange, matches=matches)
        if not alerts["success"]:
            return alerts

        return {
            "message": f"Successfully collected top {size} alerts from {index_name}",
            "success": True,
            "alerts": alerts["alerts"],
            "total_alerts": len(alerts["alerts"]),
        }

    def collect_alerts_by_agent_name(
        self,
        agent_name: str,
        size: int,
        timerange: str,
        alert_field: str,
        alert_value: str,
    ) -> Dict[str, Any]:
        """
        Collects alerts associated with a given agent name.

        Args:
            agent_name (str): The agent name associated with the alerts.
            size (int): The maximum number of alerts to return.
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.
            alert_field (str): The field to match.
            alert_value (str): The value to match.

        Returns:
            Dict[str, Any]: A dictionary containing success status, a message, and potentially the alerts associated with the agent.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_by_agent_dict = {}
        matches = [(alert_field, alert_value), ("agent_name", f"{agent_name}")]
        for index_name in indices_validation["indices"]:
            alerts = self._collect_alerts(index_name=index_name, size=size, timerange=timerange, matches=matches)
            if alerts["success"]:
                for alert in alerts["alerts"]:
                    if alert["_source"]["agent_name"] == agent_name:
                        alerts_by_agent_dict[alert["_id"]] = alert["_source"]

        alerts_by_agent_list = [{"alert_id": alert_id, "alert": alert} for alert_id, alert in alerts_by_agent_dict.items()]

        return {
            "message": f"Successfully collected alerts associated with agent {agent_name}",
            "success": True,
            "alerts_by_agent": alerts_by_agent_list,
        }

    def collect_alerts_by_host(self, size: int, timerange: str, alert_field: str, alert_value: str) -> Dict[str, int]:
        """
        Collects the number of alerts per host.

        Args:
            size (int): The maximum number of alerts to return.
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.
            alert_field (str): The field to match.
            alert_value (str): The value to match.

        Returns:
            Dict[str, int]: A dictionary containing success status and the number of alerts per host or an error message.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_by_host_dict = {}
        matches = [(alert_field, alert_value)]
        for index_name in indices_validation["indices"]:
            alerts = self._collect_alerts(index_name=index_name, size=size, timerange=timerange, matches=matches)
            if alerts["success"]:
                for alert in alerts["alerts"]:
                    host = alert["_source"]["agent_name"]
                    alerts_by_host_dict[host] = alerts_by_host_dict.get(host, 0) + 1

        alerts_by_host_list = [{"hostname": host, "number_of_alerts": count} for host, count in alerts_by_host_dict.items()]

        return {
            "message": "Successfully collected alerts by host",
            "success": True,
            "alerts_by_host": alerts_by_host_list,
        }

    def collect_alerts_by_rule(self, size: int, timerange: str, alert_field: str, alert_value: str) -> Dict[str, int]:
        """
        Collects the number of alerts per rule.

        Args:
            size (int): The maximum number of alerts to return.
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.
            alert_field (str): The field to match.
            alert_value (str): The value to match.

        Returns:
            Dict[str, int]: A dictionary containing success status and the number of alerts per rule or an error message.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_by_rule_dict = {}
        matches = [(alert_field, alert_value)]
        for index_name in indices_validation["indices"]:
            alerts = self._collect_alerts(index_name=index_name, size=size, timerange=timerange, matches=matches)
            if alerts["success"]:
                for alert in alerts["alerts"]:
                    rule = alert["_source"]["rule_description"]
                    alerts_by_rule_dict[rule] = alerts_by_rule_dict.get(rule, 0) + 1

        alerts_by_rule_list = [{"rule": rule, "number_of_alerts": count} for rule, count in alerts_by_rule_dict.items()]

        return {
            "message": "Successfully collected alerts by rule",
            "success": True,
            "alerts_by_rule": alerts_by_rule_list,
        }

    def collect_alerts_by_rule_per_host(self, size: int, timerange: str, alert_field: str, alert_value: str) -> Dict[str, int]:
        """
        Collects the number of alerts per rule per host.

        Args:
            size (int): The maximum number of alerts to return.
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.
            alert_field (str): The field to match.
            alert_value (str): The value to match.

        Returns:
            Dict[str, int]: A dictionary containing success status and the number of alerts per rule per host or an error message.
        """
        indices_validation = self._collect_indices_and_validate()
        if not indices_validation["success"]:
            return indices_validation

        alerts_by_rule_per_host_dict = {}
        matches = [(alert_field, alert_value)]
        for index_name in indices_validation["indices"]:
            alerts = self._collect_alerts(index_name=index_name, size=size, timerange=timerange, matches=matches)
            if alerts["success"]:
                for alert in alerts["alerts"]:
                    rule = alert["_source"]["rule_description"]
                    host = alert["_source"]["agent_name"]
                    alerts_by_rule_per_host_dict[rule] = alerts_by_rule_per_host_dict.get(rule, {})
                    alerts_by_rule_per_host_dict[rule][host] = alerts_by_rule_per_host_dict[rule].get(host, 0) + 1

        alerts_by_rule_per_host_list = []
        for rule, hosts in alerts_by_rule_per_host_dict.items():
            for host, count in hosts.items():
                alerts_by_rule_per_host_list.append({"rule": rule, "hostname": host, "number_of_alerts": count})

        return {
            "message": "Successfully collected alerts by rule per host",
            "success": True,
            "alerts_by_rule_per_host": alerts_by_rule_per_host_list,
        }

    @staticmethod
    def _error_response(message: str) -> Dict[str, bool]:
        """
        Standardizes the error response format.
        """
        return {"message": message, "success": False}

    def _collect_alerts(
        self,
        index_name: str,
        size: int = None,
        timerange: str = "24h",
        matches: Iterable[Tuple[str, str]] = None,
    ) -> Dict[str, object]:
        """
        Elasticsearch query to get the most recent alerts where the `rule_level` is 12 or higher or the
        `syslog_level` field is `ALERT` and return the results in descending order by the `timestamp_utc` field.
        The number of alerts to return can be limited by the `size` parameter.

        Args:
            index_name (str): The name of the index to query.
            size (int, optional): The maximum number of alerts to return. If None, all alerts are returned.
            timerange (str, optional): The time range to collect alerts from. This is a string like "24h", "1w", etc.
            matches (Iterable[Tuple[str, str]], optional): A list of tuples representing the field and value to match.
                I.E: [("syslog_level", "ALERT"), ("agent_name", "WIN-39O01J5F7G5")]

        Returns:
            Dict[str, object]: A dictionary containing success status and alerts or an error message.
        """
        logger.info(f"Collecting alerts from {index_name}")

        # Use QueryBuilder to construct the query
        query_builder = QueryBuilder()
        query_builder.add_time_range(timerange)
        if matches is not None:
            query_builder.add_matches(matches)
        else:
            query_builder.add_matches([("syslog_level", "ALERT")])
        # query_builder.add_range("rule_level", "12") # removed to get all alerts regardless of rule level
        query_builder.add_sort("timestamp_utc")

        # Get the final query
        query = query_builder.build()

        try:
            alerts = self.es.search(index=index_name, body=query, size=size)
            alerts_list = [alert for alert in alerts["hits"]["hits"]]

            # Iterate over each alert and invoke invoke_socfortress function
            for alert in alerts_list:
                ask_socfortress = self.asksocfortress_service.invoke_asksocfortress(alert["_source"]["rule_description"])
                alert["ask_socfortress"] = ask_socfortress  # Add the result to the alert

            return {
                "message": "Successfully collected alerts",
                "success": True,
                "alerts": alerts_list,  # Return the alerts list with the added results
            }
        except Exception as e:
            logger.error(f"Failed to collect alerts: {e}")
            return {"message": "Failed to collect alerts", "success": False}

    def _collect_alert(self, alert_id: str, index: str) -> Dict[str, Any]:
        """
        Collects an alert from Elasticsearch.

        Args:
            alert_uid (str): The alert UID.
            index (str): The name of the index to query.

        Returns:
            Dict[str, Any]: A dictionary containing success status and the alert or an error message.
        """
        logger.info(f"Collecting alert {alert_id} from {index}")
        try:
            alert = self.es.get(index=index, id=alert_id)
            return {"message": "Successfully collected alert", "success": True, "alert": alert["_source"]}
        except Exception as e:
            logger.error(f"Failed to collect alert: {e}")
            return {"message": "Failed to collect alert", "success": False}

    # @staticmethod
    # def _get_time_range_start(timerange: str) -> str:
    #     """
    #     Determines the start time of the time range based on the current time and the provided timerange.

    #     Args:
    #         timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.

    #     Returns:
    #         str: A string representing the start time of the time range in ISO format.
    #     """
    #     if timerange.endswith("h"):
    #         delta = timedelta(hours=int(timerange[:-1]))
    #     elif timerange.endswith("d"):
    #         delta = timedelta(days=int(timerange[:-1]))
    #     elif timerange.endswith("w"):
    #         delta = timedelta(weeks=int(timerange[:-1]))
    #     else:
    #         raise ValueError("Invalid timerange format. Expected a string like '24h', '1d', '1w', etc.")

    #     start = datetime.utcnow() - delta
    #     return start.isoformat() + "Z"  # Elasticsearch expects the time in ISO format with a Z at the end

    @staticmethod
    def _build_query(timerange: str) -> Dict[str, object]:
        """
        Builds the Elasticsearch query to get the most recent alerts where the `rule_level` is 12 or higher or
        the `syslog_level` field is `ALERT`.

        Args:
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.

        Returns:
            Dict[str, object]: A dictionary representing the Elasticsearch query.
        """
        start = AlertsService._get_time_range_start(timerange)

        return {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"timestamp_utc": {"gte": start, "lte": "now"}}},
                        {
                            "bool": {
                                "should": [
                                    {"range": {"rule_level": {"gte": 12}}},
                                    {"match": {"syslog_level": "ALERT"}},
                                ],
                            },
                        },
                    ],
                },
            },
            "sort": [{"timestamp_utc": {"order": "desc"}}],
        }

    def escalate_alert(self, alert_id: str, index: str) -> Dict[str, Any]:
        """
        Escalates an alert by creating it in DFIR-IRIS

        Args:
            alert_id (str): The alert UID.
            index (str): The index name.

        Returns:
            Dict[str, Any]: A dictionary containing success status and escalation message or an error message.
        """
        try:
            alert_details = self._collect_alert(alert_id=alert_id, index=index)
            service = IRISAlertsService()
            logger.info(f"Escalating alert {alert_details} to DFIR-IRIS")
            ask_socfortress = self.asksocfortress_service.invoke_asksocfortress(alert_details["alert"]["rule_description"])
            try:
                alert_details["alert"]["ask_socfortress"] = ask_socfortress["response"]
            except Exception:
                alert_details["alert"]["ask_socfortress"] = ask_socfortress["message"]
            escalation = service.create_alert_general(alert_data=alert_details["alert"], alert_id=alert_id, index=index)
            return {"message": escalation["message"], "success": True}
        except Exception as e:
            logger.error(f"Failed to escalate alert: {e}")
            return {"message": "Failed to escalate alert", "success": False}
