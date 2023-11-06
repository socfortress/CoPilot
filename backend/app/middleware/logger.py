from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.auth.utils import AuthHandler
from app.db.db_session import engine
from app.utils import Logger

EXCLUDED_PATHS = ["/auth/token", "/auth/register"]
INTERNAL_SERVER_ERROR = 500


async def process_request(request: Request, call_next, session, logger_instance):
    response = await call_next(request)
    user_id = await logger_instance.get_user_id_from_request(request)
    return response, user_id


def is_excluded_path(path: str) -> bool:
    return path in EXCLUDED_PATHS


async def handle_exception(e, user_id, request, logger_instance):
    user_id = await logger_instance.get_user_id_from_request(request) if user_id is None else user_id
    await logger_instance.log_error(user_id, request, e)
    status_code = e.status_code if isinstance(e, HTTPException) else INTERNAL_SERVER_ERROR
    return JSONResponse(status_code=status_code, content={"message": str(e), "success": False})


async def log_requests(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    with Session(engine) as session:
        logger_instance = Logger(session, AuthHandler())
        user_id = None

        try:
            if not is_excluded_path(request.url.path):
                response, user_id = await process_request(request, call_next, session, logger_instance)
            else:
                response = await call_next(request)
        except Exception as e:
            return await handle_exception(e, user_id, request, logger_instance)

        await logger_instance.log_route_access(user_id, request, response)

    return response if response else await call_next(request)
