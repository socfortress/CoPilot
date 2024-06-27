from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import AuthHandler
from app.connectors.velociraptor.schema.artifacts import ArtifactReccomendationAIRequest
from app.connectors.velociraptor.schema.artifacts import ArtifactReccomendationRequest
from app.connectors.velociraptor.schema.artifacts import ArtifactsResponse
from app.connectors.velociraptor.schema.artifacts import CollectArtifactBody
from app.connectors.velociraptor.schema.artifacts import CollectArtifactResponse
from app.connectors.velociraptor.schema.artifacts import OSPrefixEnum
from app.connectors.velociraptor.schema.artifacts import OSPrefixModel
from app.connectors.velociraptor.schema.artifacts import QuarantineBody
from app.connectors.velociraptor.schema.artifacts import QuarantineResponse
from app.connectors.velociraptor.schema.artifacts import RunCommandBody
from app.connectors.velociraptor.schema.artifacts import RunCommandResponse
from app.connectors.velociraptor.services.artifacts import get_artifacts
from app.connectors.velociraptor.services.artifacts import post_to_copilot_ai_module
from app.connectors.velociraptor.services.artifacts import quarantine_host
from app.connectors.velociraptor.services.artifacts import run_artifact_collection
from app.connectors.velociraptor.services.artifacts import run_remote_command
from app.db.db_session import get_db
from app.db.universal_models import Agents

# App specific imports


velociraptor_artifacts_router = APIRouter()


# Get all valid OS prefixes


def get_valid_os_prefixes() -> List[str]:
    """
    Returns a list of valid operating system prefixes.

    Returns:
        List[str]: A list of valid operating system prefixes.
    """
    return [prefix.name.lower() for prefix in OSPrefixEnum]


# Verify the OS prefix exists and return the appropriate Enum value
def verify_os_prefix_exists(os_prefix: str) -> str:
    """
    Verify if the given OS prefix exists.

    Args:
        os_prefix (str): The OS prefix to be verified.

    Returns:
        str: The value of the OS prefix.

    Raises:
        HTTPException: If the OS prefix does not exist.
    """
    os_prefix_lower = os_prefix.lower()
    os_prefix_upper = os_prefix.upper()  # Convert to uppercase for Enum matching
    valid_os_prefixes = get_valid_os_prefixes()

    if os_prefix_lower not in valid_os_prefixes:
        raise HTTPException(
            status_code=400,
            detail=f"OS prefix {os_prefix} does not exist.",
        )

    return OSPrefixEnum[os_prefix_upper].value  # Use the uppercase version for Enum matching


def get_os_prefix_from_os_name(os_name: str) -> str:
    """
    Get the OS prefix from the OS name.

    Args:
        os_name (str): The name of the operating system.

    Returns:
        str: The OS prefix corresponding to the OS name.
    """
    # Use the OSPrefixModel to get the OS prefix from the OS name
    logger.info(f"Getting OS prefix from OS name {os_name}")
    os_prefix_model = OSPrefixModel(os_name=os_name)
    result = os_prefix_model.get_os_prefix()
    logger.info(f"OS prefix for OS name {os_name} is {result}")
    return result


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


async def get_velociraptor_org(session: AsyncSession, hostname: str) -> str:
    """
    Retrieves the velociraptor_org associated with the given hostname.

    Args:
        session (AsyncSession): The database session.
        hostname (str): The hostname of the agent.

    Returns:
        str: The velociraptor_org associated with the hostname.

    Raises:
        HTTPException: If the agent with the given hostname is not found or if the velociraptor_org is not available.
    """
    logger.info(f"Getting velociraptor_org from hostname {hostname}")
    result = await session.execute(select(Agents).filter(Agents.hostname == hostname))
    agent = result.scalars().first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with hostname {hostname} not found",
        )

    if agent.velociraptor_org is None:
        raise HTTPException(
            status_code=404,
            detail=f"Velociraptor ORG for hostname {hostname} is not available",
        )

    logger.info(f"velociraptor_org for hostname {hostname} is {agent.velociraptor_org}")
    return agent.velociraptor_org


async def update_agent_quarantine_status(
    session: AsyncSession,
    quarantine_body: QuarantineBody,
    quarantine_response: QuarantineResponse,
):
    """
    Updates the quarantine status of an agent.

    Args:
        session (AsyncSession): The database session.
        quarantine_body (QuarantineBody): The body of the quarantine request.
        quarantine_response (QuarantineResponse): The response of the quarantine request.

    Raises:
        HTTPException: If the agent with the specified hostname is not found or if the quarantine action fails.

    Returns:
        None
    """
    logger.info(
        f"Updating agent quarantine status for hostname {quarantine_body.hostname}",
    )
    result = await session.execute(
        select(Agents).filter(Agents.hostname == quarantine_body.hostname),
    )
    agent = result.scalars().first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with hostname {quarantine_body.hostname} not found",
        )

    if quarantine_body.action == "quarantine":
        if quarantine_response.success:
            agent.quarantined = True
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to quarantine hostname {quarantine_body.hostname}",
            )
    elif quarantine_body.action == "remove_quarantine":
        if quarantine_response.success:
            agent.quarantined = False
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove quarantine for hostname {quarantine_body.hostname}",
            )

    await session.commit()

    logger.info(
        f"Agent quarantine status for hostname {quarantine_body.hostname} updated to {agent.quarantined}",
    )

    return None


@velociraptor_artifacts_router.get(
    "",
    response_model=ArtifactsResponse,
    description="Get all artifacts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_artifacts() -> ArtifactsResponse:
    """
    Retrieve all artifacts.

    Returns:
        ArtifactsResponse: The response containing all artifacts.
    """
    logger.info("Fetching all artifacts")
    return await get_artifacts()


@velociraptor_artifacts_router.get(
    "/{os_prefix}",
    response_model=ArtifactsResponse,
    description="Get all artifacts for a specific OS prefix",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_artifacts_for_os_prefix(
    os_prefix: str = Depends(verify_os_prefix_exists),
) -> ArtifactsResponse:
    """
    Fetches all artifacts for a specific OS prefix.

    Args:
        os_prefix (str): The OS prefix to filter the artifacts.

    Returns:
        ArtifactsResponse: The response containing the success status, message, and artifacts.
    """
    logger.info(f"Fetching all artifacts for OS prefix {os_prefix}")
    # Get all the artifacts names that begin with the OS prefix
    artifacts = await get_artifacts()
    artifacts = artifacts.artifacts
    artifacts_for_os_prefix = [artifact for artifact in artifacts if artifact.name.startswith(os_prefix)]
    return ArtifactsResponse(
        success=True,
        message=f"All artifacts for OS prefix {os_prefix} retrieved",
        artifacts=artifacts_for_os_prefix,
    )


@velociraptor_artifacts_router.get(
    "/hostname/{hostname}",
    response_model=ArtifactsResponse,
    description="Get all artifacts for a specific host's OS prefix",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_artifacts_for_hostname(
    hostname: str,
    session: AsyncSession = Depends(get_db),
) -> ArtifactsResponse:
    """
    Retrieve all artifacts for a specific host's OS prefix.

    Args:
        hostname (str): The hostname of the host.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ArtifactsResponse: The response containing the retrieved artifacts.
    """
    logger.info(f"Fetching all artifacts for hostname {hostname}")

    # Asynchronous query to find the agent
    agent_result = await session.execute(
        select(Agents).filter(Agents.hostname == hostname),
    )
    agent = agent_result.scalars().first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with hostname {hostname} not found",
        )

    os_prefix = get_os_prefix_from_os_name(os_name=agent.os.lower())
    if not os_prefix:
        raise HTTPException(
            status_code=404,
            detail=f"OS prefix of {agent.os.lower()} for hostname {hostname} not found",
        )

    # Assuming get_all_artifacts_for_os_prefix is an async function
    result = await get_all_artifacts_for_os_prefix(os_prefix)

    return ArtifactsResponse(
        success=True,
        message=f"All available artifacts that can be ran for hostname {hostname} retrieved",
        artifacts=result.artifacts,
    )


@velociraptor_artifacts_router.post(
    "/collect",
    response_model=CollectArtifactResponse,
    description="Run an analyzer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def collect_artifact(
    collect_artifact_body: CollectArtifactBody,
    session: AsyncSession = Depends(get_db),
) -> CollectArtifactResponse:
    """
    Collects an artifact for a given hostname.

    Args:
        collect_artifact_body (CollectArtifactBody): The request body containing the hostname and artifact name.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        CollectArtifactResponse: The response containing the collected artifact.
    """
    logger.info(f"Received request to collect artifact {collect_artifact_body}")
    result = await get_all_artifacts_for_hostname(
        collect_artifact_body.hostname,
        session,
    )
    artifact_names = [artifact.name for artifact in result.artifacts]

    if collect_artifact_body.artifact_name not in artifact_names:
        raise HTTPException(
            status_code=400,
            detail=f"Artifact name {collect_artifact_body.artifact_name} does not apply for hostname {collect_artifact_body.hostname} or does not exist",
        )

    collect_artifact_body.velociraptor_id = await get_velociraptor_id(
        session,
        collect_artifact_body.hostname,
    )

    collect_artifact_body.velociraptor_org = await get_velociraptor_org(
        session,
        collect_artifact_body.hostname,
    )

    # Assuming run_artifact_collection is an async function and takes a session as a parameter
    return await run_artifact_collection(collect_artifact_body)


@velociraptor_artifacts_router.post(
    "/command",
    response_model=RunCommandResponse,
    description="Run a remote command",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def run_command(
    run_command_body: RunCommandBody,
    session: AsyncSession = Depends(get_db),
) -> RunCommandResponse:
    """
    Run a remote command.

    Args:
        run_command_body (RunCommandBody): The request body containing the command details.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        RunCommandResponse: The response containing the result of the command execution.
    """
    logger.info(f"Received request to run command {run_command_body}")
    result = await get_all_artifacts_for_hostname(run_command_body.hostname, session)
    artifact_names = [artifact.name for artifact in result.artifacts]
    if run_command_body.artifact_name not in artifact_names:
        raise HTTPException(
            status_code=400,
            detail=f"Artifact name {run_command_body.artifact_name.value} does not apply for hostname {run_command_body.hostname} or does not exist",
        )
    # Add the velociraptor_id to the run_command_body object
    run_command_body.velociraptor_id = await get_velociraptor_id(
        session,
        run_command_body.hostname,
    )

    run_command_body.velociraptor_org = await get_velociraptor_org(
        session,
        run_command_body.hostname,
    )
    # Run the command
    return await run_remote_command(run_command_body)


@velociraptor_artifacts_router.post(
    "/quarantine",
    response_model=QuarantineResponse,
    description="Quarantine a host",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def quarantine(
    quarantine_body: QuarantineBody,
    session: AsyncSession = Depends(get_db),
) -> QuarantineResponse:
    """
    Quarantine a host.

    Args:
        quarantine_body (QuarantineBody): The body of the request containing the hostname and artifact name.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        QuarantineResponse: The response containing the result of the quarantine operation.
    """
    logger.info(f"Received request to quarantine host {quarantine_body}")
    result = await get_all_artifacts_for_hostname(quarantine_body.hostname, session)
    artifact_names = [artifact.name for artifact in result.artifacts]
    if quarantine_body.artifact_name not in artifact_names:
        raise HTTPException(
            status_code=400,
            detail=f"Artifact name {quarantine_body.artifact_name.value} does not apply for hostname {quarantine_body.hostname} or does not exist",
        )
    # Add the velociraptor_id to the run_command_body object
    # Add the velociraptor_id to the quarantine_body object
    quarantine_body.velociraptor_id = await get_velociraptor_id(
        session,
        quarantine_body.hostname,
    )

    quarantine_body.velociraptor_org = await get_velociraptor_org(
        session,
        quarantine_body.hostname,
    )

    # Quarantine the host
    quarantine_response = await quarantine_host(quarantine_body)

    # If the host was successfully quarantined, update the database
    await update_agent_quarantine_status(session, quarantine_body, quarantine_response)

    return quarantine_response


@velociraptor_artifacts_router.post(
    "/velociraptor-artifact-recommendation",
    description="Retrieve artifact to run based on alert. Invokes the `copilot-ai-module",
)
async def get_artifact_recommendation(request: ArtifactReccomendationAIRequest):
    """
    Retrieve the artifact to run based on the alert.

    Returns:
        str: The artifact to run based on the alert.
    """
    logger.info("Fetching artifact recommendation based on alert")
    artifacts = await get_artifacts()
    logger.info(f"Artifacts: {artifacts.artifacts}")
    return await post_to_copilot_ai_module(
        data=ArtifactReccomendationRequest(
            artifacts=artifacts.artifacts,
            os=request.os,
            prompt=request.prompt,
        ),
    )
