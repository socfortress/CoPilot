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


def create_query(query: str) -> str:
    """
    Create a query string.

    Args:
        query (str): The query to be executed.

    Returns:
        str: The created query string.
    """
    return query


def get_artifact_key(analyzer_body: CollectArtifactBody) -> str:
    """
    Construct the artifact key.

    Args:
        analyzer_body: The collector body with artifact details

    Returns:
        str: The constructed artifact key.
    """
    action = getattr(analyzer_body, "action", None)
    command = getattr(analyzer_body, "command", None)
    parameters = getattr(analyzer_body, "parameters", None)

    if action == "quarantine":
        return (
            f'collect_client(org_id="{analyzer_body.velociraptor_org}", client_id="{analyzer_body.velociraptor_id}", '
            f'artifacts=["{analyzer_body.artifact_name}"], '
            f"spec=dict(`{analyzer_body.artifact_name}`=dict()))"
        )
    elif action == "remove_quarantine":
        return (
            f'collect_client(org_id="{analyzer_body.velociraptor_org}", client_id="{analyzer_body.velociraptor_id}", '
            f'artifacts=["{analyzer_body.artifact_name}"], '
            f'spec=dict(`{analyzer_body.artifact_name}`=dict(`RemovePolicy`="Y")))'
        )
    elif command is not None:
        return (
            f"collect_client(org_id='{analyzer_body.velociraptor_org}', client_id='{analyzer_body.velociraptor_id}', "
            f"urgent=true, artifacts=['{analyzer_body.artifact_name}'], "
            f"env=dict(Command='{analyzer_body.command}'))"
        )
    elif parameters is not None:
        # Parameters are provided, will be included in the query
        return (
            f"collect_client(org_id='{analyzer_body.velociraptor_org}', client_id='{analyzer_body.velociraptor_id}', "
            f"artifacts=['{analyzer_body.artifact_name}'])"
        )
    else:
        return (
            f"collect_client(org_id='{analyzer_body.velociraptor_org}', client_id='{analyzer_body.velociraptor_id}', "
            f"artifacts=['{analyzer_body.artifact_name}'])"
        )


async def get_artifacts() -> ArtifactsResponse:
    """
    Get all artifacts from Velociraptor.

    Returns:
        ArtifactsResponse: A dictionary containing the artifacts.
    """
    logger.info("Fetching artifacts from Velociraptor")
    velociraptor_service = await UniversalService.create("Velociraptor")
    query = create_query("SELECT name,description,parameters FROM artifact_definitions()")
    all_artifacts = velociraptor_service.execute_query(query)
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


async def get_artifact_by_name(artifact_name: str) -> ArtifactsResponse:
    """
    Get a specific artifact by name from Velociraptor.

    Args:
        artifact_name (str): The name of the artifact to retrieve.

    Returns:
        ArtifactsResponse: A response containing the specific artifact.
    """
    logger.info(f"Fetching artifact '{artifact_name}' from Velociraptor")
    velociraptor_service = await UniversalService.create("Velociraptor")

    # Query for a specific artifact by name
    query = create_query(f"SELECT name,description,parameters FROM artifact_definitions() WHERE name = '{artifact_name}'")
    artifact_result = velociraptor_service.execute_query(query)

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


async def validate_artifact_parameters(
    artifact_name: str,
    provided_parameters: Optional[Dict[str, Union[str, List[ParameterKeyValue]]]],
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

    # Fetch the artifact details
    artifact_response = await get_artifact_by_name(artifact_name)

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


async def run_artifact_collection(
    collect_artifact_body: CollectArtifactBody,
) -> CollectArtifactResponse:
    """
    Run an artifact collection on a client with optional parameters.

    Args:
        collect_artifact_body: The body of the request with optional parameters.

    Returns:
        CollectArtifactResponse: A dictionary containing the success status, message and results.
    """
    velociraptor_service = await UniversalService.create("Velociraptor")
    try:
        # Build the query dynamically based on whether parameters are provided
        parameters = getattr(collect_artifact_body, "parameters", None)

        if parameters:
            # Velociraptor expects parameters in a very specific format
            # For the "env" parameter, we need to construct a dict
            if "env" in parameters and isinstance(parameters["env"], list):
                env_dict = {}
                for item in parameters["env"]:
                    env_dict[item.key] = item.value

                # Format the query with proper VQL syntax
                query = create_query(
                    f"SELECT collect_client("
                    f"org_id='{collect_artifact_body.velociraptor_org}', "
                    f"client_id='{collect_artifact_body.velociraptor_id}', "
                    f"artifacts=['{collect_artifact_body.artifact_name}'], "
                    f"env=dict(",
                )

                # Add each environment variable as a key-value pair
                env_parts = []
                for key, value in env_dict.items():
                    # Escape any single quotes in the values
                    escaped_value = value.replace("'", "\\'")
                    env_parts.append(f"`{key}`='{escaped_value}'")

                query += ", ".join(env_parts)
                query += ")) FROM scope()"
            else:
                # Handle other types of parameters
                query = create_query(
                    f"SELECT collect_client("
                    f"org_id='{collect_artifact_body.velociraptor_org}', "
                    f"client_id='{collect_artifact_body.velociraptor_id}', "
                    f"artifacts=['{collect_artifact_body.artifact_name}']",
                )

                # Add other parameters if needed
                for param_key, param_value in parameters.items():
                    if isinstance(param_value, str):
                        query += f", `{param_key}`='{param_value}'"

                query += ") FROM scope()"
        else:
            # Original query without parameters
            query = create_query(
                f"SELECT collect_client("
                f"org_id='{collect_artifact_body.velociraptor_org}', "
                f"client_id='{collect_artifact_body.velociraptor_id}', "
                f"artifacts=['{collect_artifact_body.artifact_name}']) "
                f"FROM scope()",
            )

        logger.info(f"Running artifact collection with query: {query}")
        flow = velociraptor_service.execute_query(query, org_id=collect_artifact_body.velociraptor_org)
        logger.info(f"Successfully ran artifact collection on {flow}")

        # Check if results are available
        if not flow.get("results") or len(flow["results"]) == 0:
            logger.error("No results returned from query execution")
            raise HTTPException(
                status_code=500,
                detail="Query execution did not return any results",
            )

        # Instead of relying on get_artifact_key, extract the flow_id directly from results
        # by checking all keys in the first result for a flow_id
        result_dict = flow["results"][0]
        flow_id = None

        # Look for any key that has a flow_id in its value
        for key, value in result_dict.items():
            if isinstance(value, dict) and "flow_id" in value:
                flow_id = value["flow_id"]
                logger.debug(f"Found flow_id {flow_id} in key: {key}")
                break

        if not flow_id:
            logger.error(f"Could not find flow_id in results: {result_dict}")
            raise HTTPException(
                status_code=500,
                detail="Failed to extract flow ID from results",
            )

        logger.info(f"Extracted flow_id: {flow_id}")

        completed = velociraptor_service.watch_flow_completion(flow_id, org_id=collect_artifact_body.velociraptor_org)
        logger.info(f"Successfully watched flow completion on {completed}")

        results = velociraptor_service.read_collection_results(
            client_id=collect_artifact_body.velociraptor_id,
            flow_id=flow_id,
            org_id=collect_artifact_body.velociraptor_org,
            artifact=collect_artifact_body.artifact_name,
        )

        logger.info(f"Successfully read collection results on {results}")

        return CollectArtifactResponse(
            success=results["success"],
            message=results["message"],
            results=results["results"],
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

        # Build the query with proper VQL syntax
        query = create_query(
            f"SELECT collect_client("
            f"org_id='{collect_artifact_body.velociraptor_org}', "
            f"client_id='{collect_artifact_body.velociraptor_id}', "
            f"artifacts=['{collect_artifact_body.artifact_name}'], "
            f"spec=dict(`{collect_artifact_body.artifact_name}`=dict("
            f"`collectionSpec`='{collect_artifact_body.file}', "
            f"`Root`='{collect_artifact_body.root_disk}'"
            f"))) "
            f"FROM scope()",
        )

        logger.info(f"Query: {query}")
        flow = velociraptor_service.execute_query(query, org_id=collect_artifact_body.velociraptor_org)
        logger.info(f"Successfully ran artifact collection on {flow}")

        # Check if results are available
        if not flow.get("results") or len(flow["results"]) == 0:
            logger.error("No results returned from query execution")
            raise HTTPException(
                status_code=500,
                detail="Query execution did not return any results",
            )

        # Extract flow_id from results
        result_dict = flow["results"][0]
        flow_id = None

        for key, value in result_dict.items():
            if isinstance(value, dict) and "flow_id" in value:
                flow_id = value["flow_id"]
                logger.debug(f"Found flow_id {flow_id} in key: {key}")
                break

        if not flow_id:
            logger.error(f"Could not find flow_id in results: {result_dict}")
            raise HTTPException(
                status_code=500,
                detail="Failed to extract flow ID from results",
            )

        logger.info(f"Extracted flow_id: {flow_id}")

        completed = velociraptor_service.watch_flow_completion(flow_id, org_id=collect_artifact_body.velociraptor_org)
        logger.info(f"Successfully watched flow completion on {completed}")

        results = velociraptor_service.read_collection_results(
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
    import os

    from app.data_store.data_store_operations import upload_agent_artifact_file

    velociraptor_service = await UniversalService.create("Velociraptor")

    try:
        # If hostname is not provided, fetch it from client metadata
        if not hostname:
            logger.info(f"Fetching hostname for client {client_id}")
            query = create_query(
                f"SELECT os_info.hostname AS Hostname "
                f"FROM clients(client_id='{client_id}')",
            )
            client_info = velociraptor_service.execute_query(query, org_id=org_id)

            if client_info.get("results") and len(client_info["results"]) > 0:
                hostname = client_info["results"][0].get("Hostname", client_id)
            else:
                hostname = client_id
                logger.warning(f"Could not fetch hostname, using client_id: {client_id}")

        # Step 1: Create the flow download
        logger.info(f"Creating flow download for client {client_id}, flow {flow_id}")

        download_query_parts = [
            f"client_id='{client_id}'",
            f"flow_id='{flow_id}'",
            "wait=true",
            f"format='{format}'",
            f"expand_sparse={str(expand_sparse).lower()}",
        ]

        if password:
            download_query_parts.append(f"password='{password}'")

        zip_filename = f"{hostname}-{client_id}-{flow_id}.zip"
        download_query_parts.append(f"name='{hostname}-{client_id}-{flow_id}'")

        create_download_query = create_query(
            f"SELECT create_flow_download({', '.join(download_query_parts)}) "
            f"FROM scope()",
        )

        logger.info(f"Create download query: {create_download_query}")
        download_result = velociraptor_service.execute_query(create_download_query, org_id=org_id)

        if not download_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create flow download: {download_result.get('message')}",
            )

        logger.info("Flow download created successfully")

        # Step 2: Fetch the file from Velociraptor
        vfs_path = f"downloads/{client_id}/{flow_id}/{zip_filename}"
        logger.info(f"Fetching file from VFS path: {vfs_path}")

        # Save to temporary location first
        temp_file_path = os.path.join(os.getcwd(), zip_filename)
        offset = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        total_bytes = 0

        with open(temp_file_path, 'wb') as f:
            while True:
                query = create_query(
                    f"SELECT base64encode(string=read_file("
                    f"accessor='fs', "
                    f"filename='/{vfs_path}', "
                    f"offset={offset}, "
                    f"length={chunk_size})) AS Data "
                    f"FROM scope()",
                )

                result = velociraptor_service.execute_query(query, org_id=org_id)

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
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
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

        # Remove temporary file
        os.remove(temp_file_path)
        logger.info(f"Removed temporary file {temp_file_path}")

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


async def run_remote_command(run_command_body: RunCommandBody) -> RunCommandResponse:
    """
    Run a remote command on a client.

    Args:
        run_analyzer_body (RunAnalyzerBody): The body of the request.

    Returns:
        RunAnalyzerResponse: A dictionary containing the success status and a message.
    """
    velociraptor_service = await UniversalService.create("Velociraptor")
    try:
        run_command_body.artifact_name = run_command_body.artifact_name.value
        logger.info(f"Running remote command on {run_command_body}")
        query = create_query(
            (
                f"SELECT collect_client(org_id='{run_command_body.velociraptor_org}', client_id='{run_command_body.velociraptor_id}', "
                f"urgent=true, artifacts=['{run_command_body.artifact_name}'], "
                f"env=dict(Command='{run_command_body.command}')) "
                "FROM scope()"
            ),
        )
        flow = velociraptor_service.execute_query(query, org_id=run_command_body.velociraptor_org)
        logger.info(f"Successfully ran artifact collection on {flow}")

        artifact_key = get_artifact_key(analyzer_body=run_command_body)

        flow_id = flow["results"][0][artifact_key]["flow_id"]
        logger.info(f"Extracted flow_id: {flow_id}")

        completed = velociraptor_service.watch_flow_completion(flow_id, org_id=run_command_body.velociraptor_org)
        logger.info(f"Successfully watched flow completion on {completed}")

        results = velociraptor_service.read_collection_results(
            client_id=run_command_body.velociraptor_id,
            flow_id=flow_id,
            org_id=run_command_body.velociraptor_org,
            artifact=run_command_body.artifact_name,
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
        quarantine_body.artifact_name = quarantine_body.artifact_name.value
        quarantine_body.action = quarantine_body.action.value
        if quarantine_body.action == "quarantine":
            query = create_query(
                (
                    f'SELECT collect_client(org_id="{quarantine_body.velociraptor_org}", client_id="{quarantine_body.velociraptor_id}", '
                    f'artifacts=["{quarantine_body.artifact_name}"], '
                    f"spec=dict(`{quarantine_body.artifact_name}`=dict())) "
                    "FROM scope()"
                ),
            )
        else:
            query = create_query(
                (
                    f'SELECT collect_client(org_id="{quarantine_body.velociraptor_org}", client_id="{quarantine_body.velociraptor_id}", '
                    f'artifacts=["{quarantine_body.artifact_name}"], '
                    f'spec=dict(`{quarantine_body.artifact_name}`=dict(`RemovePolicy`="Y"))) '
                    "FROM scope()"
                ),
            )
        flow = velociraptor_service.execute_query(query, org_id=quarantine_body.velociraptor_org)
        logger.info(f"Successfully ran artifact collection on {flow}")

        artifact_key = get_artifact_key(analyzer_body=quarantine_body)

        flow_id = flow["results"][0][artifact_key]["flow_id"]
        logger.info(f"Extracted flow_id: {flow_id}")

        completed = velociraptor_service.watch_flow_completion(flow_id, org_id=quarantine_body.velociraptor_org)
        logger.info(f"Successfully watched flow completion on {completed}")

        results = velociraptor_service.read_collection_results(
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
    logger.info(f"Sending POST request to http://copilot-ai-module/velociraptor-artifact-recommendation with data: {data.dict()}")
    # raise HTTPException(status_code=501, detail="Not Implemented Yet")
    async with httpx.AsyncClient() as client:
        data = await client.post(
            "http://copilot-ai-module/velociraptor-artifact-recommendation",
            json=data.dict(),
            timeout=120,
        )
        response_data = data.json()

        if not response_data.get("success"):
            raise HTTPException(
                status_code=400,
                detail=response_data.get("message", "Request to copilot-ai-module was not successful"),
            )
    return ArtifactReccomendationResponse(**data.json())
