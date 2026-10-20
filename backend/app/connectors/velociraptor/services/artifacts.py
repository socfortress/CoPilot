import os
import re
import shutil
import tempfile
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import httpx
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.velociraptor.schema.artifacts import ArtifactParametersResponse
from app.connectors.velociraptor.schema.artifacts import ArtifactReccomendationRequest
from app.connectors.velociraptor.schema.artifacts import ArtifactReccomendationResponse
from app.connectors.velociraptor.schema.artifacts import Artifacts
from app.connectors.velociraptor.schema.artifacts import ArtifactsResponse
from app.connectors.velociraptor.schema.artifacts import CollectArtifactBody
from app.connectors.velociraptor.schema.artifacts import CollectArtifactResponse
from app.connectors.velociraptor.schema.artifacts import CollectFileBody
from app.connectors.velociraptor.schema.artifacts import ParameterKeyValue
from app.connectors.velociraptor.schema.artifacts import QuarantineBody
from app.connectors.velociraptor.schema.artifacts import QuarantineResponse
from app.connectors.velociraptor.schema.artifacts import RunCommandBody
from app.connectors.velociraptor.schema.artifacts import RunCommandResponse
from app.connectors.velociraptor.utils.universal import UniversalService
from app.connectors.velociraptor.utils.validation import validate_artifact_name
from app.connectors.velociraptor.utils.validation import (
    validate_artifact_parameter_name,
)
from app.connectors.velociraptor.utils.validation import validate_client_id
from app.connectors.velociraptor.utils.validation import validate_flow_id
from app.connectors.velociraptor.utils.validation import validate_org_id
from app.connectors.velociraptor.utils.validation import vql_string_literal_value


def create_query(query: str) -> str:
    """
    Create a query string.

    Args:
        query (str): The query to be executed.

    Returns:
        str: The created query string.
    """
    return query


# Every collection is launched from a constant template: the org, client, artifact and every
# user-supplied value travel as query variables (VQLCollectorArgs.env, see
# UniversalService.execute_query) and are referenced by name, so none of them is ever part of
# the query text (GHSA-5542-j2fc-gqjm). `collect_client(env=...)` applies the dict to every
# listed artifact, exactly as `spec=dict(`<artifact>`=dict(...))` did (vql/server/flows/create.go).
VQL_COLLECT = "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName]) AS Flow FROM scope()"
VQL_COLLECT_WITH_ENV = "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName], env=dict({env})) AS Flow FROM scope()"
VQL_RUN_COMMAND = (
    "SELECT collect_client(org_id=OrgId, client_id=ClientId, urgent=true, artifacts=[ArtifactName], "
    "env=dict(Command=Command)) AS Flow FROM scope()"
)
VQL_COLLECT_FILE = (
    "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName], "
    "env=dict(collectionSpec=CollectionSpec, Root=Root)) AS Flow FROM scope()"
)
VQL_QUARANTINE = "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName], env=dict()) AS Flow FROM scope()"
VQL_REMOVE_QUARANTINE = (
    "SELECT collect_client(org_id=OrgId, client_id=ClientId, artifacts=[ArtifactName], env=dict(RemovePolicy='Y')) AS Flow FROM scope()"
)


def collection_env(org_id: str, client_id: str, artifact_name: str, **values: str) -> Dict[str, str]:
    """The query variables of a collect_client template: the target plus any extra values."""
    return {"OrgId": org_id, "ClientId": client_id, "ArtifactName": artifact_name, **values}


def extract_flow_id(flow: dict) -> Optional[str]:
    """The flow id from a collect_client result row (the `Flow` column, else any dict carrying one)."""
    results = flow.get("results") or []
    if not results:
        return None
    row = results[0]
    candidates = [row.get("Flow")] + [value for key, value in row.items() if key != "Flow"]
    for value in candidates:
        if isinstance(value, dict) and value.get("flow_id"):
            return value["flow_id"]
    return None


def requested_artifact_parameters(
    parameters: Optional[Dict[str, Union[str, List[ParameterKeyValue]]]],
) -> Optional[Dict[str, str]]:
    """The ``{name: value}`` artifact parameters a /collect body asks for, or None for none.

    Two shapes are accepted, as before: ``{"env": [{"key": ..., "value": ...}, ...]}``
    (what the frontend and Copilot Actions send) or a plain ``{name: value}`` dict whose
    string values are the parameters. An ``env`` list -- even an empty one -- returns a
    dict, so the collection still passes ``env=dict()``.
    """
    if not parameters:
        return None
    if "env" in parameters and isinstance(parameters["env"], list):
        requested = {}
        for item in parameters["env"]:
            if isinstance(item, ParameterKeyValue):
                requested[item.key] = item.value
            elif isinstance(item, dict) and "key" in item:
                requested[item["key"]] = item.get("value", "")
        return requested
    requested = {name: value for name, value in parameters.items() if isinstance(value, str)}
    return requested or None


async def declared_artifact_parameter_names(artifact_name: str, org_id: str = "root") -> set:
    """The parameter names the artifact itself declares, read from Velociraptor in `org_id`."""
    artifact_response = await get_artifact_by_name(artifact_name, org_id)
    if not artifact_response.artifacts:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_name} not found")
    return {param.name for param in (artifact_response.artifacts[0].parameters or [])}


def build_parameter_env(requested: Dict[str, str], declared: set, artifact_name: str, drop_undeclared: bool = False, literal: bool = False):
    """The ``env=dict(...)`` body and query variables for the requested artifact parameters.

    A name is only written into the query (as a backtick-quoted identifier, since VQL's
    ``dict()`` takes literal names) when the artifact declares it and it passes
    `validate_artifact_parameter_name`. A name the artifact does not declare is refused with a
    400, or -- with `drop_undeclared`, for the admin/responder CoPilot Actions path -- left
    out with a warning, as Velociraptor itself ignored it before; it never reaches the query.
    Each value goes into its own variable, ``Param<n>``, and is never part of the query text.
    With `literal` (an approved Talon v2 collection, whose values are the text the approver
    read) each value is passed as it is, without the VQL unescaping kept for the manual routes.
    """
    parts = []
    env = {}
    undeclared = [name for name in requested if name not in declared]
    if undeclared and not drop_undeclared:
        valid = ", ".join(sorted(declared)) or "none"
        raise HTTPException(
            status_code=400,
            detail=f"Parameter '{undeclared[0]}' is not valid for artifact {artifact_name}. Valid parameters: {valid}",
        )
    if undeclared:
        logger.warning(f"Dropping parameters {undeclared!r} that artifact {artifact_name} does not declare")
    requested = {name: value for name, value in requested.items() if name in declared}
    for index, (name, value) in enumerate(requested.items()):
        validate_artifact_parameter_name(name)
        if not isinstance(value, str):
            raise HTTPException(status_code=400, detail=f"Parameter '{name}' must be a string")
        variable = f"Param{index}"
        parts.append(f"`{name}`={variable}")
        # The value used to be written between single quotes, so keep its VQL escapes meaning
        # what they meant (see vql_string_literal_value).
        env[variable] = value if literal else vql_string_literal_value(value)
    return ", ".join(parts), env


async def get_artifacts() -> ArtifactsResponse:
    """
    Get all artifacts from Velociraptor.

    Returns:
        ArtifactsResponse: A dictionary containing the artifacts.
    """
    logger.info("Fetching artifacts from Velociraptor")
    velociraptor_service = await UniversalService.create("Velociraptor")
    query = create_query("SELECT name,description,parameters FROM artifact_definitions()")
    all_artifacts = await velociraptor_service.execute_query_async(query)
    try:
        if all_artifacts["success"]:
            artifacts = [Artifacts(**artifact) for artifact in all_artifacts["results"]]
            return ArtifactsResponse(
                success=True,
                message="All artifacts retrieved",
                artifacts=artifacts,
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get all artifacts: {all_artifacts['message']}",
            )
    except Exception as err:
        logger.error(f"Failed to get all artifacts: {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get all artifacts: {err}",
        )


async def get_artifact_by_name(artifact_name: str, org_id: str = "root") -> ArtifactsResponse:
    """
    Get a specific artifact by name from Velociraptor.

    Args:
        artifact_name (str): The name of the artifact to retrieve.
        org_id (str): The Velociraptor org to read the definition from.

    Returns:
        ArtifactsResponse: A response containing the specific artifact.
    """
    logger.info(f"Fetching artifact '{artifact_name}' from Velociraptor")
    validate_artifact_name(artifact_name)
    velociraptor_service = await UniversalService.create("Velociraptor")

    # Query for a specific artifact by name
    query = create_query("SELECT name,description,parameters FROM artifact_definitions() WHERE name = ArtifactName")
    artifact_result = await velociraptor_service.execute_query_async(query, org_id=org_id, env={"ArtifactName": artifact_name})

    try:
        if artifact_result["success"]:
            if artifact_result["results"]:
                artifacts = [Artifacts(**artifact) for artifact in artifact_result["results"]]
                return ArtifactsResponse(
                    success=True,
                    message=f"Artifact '{artifact_name}' retrieved successfully",
                    artifacts=artifacts,
                )
            else:
                return ArtifactsResponse(
                    success=True,
                    message=f"Artifact '{artifact_name}' not found",
                    artifacts=[],
                )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get artifact '{artifact_name}': {artifact_result['message']}",
            )
    except Exception as err:
        logger.error(f"Failed to get artifact '{artifact_name}': {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get artifact '{artifact_name}': {err}",
        )


async def get_artifact_policy_definitions(artifact_name: str, org_id: str) -> List[dict]:
    """The artifact's definition and every dependency's, as the host's org resolves them.

    `deps=true` makes Velociraptor resolve the dependencies with its own VQL parser
    (launcher.GetDependentArtifacts), the set the client would receive. Read from `org_id`, the
    host's org, where the collection will run. See `collection_policy`.
    """
    validate_artifact_name(artifact_name)
    velociraptor_service = await UniversalService.create("Velociraptor")
    query = create_query(
        "SELECT name, compiled_in, built_in, parameters, required_permissions, implied_permissions, imports, tools, "
        "export, precondition, sources FROM artifact_definitions(names=[ArtifactName], deps=true)",
    )
    result = await velociraptor_service.execute_query_async(query, org_id=org_id, env={"ArtifactName": artifact_name})
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=f"Failed to get artifact '{artifact_name}': {result.get('message')}")
    return [row for row in (result.get("results") or []) if isinstance(row, dict)]


async def validate_artifact_parameters(
    artifact_name: str,
    provided_parameters: Optional[Dict[str, Union[str, List[ParameterKeyValue]]]],
    org_id: str = "root",
) -> None:
    """
    Validates that the provided parameters match the artifact's expected parameters.

    Args:
        artifact_name (str): The name of the artifact to validate against.
        provided_parameters (Optional[Dict]): The parameters provided in the request.

    Raises:
        HTTPException: If any provided parameter is not valid for the artifact.
    """
    if not provided_parameters:
        return  # No parameters to validate

    # Fetch the artifact details from the org the collection runs in
    artifact_response = await get_artifact_by_name(artifact_name, org_id)

    if not artifact_response.artifacts or len(artifact_response.artifacts) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact {artifact_name} not found",
        )

    artifact = artifact_response.artifacts[0]

    # If the artifact has no parameters defined, reject any provided parameters
    if not artifact.parameters:
        raise HTTPException(
            status_code=400,
            detail=f"Artifact {artifact_name} does not accept any parameters",
        )

    # Get valid parameter names from the artifact
    valid_param_names = {param.name for param in artifact.parameters}

    logger.info(f"Valid parameters for artifact {artifact_name}: {valid_param_names}")
    logger.info(f"Provided parameters for artifact {artifact_name}: {provided_parameters}")

    # Check if provided parameters are valid
    # Handle both direct key-value pairs and the 'env' list format
    if isinstance(provided_parameters, dict):
        if "env" in provided_parameters and isinstance(provided_parameters["env"], list):
            # Handle env list format
            for param_pair in provided_parameters["env"]:
                # Check if it's a ParameterKeyValue model or a dict
                if isinstance(param_pair, ParameterKeyValue):
                    param_name = param_pair.key
                elif isinstance(param_pair, dict) and "key" in param_pair:
                    param_name = param_pair["key"]
                else:
                    continue

                if param_name not in valid_param_names:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Parameter '{param_name}' is not valid for artifact {artifact_name}. Valid parameters: {', '.join(sorted(valid_param_names))}",
                    )
        else:
            # Handle direct key-value format
            for param_name in provided_parameters.keys():
                if param_name not in valid_param_names:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Parameter '{param_name}' is not valid for artifact {artifact_name}. Valid parameters: {', '.join(sorted(valid_param_names))}",
                    )

    logger.info(f"All provided parameters are valid for artifact {artifact_name}")


async def get_artifact_parameters_by_prefix_service(
    artifact_name: str,
    parameter_prefix: str,
) -> ArtifactParametersResponse:
    """
    Get parameters from a specific artifact that match a given prefix.

    Args:
        artifact_name (str): The name of the artifact to retrieve parameters from.
        parameter_prefix (str): The prefix to filter parameters by.

    Returns:
        ArtifactParametersResponse: A response containing matching parameters.
    """
    logger.info(f"Fetching parameters with prefix '{parameter_prefix}' from artifact '{artifact_name}'")

    try:
        # First, get the artifact with its parameters
        artifact_response = await get_artifact_by_name(artifact_name)

        if not artifact_response.success or not artifact_response.artifacts:
            return ArtifactParametersResponse(
                success=False,
                message=f"Artifact '{artifact_name}' not found",
                artifact_name=artifact_name,
                parameter_prefix=parameter_prefix,
                matching_parameters=[],
                total_matches=0,
            )

        artifact = artifact_response.artifacts[0]

        # Filter parameters by prefix
        matching_parameters = []
        if artifact.parameters:
            for param in artifact.parameters:
                if param.name.startswith(parameter_prefix):
                    matching_parameters.append(param)

        # Sort the matching parameters for consistent ordering
        matching_parameters.sort(key=lambda x: x.name)

        total_matches = len(matching_parameters)

        if total_matches == 0:
            message = f"No parameters found matching prefix '{parameter_prefix}' in artifact '{artifact_name}'"
        elif total_matches == 1:
            message = f"Found 1 parameter matching prefix '{parameter_prefix}' in artifact '{artifact_name}'"
        else:
            message = f"Found {total_matches} parameters matching prefix '{parameter_prefix}' in artifact '{artifact_name}'"

        logger.info(message)

        return ArtifactParametersResponse(
            success=True,
            message=message,
            artifact_name=artifact_name,
            parameter_prefix=parameter_prefix,
            matching_parameters=matching_parameters,
            total_matches=total_matches,
        )

    except Exception as err:
        error_message = f"Failed to get parameters with prefix '{parameter_prefix}' from artifact '{artifact_name}': {err}"
        logger.error(error_message)
        raise HTTPException(
            status_code=500,
            detail=error_message,
        )


def started_flow_id(flow: dict) -> str:
    """The flow id a ``collect_client`` query started, validated (``F.`` and alphanumerics), or a
    500 when the answer carries no usable one."""
    flow_id = extract_flow_id(flow)
    try:
        return validate_flow_id(flow_id)
    except HTTPException:
        logger.error(f"Could not find flow_id in results: {(flow.get('results') or [None])[0]}")
        raise HTTPException(status_code=500, detail="Failed to extract flow ID from results") from None


async def start_artifact_collection(
    collect_artifact_body: CollectArtifactBody,
    drop_undeclared_parameters: bool = False,
    velociraptor_service: Optional[UniversalService] = None,
    literal_values: bool = False,
) -> str:
    """Start an artifact collection on a client and return its flow id, without waiting for it.

    The caller has checked the host, the artifact and its parameter names (``/collect``'s
    checks, ``routes.artifacts.start_collection_as``). The org, client, artifact and every
    parameter value are query variables of a constant template (GHSA-5542-j2fc-gqjm).
    `literal_values`: the values are passed as written (``build_parameter_env``).
    """
    # Validate the identifier fields (GHSA-5542-j2fc-gqjm). They and every parameter value are
    # passed as query variables; parameter names are checked against the artifact below.
    validate_org_id(collect_artifact_body.velociraptor_org)
    validate_client_id(collect_artifact_body.velociraptor_id)
    validate_artifact_name(collect_artifact_body.artifact_name)
    try:
        velociraptor_service = velociraptor_service or await UniversalService.create("Velociraptor")
        env = collection_env(
            collect_artifact_body.velociraptor_org,
            collect_artifact_body.velociraptor_id,
            collect_artifact_body.artifact_name,
        )
        requested = requested_artifact_parameters(getattr(collect_artifact_body, "parameters", None))
        if requested is None:
            query = create_query(VQL_COLLECT)
        else:
            declared = (
                await declared_artifact_parameter_names(collect_artifact_body.artifact_name, collect_artifact_body.velociraptor_org)
                if requested
                else set()
            )
            env_body, parameter_env = build_parameter_env(
                requested,
                declared,
                collect_artifact_body.artifact_name,
                drop_undeclared=drop_undeclared_parameters,
                literal=literal_values,
            )
            query = create_query(VQL_COLLECT_WITH_ENV.format(env=env_body))
            env.update(parameter_env)

        logger.info(f"Running artifact collection with query: {query}")
        flow = await velociraptor_service.execute_query_async(query, org_id=collect_artifact_body.velociraptor_org, env=env)
        logger.info(f"Successfully ran artifact collection on {flow}")

        # Check if results are available
        if not flow.get("results") or len(flow["results"]) == 0:
            logger.error("No results returned from query execution")
            raise HTTPException(
                status_code=500,
                detail="Query execution did not return any results",
            )
        flow_id = started_flow_id(flow)
        logger.info(f"Extracted flow_id: {flow_id}")
        return flow_id
    except HTTPException as he:  # Catch HTTPException separately to propagate the original message
        logger.error(f"HTTPException while starting artifact collection on {collect_artifact_body}: {he.detail}")
        raise he
    except Exception as err:
        logger.error(f"Failed to run artifact collection on {collect_artifact_body}: {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run artifact collection on {collect_artifact_body}: {err}",
        )


async def _agent_for_client(session: AsyncSession, velociraptor_id: str):
    from sqlalchemy import select

    from app.db.universal_models import Agents

    result = await session.execute(select(Agents).where(Agents.velociraptor_id == velociraptor_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with velociraptor_id {velociraptor_id} not found",
        )
    return agent


async def finish_artifact_collection(
    collect_artifact_body: CollectArtifactBody,
    flow_id: str,
    session: AsyncSession,
    velociraptor_service: Optional[UniversalService] = None,
    agent=None,
) -> CollectArtifactResponse:
    """Wait for a started collection, read its results and upload the flow's files to MinIO:
    what ``/collect`` answers after ``start_artifact_collection``."""
    from app.db.universal_models import AgentDataStore

    try:
        velociraptor_service = velociraptor_service or await UniversalService.create("Velociraptor")
        if agent is None:
            agent = await _agent_for_client(session, collect_artifact_body.velociraptor_id)

        completed = await velociraptor_service.watch_flow_completion_async(flow_id, org_id=collect_artifact_body.velociraptor_org)
        logger.info(f"Successfully watched flow completion on {completed}")

        # Only read collection results if data_store_only is False
        results = None
        if not collect_artifact_body.data_store_only:
            results = await velociraptor_service.read_collection_results_async(
                client_id=collect_artifact_body.velociraptor_id,
                flow_id=flow_id,
                org_id=collect_artifact_body.velociraptor_org,
                artifact=collect_artifact_body.artifact_name,
            )
            logger.info(f"Successfully read collection results on {results}")

        # Fetch the collected file from filestore and upload to MinIO
        file_data = None
        try:
            logger.info("Fetching collected file from filestore and uploading to MinIO")
            file_data = await fetch_file_from_filestore(
                client_id=collect_artifact_body.velociraptor_id,
                flow_id=flow_id,
                org_id=collect_artifact_body.velociraptor_org,
                agent_id=agent.agent_id,
            )

            # Save metadata to database if file upload was successful
            if file_data.get("success"):
                agent_data_store = AgentDataStore(
                    agent_id=agent.agent_id,
                    velociraptor_id=collect_artifact_body.velociraptor_id,
                    artifact_name=collect_artifact_body.artifact_name,
                    flow_id=flow_id,
                    bucket_name=file_data["bucket_name"],
                    object_key=file_data["object_key"],
                    file_name=file_data["file_name"],
                    content_type=file_data.get("content_type", "application/zip"),
                    file_size=file_data["file_size"],
                    file_hash=file_data["file_hash"],
                    collection_time=datetime.utcnow(),
                    status="completed",
                )
                session.add(agent_data_store)
                await session.commit()
                await session.refresh(agent_data_store)

                logger.info(f"Saved artifact metadata to database with ID {agent_data_store.id}")
        except Exception as file_err:
            logger.warning(f"Failed to upload file to MinIO, but artifact collection succeeded: {file_err}")
            # Continue execution even if file upload fails

        # Build response based on data_store_only flag
        if collect_artifact_body.data_store_only:
            return CollectArtifactResponse(
                success=True,
                message="Artifact collected and stored successfully. Results not retrieved.",
                results=None,
                file_info=file_data if file_data and file_data.get("success") else None,
            )
        else:
            return CollectArtifactResponse(
                success=results["success"],
                message=results["message"],
                results=results["results"],
                file_info=file_data if file_data and file_data.get("success") else None,
            )
    except HTTPException as he:  # Catch HTTPException separately to propagate the original message
        logger.error(
            f"HTTPException while running artifact collection on {collect_artifact_body}: {he.detail}",
        )
        raise he
    except Exception as err:
        logger.error(
            f"Failed to run artifact collection on {collect_artifact_body}: {err}",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run artifact collection on {collect_artifact_body}: {err}",
        )


async def run_artifact_collection(
    collect_artifact_body: CollectArtifactBody,
    session: AsyncSession,
    drop_undeclared_parameters: bool = False,
) -> CollectArtifactResponse:
    """
    Run an artifact collection on a client with optional parameters and upload results to MinIO:
    ``start_artifact_collection``, then ``finish_artifact_collection`` (the wait, the results and
    the upload).

    Args:
        collect_artifact_body: The body of the request with optional parameters.
        session: Database session for storing metadata.

    Returns:
        CollectArtifactResponse: A dictionary containing the success status, message and results.
    """
    # Validate the identifier fields (GHSA-5542-j2fc-gqjm) before anything is looked up.
    validate_org_id(collect_artifact_body.velociraptor_org)
    validate_client_id(collect_artifact_body.velociraptor_id)
    validate_artifact_name(collect_artifact_body.artifact_name)

    velociraptor_service = await UniversalService.create("Velociraptor")
    try:
        agent = await _agent_for_client(session, collect_artifact_body.velociraptor_id)
    except HTTPException as he:
        logger.error(f"HTTPException while running artifact collection on {collect_artifact_body}: {he.detail}")
        raise he
    except Exception as err:
        logger.error(f"Failed to run artifact collection on {collect_artifact_body}: {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run artifact collection on {collect_artifact_body}: {err}",
        )
    flow_id = await start_artifact_collection(collect_artifact_body, drop_undeclared_parameters, velociraptor_service)
    return await finish_artifact_collection(collect_artifact_body, flow_id, session, velociraptor_service, agent)


async def run_file_collection(
    collect_artifact_body: CollectFileBody,
    session: AsyncSession,  # Add this parameter
) -> CollectArtifactResponse:
    """
    Run an artifact collection on a client and store the result in MinIO.
    """
    from sqlalchemy import select

    from app.db.universal_models import AgentDataStore
    from app.db.universal_models import Agents

    # Validate the identifier fields (GHSA-5542-j2fc-gqjm). They and the free-form `file` and
    # `root_disk` values are passed as query variables, never as query text.
    validate_org_id(collect_artifact_body.velociraptor_org)
    validate_client_id(collect_artifact_body.velociraptor_id)
    validate_artifact_name(collect_artifact_body.artifact_name)

    velociraptor_service = await UniversalService.create("Velociraptor")

    try:
        # Get agent details from database
        result = await session.execute(
            select(Agents).where(Agents.velociraptor_id == collect_artifact_body.velociraptor_id),
        )
        agent = result.scalars().first()

        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent with velociraptor_id {collect_artifact_body.velociraptor_id} not found",
            )

        # The glob and root used to be written between single quotes (and
        # format_file_path_for_os escapes Windows backslashes for that), so keep their VQL
        # escapes meaning what they meant (see vql_string_literal_value).
        query = create_query(VQL_COLLECT_FILE)
        env = collection_env(
            collect_artifact_body.velociraptor_org,
            collect_artifact_body.velociraptor_id,
            collect_artifact_body.artifact_name,
            CollectionSpec=vql_string_literal_value(collect_artifact_body.file),
            Root=vql_string_literal_value(collect_artifact_body.root_disk or ""),
        )

        logger.info(f"Query: {query}")
        flow = await velociraptor_service.execute_query_async(query, org_id=collect_artifact_body.velociraptor_org, env=env)
        logger.info(f"Successfully ran artifact collection on {flow}")

        # Check if results are available
        if not flow.get("results") or len(flow["results"]) == 0:
            logger.error("No results returned from query execution")
            raise HTTPException(
                status_code=500,
                detail="Query execution did not return any results",
            )

        flow_id = extract_flow_id(flow)

        if not flow_id:
            logger.error(f"Could not find flow_id in results: {flow['results'][0]}")
            raise HTTPException(
                status_code=500,
                detail="Failed to extract flow ID from results",
            )

        logger.info(f"Extracted flow_id: {flow_id}")

        completed = await velociraptor_service.watch_flow_completion_async(flow_id, org_id=collect_artifact_body.velociraptor_org)
        logger.info(f"Successfully watched flow completion on {completed}")

        results = await velociraptor_service.read_collection_results_async(
            client_id=collect_artifact_body.velociraptor_id,
            flow_id=flow_id,
            org_id=collect_artifact_body.velociraptor_org,
            artifact=collect_artifact_body.artifact_name,
        )

        logger.info("Successfully read collection results")

        # Fetch the collected file from filestore and upload to MinIO
        logger.info("Fetching collected file from filestore and uploading to MinIO")
        file_data = await fetch_file_from_filestore(
            client_id=collect_artifact_body.velociraptor_id,
            flow_id=flow_id,
            org_id=collect_artifact_body.velociraptor_org,
            agent_id=agent.agent_id,
        )

        # Save metadata to database
        if file_data.get("success"):
            agent_data_store = AgentDataStore(
                agent_id=agent.agent_id,
                velociraptor_id=collect_artifact_body.velociraptor_id,
                artifact_name=collect_artifact_body.artifact_name,
                flow_id=flow_id,
                bucket_name=file_data["bucket_name"],
                object_key=file_data["object_key"],
                file_name=file_data["file_name"],
                content_type=file_data.get("content_type", "application/zip"),
                file_size=file_data["file_size"],
                file_hash=file_data["file_hash"],
                collection_time=datetime.utcnow(),
                status="completed",
            )
            session.add(agent_data_store)
            await session.commit()
            await session.refresh(agent_data_store)

            logger.info(f"Saved artifact metadata to database with ID {agent_data_store.id}")

        return CollectArtifactResponse(
            success=results["success"],
            message=results["message"],
            results=results["results"],
            file_info=file_data if file_data.get("success") else None,
        )

    except HTTPException as he:
        logger.error(f"HTTPException while running artifact collection: {he.detail}")
        raise he
    except Exception as err:
        logger.error(f"Failed to run artifact collection: {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run artifact collection: {err}",
        )


_UNSAFE_FILE_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]+")


def safe_file_component(value: Optional[str], fallback: str = "host") -> str:
    """`value` reduced to one safe file-name component: ``[A-Za-z0-9._-]``, no ``..``, no leading dot."""
    cleaned = _UNSAFE_FILE_CHARACTERS.sub("_", str(value or ""))
    cleaned = re.sub(r"\.{2,}", "_", cleaned).lstrip(".")[:128]
    return cleaned or fallback


def contained_path(directory: str, file_name: str) -> str:
    """``directory/file_name``, refusing any name that would resolve outside `directory`."""
    base = os.path.realpath(directory)
    path = os.path.realpath(os.path.join(base, file_name))
    if os.path.dirname(path) != base:
        raise HTTPException(status_code=400, detail="Invalid download file name")
    return path


async def fetch_file_from_filestore(
    client_id: str,
    flow_id: str,
    org_id: str,
    agent_id: str,  # Add this parameter
    hostname: Optional[str] = None,
    password: Optional[str] = None,
    format: str = "json",
    expand_sparse: bool = False,
) -> dict:
    """
    Fetch a file from Velociraptor's filestore and save it to MinIO.
    First creates a download pack for the flow, then fetches and uploads to MinIO.
    """
    import base64

    from app.data_store.data_store_operations import upload_agent_artifact_file

    # Validate identifier fields (GHSA-5542-j2fc-gqjm); org_id is validated centrally in
    # create_vql_request. Every value below -- including the hostname, which the endpoint
    # itself reports -- is passed as a query variable, never as query text.
    validate_client_id(client_id)
    validate_flow_id(flow_id)

    velociraptor_service = await UniversalService.create("Velociraptor")
    temp_dir = None

    try:
        # If hostname is not provided, fetch it from client metadata
        if not hostname:
            logger.info(f"Fetching hostname for client {client_id}")
            query = create_query("SELECT os_info.hostname AS Hostname FROM clients(client_id=ClientId)")
            client_info = await velociraptor_service.execute_query_async(query, org_id=org_id, env={"ClientId": client_id})

            if client_info.get("results") and len(client_info["results"]) > 0:
                hostname = client_info["results"][0].get("Hostname", client_id)
            else:
                hostname = client_id
                logger.warning(f"Could not fetch hostname, using client_id: {client_id}")

        # Step 1: Create the flow download
        logger.info(f"Creating flow download for client {client_id}, flow {flow_id}")

        download_query_parts = [
            "client_id=ClientId",
            "flow_id=FlowId",
            "wait=true",
            "format=Format",
            f"expand_sparse={'true' if expand_sparse else 'false'}",
        ]
        # The hostname is reported by the endpoint, so it only reaches a file, VFS or object
        # name reduced to a safe component; client_id and flow_id are validated above.
        download_name = f"{safe_file_component(hostname)}-{client_id}-{flow_id}"
        download_env = {
            "ClientId": client_id,
            "FlowId": flow_id,
            "Format": str(format),
            "DownloadName": download_name,
        }

        if password:
            download_query_parts.append("password=Password")
            download_env["Password"] = str(password)

        zip_filename = f"{download_name}.zip"
        download_query_parts.append("name=DownloadName")

        create_download_query = create_query(
            f"SELECT create_flow_download({', '.join(download_query_parts)}) "
            f"FROM scope()",
        )

        logger.info(f"Create download query: {create_download_query}")
        download_result = await velociraptor_service.execute_query_async(create_download_query, org_id=org_id, env=download_env)

        if not download_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create flow download: {download_result.get('message')}",
            )

        logger.info("Flow download created successfully")

        # Step 2: Fetch the file from Velociraptor
        vfs_path = f"downloads/{client_id}/{flow_id}/{zip_filename}"
        logger.info(f"Fetching file from VFS path: {vfs_path}")

        # Save to a private temporary directory first, never the working directory.
        temp_dir = tempfile.mkdtemp(prefix="velociraptor_download_")
        temp_file_path = contained_path(temp_dir, zip_filename)
        offset = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        total_bytes = 0

        with open(temp_file_path, 'wb') as f:
            while True:
                # offset and chunk_size are ints CoPilot computes; the path carries the hostname.
                query = create_query(
                    f"SELECT base64encode(string=read_file("
                    f"accessor='fs', "
                    f"filename=VfsPath, "
                    f"offset={int(offset)}, "
                    f"length={int(chunk_size)})) AS Data "
                    f"FROM scope()",
                )

                result = await velociraptor_service.execute_query_async(query, org_id=org_id, env={"VfsPath": f"/{vfs_path}"})

                if not result.get("success"):
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to fetch file chunk: {result.get('message')}",
                    )

                if not result.get("results") or len(result["results"]) == 0:
                    break

                data = result["results"][0].get("Data")
                if not data:
                    break

                try:
                    decoded_data = base64.b64decode(data)
                    if len(decoded_data) == 0:
                        break

                    f.write(decoded_data)
                    chunk_bytes = len(decoded_data)
                    total_bytes += chunk_bytes
                    offset += chunk_bytes

                    logger.debug(f"Fetched {chunk_bytes} bytes, total: {total_bytes}")

                    if chunk_bytes < chunk_size:
                        break
                except Exception as e:
                    logger.error(f"Failed to decode chunk: {e}")
                    break

        if total_bytes == 0:
            logger.warning(f"No file data found at path: {vfs_path}")
            return {
                "success": False,
                "message": f"No file found at path: {vfs_path}",
                "file_path": None,
                "file_size": 0,
            }

        logger.info(f"Successfully fetched file of size {total_bytes} bytes")

        # Step 3: Upload to MinIO
        logger.info(f"Uploading artifact file to MinIO for agent {agent_id}")
        upload_result = await upload_agent_artifact_file(
            agent_id=agent_id,
            flow_id=flow_id,
            file_path=temp_file_path,
            file_name=zip_filename,
        )

        return {
            "success": True,
            "message": "Successfully fetched file from Velociraptor and uploaded to MinIO",
            **upload_result,
        }

    except HTTPException as he:
        logger.error(f"HTTPException while fetching file: {he.detail}")
        raise he
    except Exception as err:
        logger.error(f"Failed to fetch file from filestore: {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch file from filestore: {err}",
        )
    finally:
        # The downloaded zip never outlives the call, whatever happened.
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


async def start_remote_command(
    run_command_body: RunCommandBody,
    velociraptor_service: Optional[UniversalService] = None,
    literal: bool = False,
) -> str:
    """Start a command (a collection of its shell's artifact) on a client and return its flow id,
    without waiting for it. The command is a query variable, never part of the query text.

    `literal`: the command is passed exactly as written (an approved Talon v2 command, which the
    approver read verbatim), without the VQL unescaping ``/command`` keeps for its clients.
    Any failure is a 500, as ``/command`` has always answered.
    """
    try:
        velociraptor_service = velociraptor_service or await UniversalService.create("Velociraptor")
        run_command_body.artifact_name = getattr(run_command_body.artifact_name, "value", run_command_body.artifact_name)
        # Validate the identifier fields (GHSA-5542-j2fc-gqjm); artifact_name is already an
        # enum. The free-form `command` is passed, like them, as a query variable and is never
        # part of the query text.
        validate_org_id(run_command_body.velociraptor_org)
        validate_client_id(run_command_body.velociraptor_id)
        validate_artifact_name(run_command_body.artifact_name)
        logger.info(f"Running remote command on {run_command_body}")
        query = create_query(VQL_RUN_COMMAND)
        command = run_command_body.command if run_command_body.command is not None else ""
        env = collection_env(
            run_command_body.velociraptor_org,
            run_command_body.velociraptor_id,
            run_command_body.artifact_name,
            # The command used to be written between single quotes; keep its VQL escapes
            # meaning what they meant (see vql_string_literal_value), except for a command
            # passed literally.
            Command=command if literal else vql_string_literal_value(command),
        )
        flow = await velociraptor_service.execute_query_async(query, org_id=run_command_body.velociraptor_org, env=env)
        logger.info(f"Successfully ran artifact collection on {flow}")

        flow_id = started_flow_id(flow)
        logger.info(f"Extracted flow_id: {flow_id}")
        return flow_id
    except Exception as err:
        logger.error(f"Failed to run artifact collection on {run_command_body}: {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run artifact collection on {run_command_body}: {err}",
        )


async def finish_remote_command(
    run_command_body: RunCommandBody,
    flow_id: str,
    velociraptor_service: Optional[UniversalService] = None,
) -> RunCommandResponse:
    """Wait for a started command and read its results: what ``/command`` answers."""
    try:
        velociraptor_service = velociraptor_service or await UniversalService.create("Velociraptor")
        completed = await velociraptor_service.watch_flow_completion_async(flow_id, org_id=run_command_body.velociraptor_org)
        logger.info(f"Successfully watched flow completion on {completed}")

        results = await velociraptor_service.read_collection_results_async(
            client_id=run_command_body.velociraptor_id,
            flow_id=flow_id,
            org_id=run_command_body.velociraptor_org,
            artifact=getattr(run_command_body.artifact_name, "value", run_command_body.artifact_name),
        )

        logger.info(f"Successfully read collection results on {results}")

        return RunCommandResponse(
            success=results["success"],
            message=results["message"],
            results=results["results"],
        )
    except Exception as err:
        logger.error(f"Failed to run artifact collection on {run_command_body}: {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run artifact collection on {run_command_body}: {err}",
        )


async def run_remote_command(run_command_body: RunCommandBody) -> RunCommandResponse:
    """
    Run a remote command on a client: ``start_remote_command``, then ``finish_remote_command``.

    Args:
        run_command_body (RunCommandBody): The body of the request.

    Returns:
        RunCommandResponse: The success status, a message and the command's results.
    """
    velociraptor_service = await UniversalService.create("Velociraptor")
    flow_id = await start_remote_command(run_command_body, velociraptor_service)
    return await finish_remote_command(run_command_body, flow_id, velociraptor_service)


# Built-in Velociraptor quarantine artifacts. Velociraptor 0.76.x+ added a
# "forbidden connection test" step to the built-in Linux artifact that reaches an
# external URL after applying nftables rules; when that test fails in locked-down
# environments the artifact rolls the quarantine back even though the firewall
# rules applied correctly. Velociraptor won't let you override a built-in
# artifact, so operators ship a Custom.Linux.Remediation.Quarantine that drops
# the test. The env vars below let a deployment redirect CoPilot at the custom
# artifact with no code or frontend change. See issue #913.
DEFAULT_LINUX_QUARANTINE_ARTIFACT = "Linux.Remediation.Quarantine"
DEFAULT_WINDOWS_QUARANTINE_ARTIFACT = "Windows.Remediation.Quarantine"


def resolve_quarantine_artifact(requested_artifact) -> str:
    """Map a built-in quarantine artifact name to its configured override.

    The frontend always sends the built-in name (Linux/Windows). A deployment can
    redirect either one to a custom artifact via the
    ``VELOCIRAPTOR_LINUX_QUARANTINE_ARTIFACT`` / ``VELOCIRAPTOR_WINDOWS_QUARANTINE_ARTIFACT``
    env vars. Any other (already-custom) name is returned unchanged, so the
    function is idempotent and safe to call more than once per request. Accepts
    either the ``QuarantineArtifactsEnum`` or a plain string.
    """
    name = requested_artifact.value if hasattr(requested_artifact, "value") else str(requested_artifact)
    if name == DEFAULT_LINUX_QUARANTINE_ARTIFACT:
        return os.environ.get("VELOCIRAPTOR_LINUX_QUARANTINE_ARTIFACT", "").strip() or DEFAULT_LINUX_QUARANTINE_ARTIFACT
    if name == DEFAULT_WINDOWS_QUARANTINE_ARTIFACT:
        return os.environ.get("VELOCIRAPTOR_WINDOWS_QUARANTINE_ARTIFACT", "").strip() or DEFAULT_WINDOWS_QUARANTINE_ARTIFACT
    return name


async def quarantine_host(quarantine_body: QuarantineBody) -> QuarantineResponse:
    """
    Quarantine a host.

    Args:
        quarantine_body (QuarantineBody): The body of the request.

    Returns:
        QuarantineResponse: A dictionary containing the success status and a message.
    """
    velociraptor_service = await UniversalService.create("Velociraptor")
    try:
        # Resolve any configured custom-artifact override (idempotent if the
        # route already resolved it). See issue #913.
        quarantine_body.artifact_name = resolve_quarantine_artifact(quarantine_body.artifact_name)
        quarantine_body.action = quarantine_body.action.value
        # Validate the identifier fields (GHSA-5542-j2fc-gqjm); they are passed as query
        # variables, never as query text.
        validate_org_id(quarantine_body.velociraptor_org)
        validate_client_id(quarantine_body.velociraptor_id)
        validate_artifact_name(quarantine_body.artifact_name)
        query = create_query(VQL_QUARANTINE if quarantine_body.action == "quarantine" else VQL_REMOVE_QUARANTINE)
        env = collection_env(quarantine_body.velociraptor_org, quarantine_body.velociraptor_id, quarantine_body.artifact_name)
        flow = await velociraptor_service.execute_query_async(query, org_id=quarantine_body.velociraptor_org, env=env)
        logger.info(f"Successfully ran artifact collection on {flow}")

        flow_id = extract_flow_id(flow)
        if not flow_id:
            raise HTTPException(status_code=500, detail="Failed to extract flow ID from results")
        logger.info(f"Extracted flow_id: {flow_id}")

        completed = await velociraptor_service.watch_flow_completion_async(flow_id, org_id=quarantine_body.velociraptor_org)
        logger.info(f"Successfully watched flow completion on {completed}")

        results = await velociraptor_service.read_collection_results_async(
            client_id=quarantine_body.velociraptor_id,
            flow_id=flow_id,
            org_id=quarantine_body.velociraptor_org,
            artifact=quarantine_body.artifact_name,
        )

        logger.info(f"Successfully read collection results on {results}")

        return QuarantineResponse(
            success=results["success"],
            message=results["message"],
            results=results["results"],
        )
    except Exception as err:
        logger.error(f"Failed to run artifact collection on {quarantine_body}: {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run artifact collection on {quarantine_body}: {err}",
        )


################# ! ARTIFACT RECOMMENDATION ! #################
async def post_to_copilot_ai_module(data: ArtifactReccomendationRequest) -> ArtifactReccomendationResponse:
    """
    Send a POST request to the copilot-ai-module Docker container.

    Args:
        data (ArtifactReccomendationRequest): The data to send to the copilot-ai-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-ai-module/velociraptor-artifact-recommendation with data: {data.model_dump()}")
    # raise HTTPException(status_code=501, detail="Not Implemented Yet")
    async with httpx.AsyncClient() as client:
        data = await client.post(
            "http://copilot-ai-module/velociraptor-artifact-recommendation",
            json=data.model_dump(),
            timeout=120,
        )
        response_data = data.json()

        if not response_data.get("success"):
            raise HTTPException(
                status_code=400,
                detail=response_data.get("message", "Request to copilot-ai-module was not successful"),
            )
    return ArtifactReccomendationResponse(**data.json())
