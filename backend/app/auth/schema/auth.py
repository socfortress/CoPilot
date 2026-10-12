from typing import List
from typing import Optional

from pydantic import BaseModel


class UserResponse(BaseModel):
    message: str
    success: bool


class UserLoginResponse(BaseModel):
    token: str
    message: str
    success: bool


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UpdateUserRoleRequest(BaseModel):
    role_name: str
    # Replaces the user's customers in the same change. Required when the user becomes an
    # analyst or responder and has none yet (#1219); ignored for other roles' rules.
    customer_codes: Optional[List[str]] = None
