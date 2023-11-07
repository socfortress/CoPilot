from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.dfir_iris.schema.notes import NoteCreationBody
from app.connectors.dfir_iris.schema.notes import NoteCreationResponse
from app.connectors.dfir_iris.schema.notes import NotesResponse
from app.connectors.dfir_iris.services.notes import create_case_note
from app.connectors.dfir_iris.services.notes import get_case_notes
from app.connectors.dfir_iris.utils.universal import check_case_exists


async def verify_case_exists(case_id: int) -> int:
    if not await check_case_exists(case_id):
        raise HTTPException(status_code=400, detail=f"Case {case_id} does not exist.")
    return case_id


dfir_iris_notes_router = APIRouter()


@dfir_iris_notes_router.get(
    "/{case_id}",
    response_model=NotesResponse,
    description="Get all notes for a case",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_case_notes_route(case_id: int = Depends(verify_case_exists), search_term: Optional[str] = "%") -> NotesResponse:
    logger.info(f"Fetching notes for case {case_id}")
    return await get_case_notes(case_id, search_term)


@dfir_iris_notes_router.post(
    "/{case_id}",
    response_model=NoteCreationResponse,
    description="Create a note for a case",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_case_note_route(case_id: int, note_creation_body: NoteCreationBody) -> NoteCreationResponse:
    verify_case_exists(case_id)
    logger.info(f"Creating a note for case {case_id}")
    return await create_case_note(case_id, note_creation_body)
