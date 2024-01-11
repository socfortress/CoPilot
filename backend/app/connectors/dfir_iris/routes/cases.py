from datetime import timedelta

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.dfir_iris.schema.cases import CaseOlderThanBody
from app.connectors.dfir_iris.schema.cases import CaseResponse
from app.connectors.dfir_iris.schema.cases import CasesBreachedResponse
from app.connectors.dfir_iris.schema.cases import SingleCaseBody
from app.connectors.dfir_iris.schema.cases import SingleCaseResponse
from app.connectors.dfir_iris.schema.cases import TimeUnit
from app.connectors.dfir_iris.services.cases import get_all_cases
from app.connectors.dfir_iris.services.cases import get_cases_older_than
from app.connectors.dfir_iris.services.cases import get_single_case
from app.connectors.dfir_iris.utils.universal import check_case_exists
from app.connectors.dfir_iris.services.cases import purge_cases


async def verify_case_exists(case_id: int) -> int:
    """
    Verify if a case exists based on the given case ID.

    Args:
        case_id (int): The ID of the case to verify.

    Returns:
        int: The verified case ID.

    Raises:
        HTTPException: If the case does not exist.
    """
    if not await check_case_exists(case_id):
        raise HTTPException(status_code=400, detail=f"Case {case_id} does not exist.")
    return case_id


dfir_iris_cases_router = APIRouter()


def get_timedelta(older_than: int, time_unit: TimeUnit) -> CaseOlderThanBody:
    """
    Calculate a timedelta based on the given older_than value and time_unit.

    Args:
        older_than (int): The value representing the duration.
        time_unit (TimeUnit): The unit of time (hours, days, weeks).

    Returns:
        CaseOlderThanBody: An instance of CaseOlderThanBody with the calculated timedelta.

    """
    delta = None
    if time_unit == TimeUnit.HOURS:
        delta = timedelta(hours=older_than)
    elif time_unit == TimeUnit.DAYS:
        delta = timedelta(days=older_than)
    elif time_unit == TimeUnit.WEEKS:
        delta = timedelta(weeks=older_than)
    return CaseOlderThanBody(older_than=delta, time_unit=time_unit)


@dfir_iris_cases_router.get(
    "",
    response_model=CaseResponse,
    description="Get all cases",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_cases_route() -> CaseResponse:
    """
    Get all cases.

    Returns:
        CaseResponse: The response containing all cases.
    """
    logger.info("Fetching all cases")
    return await get_all_cases()


@dfir_iris_cases_router.post(
    "/older_than",
    response_model=CasesBreachedResponse,
    description="Get all cases older than a specified date",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_cases_older_than_route(case_older_than_body: CaseOlderThanBody = Depends(get_timedelta)) -> CaseResponse:
    """
    Fetches all cases older than a specified date.

    Args:
        case_older_than_body (CaseOlderThanBody): The request body containing the date and time unit.

    Returns:
        CaseResponse: The response containing the cases older than the specified date.
    """
    logger.info(f"Fetching all cases older than {case_older_than_body.older_than} ({case_older_than_body.time_unit.value})")
    return await get_cases_older_than(case_older_than_body)

@dfir_iris_cases_router.delete(
    "/purge",
    response_model=CaseResponse,
    description="Purge all cases",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def purge_cases_route() -> CaseResponse:
    """
    Purge all cases.

    Returns:
        CaseResponse: The response containing all cases.
    """
    logger.info("Purging all cases")
    return await purge_cases()


@dfir_iris_cases_router.get(
    "/{case_id}",
    response_model=SingleCaseResponse,
    description="Get a single case",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_single_case_route(case_id: int = Depends(verify_case_exists)) -> SingleCaseResponse:
    """
    Retrieve a single case by its ID.

    Args:
        case_id (int): The ID of the case to retrieve.

    Returns:
        SingleCaseResponse: The response containing the single case information.
    """
    logger.info(f"Fetching case {case_id}")
    single_case_body = SingleCaseBody(case_id=case_id)
    return await get_single_case(single_case_body.case_id)
