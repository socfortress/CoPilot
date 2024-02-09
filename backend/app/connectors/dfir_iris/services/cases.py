from datetime import datetime
from typing import Dict
from typing import List

from dfir_iris_client.case import Case
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.dfir_iris.schema.cases import CaseOlderThanBody
from app.connectors.dfir_iris.schema.cases import CaseResponse
from app.connectors.dfir_iris.schema.cases import CasesBreachedResponse
from app.connectors.dfir_iris.schema.cases import ClosedCaseResponse
from app.connectors.dfir_iris.schema.cases import PurgeCaseResponse
from app.connectors.dfir_iris.schema.cases import ReopenedCaseResponse
from app.connectors.dfir_iris.schema.cases import SingleCaseBody
from app.connectors.dfir_iris.schema.cases import SingleCaseResponse
from app.connectors.dfir_iris.utils.universal import create_dfir_iris_client
from app.connectors.dfir_iris.utils.universal import fetch_and_parse_data
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)


async def get_client_and_cases() -> Dict:
    """
    Initialize the client session and fetch all cases.

    Returns:
        Dictionary containing the success status and either the case data or an error message.
    """
    dfir_iris_client = await create_dfir_iris_client("DFIR-IRIS")
    case = Case(session=dfir_iris_client)
    logger.info("Fetching all cases after getting session")
    result = await fetch_and_parse_data(dfir_iris_client, case.list_cases)
    return result


async def get_customer_code(session: AsyncSession, client_name: str) -> str:
    """
    Retrieves the customer code for a given customer ID.

    Args:
        session (AsyncSession): The database session.
        customer_id (int): The ID of the customer.

    Returns:
        The customer code for the given customer ID.
    """
    try:
        alert_creation_settings = await session.execute(
            select(AlertCreationSettings).filter(
                AlertCreationSettings.iris_customer_name == client_name,
            ),
        )
        alert_creation_settings = alert_creation_settings.scalars().first()
        if alert_creation_settings is None:
            return "Customer Not Found"
        return alert_creation_settings.customer_code
    except Exception as e:
        logger.error(
            f"Error retrieving customer code for customer ID {client_name}: {e}",
        )
        return "Customer Not Found"


def filter_open_cases(cases: List[Dict]) -> List[Dict]:
    """
    Filters out cases that are still open.

    Args:
        cases (List): List of all cases.

    Returns:
        List of cases that are still open.
    """
    return [case for case in cases if case["case_close_date"] == ""]


def filter_cases_older_than(cases: List[Dict], older_than: datetime) -> List[Dict]:
    """
    Filters out cases that are older than the specified time.

    Args:
        cases (List): List of all cases.
        older_than (datetime): The datetime to filter by.

    Returns:
        List of cases that are older than the specified time.
    """
    current_time = datetime.now()
    filtered_cases = []
    for case in cases:
        case_open_date = (
            datetime.strptime(case["case_open_date"], "%m/%d/%Y")
            if not isinstance(case["case_open_date"], datetime)
            else case["case_open_date"]
        )
        if case_open_date < current_time - older_than:
            case["case_open_date"] = case_open_date.strftime(
                "%m/%d/%Y",
            )  # Convert back to string to match the model
            filtered_cases.append(case)
    return filtered_cases


async def get_all_cases(session: AsyncSession) -> CaseResponse:
    """
    Retrieves all cases from DFIR-IRIS.

    Returns:
        CaseResponse: The response object containing the success status, message, and cases data.

    Raises:
        HTTPException: If there is an error retrieving the cases.
    """
    result = await get_client_and_cases()
    try:
        if not result["success"]:
            logger.error(f"Failed to get all cases: {result['message']}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get all cases: {result['message']}",
            )
        for case in result["data"]:
            case["customer_code"] = await get_customer_code(
                session,
                case["client_name"],
            )
        return CaseResponse(
            success=True,
            message="Successfully fetched all cases",
            cases=result["data"],
        )
    except Exception as err:
        logger.error(f"Failed to get all cases: {err}")
        raise HTTPException(status_code=500, detail=f"Failed to get all cases: {err}")


async def get_cases_older_than(
    case_older_than_body: CaseOlderThanBody,
) -> CasesBreachedResponse:
    """
    Retrieves cases that are older than a specified duration.

    Args:
        case_older_than_body (CaseOlderThanBody): The body containing the duration threshold.

    Returns:
        CasesBreachedResponse: The response object containing the breached cases.
    """
    result = await get_client_and_cases()
    if not result["success"]:
        logger.error(f"Failed to get all cases: {result['message']}")
        return HTTPException(
            status_code=500,
            detail=f"Failed to get all cases: {result['message']}",
        )

    open_cases = filter_open_cases(result["data"])
    breached_cases = filter_cases_older_than(
        open_cases,
        case_older_than_body.older_than,
    )
    return CasesBreachedResponse(
        success=True,
        message=f"Successfully fetched all cases older than {case_older_than_body.older_than}",
        cases_breached=breached_cases,
    )


async def get_single_case(
    case_id: SingleCaseBody,
    session: AsyncSession,
) -> SingleCaseResponse:
    """
    Fetches a single case from DFIR-IRIS based on the provided case ID.

    Args:
        case_id (SingleCaseBody): The ID of the case to fetch.

    Returns:
        SingleCaseResponse: The response containing the fetched case.

    Raises:
        Any exceptions raised during the execution of the function will be propagated.
    """
    dfir_iris_client = await create_dfir_iris_client("DFIR-IRIS")
    case = Case(session=dfir_iris_client)
    result = await fetch_and_parse_data(dfir_iris_client, case.get_case, case_id)
    result["data"]["customer_code"] = await get_customer_code(
        session,
        result["data"]["customer_name"],
    )
    return SingleCaseResponse(
        success=True,
        message="Successfully fetched single case",
        case=result["data"],
    )


async def close_case(case_id: SingleCaseBody) -> ClosedCaseResponse:
    """
    Closes a single case from DFIR-IRIS based on the provided case ID.

    Args:
        case_id (SingleCaseBody): The ID of the case to close.

    Returns:
        ClosedCaseResponse: The response containing the closed case.

    Raises:
        Any exceptions raised during the execution of the function will be propagated.
    """
    logger.info(f"Closing case: {case_id}")
    dfir_iris_client = await create_dfir_iris_client("DFIR-IRIS")
    case = Case(session=dfir_iris_client)
    result = await fetch_and_parse_data(dfir_iris_client, case.close_case, case_id)
    return ClosedCaseResponse(
        success=True,
        case=result["data"],
        message="Successfully closed case",
    )


async def reopen_case(case_id: SingleCaseBody) -> ReopenedCaseResponse:
    """
    Opens a single case from DFIR-IRIS based on the provided case ID.

    Args:
        case_id (SingleCaseBody): The ID of the case to open.

    Returns:
        OpenCaseResponse: The response containing the opened case.

    Raises:
        Any exceptions raised during the execution of the function will be propagated.
    """
    logger.info(f"Opening case: {case_id}")
    dfir_iris_client = await create_dfir_iris_client("DFIR-IRIS")
    case = Case(session=dfir_iris_client)
    result = await fetch_and_parse_data(dfir_iris_client, case.reopen_case, case_id)
    logger.info(f"Successfully opened case: {result}")
    return ReopenedCaseResponse(
        success=True,
        case=result["data"],
        message="Successfully opened case",
    )


############# ! DELETE ACTIONS ! #############
async def purge_cases() -> PurgeCaseResponse:
    """
    Purges all cases from DFIR-IRIS.

    Returns:
        PurgeCaseResponse: The response containing the purge status.

    Raises:
        HTTPException: If there is an error purging the cases.
    """
    dfir_iris_client = await create_dfir_iris_client("DFIR-IRIS")
    case = Case(session=dfir_iris_client)

    case_ids = await get_case_ids_to_purge()

    for case_id in case_ids:
        await purge_case(dfir_iris_client, case, case_id)

    return PurgeCaseResponse(success=True, message="Successfully purged all cases")


async def get_case_ids_to_purge() -> List[int]:
    """
    Retrieves all case IDs to be purged, skipping over specific cases as needed.

    Returns:
        List[int]: List of case IDs to purge.
    """
    result = await get_client_and_cases()
    handle_cases_retrieval_failure(result)

    # Extract case IDs, skipping over specific cases
    return [case["case_id"] for case in result["data"] if case["case_id"] != 1]


def handle_cases_retrieval_failure(result: Dict) -> None:
    """
    Handles failure in retrieving cases.

    Args:
        result (Dict): The result of the cases retrieval attempt.
    """
    if not result["success"]:
        error_message = f"Failed to get all cases: {result['message']}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


async def purge_case(client, case, case_id) -> PurgeCaseResponse:
    """
    Purges a single case.

    Args:
        client: The DFIR-IRIS client.
        case: The case object.
        case_id (int): The ID of the case to purge.
    """
    try:
        logger.info(f"Purging case: {case_id}")
        await fetch_and_parse_data(client, case.delete_case, case_id)
        return PurgeCaseResponse(
            success=True,
            message=f"Successfully purged case {case_id}",
        )
    except Exception as err:
        error_message = f"Failed to purge case {case_id}: {err}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


async def delete_single_case(case_id: SingleCaseBody) -> PurgeCaseResponse:
    """
    Deletes a single case from DFIR-IRIS based on the provided case ID.

    Args:
        case_id (SingleCaseBody): The ID of the case to delete.

    Returns:
        SingleCaseResponse: The response containing the deleted case.

    Raises:
        Any exceptions raised during the execution of the function will be propagated.
    """
    dfir_iris_client = await create_dfir_iris_client("DFIR-IRIS")
    case = Case(session=dfir_iris_client)
    await fetch_and_parse_data(dfir_iris_client, case.delete_case, case_id)
    return PurgeCaseResponse(success=True, message="Successfully deleted single case")
