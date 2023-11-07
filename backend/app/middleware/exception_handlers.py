# from fastapi import HTTPException
# from fastapi import Request
# from fastapi.exceptions import RequestValidationError
# from fastapi.responses import JSONResponse
# from sqlmodel import Session

# from app.auth.utils import AuthHandler
# from app.db.db_session import engine
# from app.utils import ErrorType
# from app.utils import Logger
# from app.utils import ValidationErrorItem
# from app.utils import ValidationErrorResponse


# # Utility function to get user_id from request
# async def get_user_id_from_request(request: Request, session, logger_instance):
#     return await logger_instance.get_user_id_from_request(request)


# async def custom_http_exception_handler(request: Request, exc: HTTPException):
#     with Session(engine) as session:
#         logger_instance = Logger(session, AuthHandler())
#         user_id = await get_user_id_from_request(request, session, logger_instance)
#         await logger_instance.log_error(user_id, request, exc.detail)

#     return JSONResponse(
#         status_code=exc.status_code,
#         content={
#             "success": False,
#             "message": exc.detail,
#         },
#     )


# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     errors = exc.errors()
#     details = []

#     for error in errors:
#         field = error["loc"][-1]
#         error_type = ErrorType(error["type"])
#         details.append(ValidationErrorItem(field=field, error_type=error_type))

#     main_message = details[0].message if details else "Validation Error"

#     with Session(engine) as session:
#         logger_instance = Logger(session, AuthHandler())
#         user_id = await get_user_id_from_request(request, session, logger_instance)
#         await logger_instance.log_error(user_id, request, main_message)

#     return JSONResponse(
#         status_code=422,
#         content=ValidationErrorResponse(message=main_message, details=details).dict(),
#     )

# ! With Async
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
    return await logger_instance.get_user_id_from_request(request)


async def custom_http_exception_handler(request: Request, exc: HTTPException):
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


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    details = []

    for error in errors:
        field = error["loc"][-1]
        error_type = ErrorType(error["type"])
        details.append(ValidationErrorItem(field=field, error_type=error_type))

    main_message = details[0].message if details else "Validation Error"

    async with AsyncSession(async_engine) as session:  # Use AsyncSession
        logger_instance = Logger(session, AuthHandler())
        user_id = await get_user_id_from_request(request, logger_instance)
        await logger_instance.log_error(user_id, request, main_message)
        await session.commit()  # Make sure to commit the session

    return JSONResponse(
        status_code=422,
        content=ValidationErrorResponse(message=main_message, details=details).dict(),
    )
