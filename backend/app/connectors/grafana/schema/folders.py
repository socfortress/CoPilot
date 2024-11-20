from pydantic import BaseModel
from typing import List

class Folder(BaseModel):
    id: int
    uid: str
    title: str

class FoldersResponse(BaseModel):
    folders: List[Folder]
