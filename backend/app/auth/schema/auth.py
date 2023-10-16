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
