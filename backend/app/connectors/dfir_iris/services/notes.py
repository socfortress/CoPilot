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


def process_notes(notes: List[Dict], case_id: int) -> List[Dict]:
    processed_notes = []
    for note in notes:
        note_details = get_case_note_details(note["note_id"], case_id)
        logger.info(f"Note details: {note_details}")
        note["note_details"] = note_details.note_details
        processed_notes.append(note)
    return processed_notes


def get_case_notes(case_id: int, search_term: str) -> NotesResponse:
    client, case = initialize_client_and_case("DFIR-IRIS")
    result = fetch_and_validate_data(client, case.search_notes, search_term, case_id)
    processed_notes = process_notes(result["data"], case_id)
    return NotesResponse(success=True, message="Successfully fetched notes for case", notes=processed_notes)


def get_case_note_details(note_id: int, case_id: int) -> NoteDetailsResponse:
    client, case = initialize_client_and_case("DFIR-IRIS")
    result = fetch_and_validate_data(client, case.get_note, note_id, case_id)
    note_details = NoteDetails(**result["data"])
    return NoteDetailsResponse(success=True, message="Successfully fetched note details", note_details=note_details)


def perform_note_creation(client: Any, case: Case, note_creation_body: NoteCreationBody, case_id: int) -> Dict:
    result = fetch_and_validate_data(client, case.add_notes_group, note_creation_body.note_title, case_id)
    note_id = result["data"]["group_id"]
    custom_attributes = {}
    return fetch_and_validate_data(
        client,
        case.add_note,
        note_creation_body.note_title,
        note_creation_body.note_content,
        note_id,
        custom_attributes,
        case_id,
    )


def create_case_note(case_id: int, note_creation_body: NoteCreationBody) -> NoteCreationResponse:
    client, case = initialize_client_and_case("DFIR-IRIS")
    result = perform_note_creation(client, case, note_creation_body, case_id)
    return NoteCreationResponse(success=True, message="Successfully created note", note=result["data"])
