import httpx
from fastapi import HTTPException
from loguru import logger

from app.connectors.velociraptor.schema.artifacts import ArtifactReccomendationRequest
from app.connectors.velociraptor.schema.artifacts import ArtifactReccomendationResponse
from app.connectors.velociraptor.schema.artifacts import Artifacts
from app.connectors.velociraptor.schema.artifacts import ArtifactsResponse
from app.connectors.velociraptor.schema.artifacts import CollectArtifactBody
from app.connectors.velociraptor.schema.artifacts import CollectArtifactResponse
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
        client_id (str): The ID of the client.
        artifact (str): The name of the artifact.
        command (str): The command that was run, if applicable.
        quarantined (bool): Whether the client is quarantined or not.

    Returns:
        str: The constructed artifact key.
    """
    action = getattr(analyzer_body, "action", None)
    command = getattr(analyzer_body, "command", None)

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
    query = create_query("SELECT name,description FROM artifact_definitions()")
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


async def run_artifact_collection(
    collect_artifact_body: CollectArtifactBody,
) -> CollectArtifactResponse:
    """
    Run an artifact collection on a client.

    Args:
        run_analyzer_body (RunAnalyzerBody): The body of the request.

    Returns:
        RunAnalyzerResponse: A dictionary containing the success status and a message.
    """
    velociraptor_service = await UniversalService.create("Velociraptor")
    try:
        # ! Can specify org_id with org_id='OL680' ! #
        query = create_query(
            (
                f"SELECT collect_client("
                f"org_id='{collect_artifact_body.velociraptor_org}', "
                f"client_id='{collect_artifact_body.velociraptor_id}', "
                f"artifacts=['{collect_artifact_body.artifact_name}']) "
                f"FROM scope()"
            ),
        )
        flow = velociraptor_service.execute_query(query, org_id=collect_artifact_body.velociraptor_org)
        logger.info(f"Successfully ran artifact collection on {flow}")

        artifact_key = get_artifact_key(analyzer_body=collect_artifact_body)

        flow_id = flow["results"][0][artifact_key]["flow_id"]
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
