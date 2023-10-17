from enum import Enum
from typing import List
from typing import Optional

from fastapi import HTTPException
from fastapi import Request
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator

from app.auth.services.universal import find_user
from app.auth.utils import AuthHandler
from app.db.universal_models import LogEntry


################## ! 422 VALIDATION ERROR TYPES FOR PYDANTIC RESPONSE ! ##################
class ErrorType(str, Enum):
    PASSWORD_REGEX = "value_error.str.regex"
    EMAIL = "value_error.email"
    # Add other error types as needed


class ValidationErrorItem(BaseModel):
    field: str
    error_type: ErrorType
    message: str = None  # Initialize as None or some default

    @validator("message", pre=True, always=True)
    def set_message(cls, value, values):
        error_type = values.get("error_type")
        if error_type == ErrorType.PASSWORD_REGEX:
            return "Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character"
        else:
            return value  # if the message is already set, or you can put a generic message here


class ValidationErrorResponse(BaseModel):
    message: str
    details: List[ValidationErrorItem]


################## ! LOGGING TO `log_entry` table ! ##################
class LogEntryModel(BaseModel):
    event_type: str = Field(..., example="Info", description="Event type")
    user_id: Optional[int] = Field(None, example=1, description="User ID")
    route: str = Field(..., example="/wazuh_indexer/health", description="Route")
    method: str = Field(..., example="GET", description="Method")
    status_code: int = Field(..., example=200, description="Status code")
    message: str = Field(..., example="Route accessed", description="Message")
    additional_info: Optional[str] = Field(None, example="Additional details here", description="Additional info")


class Logger:
    def __init__(self, session, auth_handler: AuthHandler):
        self.session = session
        self.auth_handler = auth_handler

    async def get_user_id_from_request(self, request: Request):
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.replace("Bearer ", "")
            username, _ = self.auth_handler.decode_token(token)
            user = find_user(username)
            if user:
                return user.id
        return None

    def insert_log_entry(self, log_entry_model: LogEntryModel):
        log_entry = LogEntry(**log_entry_model.dict())
        self.session.add(log_entry)
        self.session.commit()

    async def log_route_access(self, user_id, request: Request, response):
        log_entry_model = LogEntryModel(
            event_type="Info",
            user_id=user_id,
            route=str(request.url),
            method=request.method,
            status_code=response.status_code,
            message="Route accessed",
        )
        self.insert_log_entry(log_entry_model)

    async def log_error(self, user_id, request: Request, exception: Exception):
        log_entry_model = LogEntryModel(
            event_type="Error",
            user_id=user_id,
            route=str(request.url),
            method=request.method,
            status_code=500,  # Internal Server Error
            message=str(exception),
        )
        self.insert_log_entry(log_entry_model)

    async def log_and_raise_http_error(self, user_id, request: Request, exception: Exception):
        await self.log_error(user_id, request, exception)
        raise HTTPException(status_code=500, detail="Internal Server Error")


################## ! ALLOWED FILES ! ##################


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {"yaml", "txt"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
