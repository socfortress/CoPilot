from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import EmailStr


class UserBase(BaseModel):
    id: int
    username: str
    email: EmailStr
    role_id: Optional[int] = None
    role_name: Optional[str] = None


class UserBaseResponse(BaseModel):
    users: List[UserBase]
    message: str
    success: bool
