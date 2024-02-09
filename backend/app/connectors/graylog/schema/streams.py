from typing import List
from typing import Optional

from pydantic import BaseModel


class Rule(BaseModel):
    description: Optional[str]
    field: str
    id: str
    inverted: bool
    stream_id: str
    type: int
    value: str


class Stream(BaseModel):
    content_pack: Optional[str]
    created_at: str
    creator_user_id: str
    description: str
    disabled: bool
    id: str
    index_set_id: str
    is_default: bool
    is_editable: bool
    matching_type: str
    outputs: list
    remove_matches_from_default_stream: bool
    rules: List[Rule]
    title: str


class GraylogStreamsResponse(BaseModel):
    message: str
    streams: List[Stream]
    total: int
    success: bool
