from typing import List

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dfir_iris.schema.cases import AssetCaseIDResponse
from app.connectors.dfir_iris.services.assets import get_case_assets
from app.connectors.dfir_iris.services.cases import get_all_cases


async def collect_agent_soc_cases(
    agent_id: int,
    session: AsyncSession,
) -> AssetCaseIDResponse:
    """
    Get all cases for the given agent ID.

    Args:
        agent_id (int): The ID of the agent to get cases for.

    Returns:
        AssetCaseIDResponse: An instance of AssetCaseIDResponse containing the cases for the given agent ID.
    """
    logger.info(f"Getting cases for agent: {agent_id}")
    all_cases = await get_all_cases(session=session)
    case_ids = await filter_cases_by_agent_id(all_cases, agent_id)

    logger.info(f"Found cases: {case_ids}")
    return AssetCaseIDResponse(
        case_ids=case_ids,
        success=True,
        message="Successfully retrieved cases for agent",
    )


async def filter_cases_by_agent_id(cases, agent_id: int) -> List[int]:
    """
    Filters cases by the given agent ID and collects all associated case IDs.

    Args:
        cases: All available cases.
        agent_id (int): Agent ID to filter by.

    Returns:
        List[int]: List of case IDs associated with the given agent ID.
    """
    case_ids = []
    for case in cases.cases:
        if await is_agent_in_case(case.case_id, agent_id):
            case_ids.append(case.case_id)
    return case_ids


async def is_agent_in_case(case_id: int, agent_id: int) -> bool:
    """
    Checks if a given agent ID is associated with a case.

    Args:
        case_id (int): The case ID to check.
        agent_id (int): The agent ID to check.

    Returns:
        bool: True if the agent is associated with the case, False otherwise.
    """
    logger.info(f"Getting assets for case: {case_id}")
    assets = await get_case_assets(case_id)
    for asset in assets.assets:
        if f"agent_id:{agent_id}" in asset.asset_tags:
            logger.info(f"Found case with agent: {agent_id} in case: {case_id}")
            return True
    return False
