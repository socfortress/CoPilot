from typing import Dict

# import requests
from dfir_iris_client.case import Case

# from dfir_iris_client.helper.utils import assert_api_resp
# from dfir_iris_client.helper.utils import get_data_from_resp
# from dfir_iris_client.session import ClientSession
from loguru import logger

from app.services.DFIR_IRIS.universal import UniversalService


class AssetsService:
    """
    A service class that encapsulates the logic for pulling case assets from DFIR-IRIS.
    """

    def __init__(self):
        self.universal_service = UniversalService("DFIR-IRIS")
        session_result = self.universal_service.create_session()

        if not session_result["success"]:
            logger.error(session_result["message"])
            self.iris_session = None
        else:
            self.iris_session = session_result["session"]

    def get_case_assets(self, cid: int) -> Dict[str, object]:
        """
        Gets a case's assets from DFIR-IRIS

        ARGS:
            cid: The case ID to search for

        Returns:
            dict: A dictionary containing the success status, a message and potentially the notes of a given case.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info(f"Collecting case {cid} assets from DFIR-IRIS")
        case = Case(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            case.list_assets,
            cid,
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to collect notes from DFIR-IRIS",
            }

        return result
