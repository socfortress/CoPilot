from pydantic import BaseModel
from typing import List


class DeletedIndexBody(BaseModel):
    index_name: str


class DeletedIndexResponse(BaseModel):
    success: bool
    message: str


class StopInputBody(BaseModel):
    input_id: str


class StopInputResponse(BaseModel):
    success: bool
    message: str


class StartInputBody(BaseModel):
    input_id: str


class StartInputResponse(BaseModel):
    success: bool
    message: str


class StopStreamBody(BaseModel):
    stream_id: str


class StopStreamResponse(BaseModel):
    success: bool
    message: str


class StartStreamBody(BaseModel):
    stream_id: str


class StartStreamResponse(BaseModel):
    success: bool
    message: str


class UrlWhitelistEntry(BaseModel):
    id: str
    type: str
    title: str
    value: str

class UrlWhitelistEntries(BaseModel):
    entries: List[UrlWhitelistEntry]
    disabled: bool

class UrlWhitelistEntryResponse(BaseModel):
    success: bool
    message: str
    url_whitelist_entries: UrlWhitelistEntries
