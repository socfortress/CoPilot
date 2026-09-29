from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel


class UserBase(BaseModel):
    id: int
    username: str
    # A plain string, not EmailStr: this is a response, and one stored address the
    # validator rejects (a reserved domain such as `.local`, common for internal
    # accounts) used to fail the whole user list. Creating a user still goes
    # through UserInput, which validates the address.
    email: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    last_login_at: Optional[datetime] = None


class UserBaseResponse(BaseModel):
    users: List[UserBase]
    message: str
    success: bool


class UserDetailResponse(BaseModel):
    success: bool
    message: str
    user: UserBase
