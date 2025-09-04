import os
from typing import Optional

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


async def get_agent_by_hostname(session: AsyncSession, hostname: str) -> Agents:
    """Retrieve agent from database by hostname."""
    agent_details = await session.execute(
        select(Agents).filter(Agents.hostname == hostname),
    )
    agent = agent_details.scalars().first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with hostname {hostname} not found",
        )

    logger.info(f"Found agent: {agent.hostname} with OS: {agent.os}")
    return agent


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


def build_velociraptor_parameters(copilot_params: dict) -> dict:
    """Convert Copilot Action parameters to Velociraptor format."""
    if not copilot_params:
        return {}

    env_array = [{"key": key, "value": str(value)} for key, value in copilot_params.items()]

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


@copilot_action_router.post(
    "/invoke",
    response_model=CollectArtifactResponse,
    description="Invoke a Copilot Action on a target agent",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def invoke_action(body: InvokeCopilotActionBody, session: AsyncSession = Depends(get_db)) -> CollectArtifactResponse:
    """
    Invoke a Copilot Action on a target agent.

    This endpoint orchestrates the process of:
    1. Finding the target agent
    2. Determining the appropriate Velociraptor artifact
    3. Fetching action details and validating parameters
    4. Building and executing the artifact collection request

    Args:
        body: Request body containing action name, agent name, and parameters
        session: Database session

    Returns:
        CollectArtifactResponse: Response from the artifact collection
    """
    logger.info(f"Invoking Copilot action '{body.copilot_action_name}' on agent '{body.agent_name}'")

    try:
        # Step 1: Get the target agent
        agent = await get_agent_by_hostname(session, body.agent_name)

        # Step 2: Determine the appropriate artifact based on OS
        artifact_name = determine_artifact_name(agent.os)
        logger.info(f"Using artifact: {artifact_name} for OS: {agent.os}")

        # Step 3: Fetch action details
        copilot_action_details = await get_action_by_name(body.copilot_action_name)
        logger.info(f"Found action details for: {body.copilot_action_name}")

        # Add the `repo_url` and the `script_name` to the parameters
        if copilot_action_details.copilot_action.repo_url:
            if not body.parameters:
                body.parameters = {}
            body.parameters["RepoURL"] = copilot_action_details.copilot_action.repo_url
        if copilot_action_details.copilot_action.script_name:
            if not body.parameters:
                body.parameters = {}
            body.parameters["ScriptName"] = copilot_action_details.copilot_action.script_name

        logger.info(f"Parameters after adding repo and script: {body.parameters}")

        # Step 4: Validate parameters
        await validate_parameters(body.parameters or {}, copilot_action_details.copilot_action.script_parameters)

        # Step 5: Build Velociraptor parameters
        velociraptor_params = build_velociraptor_parameters(body.parameters or {})

        # Step 6: Build artifact collection request
        artifact_body = await build_artifact_collection_body(agent, artifact_name, velociraptor_params)
        logger.info(f"Built artifact collection request for {agent.hostname}")

        # Step 7: Execute the collection
        response = await run_artifact_collection(artifact_body)
        logger.info(f"Successfully invoked Copilot action on {agent.hostname}")

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, not found, etc.)
        raise
    except Exception as e:
        logger.error(f"Unexpected error invoking Copilot action: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error invoking Copilot action: {str(e)}")
