from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from starlette.status import HTTP_401_UNAUTHORIZED

# App specific imports
from app.auth.routes.auth import auth_handler
from app.connectors.dfir_iris.schema.cases import CaseOlderThanBody
from app.connectors.dfir_iris.schema.cases import CaseResponse
from app.connectors.dfir_iris.schema.cases import CasesBreachedResponse
from app.connectors.dfir_iris.schema.cases import SingleCaseBody
from app.connectors.dfir_iris.schema.cases import SingleCaseResponse
from app.connectors.dfir_iris.schema.cases import TimeUnit
from app.connectors.dfir_iris.schema.notes import NotesQueryParams
from app.connectors.dfir_iris.schema.notes import NotesResponse
from app.connectors.dfir_iris.services.cases import get_all_cases
from app.connectors.dfir_iris.services.cases import get_cases_older_than
from app.connectors.dfir_iris.services.cases import get_single_case
from app.connectors.dfir_iris.utils.universal import check_case_exists
from app.connectors.wazuh_indexer.utils.universal import collect_indices
from app.db.db_session import session


def verify_case_exists(case_id: int) -> int:
    if not check_case_exists(case_id):
        raise HTTPException(status_code=400, detail=f"Case {case_id} does not exist.")
    return case_id


cases_router = APIRouter()


def get_timedelta(older_than: int, time_unit: TimeUnit) -> CaseOlderThanBody:
    delta = None
    if time_unit == TimeUnit.HOURS:
        delta = timedelta(hours=older_than)
    elif time_unit == TimeUnit.DAYS:
        delta = timedelta(days=older_than)
    elif time_unit == TimeUnit.WEEKS:
        delta = timedelta(weeks=older_than)
    return CaseOlderThanBody(older_than=delta, time_unit=time_unit)


@cases_router.get("", response_model=CaseResponse, description="Get all cases")
async def get_cases_route() -> CaseResponse:
    logger.info(f"Fetching all cases")
    return get_all_cases()


@cases_router.post("/older_than", response_model=CasesBreachedResponse, description="Get all cases older than a specified date")
async def get_cases_older_than_route(case_older_than_body: CaseOlderThanBody = Depends(get_timedelta)) -> CaseResponse:
    logger.info(f"Fetching all cases older than {case_older_than_body.older_than} ({case_older_than_body.time_unit.value})")
    return get_cases_older_than(case_older_than_body)


@cases_router.get("/{case_id}", response_model=SingleCaseResponse, description="Get a single case")
async def get_single_case_route(case_id: int = Depends(verify_case_exists)) -> SingleCaseResponse:
    logger.info(f"Fetching case {case_id}")
    single_case_body = SingleCaseBody(case_id=case_id)
    return get_single_case(single_case_body.case_id)
