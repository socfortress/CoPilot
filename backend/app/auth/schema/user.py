from pydantic import BaseModel
from typing import List

class UserBase(BaseModel):
    id: int
    username: str

class UserBaseResponse(BaseModel):
    users : List[UserBase]
    message: str
    success: bool
