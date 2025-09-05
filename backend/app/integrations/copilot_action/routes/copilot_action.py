import os
from typing import Optional, List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.routes.auth import AuthHandler
from app.connectors.velociraptor.schema.artifacts import CollectArtifactBody
from app.connectors.velociraptor.schema.artifacts import CollectArtifactResponse
from app.connectors.velociraptor.schema.artifacts import InvokeCopilotActionBody
from app.connectors.velociraptor.services.artifacts import run_artifact_collection
from app.db.db_session import get_db
from app.db.universal_models import Agents
from app.integrations.copilot_action.schema.copilot_action import ActionDetailResponse
from app.integrations.copilot_action.schema.copilot_action import (
    InventoryMetricsResponse,
)
from app.integrations.copilot_action.schema.copilot_action import InventoryResponse
from app.integrations.copilot_action.schema.copilot_action import Technology
from app.integrations.copilot_action.services.copilot_action import CopilotActionService

copilot_action_router = APIRouter()
auth_handler = AuthHandler()

# Helper functions for better modularity


def get_license_key() -> str:
    """Get and validate the COPILOT_API_KEY environment variable."""
    license_key = os.getenv("COPILOT_API_KEY")
    if not license_key:
        logger.error("COPILOT_API_KEY environment variable not set")
        raise HTTPException(status_code=500, detail="COPILOT_API_KEY environment variable not configured")
    return license_key


async def get_agents_by_hostnames(session: AsyncSession, hostnames: List[str]) -> List[Agents]:
    """Retrieve multiple agents from database by hostnames."""
    agent_details = await session.execute(
        select(Agents).filter(Agents.hostname.in_(hostnames))
    )
    agents = agent_details.scalars().all()

    found_hostnames = {agent.hostname for agent in agents}
    missing_hostnames = set(hostnames) - found_hostnames

    if missing_hostnames:
        raise HTTPException(
            status_code=404,
            detail=f"Agents with hostnames {list(missing_hostnames)} not found",
        )

    logger.info(f"Found {len(agents)} agents")
    return agents


def determine_artifact_name(agent_os: str) -> str:
    """Determine the appropriate Velociraptor artifact based on OS."""
    if "Windows" in agent_os:
        return "Windows.Execute.RemotePowerShellScript"
    elif "Linux" in agent_os:
        return "Linux.Execute.RemoteBashScript"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OS: {agent_os}",
        )


def build_velociraptor_parameters(copilot_params: dict, script_params: list) -> dict:
    """
    Convert Copilot Action parameters to Velociraptor format.

    Args:
        copilot_params: Dictionary of parameters provided by the user
        script_params: List of ScriptParameter objects from the action details

    Returns:
        Dictionary with env array for Velociraptor
    """
    if not copilot_params:
        return {}

    env_array = []

    # Always add RepoURL and ScriptName first
    if "RepoURL" in copilot_params:
        env_array.append({"key": "RepoURL", "value": str(copilot_params["RepoURL"])})
    if "ScriptName" in copilot_params:
        env_array.append({"key": "ScriptName", "value": str(copilot_params["ScriptName"])})

    # Create a mapping of parameter names to their arg_position
    param_position_map = {}
    for param in script_params:
        if param.arg_position is not None:
            param_position_map[param.name] = param.arg_position

    # Add parameters with arg_position as Arg{position}
    for param_name, param_value in copilot_params.items():
        if param_name in param_position_map:
            arg_key = f"Arg{param_position_map[param_name]}"
            env_array.append({"key": arg_key, "value": str(param_value)})

    # Add other parameters (those without arg_position and not RepoURL/ScriptName)
    for param_name, param_value in copilot_params.items():
        if param_name not in param_position_map and param_name not in ["RepoURL", "ScriptName"]:
            env_array.append({"key": param_name, "value": str(param_value)})

    return {"env": env_array}


async def validate_parameters(provided_params: dict, script_params: list) -> None:
    """
    Validate provided parameters against the script's expected parameters.

    Args:
        provided_params: Dictionary of parameters provided by the user
        script_params: List of ScriptParameter objects defining expected parameters

    Raises:
        HTTPException: If invalid or missing parameters are provided
    """
    if not provided_params:
        provided_params = {}

    logger.info(f"Validating {len(provided_params)} provided parameters against {len(script_params)} script parameters")

    # Extract parameter info from script
    valid_param_names = {param.name for param in script_params}
    required_params = {param.name for param in script_params if param.required}
    provided_param_keys = set(provided_params.keys())

    # Add RepoURL and ScriptName as required parameters for Copilot Actions
    required_params.add("RepoURL")
    required_params.add("ScriptName")
    valid_param_names.add("RepoURL")
    valid_param_names.add("ScriptName")

    logger.info(f"Valid parameters: {valid_param_names}")
    logger.info(f"Required parameters: {required_params}")
    logger.info(f"Provided parameters: {provided_param_keys}")

    # Validate: no invalid parameters
    invalid_params = provided_param_keys - valid_param_names
    if invalid_params:
        logger.error(f"Invalid parameters provided: {invalid_params}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid parameters provided: {list(invalid_params)}. Valid parameters are: {list(valid_param_names)}",
        )

    # Validate: all required parameters present
    missing_params = required_params - provided_param_keys
    if missing_params:
        logger.error(f"Missing required parameters: {missing_params}")
        raise HTTPException(status_code=400, detail=f"Missing required parameters: {list(missing_params)}")

    logger.info("Parameter validation successful")


async def build_artifact_collection_body(agent: Agents, artifact_name: str, velociraptor_params: dict) -> CollectArtifactBody:
    """Build the artifact collection request body for Velociraptor."""
    return CollectArtifactBody(
        hostname=agent.hostname,
        velociraptor_id=agent.velociraptor_id,
        velociraptor_org=agent.velociraptor_org,
        artifact_name=artifact_name,
        parameters=velociraptor_params,
    )


# Route handlers (keeping existing routes but updating invoke_action)


@copilot_action_router.get(
    "/inventory",
    response_model=InventoryResponse,
    description="Get inventory of available active response scripts",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_inventory(
    technology: Optional[Technology] = Query(None, description="Filter by technology type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    q: Optional[str] = Query(None, description="Free-text search query"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    refresh: bool = Query(False, description="Force refresh cache"),
    include: Optional[str] = Query(None, description="Comma-separated extra fields to include"),
) -> InventoryResponse:
    """Retrieve inventory of available active response scripts."""
    logger.info(f"Fetching active response inventory with filters: tech={technology}, category={category}, tag={tag}, q={q}")

    license_key = get_license_key()

    try:
        response = await CopilotActionService.get_inventory(
            license_key=license_key,
            technology=technology,
            category=category,
            tag=tag,
            q=q,
            limit=limit,
            offset=offset,
            refresh=refresh,
            include=include,
        )

        logger.info(f"Successfully fetched inventory: {len(response.copilot_actions)} actions")
        return response

    except Exception as e:
        logger.error(f"Error fetching inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching inventory: {str(e)}")


@copilot_action_router.get(
    "/inventory/{copilot_action_name}",
    response_model=ActionDetailResponse,
    description="Get details for a specific active response script",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_action_by_name(copilot_action_name: str) -> ActionDetailResponse:
    """Get detailed information for a specific active response script."""
    logger.info(f"Fetching action details for: {copilot_action_name}")

    license_key = get_license_key()

    try:
        response = await CopilotActionService.get_action_by_name(license_key=license_key, copilot_action_name=copilot_action_name)

        if not response.success:
            if "not found" in response.message.lower():
                raise HTTPException(status_code=404, detail=response.message)
            else:
                raise HTTPException(status_code=500, detail=response.message)

        logger.info(f"Successfully fetched action details for: {copilot_action_name}")
        logger.info(f"Raw action feteched: {response}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching action details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching action details: {str(e)}")


@copilot_action_router.get(
    "/metrics",
    response_model=InventoryMetricsResponse,
    description="Get inventory metrics and status",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_metrics() -> InventoryMetricsResponse:
    """Get metrics and status information for the inventory service."""
    logger.info("Fetching inventory metrics")

    license_key = get_license_key()

    try:
        response = await CopilotActionService.get_metrics(license_key=license_key)
        logger.info("Successfully fetched inventory metrics")
        return response

    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {str(e)}")


@copilot_action_router.get(
    "/technologies",
    description="Get available technology types",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_technologies() -> dict:
    """Get list of available technology types for filtering."""
    technologies = [tech.value for tech in Technology]

    return {
        "technologies": technologies,
        "total": len(technologies),
        "message": "Successfully retrieved available technologies",
        "success": True,
    }


async def get_agents_by_hostnames(session: AsyncSession, hostnames: List[str]) -> List[Agents]:
    """Retrieve multiple agents from database by hostnames."""
    agent_details = await session.execute(
        select(Agents).filter(Agents.hostname.in_(hostnames))
    )
    agents = agent_details.scalars().all()

    found_hostnames = {agent.hostname for agent in agents}
    missing_hostnames = set(hostnames) - found_hostnames

    if missing_hostnames:
        raise HTTPException(
            status_code=404,
            detail=f"Agents with hostnames {list(missing_hostnames)} not found",
        )

    logger.info(f"Found {len(agents)} agents")
    return agents


async def invoke_action_on_agent(
    agent: Agents,
    copilot_action_name: str,
    copilot_action_details: ActionDetailResponse,
    parameters: dict
) -> CollectArtifactResponse:
    """
    Invoke a Copilot Action on a single agent.

    Args:
        agent: The agent to invoke the action on
        copilot_action_name: Name of the action
        copilot_action_details: Action details from the service
        parameters: Parameters for the action

    Returns:
        CollectArtifactResponse: Response from the artifact collection
    """
    try:
        # Determine the appropriate artifact based on OS
        artifact_name = determine_artifact_name(agent.os)
        logger.info(f"Using artifact: {artifact_name} for OS: {agent.os} on agent {agent.hostname}")

        # Build Velociraptor parameters
        velociraptor_params = build_velociraptor_parameters(
            parameters,
            copilot_action_details.copilot_action.script_parameters
        )

        # Build artifact collection request
        artifact_body = await build_artifact_collection_body(agent, artifact_name, velociraptor_params)
        logger.info(f"Built artifact collection request for {agent.hostname}")

        # Execute the collection
        response = await run_artifact_collection(artifact_body)
        logger.info(f"Successfully invoked Copilot action on {agent.hostname}")

        return response

    except Exception as e:
        logger.error(f"Error invoking action on agent {agent.hostname}: {str(e)}")
        # You might want to return a failed response instead of raising
        raise HTTPException(status_code=500, detail=f"Error invoking action on agent {agent.hostname}: {str(e)}")


@copilot_action_router.post(
    "/invoke",
    response_model=List[CollectArtifactResponse],  # Now returns a list of responses
    description="Invoke a Copilot Action on multiple target agents",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def invoke_action(body: InvokeCopilotActionBody, session: AsyncSession = Depends(get_db)) -> List[CollectArtifactResponse]:
    """
    Invoke a Copilot Action on multiple target agents.

    This endpoint orchestrates the process of:
    1. Finding all target agents
    2. Fetching action details and validating parameters once
    3. Building and executing the artifact collection request for each agent

    Args:
        body: Request body containing action name, agent names, and parameters
        session: Database session

    Returns:
        List[CollectArtifactResponse]: List of responses from the artifact collections
    """
    logger.info(f"Invoking Copilot action '{body.copilot_action_name}' on {len(body.agent_names)} agents")

    try:
        # Step 1: Get all target agents
        agents = await get_agents_by_hostnames(session, body.agent_names)
        logger.info(f"Found agents: {[agent.hostname for agent in agents]}")

        # Step 2: Fetch action details (do this once for all agents)
        copilot_action_details = await get_action_by_name(body.copilot_action_name)
        logger.info(f"Found action details for: {body.copilot_action_name}")

        # Step 3: Prepare parameters (do this once for all agents)
        final_parameters = body.parameters or {}

        # Add the `repo_url` and the `script_name` to the parameters
        if copilot_action_details.copilot_action.repo_url:
            final_parameters["RepoURL"] = copilot_action_details.copilot_action.repo_url
        if copilot_action_details.copilot_action.script_name:
            final_parameters["ScriptName"] = copilot_action_details.copilot_action.script_name

        logger.info(f"Parameters after adding repo and script: {final_parameters}")

        # Step 4: Validate parameters (do this once for all agents)
        await validate_parameters(final_parameters, copilot_action_details.copilot_action.script_parameters)

        # Step 5: Execute action on each agent
        responses = []
        successful_agents = []
        failed_agents = []

        for agent in agents:
            try:
                response = await invoke_action_on_agent(
                    agent,
                    body.copilot_action_name,
                    copilot_action_details,
                    final_parameters
                )
                responses.append(response)
                successful_agents.append(agent.hostname)

            except Exception as e:
                logger.error(f"Failed to invoke action on agent {agent.hostname}: {str(e)}")
                failed_agents.append(agent.hostname)
                # Add a failed response to maintain order
                failed_response = CollectArtifactResponse(
                    message=f"Failed to invoke action on {agent.hostname}: {str(e)}",
                    success=False,
                    results=[]
                )
                responses.append(failed_response)

        # Log summary
        logger.info(f"Action invocation complete. Successful: {len(successful_agents)}, Failed: {len(failed_agents)}")
        if successful_agents:
            logger.info(f"Successful agents: {successful_agents}")
        if failed_agents:
            logger.warning(f"Failed agents: {failed_agents}")

        return responses

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, not found, etc.)
        raise
    except Exception as e:
        logger.error(f"Unexpected error invoking Copilot action: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error invoking Copilot action: {str(e)}")
