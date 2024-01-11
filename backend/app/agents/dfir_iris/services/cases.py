from fastapi import HTTPException
from loguru import logger


from app.connectors.dfir_iris.services.cases import get_all_cases
from app.connectors.dfir_iris.schema.cases import CaseResponse

from app.connectors.dfir_iris.services.cases import get_all_cases
from app.connectors.dfir_iris.services.assets import get_case_assets


async def collect_agent_soc_cases(agent_id: int) -> CaseResponse:
    """
    Get all cases for the given agent ID.

    Args:
        agent_id (int): The ID of the agent to get cases for.

    Returns:
        CaseResponse: An instance of CaseResponse containing the cases for the given agent ID.

    Raises:
        HTTPException: If the agent does not exist.
    """
    logger.info(f"Getting cases for agent: {agent_id}")
    cases = await get_all_cases()
    # for every case, get the assets
    for case in cases.cases:
        logger.info(f"Getting assets for case: {case.case_id}")
        assets = await get_case_assets(case.case_id)
        logger.info(f"Assets for case: {case.case_id} are: {assets.assets}")
    return None
