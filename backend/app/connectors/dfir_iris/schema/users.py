from typing import List

from pydantic import BaseModel


class User(BaseModel):
    user_active: bool
    user_id: int
    user_login: str
    user_name: str
    user_uuid: str


class UsersResponse(BaseModel):
    message: str
    success: bool
    users: List[User]


class UserAddedToCustomerResponse(BaseModel):
    success: bool
    message: str


class UserRemovedFromCustomerResponse(BaseModel):
    success: bool
    message: str
