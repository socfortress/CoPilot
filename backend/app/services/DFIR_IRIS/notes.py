from typing import Dict

import requests
from dfir_iris_client.case import Case
from dfir_iris_client.helper.utils import assert_api_resp
from dfir_iris_client.helper.utils import get_data_from_resp
from dfir_iris_client.session import ClientSession
from loguru import logger

from app.services.DFIR_IRIS.universal import UniversalService


class NotesService:
    """
    A service class that encapsulates the logic for pulling case notes from DFIR-IRIS.
    """

    def __init__(self):
        self.universal_service = UniversalService("DFIR-IRIS")
        session_result = self.universal_service.create_session()

        if not session_result["success"]:
            logger.error(session_result["message"])
            self.iris_session = None
        else:
            self.iris_session = session_result["session"]

    def get_case_notes(self, search_term: str, cid: int) -> Dict[str, object]:
        """
        Gets a case's notes from DFIR-IRIS and return the ID and Title

        ARGS:
            cid: The case ID to search for
            search_term: The search term to use

        Returns:
            dict: A dictionary containing the success status, a message and potentially the notes of a given case.
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
        Gets a case's notes from DFIR-IRIS and returns the note details such as the content

        ARGS:
            cid: The case ID to search for
            note_id: The note ID to search for

        Returns:
            dict: A dictionary containing the success status, a message and potentially the notes of a given case.
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
        Creates a case note in DFIR-IRIS

        ARGS:
            cid: The case ID to search for
            title: The title of the note
            content: The content of the note

        Returns:
            dict: A dictionary containing the success status, a message and potentially the notes of a given case.
        """
        if self.iris_session is None:
            return {
                "success": False,
                "message": "DFIR-IRIS session was not successfully created.",
            }

        logger.info(f"Creating case {cid} note in DFIR-IRIS")
        case = Case(session=self.iris_session)
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
