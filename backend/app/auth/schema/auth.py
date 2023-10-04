from pydantic import BaseModel

class UserResponse(BaseModel):
    message: str
    success: bool

class UserLoginResponse(BaseModel):
    token: str
    message: str
    success: bool
