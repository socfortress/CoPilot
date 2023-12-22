from typing import List

from pydantic import BaseModel


class UserBase(BaseModel):
    id: int
    username: str


class UserBaseResponse(BaseModel):
    users: List[UserBase]
    message: str
    success: bool
