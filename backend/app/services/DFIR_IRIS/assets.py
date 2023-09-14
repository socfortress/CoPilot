from typing import Dict

# import requests
from dfir_iris_client.case import Case

# from dfir_iris_client.helper.utils import assert_api_resp
# from dfir_iris_client.helper.utils import get_data_from_resp
# from dfir_iris_client.session import ClientSession
from loguru import logger

from app.services.dfir_iris.universal import UniversalService


class AssetsService:
    """
    A service class that encapsulates the logic for pulling case assets from DFIR-IRIS. It creates a DFIR-IRIS session upon
    initialization and uses it to fetch case assets.
    """

    def __init__(self):
        """
        Initializes the AssetsService by creating a UniversalService object for "DFIR-IRIS" and establishing a session.
        If the session creation is unsuccessful, an error is logged and the iris_session attribute is set to None.
        """
        self.universal_service = UniversalService("DFIR-IRIS")
        session_result = self.universal_service.create_session()

        if not session_result["success"]:
            logger.error(session_result["message"])
            self.iris_session = None
        else:
            self.iris_session = session_result["session"]

    def get_case_assets(self, cid: int) -> Dict[str, object]:
        """
        Retrieves the assets of a specific case from DFIR-IRIS. If the iris_session attribute is None, this indicates
        that the session creation was unsuccessful, and a dictionary with "success" set to False is returned. Otherwise,
        it attempts to fetch and parse the assets data for the case specified by the `cid` parameter.

        Args:
            cid (int): The ID of the case for which to retrieve assets.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the fetched assets. The
            "success" key is a boolean indicating whether the operation was successful. The "message" key is a string
            providing details about the operation. If "success" is True, the dictionary also contains the "data" key
            with the fetched assets.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info(f"Collecting case {cid} assets from DFIR-IRIS")
        case = Case(session=self.iris_session)
        cid = int(cid)
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
