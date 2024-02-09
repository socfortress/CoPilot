from typing import List

from pydantic import BaseModel
from pydantic import EmailStr


class UserBase(BaseModel):
    id: int
    username: str
    email: EmailStr


class UserBaseResponse(BaseModel):
    users: List[UserBase]
    message: str
    success: bool
