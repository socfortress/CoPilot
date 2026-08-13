from typing import Optional

from fastapi import HTTPException
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import async_engine  # Make sure to import the async engine
from app.utils import ErrorType
from app.utils import Logger
from app.utils import ValidationErrorItem
from app.utils import ValidationErrorResponse


# Utility function to get user_id from request
async def get_user_id_from_request(request: Request, logger_instance):
    """
    Retrieves the user ID from the given request using the provided logger instance.

    Args:
        request (Request): The request object.
        logger_instance: The logger instance used to retrieve the user ID.

    Returns:
        The user ID extracted from the request.
    """
    return await logger_instance.get_user_id_from_request(request)


async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom exception handler for handling HTTP exceptions.

    Args:
        request (Request): The incoming request object.
        exc (HTTPException): The raised HTTP exception.

    Returns:
        JSONResponse: The JSON response containing the error details.
    """
    async with AsyncSession(async_engine) as session:  # Use AsyncSession
        logger_instance = Logger(session, AuthHandler())
        user_id = await get_user_id_from_request(request, logger_instance)
        await logger_instance.log_error(user_id, request, exc.detail)
        await session.commit()  # Make sure to commit the session

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
        },
    )


# FastAPI prefixes every `loc` with where the value came from; that is plumbing
# detail, not something to show an analyst.
_REQUEST_LOCATIONS = ("body", "query", "path", "header", "cookie")
# Pydantic 2 prefixes messages raised by custom validators with this.
_PYDANTIC_VALUE_ERROR_PREFIX = "Value error, "


def _describe(error: dict, loc: tuple) -> Optional[str]:
    """Render one Pydantic error as `field.path: reason`, or None if it says nothing."""
    raw_message = str(error.get("msg") or "").strip()
    if not raw_message:
        return None
    raw_message = raw_message.removeprefix(_PYDANTIC_VALUE_ERROR_PREFIX)

    parts = loc[1:] if loc and loc[0] in _REQUEST_LOCATIONS else loc
    path = ".".join(str(part) for part in parts)
    return f"{path}: {raw_message}" if path else raw_message


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles validation exceptions and logs the error.

    Args:
        request (Request): The incoming request.
        exc (RequestValidationError): The validation exception.

    Returns:
        JSONResponse: The JSON response with the validation error details.
    """
    errors = exc.errors()
    details = []

    for error in errors:
        loc = error.get("loc") or ()
        # `loc` entries are ints for list indices; ValidationErrorItem.field is a
        # str and Pydantic 2 will not coerce, so stringify before handing it over.
        field = str(loc[-1]) if loc else "body"
        try:
            error_type = ErrorType(error["type"])
        except ValueError:
            # Pydantic 2 emits codes the v1-era ErrorType enum doesn't list
            # (string_too_long, string_pattern_mismatch, etc.) — fall back to
            # GENERAL so unknown codes still produce a 422 with a sensible
            # message instead of crashing the handler.
            error_type = ErrorType.GENERAL

        # GENERAL is the "we have no specific wording" bucket, and its canned text
        # is "Invalid value." — naming neither the field nor the reason. That
        # opacity is what made #960 unreadable from the UI, so whenever we land on
        # GENERAL (unmapped code, or a custom validator's `value_error`) carry
        # Pydantic's own message through instead. Every other code keeps its
        # friendlier hand-written wording.
        message = _describe(error, loc) if error_type is ErrorType.GENERAL else None
        details.append(ValidationErrorItem(field=field, error_type=error_type, message=message))

    main_message = details[0].message if details else "Validation Error"

    async with AsyncSession(async_engine) as session:  # Use AsyncSession
        logger_instance = Logger(session, AuthHandler())
        user_id = await get_user_id_from_request(request, logger_instance)
        await logger_instance.log_error(user_id, request, main_message)
        await session.commit()  # Make sure to commit the session

    return JSONResponse(
        status_code=422,
        content=ValidationErrorResponse(message=main_message, details=details).model_dump(),
    )


async def value_error_handler(request: Request, exc: ValueError):
    """
    Handles the ValueError exception and logs the error message.

    Args:
        request (Request): The incoming request object.
        exc (ValueError): The ValueError exception object.

    Returns:
        JSONResponse: The response containing the error message.
    """
    error_message = str(exc)

    async with AsyncSession(async_engine) as session:
        logger_instance = Logger(session, AuthHandler())
        user_id = await get_user_id_from_request(request, logger_instance)
        await logger_instance.log_error(user_id, request, error_message)
        await session.commit()

    return JSONResponse(
        status_code=400,  # Bad Request
        content={
            "success": False,
            "message": error_message,
        },
    )
