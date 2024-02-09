from app.auth.utils import AuthHandler
from app.connectors.velociraptor.schema.artifacts import CollectArtifactResponse
from app.connectors.velociraptor.schema.flows import FlowResponse, RetrieveFlowRequest
from app.connectors.velociraptor.services.flows import get_flow, get_flows
from app.db.db_session import get_db
from app.db.universal_models import Agents
from fastapi import APIRouter, Depends, HTTPException, Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

velociraptor_flows_router = APIRouter()


async def get_velociraptor_id(session: AsyncSession, hostname: str) -> str:
    """
    Retrieves the velociraptor_id associated with the given hostname.

    Args:
        session (AsyncSession): The database session.
        hostname (str): The hostname of the agent.

    Returns:
        str: The velociraptor_id associated with the hostname.

    Raises:
        HTTPException: If the agent with the given hostname is not found or if the velociraptor_id is not available.
    """
    logger.info(f"Getting velociraptor_id from hostname {hostname}")
    # log all the agents
    agents = await session.execute(select(Agents))
    for agent in agents.scalars().all():
        logger.info(f"agent: {agent}")
    result = await session.execute(select(Agents).filter(Agents.hostname == hostname))
    agent = result.scalars().first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with hostname {hostname} not found",
        )

    if agent.velociraptor_id == "n/a":
        raise HTTPException(
            status_code=404,
            detail=f"Velociraptor ID for hostname {hostname} is not available",
        )

    logger.info(f"velociraptor_id for hostname {hostname} is {agent.velociraptor_id}")
    return agent.velociraptor_id


@velociraptor_flows_router.get(
    "/{hostname}",
    response_model=FlowResponse,
    description="Get all artifacts for a specific host's OS prefix",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_flows_for_hostname(
    hostname: str,
    session: AsyncSession = Depends(get_db),
) -> FlowResponse:
    """
    Retrieve ran flows for a specific host.

    Args:
        hostname (str): The hostname of the host.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        FlowResponse: The response containing the retrieved flows.
    """
    logger.info(f"Fetching all flows for hostname {hostname}")

    velociraptor_id = await get_velociraptor_id(session, hostname)
    logger.info(f"velociraptor_id for hostname {hostname} is {velociraptor_id}")
    return await get_flows(velociraptor_id)


@velociraptor_flows_router.post(
    "/retrieve",
    response_model=CollectArtifactResponse,
    description="Retrieve a flow based on the flow_id",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def retrieve_flow(
    retrieve_flow_request: RetrieveFlowRequest,
) -> CollectArtifactResponse:
    """
    Retrieve ran flows for a specific host.

    Args:
        retrieve_flow_request (RetrieveFlowRequest): The request containing the flow_id.


    Returns:
        CollectArtifactResponse: The response containing the retrieved flows.
    """
    logger.info(f"Fetching flow for flow_id {retrieve_flow_request.session_id}")
    return await get_flow(retrieve_flow_request)
