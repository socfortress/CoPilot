from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class Directory(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    case_id: int


class ModificationHistory(BaseModel):
    user: str
    user_id: int
    action: str


class NoteDetails(BaseModel):
    directory: Directory
    note_id: int
    note_uuid: str
    note_title: str
    note_content: str
    note_user: int
    note_creationdate: str
    note_lastupdate: str
    note_case_id: int
    custom_attributes: Optional[Dict]
    directory_id: int
    modification_history: Dict[str, ModificationHistory]
    comments: List[str]


class NoteDetailsResponse(BaseModel):
    note_details: NoteDetails
    message: str
    success: bool


class NoteItem(BaseModel):
    note_details: NoteDetails


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
