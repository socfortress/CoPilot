import time
from typing import Any
from typing import Dict

from cortex4py.api import Api
from fastapi import HTTPException
from loguru import logger

from app.connectors.cortex.schema.analyzers import AnalyzerJobData
from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session


async def verify_cortex_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to Cortex service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(f"Verifying the Cortex connection to {attributes['connector_url']}")

    try:
        api = Api(
            attributes["connector_url"],
            attributes["connector_api_key"],
            verify_cert=False,
        )
        # Get Cortex Status
        status = api.status
        if status:
            logger.debug("Cortex connection successful")
            return {
                "connectionSuccessful": True,
                "message": "Cortex connection successful",
            }
        else:
            logger.error(
                f"Connection to {attributes['connector_url']} failed with error.",
            )
            return {
                "connectionSuccessful": False,
                "message": f"Connection to {attributes['connector_url']} failed with error.",
            }
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed with error: {e}",
        }


async def verify_cortex_connection(connector_name: str) -> str:
    """
    Returns the authentication token for the Cortex service.

    Returns:
        str: Authentication token for the Cortex service.
    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Cortex connector found in the database")
        return None
    return await verify_cortex_credentials(attributes)


async def create_cortex_client(connector_name: str) -> Api:
    """
    Returns an Cortex client for the Wazuh Indexer service.

    Returns:
        Cortex: Cortex client for the Cortex service.
    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Wazuh Indexer connector found in the database")
        return None
    return Api(
        attributes["connector_url"],
        attributes["connector_api_key"],
        verify_cert=False,
    )


async def run_and_wait_for_analyzer(
    analyzer_name: str,
    job_data: AnalyzerJobData,
) -> Dict[str, Any]:
    """
    Runs an analyzer by name and waits for the job to complete.

    Args:
        analyzer_name (str): The name of the analyzer to run.
        job_data (AnalyzerJobData): The data for the analyzer job.

    Returns:
        Dict[str, Any]: A dictionary containing the result of the analyzer job.
    """
    api = await create_cortex_client("Cortex")  # Create Api object
    if api is None:
        return {"success": False, "message": "API initialization failed"}
    try:
        job = api.analyzers.run_by_name(analyzer_name, job_data.dict(), force=1)
        return await monitor_analyzer_job(api, job)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running analyzer {analyzer_name}: {e}",
        )


async def monitor_analyzer_job(api: Api, job: Any) -> Dict[str, Any]:
    """
    Monitors the status of an analyzer job and retrieves the final report when the job is completed.

    Args:
        api (Api): The API object used to make requests to the Cortex API.
        job (Any): The job object representing the analyzer job.

    Returns:
        Dict[str, Any]: A dictionary containing the success status and message of the job.
    """
    r_json = job.json()
    job_id = r_json["id"]
    logger.info(f"Job ID is: {job_id}")

    job_state = r_json["status"]
    timer = 0

    while job_state != "Success":
        if timer == 60:
            logger.error("Job failed to complete after 5 minutes.")
            return {"success": False, "message": "Job timed out"}

        timer += 1
        logger.info(f"Timer is: {timer}")

        if job_state == "Failure":
            error_message = r_json["errorMessage"]
            logger.error(f"Cortex Failure: {error_message}")
            return {"success": False, "message": f"Analyzer failed: {error_message}"}

        time.sleep(5)
        followup_request = api.jobs.get_by_id(job_id)
        r_json = followup_request.json()
        job_state = r_json["status"]

    return await retrieve_final_report(api, job_id)


async def retrieve_final_report(api: Api, job_id: str) -> Dict[str, Any]:
    """
    Retrieves the final report for a given job ID from the Cortex API.

    Args:
        api (Api): The Cortex API instance.
        job_id (str): The ID of the job.

    Returns:
        Dict[str, Any]: A dictionary containing the success status, message, and final report.
    """
    report = api.jobs.get_report(job_id).report
    final_report = report["full"]
    return {
        "success": True,
        "message": "Analyzer ran successfully",
        "report": final_report,
    }
