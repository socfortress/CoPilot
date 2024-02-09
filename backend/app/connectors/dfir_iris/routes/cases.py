from datetime import timedelta

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.dfir_iris.schema.cases import CaseOlderThanBody
from app.connectors.dfir_iris.schema.cases import CaseResponse
from app.connectors.dfir_iris.schema.cases import CasesBreachedResponse
from app.connectors.dfir_iris.schema.cases import ClosedCaseResponse
from app.connectors.dfir_iris.schema.cases import PurgeCaseResponse
from app.connectors.dfir_iris.schema.cases import ReopenedCaseResponse
from app.connectors.dfir_iris.schema.cases import SingleCaseBody
from app.connectors.dfir_iris.schema.cases import SingleCaseResponse
from app.connectors.dfir_iris.schema.cases import TimeUnit
from app.connectors.dfir_iris.services.cases import close_case
from app.connectors.dfir_iris.services.cases import delete_single_case
from app.connectors.dfir_iris.services.cases import get_all_cases
from app.connectors.dfir_iris.services.cases import get_cases_older_than
from app.connectors.dfir_iris.services.cases import get_single_case
from app.connectors.dfir_iris.services.cases import purge_cases
from app.connectors.dfir_iris.services.cases import reopen_case
from app.connectors.dfir_iris.utils.universal import check_case_exists
from app.db.db_session import get_db


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
async def get_cases_route(session: AsyncSession = Depends(get_db)) -> CaseResponse:
    """
    Get all cases.

    Returns:
        CaseResponse: The response containing all cases.
    """
    logger.info("Fetching all cases")
    return await get_all_cases(session=session)


@dfir_iris_cases_router.post(
    "/older_than",
    response_model=CasesBreachedResponse,
    description="Get all cases older than a specified date",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_cases_older_than_route(
    case_older_than_body: CaseOlderThanBody = Depends(get_timedelta),
) -> CaseResponse:
    """
    Fetches all cases older than a specified date.

    Args:
        case_older_than_body (CaseOlderThanBody): The request body containing the date and time unit.

    Returns:
        CaseResponse: The response containing the cases older than the specified date.
    """
    logger.info(
        f"Fetching all cases older than {case_older_than_body.older_than} ({case_older_than_body.time_unit.value})",
    )
    return await get_cases_older_than(case_older_than_body)


@dfir_iris_cases_router.delete(
    "/purge",
    response_model=PurgeCaseResponse,
    description="Purge all cases",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def purge_cases_route() -> PurgeCaseResponse:
    """
    Purge all cases.

    Returns:
        PurgeCaseResponse: The response containing the purge status.
    """
    logger.info("Purging all cases")
    return await purge_cases()


@dfir_iris_cases_router.delete(
    "/purge/{case_id}",
    response_model=PurgeCaseResponse,
    description="Purge a single case",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def purge_single_case_route(
    case_id: int = Depends(verify_case_exists),
) -> PurgeCaseResponse:
    """
    Purge a single case by its ID.

    Args:
        case_id (int): The ID of the case to purge.

    Returns:
        PurgeCaseResponse: The response containing the purge status.
    """
    logger.info(f"Purging case {case_id}")
    single_case_body = SingleCaseBody(case_id=case_id)
    return await delete_single_case(single_case_body.case_id)


@dfir_iris_cases_router.get(
    "/{case_id}",
    response_model=SingleCaseResponse,
    description="Get a single case",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_single_case_route(
    case_id: int = Depends(verify_case_exists),
    session: AsyncSession = Depends(get_db),
) -> SingleCaseResponse:
    """
    Retrieve a single case by its ID.

    Args:
        case_id (int): The ID of the case to retrieve.

    Returns:
        SingleCaseResponse: The response containing the single case information.
    """
    logger.info(f"Fetching case {case_id}")
    single_case_body = SingleCaseBody(case_id=case_id)
    return await get_single_case(single_case_body.case_id, session=session)


@dfir_iris_cases_router.put(
    "/close/{case_id}",
    response_model=ClosedCaseResponse,
    description="Close a single case",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def close_single_case_route(
    case_id: int = Depends(verify_case_exists),
) -> ClosedCaseResponse:
    """
    Close a single case by its ID.

    Args:
        case_id (int): The ID of the case to close.

    Returns:
        ClosedCaseResponse: The response containing the closed case information.
    """
    logger.info(f"Closing case {case_id}")
    single_case_body = SingleCaseBody(case_id=case_id)
    return await close_case(single_case_body.case_id)


@dfir_iris_cases_router.put(
    "/open/{case_id}",
    response_model=ReopenedCaseResponse,
    description="Open a single case",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def reopen_single_case_route(
    case_id: int = Depends(verify_case_exists),
) -> ReopenedCaseResponse:
    """
    Open a single case by its ID.

    Args:
        case_id (int): The ID of the case to open.

    Returns:
        ReopenedCaseResponse: The response containing the opened case information.
    """
    logger.info(f"Opening case {case_id}")
    single_case_body = SingleCaseBody(case_id=case_id)
    return await reopen_case(single_case_body.case_id)
