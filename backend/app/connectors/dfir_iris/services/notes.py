from datetime import datetime
from typing import List, Dict, Any, Callable, Tuple
from fastapi import HTTPException
from loguru import logger
from dfir_iris_client.case import Case
from app.connectors.dfir_iris.schema.cases import CaseModel, CaseResponse, CaseOlderThanBody, CasesBreachedResponse, SingleCaseBody, SingleCaseResponse
from app.connectors.dfir_iris.schema.notes import NotesResponse, NotesQueryParams, NoteDetails, NoteDetailsResponse, NoteCreationBody, NoteCreationResponse
from app.connectors.dfir_iris.utils.universal import create_dfir_iris_client, fetch_and_parse_data, initialize_client_and_case, fetch_and_validate_data, handle_error


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
    return fetch_and_validate_data(client, case.add_note, note_creation_body.note_title, note_creation_body.note_content, note_id, custom_attributes, case_id)

def create_case_note(case_id: int, note_creation_body: NoteCreationBody) -> NoteCreationResponse:
    client, case = initialize_client_and_case("DFIR-IRIS")
    result = perform_note_creation(client, case, note_creation_body, case_id)
    return NoteCreationResponse(success=True, message="Successfully created note", note=result["data"])
