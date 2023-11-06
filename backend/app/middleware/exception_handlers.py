from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlmodel import Session

from app.db.db_session import engine
from app.auth.utils import AuthHandler
from app.utils import Logger, ErrorType, ValidationErrorItem, ValidationErrorResponse

# Utility function to get user_id from request
async def get_user_id_from_request(request: Request, session, logger_instance):
    return await logger_instance.get_user_id_from_request(request)

async def custom_http_exception_handler(request: Request, exc: HTTPException):
    with Session(engine) as session:
        logger_instance = Logger(session, AuthHandler())
        user_id = await get_user_id_from_request(request, session, logger_instance)
        await logger_instance.log_error(user_id, request, exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
        },
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    details = []

    for error in errors:
        field = error["loc"][-1]
        error_type = ErrorType(error["type"])
        details.append(ValidationErrorItem(field=field, error_type=error_type))

    main_message = details[0].message if details else "Validation Error"

    with Session(engine) as session:
        logger_instance = Logger(session, AuthHandler())
        user_id = await get_user_id_from_request(request, session, logger_instance)
        await logger_instance.log_error(user_id, request, main_message)

    return JSONResponse(
        status_code=422,
        content=ValidationErrorResponse(message=main_message, details=details).dict(),
    )
