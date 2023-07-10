from typing import Dict
import requests
from loguru import logger
from app.services.DFIR_IRIS.universal import UniversalService
from dfir_iris_client.helper.utils import assert_api_resp
from dfir_iris_client.helper.utils import get_data_from_resp
from dfir_iris_client.alert import Alert


class AlertsService:
    """
    A service class that encapsulates the logic for pulling alerts from DFIR-IRIS.
    """

    def __init__(self):
        self.universal_service = UniversalService("DFIR-IRIS")
        session_result = self.universal_service.create_session()
        
        if not session_result['success']:
            logger.error(session_result['message'])
            self.iris_session = None
        else:
            self.iris_session = session_result['session']

    def list_alerts(self) -> Dict[str, object]:
        """
        Lists all alerts from DFIR-IRIS

        Returns:
            dict: A dictionary containing the success status, a message and potentially the cases.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info("Collecting cases from DFIR-IRIS")
        alert = Alert(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(self.iris_session, alert.filter_alerts)

        if not result["success"]:
            return {"success": False, "message": "Failed to collect cases from DFIR-IRIS"}

        return {"success": True, "message": "Successfully collected cases from DFIR-IRIS", "results": result["data"]}
