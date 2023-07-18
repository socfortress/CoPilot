# Standard library imports
from typing import Any
from typing import Dict
from typing import Set

# Local application imports
from dfir_iris_client.alert import Alert

# Third-party library imports
from loguru import logger

from app.models.agents import agent_metadata_schema
from app.services.agents.agents import AgentService
from app.services.DFIR_IRIS.host_enrichment import AssetTypeResolver
from app.services.DFIR_IRIS.ioc_enrichment import DomainValidator
from app.services.DFIR_IRIS.ioc_enrichment import HashValidator
from app.services.DFIR_IRIS.ioc_enrichment import IPv4AddressValidator
from app.services.DFIR_IRIS.universal import UniversalService


class IRISAlertsService:
    """
    A service class that encapsulates the logic for pulling alerts from DFIR-IRIS.
    """

    def __init__(self):
        """
        Initializes the AlertsService by creating a UniversalService object for "DFIR-IRIS".
        """
        self.universal_service = UniversalService("DFIR-IRIS")
        self.iris_session = self._create_iris_session()

    def _create_iris_session(self):
        """
        Create a session with the universal service. If the session creation fails,
        log an error and return None.
        """
        session_result = self.universal_service.create_session()
        if not session_result["success"]:
            logger.error(session_result["message"])
            return None
        return session_result["session"]

    def list_alerts(self) -> Dict[str, object]:
        """
        List all alerts from DFIR-IRIS.
        If the iris_session attribute is None, this indicates that the session creation
        was unsuccessful, and a dictionary with "success" set to False is returned.
        Otherwise, it attempts to fetch and parse the alerts data.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        alert = Alert(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            alert.filter_alerts,
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to collect alerts from DFIR-IRIS",
            }

        return {
            "success": True,
            "message": "Successfully collected alerts from DFIR-IRIS",
            "results": result["data"],
        }

    def create_alert_general(self, alert_data: Dict[str, Any], alert_id: str, index: str) -> Dict[str, Any]:
        """
        Create an alert with the provided data.
        """
        # Get agent data
        agent_id = alert_data["agent_id"]
        service = AgentService()
        agent = service.get_agent(agent_id)
        agent_data = agent_metadata_schema.dump(agent)

        # Use AssetTypeResolver to determine the asset type ID
        asset_resolver = AssetTypeResolver(agent_data["os"])
        agent_asset_type = asset_resolver.get_asset_type_id()

        # Append the asset type ID to the alert data
        alert_data["asset_type_id"] = agent_asset_type

        # Check if IoC field exists
        ioc_field_present = self.field_exists_ioc(alert_data)
        if ioc_field_present["success"]:
            logger.info(f"Found IoC field: {ioc_field_present}")
            alert_data["ioc_value"] = ioc_field_present["field_value"]

            # Define the validator classes to be used
            validators = [IPv4AddressValidator, HashValidator, DomainValidator]
            ioc_type = None

            # Iterate over each validator class
            for Validator in validators:
                validator = Validator(ioc_field_present["field_value"])
                result = validator.validate()

                # If the validation is successful, store the ioc_type and break the loop
                if result["success"]:
                    ioc_type = result["ioc_type"]
                    break

            if ioc_type is not None:
                alert_data["ioc_type"] = ioc_type
            else:
                logger.error("Failed to validate IoC value.")

            alert_payload = self.create_general_ioc_payload(alert_data=alert_data, agent_data=agent_data, alert_id=alert_id, index=index)

            # Create an alert
            alert = Alert(session=self.iris_session)
            result = self.universal_service.fetch_and_parse_data(
                self.iris_session,
                alert.add_alert,
                alert_payload,
            )

            if not result["success"]:
                return {
                    "success": False,
                    "message": "Failed to create alert in DFIR-IRIS",
                }

            return {
                "success": True,
                "message": "Successfully created alert in DFIR-IRIS",
                "results": result["data"],
            }

        # Create alert payload
        alert_payload = self.create_general_payload(alert_data=alert_data, agent_data=agent_data, alert_id=alert_id, index=index)

        # Create an alert
        alert = Alert(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            alert.add_alert,
            alert_payload,
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to create alert in DFIR-IRIS",
            }

        return {
            "success": True,
            "message": "Successfully created alert in DFIR-IRIS",
            "results": result["data"],
        }

    def field_exists_ioc(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an IoC field exists in the alert data.
        """
        for field_name in self.valid_ioc_fields:
            if field_name in alert_data:
                return {
                    "success": True,
                    "field_name": field_name,
                    "field_value": alert_data[field_name],
                }
        return {"success": False, "field_name": None}

    @property
    def valid_ioc_fields(self) -> Set[str]:
        """
        Get the set of valid IoC fields.
        """
        return {"misp_value", "opencti_value", "threat_intel_value"}

    def create_general_payload(self, alert_data: Dict[str, Any], agent_data: Dict[str, Any], alert_id: str, index: str) -> Dict[str, Any]:
        """
        Craft the general alert payload when it does not contain an IoC.
        """
        try:
            payload = {
                "alert_title": alert_data["rule_description"],
                "alert_description": alert_data["rule_description"],
                "alert_source": "Wazuh",
                "assets": [
                    {
                        "asset_name": agent_data["hostname"],
                        "asset_ip": agent_data["ip_address"],
                        "asset_description": agent_data["os"],
                        "asset_type_id": alert_data["asset_type_id"],
                    },
                ],
                # "alert_source_link": f"{self.grafana_url}/explore?left=%5B%22now-6h%22,%22now%22,%22WAZUH%22,%7B%22refId%22"
                # ":%22A%22,%22query%22:%22process_id:%5C%22"
                # f"{alert_data['process_id']}%5C%22%20AND%20"
                # f"agent_name:%5C%22{alert_data['agent_name']}%5C%22%22,%22alias%22"
                # ":%22%22,%22metrics%22:%5B%7B%22id%22:%221%22,%22type%22:%22logs%22,%22settings%22:%7B%22limit%22:%22500%22"
                # "%7D%7D%5D,%22bucketAggs%22:%5B%5D,%22timeField%22:%22timestamp%22%7D%5D",
                "alert_status_id": 3,
                "alert_severity_id": 5,
                # "alert_customer_id": customer_code_details["customer_code_iris_id"],
                "alert_customer_id": 1,
                "alert_source_content": alert_data,
                "alert_context": {
                    # "customer_id": f"{alert_data['alert_payload']['alert_details']['_source']['agent_labels_customer']},"
                    # f"{customer_code_details['customer_code_iris_index']}",
                    "alert_id": alert_id,
                    "alert_name": alert_data["rule_description"],
                    "alert_level": alert_data["rule_level"],
                    "rule_id": alert_data["rule_id"],
                    "asset_name": agent_data["hostname"],
                    "asset_ip": agent_data["ip_address"],
                    "asset_type": alert_data["asset_type_id"],
                    "process_id": alert_data["process_id"],
                    # If the `rule_mitre_id` field exists in the alert_details, add it to the payload
                    "rule_mitre_id": alert_data.get("rule_mitre_id", "n/a"),
                    "rule_mitre_tactic": alert_data.get("rule_mitre_tactic", "n/a"),
                    "rule_mitre_technique": alert_data.get("rule_mitre_technique", "n/a"),
                },
                "alert_note": alert_data.get("ask_socfortress", "Ask SOCFortress not enabled"),
            }
            return payload
        except Exception as e:
            logger.error(f"Error creating general alert payload: {e}")
            return {"success": False, "message": f"Error creating general alert payload: {e}"}

    def create_general_ioc_payload(
        self,
        alert_data: Dict[str, Any],
        agent_data: Dict[str, Any],
        alert_id: str,
        index: str,
    ) -> Dict[str, Any]:
        """
        Craft the general alert payload when it does contain an IoC.
        """
        try:
            payload = {
                "alert_title": alert_data["rule_description"],
                "alert_description": alert_data["rule_description"],
                "alert_source": "Wazuh",
                "assets": [
                    {
                        "asset_name": agent_data["hostname"],
                        "asset_ip": agent_data["ip_address"],
                        "asset_description": agent_data["os"],
                        "asset_type_id": alert_data["asset_type_id"],
                    },
                ],
                # "alert_source_link": f"{self.grafana_url}/explore?left=%5B%22now-6h%22,%22now%22,%22WAZUH%22,%7B%22refId%22"
                # ":%22A%22,%22query%22:%22process_id:%5C%22"
                # f"{alert_data['process_id']}%5C%22%20AND%20"
                # f"agent_name:%5C%22{alert_data['agent_name']}%5C%22%22,%22alias%22"
                # ":%22%22,%22metrics%22:%5B%7B%22id%22:%221%22,%22type%22:%22logs%22,%22settings%22:%7B%22limit%22:%22500%22"
                # "%7D%7D%5D,%22bucketAggs%22:%5B%5D,%22timeField%22:%22timestamp%22%7D%5D",
                "alert_status_id": 3,
                "alert_severity_id": 5,
                # "alert_customer_id": customer_code_details["customer_code_iris_id"],
                "alert_customer_id": 1,
                "alert_source_content": alert_data,
                "alert_context": {
                    # "customer_id": f"{alert_data['alert_payload']['alert_details']['_source']['agent_labels_customer']},"
                    # f"{customer_code_details['customer_code_iris_index']}",
                    "alert_id": alert_id,
                    "alert_name": alert_data["rule_description"],
                    "alert_level": alert_data["rule_level"],
                    "rule_id": alert_data["rule_id"],
                    "asset_name": agent_data["hostname"],
                    "asset_ip": agent_data["ip_address"],
                    "asset_type": alert_data["asset_type_id"],
                    "process_id": alert_data["process_id"],
                    # If the `rule_mitre_id` field exists in the alert_details, add it to the payload
                    "rule_mitre_id": alert_data.get("rule_mitre_id", "n/a"),
                    "rule_mitre_tactic": alert_data.get("rule_mitre_tactic", "n/a"),
                    "rule_mitre_technique": alert_data.get("rule_mitre_technique", "n/a"),
                },
                "alert_note": alert_data.get("ask_socfortress", "Ask SOCFortress not enabled"),
                "alert_iocs": [
                    {
                        "ioc_value": alert_data["ioc_value"],
                        "ioc_description": "IoC found in the alert",
                        "ioc_tlp_id": 1,
                        "ioc_type_id": alert_data["ioc_type"],
                    },
                ],
            }
            return payload
        except Exception as e:
            logger.error(f"Error creating general alert payload with IoC: {e}")
            return {"success": False, "message": f"Error creating general alert payload with IoC: {e}"}
