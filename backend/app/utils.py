from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import requests
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Security
from fastapi.exceptions import RequestValidationError
from loguru import logger
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.services.universal import find_user
from app.auth.utils import AuthHandler
from app.connectors.utils import get_connector_info_from_db
from app.db.all_models import Connectors
from app.db.db_session import Session
from app.db.db_session import engine
from app.db.db_session import get_db_session
from app.db.db_session import get_session
from app.db.universal_models import LogEntry
from app.integrations.alert_creation_settings.models.alert_creation_settings import AlertCreationSettings


################## ! 422 VALIDATION ERROR TYPES FOR PYDANTIC VALUE ERROR RESPONSE ! ##################
class ErrorType(str, Enum):
    PASSWORD_REGEX = "value_error.str.regex"
    TIME_RANGE = "value_error.time_range"
    JSON_INVALID = "json_invalid"
    MIN_LENGTH = "value_error.any_str.min_length"
    MAX_LENGTH = "value_error.any_str.max_length"
    NOT_A_NUMBER = "value_error.number.not_a_number"
    TOO_SMALL = "value_error.number.too_small"
    TOO_LARGE = "value_error.number.too_large"
    INVALID_DATETIME = "value_error.datetime"
    INVALID_DATE = "value_error.date"
    MIN_ITEMS = "value_error.list.min_items"
    MAX_ITEMS = "value_error.list.max_items"
    UNIQUE = "value_error.list.unique"
    NONE_NOT_ALLOWED = "value_error.none.not_allowed"
    MISSING = "value_error.missing"
    GENERAL = "value_error"
    # Add other types as needed


class ValidationErrorItem(BaseModel):
    field: str
    error_type: ErrorType
    message: str = None  # Initialize as None or some default

    @validator("message", pre=True, always=True)
    def set_message(cls, value, values):
        error_type = values.get("error_type")
        logger.info(error_type)

        error_messages = {
            ErrorType.PASSWORD_REGEX: "Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character.",
            ErrorType.TIME_RANGE: "Invalid time range. Use 'h' for hours, 'd' for days, and 'w' for weeks.",
            ErrorType.JSON_INVALID: "Invalid JSON. Please check your JSON syntax and try again.",
            ErrorType.MIN_LENGTH: "Value is shorter than minimum length.",
            ErrorType.MAX_LENGTH: "Value is longer than maximum length.",
            ErrorType.NOT_A_NUMBER: "Input is not a number.",
            ErrorType.TOO_SMALL: "Value is too small.",
            ErrorType.TOO_LARGE: "Value is too large.",
            ErrorType.INVALID_DATETIME: "Invalid datetime format.",
            ErrorType.INVALID_DATE: "Invalid date format.",
            ErrorType.MIN_ITEMS: "Number of items is less than minimum.",
            ErrorType.MAX_ITEMS: "Number of items is more than maximum.",
            ErrorType.UNIQUE: "Items are not unique.",
            ErrorType.NONE_NOT_ALLOWED: "None is not an allowed value.",
            ErrorType.MISSING: "Missing data for required field.",
            ErrorType.GENERAL: "Invalid value.",
        }

        return error_messages.get(error_type, value)


class ValidationErrorResponse(BaseModel):
    message: str
    details: List[ValidationErrorItem]


################## ! LOGGING TO `log_entry` table ! ##################
########! MODELS !########
class LogEntryModel(BaseModel):
    event_type: str = Field(..., example="Info", description="Event type")
    user_id: Optional[int] = Field(None, example=1, description="User ID")
    route: str = Field(..., example="/wazuh_indexer/health", description="Route")
    method: str = Field(..., example="GET", description="Method")
    status_code: int = Field(..., example=200, description="Status code")
    message: str = Field(..., example="Route accessed", description="Message")
    additional_info: Optional[str] = Field(None, example="Additional details here", description="Additional info")


class LogRetrieveModel(LogEntryModel):
    timestamp: datetime = Field(..., example=datetime.now(), description="Timestamp")


class LogsResponse(BaseModel):
    logs: List[LogRetrieveModel]
    success: bool
    message: str


class EventType(str, Enum):
    INFO = "Info"
    ERROR = "Error"
    # Add other event types as needed


class TimeRangeModel(BaseModel):
    time_range: Union[str, int] = Field("1d", description="Time range to fetch logs for, e.g., 1, 1h, 1d, 1w")

    @validator("time_range")
    def validate_time_range(cls, value):
        try:
            if isinstance(value, int):
                if value < 1 or value > 7:
                    raise RequestValidationError(
                        [{"loc": ("time_range",), "msg": "The integer part should be between 1 and 7.", "type": "value_error.time_range"}],
                    )
                return f"{value}d"  # convert integer to day representation

            elif isinstance(value, str):
                unit = value[-1]
                int_part = int(value[:-1])

                if unit not in ["h", "d", "w"]:
                    raise RequestValidationError(
                        [
                            {
                                "loc": ("time_range",),
                                "msg": "Invalid unit. Use 'h' for hours, 'd' for days, and 'w' for weeks.",
                                "type": "value_error.time_range",
                            },
                        ],
                    )

                if int_part <= 0:
                    raise RequestValidationError(
                        [{"loc": ("time_range",), "msg": "The integer part should be greater than 0.", "type": "value_error.time_range"}],
                    )

                if unit == "w" and int_part > 1:
                    raise RequestValidationError(
                        [{"loc": ("time_range",), "msg": "The maximum allowed time range is 1 week.", "type": "value_error.time_range"}],
                    )
                return value

            else:
                raise RequestValidationError(
                    [
                        {
                            "loc": ("time_range",),
                            "msg": "Invalid type. Time range should be either an integer or a string.",
                            "type": "value_error.time_range",
                        },
                    ],
                )

        except ValueError:
            raise RequestValidationError(
                [
                    {
                        "loc": ("time_range",),
                        "msg": "Invalid format. Time range should be an integer followed by a unit (h, d, w).",
                        "type": "value_error.time_range",
                    },
                ],
            )


#########! LOGGER CLASS !#########
class Logger:
    # def __init__(self, session, auth_handler: AuthHandler):
    #     self.session = session
    #     self.auth_handler = auth_handler
    def __init__(self, session: AsyncSession, auth_handler: AuthHandler):
        self.session = session
        self.auth_handler = auth_handler

    # async def get_user_id_from_request(self, request: Request):
    #     auth_header = request.headers.get("Authorization")
    #     if auth_header:
    #         token = auth_header.replace("Bearer ", "")
    #         username, _ = self.auth_handler.decode_token(token)
    #         user = find_user(username)
    #         if user:
    #             return user.id
    #     return None
    async def get_user_id_from_request(self, request: Request):
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1]  # Better split by space and take the second part
            username, _ = self.auth_handler.decode_token(token)
            user = await find_user(username)  # Correctly using await for an async call
            if user:
                return user.id
        return None

    async def insert_log_entry(self, log_entry_model: LogEntryModel):
        log_entry = LogEntry(**log_entry_model.dict())
        self.session.add(log_entry)
        await self.session.commit()

    async def log_route_access(self, user_id, request: Request, response):
        log_entry_model = LogEntryModel(
            event_type="Info",
            user_id=user_id,
            route=str(request.url),
            method=request.method,
            status_code=response.status_code,
            message="Route accessed",
        )
        await self.insert_log_entry(log_entry_model)

    async def log_error(self, user_id, request: Request, exception: Exception, additional_info: Optional[str] = None):
        log_entry_model = LogEntryModel(
            event_type="Error",
            user_id=user_id,
            route=str(request.url),
            method=request.method,
            status_code=500,  # Internal Server Error
            message=str(exception),
            additional_info=additional_info,
        )
        await self.insert_log_entry(log_entry_model)

    async def log_and_raise_http_error(self, user_id, request: Request, exception: Exception):
        await self.log_error(user_id, request, exception)
        raise HTTPException(status_code=500, detail="Internal Server Error")

    async def fetch_all_logs(self):
        # Perform an asynchronous query to fetch all log entries
        result = await self.session.execute(select(LogEntry))
        logs = result.scalars().all()
        return logs


################## ! RETRIEVE LOGS ROUTES ! ##################
logs_router = APIRouter()


@logs_router.get(
    "",
    response_model=LogsResponse,
    description="Fetch all logs",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_logs(session: AsyncSession = Depends(get_session)) -> LogsResponse:
    """
    Fetch all logs from the database.

    This endpoint retrieves all the logs stored in the database and returns them
    along with a success status and message.

    Returns:
        LogsResponse: A Pydantic model containing a list of logs and additional metadata.

    Raises:
        HTTPException: An exception with a 404 status code is raised if no logs are found.
    """
    auth_handler_instance = AuthHandler()  # Initialize your AuthHandler
    logger_instance = Logger(session, auth_handler_instance)

    logs = await logger_instance.fetch_all_logs()  # Assuming fetch_all_logs is an async function
    if logs:
        return LogsResponse(logs=logs, success=True, message="Logs fetched successfully")
    else:
        raise HTTPException(status_code=404, detail="No logs found")


@logs_router.get(
    "/{user_id}",
    response_model=LogsResponse,
    description="Fetch logs by user ID",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_logs_by_user_id(user_id: int, session: AsyncSession = Depends(get_session)) -> LogsResponse:
    """
    Fetch all logs from the database where the user_id matches the provided user_id.

    This endpoint retrieves all the logs stored in the database where the user_id matches the provided user_id
    and returns them along with a success status and message.

    Args:
        user_id (int): The user_id to filter logs by.

    Returns:
        LogsResponse: A Pydantic model containing a list of logs and additional metadata.

    Raises:
        HTTPException: An exception with a 404 status code is raised if no logs are found.
    """
    result = await session.execute(select(LogEntry).filter(LogEntry.user_id == user_id))
    logs = result.scalars().all()

    if not logs:
        raise HTTPException(status_code=404, detail=f"No logs found for user ID: {user_id}")

    return LogsResponse(logs=logs, success=True, message="Logs fetched successfully")


@logs_router.post(
    "/timerange",
    response_model=LogsResponse,
    description="Fetch logs by time range",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_logs_by_time_range(time_range: TimeRangeModel, session: AsyncSession = Depends(get_session)) -> LogsResponse:
    """
    Fetch all logs from the database where the timestamp is within the provided time range.

    This endpoint retrieves all the logs stored in the database where the timestamp is within the provided time range
    and returns them along with a success status and message.

    Args:
        time_range (TimeRangeModel): The time range to filter logs by.

    Returns:
        LogsResponse: A Pydantic model containing a list of logs and additional metadata.

    Raises:
        HTTPException: An exception with a 404 status code is raised if no logs are found.
    """
    result = await session.execute(select(LogEntry))
    logs = result.scalars().all()

    if logs:
        logs = [log for log in logs if log.timestamp >= datetime.now() - timedelta(days=int(time_range.time_range[:-1]))]
        if logs != []:
            return LogsResponse(logs=logs, success=True, message="Logs fetched successfully")
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No logs found for time range: {time_range.time_range}".format(time_range=time_range.time_range),
            )
    else:
        raise HTTPException(status_code=404, detail="No logs found")


@logs_router.post(
    "/{event_type}",
    response_model=LogsResponse,
    description="Fetch logs by event type",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_logs_by_event_type(
    event_type: EventType,
    session: AsyncSession = Depends(get_session),
) -> LogsResponse:  # Update this line to use the new model
    """
    Fetch all logs from the database where the event_type matches the provided event_type.

    This endpoint retrieves all the logs stored in the database where the event_type matches the provided event_type
    and returns them along with a success status and message.

    Args:
        event_type (EventType): The event_type to filter logs by.

    Returns:
        LogsResponse: A Pydantic model containing a list of logs and additional metadata.

    Raises:
        HTTPException: An exception with a 404 status code is raised if no logs are found.
    """
    result = await session.execute(select(LogEntry).filter(LogEntry.event_type == event_type))
    logs = result.scalars().all()

    if not logs:
        raise HTTPException(status_code=404, detail=f"No logs found for event type: {event_type}")

    return LogsResponse(logs=logs, success=True, message="Logs fetched successfully")


@logs_router.delete(
    "",
    response_model=LogsResponse,
    description="Purge all logs",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def purge_logs(session: AsyncSession = Depends(get_session)) -> LogsResponse:  # Update this line to use the new model
    """
    Purge all logs from the database.

    This endpoint purges all the logs stored in the database and returns a success status and message.

    Returns:
        LogsResponse: A Pydantic model containing a list of logs and additional metadata.

    Raises:
        HTTPException: An exception with a 404 status code is raised if no logs are found.
    """
    result = await session.execute(select(LogEntry))
    logs = result.scalars().all()

    if logs:
        for log in logs:
            await session.delete(log)
        await session.commit()
        return LogsResponse(logs=[], success=True, message="Logs purged successfully")
    else:
        raise HTTPException(status_code=404, detail="No logs found")


@logs_router.delete(
    "/timerange",
    response_model=LogsResponse,
    description="Purge logs by time range",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def purge_logs_by_time_range(time_range: TimeRangeModel, session: AsyncSession = Depends(get_session)) -> LogsResponse:
    """
    Purge all logs from the database where the timestamp is within the provided time range.

    This endpoint purges all the logs stored in the database where the timestamp is within the provided time range
    and returns a success status and message.

    Args:
        time_range (TimeRangeModel): The time range to filter logs by.

    Returns:
        LogsResponse: A Pydantic model containing a list of logs and additional metadata.

    Raises:
        HTTPException: An exception with a 404 status code is raised if no logs are found.
    """
    result = await session.execute(select(LogEntry))
    logs = result.scalars().all()

    if logs:
        logs = [log for log in logs if log.timestamp >= datetime.now() - timedelta(days=int(time_range.time_range[:-1]))]
        if logs != []:
            for log in logs:
                await session.delete(log)
            await session.commit()
            return LogsResponse(logs=[], success=True, message="Logs purged successfully")
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No logs found for time range: {time_range.time_range}".format(time_range=time_range.time_range),
            )
    else:
        raise HTTPException(status_code=404, detail="No logs found")


################## ! ALLOWED FILES ! ##################
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {"yaml", "txt"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


################## ! DATABASE UTILS ! ##################
async def get_connector_attribute(connector_id: int, column_name: str, session: AsyncSession = Depends(get_session)) -> Optional[Any]:
    result = await session.execute(select(Connectors).filter(Connectors.id == connector_id))
    connector = result.scalars().first()

    if connector:
        return getattr(connector, column_name, None)
    return None


async def get_customer_alert_settings(customer_code: str, session: AsyncSession) -> Optional[AlertCreationSettings]:
    result = await session.execute(select(AlertCreationSettings).filter(AlertCreationSettings.customer_code == customer_code))
    settings = result.scalars().first()

    if settings:
        return settings
    return None


################## ! Wazuh Worker Provisioning App ! ##################
################## ! https://github.com/socfortress/Customer-Provisioning-Worker ! ##################
async def verify_wazuh_worker_provisioning_healtcheck(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to Wazuh Worker Provisioning service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status.
    """
    logger.info(f"Verifying the wazuh-worker provisioning connection to {attributes['connector_url']}")

    try:
        wazuh_worker_provisioning_healthcheck = requests.get(
            f"{attributes['connector_url']}/healthcheck",
            verify=False,
        )

        if wazuh_worker_provisioning_healthcheck.status_code == 200:
            return {"connectionSuccessful": True, "message": "Wazuh Worker Provisioning healthcheck successful"}
        else:
            logger.error(f"Connection to {attributes['connector_url']} failed with error: {wazuh_worker_provisioning_healthcheck.text}")

            return {"connectionSuccessful": False, "message": f"Connection to {attributes['connector_url']} failed"}
    except Exception as e:
        logger.error(f"Connection to {attributes['connector_url']} failed with error: {e}")

        return {"connectionSuccessful": False, "message": f"Connection to {attributes['connector_url']} failed with error."}


async def verify_wazuh_worker_provisioning_connection(connector_name: str) -> str:
    """
    Returns the status of the connection to Wazuh Worker Provisioning service.
    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Wazuh Worker Provisioning connector found in the database")
        return None
    return await verify_wazuh_worker_provisioning_healtcheck(attributes)
