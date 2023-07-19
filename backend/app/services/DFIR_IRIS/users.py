from typing import Dict

from dfir_iris_client.alert import Alert

# import requests
from dfir_iris_client.users import User

# from dfir_iris_client.helper.utils import assert_api_resp
# from dfir_iris_client.helper.utils import get_data_from_resp
# from dfir_iris_client.session import ClientSession
from loguru import logger

from app.services.DFIR_IRIS.universal import UniversalService


class IRISUsersService:
    """
    A service class that encapsulates the logic for pulling and managing users from DFIR-IRIS. This class handles
    fetching and creating users. It creates a DFIR-IRIS session upon initialization and uses it to interact with
    the DFIR-IRIS users.
    """

    def __init__(self):
        """
        Initializes the IRISUsersService by creating a UniversalService object for "DFIR-IRIS" and establishing a session.
        If the session creation is unsuccessful, an error is logged and the iris_session attribute is set to None.
        """
        self.universal_service = UniversalService("DFIR-IRIS")
        session_result = self.universal_service.create_session()

        if not session_result["success"]:
            logger.error(session_result["message"])
            self.iris_session = None
        else:
            self.iris_session = session_result["session"]

    def list_users(self) -> Dict[str, object]:
        """
        Retrieves the list of users from DFIR-IRIS. If the iris_session attribute is None, this indicates
        that the session creation was unsuccessful, and a dictionary with "success" set to False is returned. Otherwise,
        it attempts to fetch and parse the user data.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the fetched users. The
            "success" key is a boolean indicating whether the operation was successful. The "message" key is a string
            providing details about the operation. If "success" is True, the dictionary also contains the "data" key
            with the fetched users.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info("Collecting users from DFIR-IRIS")
        user = User(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            user.list_users,
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to collect users from DFIR-IRIS",
            }

        return {
            "success": True,
            "message": "Successfully collected users from DFIR-IRIS",
            "users": result["data"],
        }

    def assign_user_alert(self, alert_id: str, alert_owner_id: int) -> Dict[str, object]:
        """
        Assigns a user to an alert in DFIR-IRIS. If the iris_session attribute is None, this indicates
        that the session creation was unsuccessful, and a dictionary with "success" set to False is returned. Otherwise,
        it attempts to assign a user to an alert.

        Args:
            alert_id (str): The ID of the alert to assign a user to.
            alert_owner_id (int): The ID of the user to assign to the alert.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the assigned user. The
            "success" key is a boolean indicating whether the operation was successful. The "message" key is a string
            providing details about the operation. If "success" is True, the dictionary also contains the "data" key
            with the assigned user.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info(f"Assigning user with user id {alert_owner_id} to alert {alert_id} in DFIR-IRIS")
        alert = Alert(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            alert.update_alert,
            alert_id,
            {"alert_owner_id": alert_owner_id},
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to assign user to alert in DFIR-IRIS",
            }

        return {
            "success": True,
            "message": "Successfully assigned user to alert in DFIR-IRIS",
            "user": result["data"],
        }
