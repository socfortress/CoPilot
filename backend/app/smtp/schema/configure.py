from pydantic import BaseModel


class SMTPResponse(BaseModel):
    message: str
    success: bool
