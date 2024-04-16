from typing import Any
from typing import Dict
from typing import List

from dfir_iris_client.case import Case
from loguru import logger

from app.connectors.dfir_iris.schema.notes import NoteCreationBody
from app.connectors.dfir_iris.schema.notes import NoteCreationResponse
from app.connectors.dfir_iris.schema.notes import NoteDetails
from app.connectors.dfir_iris.schema.notes import NoteDetailsResponse
from app.connectors.dfir_iris.schema.notes import NotesResponse
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_case


async def process_directories(directories: List[Dict], case_id: int) -> List[Dict]:
    """
    Process a list of notes for a given case.

    Args:
        notes (List[Dict]): The list of notes to be processed.
        case_id (int): The ID of the case.

    Returns:
        List[Dict]: The processed list of notes.
    """
    processed_notes = []
    for directory in directories:
        for note in directory["notes"]:
            logger.info(f"Note: {note}")
            note_details = await get_case_note_details(note["id"], case_id)
            logger.info(f"Note details: {note_details}")
            note["note_details"] = note_details.note_details
            processed_notes.append(note)
    return processed_notes


async def get_case_notes(case_id: int, search_term: str) -> NotesResponse:
    """
    Retrieves case notes based on the provided case ID and search term.

    Args:
        case_id (int): The ID of the case.
        search_term (str): The search term to filter the notes.

    Returns:
        NotesResponse: An object containing the success status, message, and retrieved notes.
    """
    client, case = await initialize_client_and_case("DFIR-IRIS")
    result = await fetch_and_validate_data(
        client,
        case.list_notes_directories,
        case_id,
    )
    logger.info(f"Result: {result}")
    processed_notes = await process_directories(result["data"], case_id)
    return NotesResponse(
        success=True,
        message="Successfully fetched notes for case",
        notes=processed_notes,
    )


async def get_case_note_details(directory_id: int, case_id: int) -> NoteDetailsResponse:
    """
    Retrieves the details of a specific case note.

    Args:
        note_id (int): The ID of the note.
        case_id (int): The ID of the case.

    Returns:
        NoteDetailsResponse: The response containing the note details.

    Raises:
        SomeException: If there is an error retrieving the note details.
    """
    client, case = await initialize_client_and_case("DFIR-IRIS")
    result = await fetch_and_validate_data(client, case.get_note, directory_id, case_id)
    logger.info(f"Result: {result}")
    note_details = NoteDetails(**result["data"])
    return NoteDetailsResponse(
        success=True,
        message="Successfully fetched note details",
        note_details=note_details,
    )


async def perform_note_creation(
    client: Any,
    case: Case,
    note_creation_body: NoteCreationBody,
    case_id: int,
) -> Dict:
    """
    Performs the creation of a note in a case.

    Args:
        client (Any): The client object used for making API requests.
        case (Case): The case object representing the case where the note will be created.
        note_creation_body (NoteCreationBody): The body containing the details of the note to be created.
        case_id (int): The ID of the case where the note will be created.

    Returns:
        Dict: The response data containing the created note information.
    """
    result = await fetch_and_validate_data(
        client,
        case.add_notes_directory,
        "CoPilot",
        None,
        case_id,
    )
    logger.info(f"Result: {result}")
    note_id = result["data"]["id"]
    custom_attributes = {}
    return await fetch_and_validate_data(
        client,
        case.add_note,
        note_creation_body.note_title,
        note_creation_body.note_content,
        note_id,
        custom_attributes,
        case_id,
    )


async def create_case_note(
    case_id: int,
    note_creation_body: NoteCreationBody,
) -> NoteCreationResponse:
    """
    Creates a note for a specific case.

    Args:
        case_id (int): The ID of the case.
        note_creation_body (NoteCreationBody): The body of the note creation request.

    Returns:
        NoteCreationResponse: The response containing the success status, message, and created note.
    """
    client, case = await initialize_client_and_case("DFIR-IRIS")
    result = await perform_note_creation(client, case, note_creation_body, case_id)
    return NoteCreationResponse(
        success=True,
        message="Successfully created note",
        note=result["data"],
    )
