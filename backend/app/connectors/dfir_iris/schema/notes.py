from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class CustomAttributes(BaseModel):
    # Define additional fields if custom_attributes contains specific keys
    pass


class NoteDetails(BaseModel):
    custom_attributes: CustomAttributes
    group_id: int
    group_title: str
    group_uuid: str
    note_content: str
    note_creationdate: str
    note_id: int
    note_lastupdate: str
    note_title: str
    note_uuid: str


class NoteDetailsResponse(BaseModel):
    note_details: NoteDetails
    message: str
    success: bool


class NoteItem(BaseModel):
    note_details: NoteDetails
    note_id: int
    note_title: str


class NotesResponse(BaseModel):
    notes: List[NoteItem]
    message: str
    success: bool


class NotesQueryParams(BaseModel):
    case_id: int
    search_term: Optional[str] = Field(
        "%",
        description="Search term to filter notes by. Defaults to wildcard search (%).",
    )


class NoteCreationBody(BaseModel):
    note_title: str = Field(..., description="Title of the note to be created.")
    note_content: str = Field(..., description="Content of the note to be created.")


class NoteAttributes(BaseModel):
    custom_attributes: Dict[str, str] = Field(...)
    note_content: str = Field(...)
    note_creationdate: str = Field(...)
    note_id: int = Field(...)
    note_lastupdate: str = Field(...)
    note_title: str = Field(...)
    note_uuid: str = Field(...)


class NoteCreationResponse(BaseModel):
    message: str = Field(...)
    note: NoteAttributes = Field(...)
    success: bool = Field(...)
