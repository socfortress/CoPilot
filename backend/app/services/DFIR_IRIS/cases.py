from datetime import datetime
from typing import Dict

from dfir_iris_client.case import Case
from loguru import logger

from app.services.dfir_iris.universal import UniversalService


class CasesService:
    """
    A service class that encapsulates the logic for pulling cases from DFIR-IRIS.
    """

    def __init__(self):
        self.universal_service = UniversalService("DFIR-IRIS")
        session_result = self.universal_service.create_session()

        if not session_result["success"]:
            logger.error(session_result["message"])
            self.iris_session = None
        else:
            self.iris_session = session_result["session"]

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
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            case.list_cases,
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to collect cases from DFIR-IRIS",
            }

        return {
            "success": True,
            "message": "Successfully collected cases from DFIR-IRIS",
            "cases": result["data"],
        }

    def calculate_kpis(self, cases):
        """
        Calculate KPIs for a list of cases and return only those that have breached.

        Args:
            cases (List[Dict]): The list of cases to calculate KPIs for.

        Returns:
            Dict: A dictionary containing the success status, a message, and the cases that have breached KPIs.
        """
        try:
            cases_breached = [case for case in cases if self._is_kpi_breached(case)]
            return {"success": True, "message": "Successfully calculated KPIs.", "cases_breached": cases_breached}
        except Exception as e:
            return {"success": False, "message": f"Failed to calculate KPIs: {e}"}

    def _is_kpi_breached(self, case):
        """
        Check if a case's KPI is breached. A case is breached if it is older than 24 hours and still open.

        Args:
            case (Dict): The case to check.

        Returns:
            bool: True if the KPI is breached, False otherwise.
        """
        # Check if the `case_close_date` is empty and `case_open_date` is not
        if case["case_close_date"] == "" and case["case_open_date"] != "":
            # Get the current date
            current_date = datetime.now()
            # Get the case open date
            case_open_date = datetime.strptime(case["case_open_date"], "%m/%d/%Y")
            # Calculate the difference between the current date and the case open date
            difference = current_date - case_open_date
            # Convert the difference to days
            difference = difference.days
            # Check if the difference is greater than 1 day
            if difference > 1:
                # Set the KPI to True
                case["kpi_breached"] = True
                return True
        return False

    def get_case(self, case_id: int) -> bool:
        """
        Gets a case from DFIR-IRIS and returns all the details

        Returns:
            dict: A dictionary containing the success status, a message and potentially the case.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info(f"Collecting case {case_id} from DFIR-IRIS")
        case = Case(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            case.get_case,
            case_id,
        )

        if not result["success"]:
            return {
                "success": False,
                "message": f"Failed to collect case {case_id} from DFIR-IRIS",
            }

        return {
            "success": True,
            "message": f"Successfully collected case {case_id} from DFIR-IRIS",
            "case": result["data"],
        }

    def check_case_id(self, case_id: int) -> bool:
        """
        Checks if a case exists in DFIR-IRIS

        Returns:
            dict: A dictionary containing the success status, a message and potentially the case.
        """
        return self.get_case(case_id)
