from typing import Optional

from fastapi import HTTPException
from fastapi import Request
from pydantic import BaseModel
from pydantic import Field

from app.auth.services.universal import find_user
from app.auth.utils import AuthHandler
from app.db.universal_models import LogEntry


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
