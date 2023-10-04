from datetime import datetime
from typing import List, Dict, Any, Callable, Tuple
from fastapi import HTTPException
from loguru import logger
from dfir_iris_client.case import Case
from app.connectors.dfir_iris.schema.cases import CaseModel, CaseResponse, CaseOlderThanBody, CasesBreachedResponse, SingleCaseBody, SingleCaseResponse
from app.connectors.dfir_iris.schema.notes import NotesResponse, NotesQueryParams, NoteDetails, NoteDetailsResponse
from app.connectors.dfir_iris.utils.universal import create_dfir_iris_client, fetch_and_parse_data

def get_client_and_cases() -> Dict:
    """
    Initialize the client session and fetch all cases.

    Returns:
        Dictionary containing the success status and either the case data or an error message.
    """
    dfir_iris_client = create_dfir_iris_client("DFIR-IRIS")
    case = Case(session=dfir_iris_client)
    logger.info("Fetching all cases after getting session")
    result = fetch_and_parse_data(dfir_iris_client, case.list_cases)
    return result

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
        case_open_date = datetime.strptime(case["case_open_date"], "%m/%d/%Y") if not isinstance(case["case_open_date"], datetime) else case["case_open_date"]
        if case_open_date < current_time - older_than:
            case["case_open_date"] = case_open_date.strftime("%m/%d/%Y")  # Convert back to string to match the model
            filtered_cases.append(case)
    return filtered_cases

def get_all_cases() -> CaseResponse:
    result = get_client_and_cases()
    if not result["success"]:
        logger.error(f"Failed to get all cases: {result['message']}")
        return HTTPException(status_code=500, detail=f"Failed to get all cases: {result['message']}")
    return CaseResponse(success=True, message="Successfully fetched all cases", cases=result["data"])

def get_cases_older_than(case_older_than_body: CaseOlderThanBody) -> CasesBreachedResponse:
    result = get_client_and_cases()
    if not result["success"]:
        logger.error(f"Failed to get all cases: {result['message']}")
        return HTTPException(status_code=500, detail=f"Failed to get all cases: {result['message']}")
    
    open_cases = filter_open_cases(result["data"])
    breached_cases = filter_cases_older_than(open_cases, case_older_than_body.older_than)
    return CasesBreachedResponse(
        success=True,
        message=f"Successfully fetched all cases older than {case_older_than_body.older_than}",
        cases_breached=breached_cases,
    )

def get_single_case(case_id: SingleCaseBody) -> SingleCaseResponse:
    dfir_iris_client = create_dfir_iris_client("DFIR-IRIS")
    case = Case(session=dfir_iris_client)
    result = fetch_and_parse_data(dfir_iris_client, case.get_case, case_id)
    return SingleCaseResponse(success=True, message="Successfully fetched single case", case=result["data"])