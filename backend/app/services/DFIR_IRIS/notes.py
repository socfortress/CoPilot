from typing import Dict

from dfir_iris_client.case import Case
from loguru import logger

from app.services.dfir_iris.universal import UniversalService


class NotesService:
    """
    A service class that encapsulates the logic for pulling and managing case notes from DFIR-IRIS. This class handles
    fetching and creating case notes. It creates a DFIR-IRIS session upon initialization and uses it to interact with
    the DFIR-IRIS case notes.
    """

    def __init__(self):
        """
        Initializes the NotesService by creating a UniversalService object for "DFIR-IRIS" and establishing a session.
        If the session creation is unsuccessful, an error is logged and the iris_session attribute is set to None.
        """
        self.universal_service = UniversalService("DFIR-IRIS")
        session_result = self.universal_service.create_session()

        if not session_result["success"]:
            logger.error(session_result["message"])
            self.iris_session = None
        else:
            self.iris_session = session_result["session"]

    def get_case_notes(self, search_term: str, cid: int) -> Dict[str, object]:
        """
        Retrieves the notes of a specific case from DFIR-IRIS. If the iris_session attribute is None, this indicates
        that the session creation was unsuccessful, and a dictionary with "success" set to False is returned. Otherwise,
        it attempts to fetch and parse the notes data for the case specified by the `cid` parameter.

        Args:
            search_term (str): The search term to use when fetching case notes.
            cid (int): The ID of the case for which to retrieve notes.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the fetched notes. The
            "success" key is a boolean indicating whether the operation was successful. The "message" key is a string
            providing details about the operation. If "success" is True, the dictionary also contains the "data" key
            with the fetched notes.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info(f"Collecting case {cid} from DFIR-IRIS")
        case = Case(session=self.iris_session)
        cid = int(cid)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            case.search_notes,
            search_term,
            cid,
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to collect notes from DFIR-IRIS",
            }

        # Loop through the notes and get the details
        for note in result["data"]:
            note_details = self._get_case_note_details(note["note_id"], cid)
            if not note_details["success"]:
                return {
                    "success": False,
                    "message": "Failed to collect notes from DFIR-IRIS",
                }
            note["note_details"] = note_details["notes"]

        return result

    def _get_case_note_details(self, note_id: int, cid: int) -> Dict[str, object]:
        """
        Retrieves the details of a specific note of a specific case from DFIR-IRIS. If the iris_session attribute is None,
        this indicates that the session creation was unsuccessful, and a dictionary with "success" set to False is
        returned. Otherwise, it attempts to fetch and parse the note data for the note specified by the `note_id`
        parameter and the case specified by the `cid` parameter.

        Args:
            note_id (int): The ID of the note for which to retrieve details.
            cid (int): The ID of the case for which to retrieve the note details.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the fetched note details. The
            "success" key is a boolean indicating whether the operation was successful. The "message" key is a string
            providing details about the operation. If "success" is True, the dictionary also contains the "notes" key
            with the fetched note details.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info(f"Collecting case {cid} from DFIR-IRIS")
        case = Case(session=self.iris_session)
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            case.get_note,
            note_id,
            cid,
        )

        if not result["success"]:
            return {
                "success": False,
                "message": "Failed to collect notes from DFIR-IRIS",
            }

        return {
            "success": True,
            "message": "Successfully collected notes from DFIR-IRIS",
            "notes": result["data"],
        }

    def create_case_note(
        self,
        cid: int,
        note_title: str,
        note_content: str,
    ) -> Dict[str, object]:
        """
        Creates a note for a specific case in DFIR-IRIS. If the iris_session attribute is None, this indicates that
        the session creation was unsuccessful, and a dictionary with "success" set to False is returned. Otherwise,
        it attempts to create a note with the specified `note_title` and `note_content` for the case specified by the
        `cid` parameter.

        Args:
            cid (int): The ID of the case for which to create a note.
            note_title (str): The title of the note to create.
            note_content (str): The content of the note to create.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially the created note. The
            "success" key is a boolean indicating whether the operation was successful. The "message" key is a string
            providing details about the operation. If "success" is True, the dictionary also contains the "notes" key
            with the created note.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info(f"Creating case {cid} note in DFIR-IRIS")
        case = Case(session=self.iris_session)
        cid = int(cid)
        # Creating Group for New Note
        note_group = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            case.add_notes_group,
            note_title,
            cid,
        )

        if not note_group["success"]:
            return {"success": False, "message": "Failed to create note in DFIR-IRIS"}
        note_group_id = note_group["data"]["group_id"]
        custom_attributes = {}
        result = self.universal_service.fetch_and_parse_data(
            self.iris_session,
            case.add_note,
            note_title,
            note_content,
            note_group_id,
            custom_attributes,
            cid,
        )

        if not result["success"]:
            return {"success": False, "message": "Failed to create note in DFIR-IRIS"}

        return {
            "success": True,
            "message": "Successfully created note in DFIR-IRIS",
            "notes": result["data"],
        }
