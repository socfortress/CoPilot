from typing import List

from pydantic import BaseModel


class Folder(BaseModel):
    id: int
    uid: str
    title: str


class FoldersResponse(BaseModel):
    folders: List[Folder]
