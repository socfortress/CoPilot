from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.management import DeletedIndexBody
from app.connectors.graylog.schema.management import DeletedIndexResponse
from app.connectors.graylog.schema.management import StartInputBody
from app.connectors.graylog.schema.management import StartInputResponse
from app.connectors.graylog.schema.management import StartStreamBody
from app.connectors.graylog.schema.management import StartStreamResponse
from app.connectors.graylog.schema.management import StopInputBody
from app.connectors.graylog.schema.management import StopInputResponse
from app.connectors.graylog.schema.management import StopStreamBody
from app.connectors.graylog.schema.management import StopStreamResponse
from app.connectors.graylog.services.collector import get_index_names
from app.connectors.graylog.services.collector import get_input_ids
from app.connectors.graylog.services.management import delete_index
from app.connectors.graylog.services.management import start_input
from app.connectors.graylog.services.management import start_stream
from app.connectors.graylog.services.management import stop_input
from app.connectors.graylog.services.management import stop_stream
from app.connectors.graylog.services.streams import get_stream_ids

graylog_management_router = APIRouter()


def get_managed_index_names() -> List[str]:
    return get_index_names()


def get_managed_input_ids() -> List[str]:
    return get_input_ids()


def get_managed_stream_ids() -> List[str]:
    return get_stream_ids()


def verify_index_name(deleted_index_body: DeletedIndexBody) -> DeletedIndexBody:
    # Remove any extra spaces from index_name
    deleted_index_body.index_name = deleted_index_body.index_name.strip()

    managed_index_names = get_managed_index_names()
    if deleted_index_body.index_name not in managed_index_names:
        raise HTTPException(
            status_code=400,
            detail=f"Index name '{deleted_index_body.index_name}' is not managed by Graylog or no longer exists.",
        )
    return deleted_index_body


def verify_input_id(stop_input_body: StopInputBody) -> StopInputBody:
    # Remove any extra spaces from input_id
    stop_input_body.input_id = stop_input_body.input_id.strip()

    managed_input_ids = get_managed_input_ids()
    if stop_input_body.input_id not in managed_input_ids:
        raise HTTPException(status_code=400, detail=f"Input ID '{stop_input_body.input_id}' is not managed by Graylog or no longer exists.")
    return stop_input_body


def verify_stream_id(stop_stream_body: StopStreamBody) -> StopStreamBody:
    # Remove any extra spaces from stream_id
    stop_stream_body.stream_id = stop_stream_body.stream_id.strip()

    managed_stream_ids = get_managed_stream_ids()
    if stop_stream_body.stream_id not in managed_stream_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Stream ID '{stop_stream_body.stream_id}' is not managed by Graylog or no longer exists.",
        )
    return stop_stream_body


@graylog_management_router.delete(
    "/index",
    response_model=DeletedIndexResponse,
    description="Delete index",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def delete_index_route(deleted_index_body: DeletedIndexBody = Depends(verify_index_name)) -> DeletedIndexResponse:
    logger.info(f"Deleting index {deleted_index_body.index_name}")

    return delete_index(deleted_index_body.index_name)


@graylog_management_router.post(
    "/input/stop",
    response_model=StopInputResponse,
    description="Stop input",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def stop_input_route(stop_input_body: StopInputBody = Depends(verify_input_id)) -> StopInputResponse:
    logger.info(f"Stopping input {stop_input_body.input_id}")

    return stop_input(stop_input_body.input_id)


@graylog_management_router.post(
    "/input/start",
    response_model=StartInputResponse,
    description="Start input",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def start_input_route(start_input_body: StartInputBody = Depends(verify_input_id)) -> StartInputResponse:
    logger.info(f"Starting input {start_input_body.input_id}")

    return start_input(start_input_body.input_id)


@graylog_management_router.post(
    "/stream/stop",
    response_model=StopStreamResponse,
    description="Stop stream",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def stop_stream_route(stop_stream_body: StopStreamBody = Depends(verify_stream_id)) -> StopStreamResponse:
    logger.info(f"Stopping stream {stop_stream_body.stream_id}")

    return stop_stream(stop_stream_body.stream_id)


@graylog_management_router.post(
    "/stream/start",
    response_model=StartStreamResponse,
    description="Start stream",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def start_stream_route(start_stream_body: StartStreamBody = Depends(verify_stream_id)) -> StartStreamResponse:
    logger.info(f"Starting stream {start_stream_body.stream_id}")

    return start_stream(start_stream_body.stream_id)
