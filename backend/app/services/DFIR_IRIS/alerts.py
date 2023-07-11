from typing import Dict

# import requests
from dfir_iris_client.alert import Alert

# from dfir_iris_client.helper.utils import assert_api_resp
# from dfir_iris_client.helper.utils import get_data_from_resp
from loguru import logger

from app.services.DFIR_IRIS.universal import UniversalService


class AlertsService:
    """
    A service class that encapsulates the logic for pulling alerts from DFIR-IRIS. It creates a DFIR-IRIS session upon
    initialization and uses it to fetch alerts.
    """

    def __init__(self):
        """
        Initializes the AlertsService by creating a UniversalService object for "DFIR-IRIS" and establishing a session.
        If the session creation is unsuccessful, an error is logged and the iris_session attribute is set to None.
        """
        self.universal_service = UniversalService("DFIR-IRIS")
        session_result = self.universal_service.create_session()

        if not session_result["success"]:
            logger.error(session_result["message"])
            self.iris_session = None
        else:
            self.iris_session = session_result["session"]

    def list_alerts(self) -> Dict[str, object]:
        """
        List all alerts from DFIR-IRIS. If the iris_session attribute is None, this indicates that the session creation
        was unsuccessful, and a dictionary with "success" set to False is returned. Otherwise, it attempts to fetch and
        parse the alerts data.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the fetched alerts. The
            "success" key is a boolean indicating whether the operation was successful. The "message" key is a string
            providing details about the operation. The "results" key, included when "success" is True, contains the
            fetched alerts data.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info("Collecting cases from DFIR-IRIS")
        alert = Alert(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            alert.filter_alerts,
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to collect cases from DFIR-IRIS",
            }

        return {
            "success": True,
            "message": "Successfully collected cases from DFIR-IRIS",
            "results": result["data"],
        }
