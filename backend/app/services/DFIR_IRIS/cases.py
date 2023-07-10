from typing import Dict
import requests
from loguru import logger
from app.services.DFIR_IRIS.universal import UniversalService
from dfir_iris_client.case import Case
from dfir_iris_client.helper.utils import assert_api_resp
from dfir_iris_client.helper.utils import get_data_from_resp
from dfir_iris_client.session import ClientSession


class CasesService:
    """
    A service class that encapsulates the logic for pulling cases from DFIR-IRIS.
    """

    def __init__(self):
        self.universal_service = UniversalService("DFIR-IRIS")
        session_result = self.universal_service.create_session()
        
        if not session_result['success']:
            logger.error(session_result['message'])
            self.iris_session = None
        else:
            self.iris_session = session_result['session']

    def list_cases(self) -> Dict[str, object]:
        """
        Lists all cases from DFIR-IRIS

        Returns:
            dict: A dictionary containing the success status, a message and potentially the cases.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info("Collecting cases from DFIR-IRIS")
        case = Case(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(self.iris_session, case.list_cases)

        if not result["success"]:
            return {"success": False, "message": "Failed to collect cases from DFIR-IRIS"}

        return {"success": True, "message": "Successfully collected cases from DFIR-IRIS", "cases": result["data"]}

    def get_case(self, case_id: int) -> bool:
        """
        Gets a case from DFIR-IRIS and returns all the details

        Returns:
            dict: A dictionary containing the success status, a message and potentially the case.
        """
        if self.iris_session is None:
            return {"success": False, "message": "DFIR-IRIS session was not successfully created."}

        logger.info(f"Collecting case {case_id} from DFIR-IRIS")
        case = Case(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(self.iris_session, case.get_case, case_id)

        if not result["success"]:
            return {"success": False, "message": f"Failed to collect case {case_id} from DFIR-IRIS"}

        return {"success": True, "message": f"Successfully collected case {case_id} from DFIR-IRIS", "case": result["data"]}

    def check_case_id(self, case_id: int) -> bool:
        """
        Checks if a case exists in DFIR-IRIS

        Returns:
            dict: A dictionary containing the success status, a message and potentially the case.
        """
        return self.get_case(case_id)





        
