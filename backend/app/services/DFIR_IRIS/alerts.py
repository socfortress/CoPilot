from typing import Any
from typing import Dict
from typing import Set

from dfir_iris_client.alert import Alert
from loguru import logger

from app.models.agents import agent_metadata_schema
from app.services.agents.agents import AgentService
from app.services.dfir_iris.host_enrichment import AssetTypeResolver
from app.services.dfir_iris.ioc_enrichment import DomainValidator
from app.services.dfir_iris.ioc_enrichment import HashValidator
from app.services.dfir_iris.ioc_enrichment import IPv4AddressValidator
from app.services.dfir_iris.universal import UniversalService


class IRISAlertsService:
    """
    A service class that encapsulates the logic for pulling alerts from DFIR-IRIS.

    Attributes
    ----------
    universal_service : UniversalService
        UniversalService object for interacting with "DFIR-IRIS"
    iris_session : Optional[dict]
        Session object for interacting with "DFIR-IRIS". None if session creation failed.

    Methods
    -------
    _create_iris_session() -> Optional[dict]:
        Create a session with the universal service.
    list_alerts() -> Dict[str, Any]:
        List all alerts from DFIR-IRIS.
    create_alert_general(alert_data: Dict[str, Any], alert_id: str, index: str) -> Dict[str, Any]:
        Create an alert with the provided data.
    get_agent_data(agent_id: str) -> Dict[str, Any]:
        Get agent data based on agent_id.
    get_asset_type_id(os: str) -> int:
        Use AssetTypeResolver to determine the asset type ID.
    validate_ioc_type(ioc_value: str) -> str:
        Validate IoC type using validators.
    create_alert_with_payload(alert_payload: Dict[str, Any]) -> Dict[str, Any]:
        Create an alert using given alert_payload.
    field_exists_ioc(alert_data: Dict[str, Any]) -> Dict[str, Any]:
        Check if an IoC field exists in the alert data.
    valid_ioc_fields() -> Set[str]:
        Get the set of valid IoC fields.
    create_general_payload(alert_data: Dict[str, Any], agent_data: Dict[str, Any], alert_id: str, index: str) -> Dict[str, Any]:
        Craft the general alert payload when it does not contain an IoC.
    create_general_ioc_payload(alert_data: Dict[str, Any], agent_data: Dict[str, Any], alert_id: str, index: str) -> Dict[str, Any]:
        Craft the general alert payload when it does contain an IoC.
    create_base_payload(alert_data: Dict[str, Any], agent_data: Dict[str, Any], alert_id: str, index: str) -> Dict[str, Any]:
        Craft the base alert payload.
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

    def bookmark_alert(self, alert_id: str) -> Dict[str, Any]:
        """
        Bookmark an alert in DFIR-IRIS.

        Parameters
        ----------
        alert_id : str
            The ID of the alert to bookmark.

        Returns
        -------
        Dict[str, Any]
            The result of the bookmark operation. Contains information on whether the bookmark operation was successful,
            an associated message, and the resulting data.
        """
        alert = Alert(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            alert.update_alert,
            alert_id,
            {"alert_tags": "bookmarked"},
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to bookmark alert in DFIR-IRIS",
            }

        return {
            "success": True,
            "message": "Successfully bookmarked alert in DFIR-IRIS",
            "results": result["data"],
        }

    def unbookmark_alert(self, alert_id: str) -> Dict[str, Any]:
        """
        Unbookmark an alert in DFIR-IRIS.

        Parameters
        ----------
        alert_id : str
            The ID of the alert to unbookmark.

        Returns
        -------
        Dict[str, Any]
            The result of the unbookmark operation. Contains information on whether the unbookmark operation was successful,
            an associated message, and the resulting data.
        """
        alert = Alert(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            alert.update_alert,
            alert_id,
            {"alert_tags": ""},
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to unbookmark alert in DFIR-IRIS",
            }

        return {
            "success": True,
            "message": "Successfully unbookmarked alert in DFIR-IRIS",
            "results": result["data"],
        }

    def list_bookmarked_alerts(self) -> Dict[str, Any]:
        """
        List all bookmarked alerts from DFIR-IRIS.

        Returns
        -------
        Dict[str, Any]
            The result of the bookmarked alerts listing. Contains information on whether the listing was successful,
            an associated message, and the resulting data.
        """
        alerts = self.list_alerts()["results"]["alerts"]
        # Loop thorugh the alerts and collect ones where `alert_tags` contains `bookmarked`
        bookmarked_alerts = []
        for alert in alerts:
            if alert["alert_tags"] is not None and "bookmarked" in alert["alert_tags"]:
                bookmarked_alerts.append(alert)
        return {
            "success": True,
            "message": "Successfully collected bookmarked alerts from DFIR-IRIS",
            "bookmarked_alerts": bookmarked_alerts,
        }

    def create_alert_general(self, alert_data: Dict[str, Any], alert_id: str, index: str) -> Dict[str, Any]:
        """
        Create an alert within DFIR-IRIS with the provided data.

        Parameters
        ----------
        alert_data : Dict[str, Any]
            The alert data used to create the alert.
        alert_id : str
            The ID of the alert.
        index : str
            The index.

        Returns
        -------
        Dict[str, Any]
            The result of the alert creation. Contains information on whether the alert creation was successful,
            an associated message, and the resulting data.
        """
        agent_data = self.get_agent_data(alert_data["agent_id"])
        alert_data["asset_type_id"] = self.get_asset_type_id(agent_data["os"])

        ioc_field_present = self.field_exists_ioc(alert_data)
        if ioc_field_present["success"]:
            logger.info(f"Found IoC field: {ioc_field_present}")
            alert_data["ioc_value"] = ioc_field_present["field_value"]
            alert_data["ioc_type"] = self.validate_ioc_type(ioc_field_present["field_value"])
            alert_payload = self.create_general_ioc_payload(alert_data, agent_data, alert_id, index)
        else:
            alert_payload = self.create_general_payload(alert_data, agent_data, alert_id, index)

        return self.create_alert_with_payload(alert_payload)

    def get_agent_data(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent data based on agent_id from the `agent_metadata` table.

        Parameters
        ----------
        agent_id : str
            The ID of the agent.

        Returns
        -------
        Dict[str, Any]
            The agent data corresponding to the given agent_id.
        """
        service = AgentService()
        agent = service.get_agent(agent_id)
        return agent_metadata_schema.dump(agent)

    def get_asset_type_id(self, os: str) -> int:
        """
        Use AssetTypeResolver to determine the asset type ID to set within DFIR-IRIS.

        Parameters
        ----------
        os : str
            The operating system (OS) string used to resolve the asset type ID.

        Returns
        -------
        int
            The ID corresponding to the asset type.
        """
        asset_resolver = AssetTypeResolver(os)
        return asset_resolver.get_asset_type_id()

    def validate_ioc_type(self, ioc_value: str) -> str:
        """
        Validate IoC type using validators.

        Parameters
        ----------
        ioc_value : str
            The value to validate the IoC type.

        Returns
        -------
        str
            The type of the IoC. Returns None if validation fails.
        """
        validators = [IPv4AddressValidator, HashValidator, DomainValidator]
        ioc_type = None

        for Validator in validators:
            validator = Validator(ioc_value)
            result = validator.validate()

            if result["success"]:
                ioc_type = result["ioc_type"]
                break

        if ioc_type is None:
            logger.error("Failed to validate IoC value.")
        return ioc_type

    def create_alert_with_payload(self, alert_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create the alert payload to be sent to DFIR-IRIS.

        Parameters
        ----------
        alert_payload : Dict[str, Any]
            The payload used to create the alert.

        Returns
        -------
        Dict[str, Any]
            The result of the alert creation. Contains information on whether the alert creation was successful,
            an associated message, and the resulting data.
        """
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
        Checks if an IoC field exists in the alert data.

        Parameters
        ----------
        alert_data : Dict[str, Any]
            The alert data to check for the presence of an IoC field.

        Returns
        -------
        Dict[str, Any]
            If an IoC field exists, returns a dictionary with 'success' set to True,
            'field_name' as the name of the field, and 'field_value' as the value of the field.
            If an IoC field does not exist, returns a dictionary with 'success' set to False,
            and 'field_name' set to None.
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
        Getter for the set of valid IoC fields.

        Returns
        -------
        Set[str]
            The set of valid IoC fields.
        """
        return {"misp_value", "opencti_value", "threat_intel_value"}

    def create_general_payload(self, alert_data: Dict[str, Any], agent_data: Dict[str, Any], alert_id: str, index: str) -> Dict[str, Any]:
        """
        Crafts the general alert payload when it does not contain an IoC.

        Parameters
        ----------
        alert_data : Dict[str, Any]
            The alert data.
        agent_data : Dict[str, Any]
            The agent data.
        alert_id : str
            The ID of the alert.
        index : str
            The index.

        Returns
        -------
        Dict[str, Any]
            The crafted alert payload. If an error occurs during crafting,
            a dictionary with 'success' set to False and an error message is returned.
        """
        try:
            payload = self.create_base_payload(alert_data, agent_data, alert_id, index)
            payload["alert_note"] = alert_data.get("ask_socfortress", "Ask SOCFortress not enabled")
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
        Crafts the general alert payload when it does contain an IoC.

        Parameters
        ----------
        alert_data : Dict[str, Any]
            The alert data.
        agent_data : Dict[str, Any]
            The agent data.
        alert_id : str
            The ID of the alert.
        index : str
            The index.

        Returns
        -------
        Dict[str, Any]
            The crafted alert payload with IoC. If an error occurs during crafting,
            a dictionary with 'success' set to False and an error message is returned.
        """
        try:
            payload = self.create_base_payload(alert_data, agent_data, alert_id, index)
            payload["alert_note"] = alert_data.get("ask_socfortress", "Ask SOCFortress not enabled")
            payload["alert_iocs"] = [
                {
                    "ioc_value": alert_data["ioc_value"],
                    "ioc_description": "IoC found in the alert",
                    "ioc_tlp_id": 1,
                    "ioc_type_id": alert_data["ioc_type"],
                },
            ]
            return payload
        except Exception as e:
            logger.error(f"Error creating general alert payload with IoC: {e}")
            return {"success": False, "message": f"Error creating general alert payload with IoC: {e}"}

    def create_base_payload(self, alert_data: Dict[str, Any], agent_data: Dict[str, Any], alert_id: str, index: str) -> Dict[str, Any]:
        """
        Crafts the base alert payload.

        Parameters
        ----------
        alert_data : Dict[str, Any]
            The alert data.
        agent_data : Dict[str, Any]
            The agent data.
        alert_id : str
            The ID of the alert.
        index : str
            The index.

        Returns
        -------
        Dict[str, Any]
            The crafted base alert payload.
        """
        return {
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
            "alert_status_id": 3,
            "alert_severity_id": 5,
            "alert_customer_id": 1,
            "alert_source_content": alert_data,
            "alert_context": {
                "alert_id": alert_id,
                "alert_name": alert_data["rule_description"],
                "alert_level": alert_data["rule_level"],
                "rule_id": alert_data["rule_id"],
                "asset_name": agent_data["hostname"],
                "asset_ip": agent_data["ip_address"],
                "asset_type": alert_data["asset_type_id"],
                "process_id": alert_data.get("process_id", "No process ID found"),
                "rule_mitre_id": alert_data.get("rule_mitre_id", "n/a"),
                "rule_mitre_tactic": alert_data.get("rule_mitre_tactic", "n/a"),
                "rule_mitre_technique": alert_data.get("rule_mitre_technique", "n/a"),
            },
        }
