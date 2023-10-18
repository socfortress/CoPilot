from fastapi import HTTPException
from loguru import logger

from app.connectors.velociraptor.schema.artifacts import Artifacts
from app.connectors.velociraptor.schema.artifacts import ArtifactsResponse
from app.connectors.velociraptor.schema.artifacts import CollectArtifactBody
from app.connectors.velociraptor.schema.artifacts import CollectArtifactResponse
from app.connectors.velociraptor.schema.artifacts import QuarantineBody
from app.connectors.velociraptor.schema.artifacts import QuarantineResponse
from app.connectors.velociraptor.schema.artifacts import RunCommandBody
from app.connectors.velociraptor.schema.artifacts import RunCommandResponse
from app.connectors.velociraptor.utils.universal import UniversalService

universal_service = UniversalService()


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
        return f'collect_client(client_id="{analyzer_body.velociraptor_id}", artifacts=["{analyzer_body.artifact_name}"], spec=dict(`{analyzer_body.artifact_name}`=dict()))'
    elif action == "remove_quarantine":
        return f'collect_client(client_id="{analyzer_body.velociraptor_id}", artifacts=["{analyzer_body.artifact_name}"], spec=dict(`{analyzer_body.artifact_name}`=dict(`RemovePolicy`="Y")))'
    elif command is not None:
        return f"collect_client(client_id='{analyzer_body.velociraptor_id}', urgent=true, artifacts=['{analyzer_body.artifact_name}'], env=dict(Command='{analyzer_body.command}'))"
    else:
        return f"collect_client(client_id='{analyzer_body.velociraptor_id}', artifacts=['{analyzer_body.artifact_name}'])"


def get_artifacts() -> ArtifactsResponse:
    """
    Get all artifacts from Velociraptor.

    Returns:
        ArtifactsResponse: A dictionary containing the artifacts.
    """
    logger.info("Fetching artifacts from Velociraptor")
    query = create_query("SELECT name,description FROM artifact_definitions()")
    all_artifacts = universal_service.execute_query(query)
    if all_artifacts["success"]:
        artifacts = [Artifacts(**artifact) for artifact in all_artifacts["results"]]
        return ArtifactsResponse(success=True, message="All artifacts retrieved", artifacts=artifacts)
    else:
        raise HTTPException(status_code=500, detail=f"Failed to get all artifacts: {all_artifacts['message']}")


def run_artifact_collection(collect_artifact_body: CollectArtifactBody) -> CollectArtifactResponse:
    """
    Run an artifact collection on a client.

    Args:
        run_analyzer_body (RunAnalyzerBody): The body of the request.

    Returns:
        RunAnalyzerResponse: A dictionary containing the success status and a message.
    """
    try:
        query = create_query(
            f"SELECT collect_client(client_id='{collect_artifact_body.velociraptor_id}', artifacts=['{collect_artifact_body.artifact_name}']) FROM scope()",
        )
        flow = universal_service.execute_query(query)
        logger.info(f"Successfully ran artifact collection on {flow}")

        artifact_key = get_artifact_key(analyzer_body=collect_artifact_body)

        flow_id = flow["results"][0][artifact_key]["flow_id"]
        logger.info(f"Extracted flow_id: {flow_id}")

        completed = universal_service.watch_flow_completion(flow_id)
        logger.info(f"Successfully watched flow completion on {completed}")

        results = universal_service.read_collection_results(
            client_id=collect_artifact_body.velociraptor_id,
            flow_id=flow_id,
            artifact=collect_artifact_body.artifact_name,
        )

        logger.info(f"Successfully read collection results on {results}")

        return CollectArtifactResponse(success=results["success"], message=results["message"], results=results["results"])
    except Exception as err:
        logger.error(f"Failed to run artifact collection on {collect_artifact_body}: {err}")
        raise HTTPException(status_code=500, detail=f"Failed to run artifact collection on {collect_artifact_body}: {err}")


def run_remote_command(run_command_body: RunCommandBody) -> RunCommandResponse:
    """
    Run a remote command on a client.

    Args:
        run_analyzer_body (RunAnalyzerBody): The body of the request.

    Returns:
        RunAnalyzerResponse: A dictionary containing the success status and a message.
    """
    try:
        run_command_body.artifact_name = run_command_body.artifact_name.value
        logger.info(f"Running remote command on {run_command_body}")
        query = create_query(
            f"SELECT collect_client(client_id='{run_command_body.velociraptor_id}', urgent=true, artifacts=['{run_command_body.artifact_name}'], env=dict(Command='{run_command_body.command}')) "
            "FROM scope()",
        )
        flow = universal_service.execute_query(query)
        logger.info(f"Successfully ran artifact collection on {flow}")

        artifact_key = get_artifact_key(analyzer_body=run_command_body)

        flow_id = flow["results"][0][artifact_key]["flow_id"]
        logger.info(f"Extracted flow_id: {flow_id}")

        completed = universal_service.watch_flow_completion(flow_id)
        logger.info(f"Successfully watched flow completion on {completed}")

        results = universal_service.read_collection_results(
            client_id=run_command_body.velociraptor_id,
            flow_id=flow_id,
            artifact=run_command_body.artifact_name,
        )

        logger.info(f"Successfully read collection results on {results}")

        return RunCommandResponse(success=results["success"], message=results["message"], results=results["results"])
    except Exception as err:
        logger.error(f"Failed to run artifact collection on {run_command_body}: {err}")
        raise HTTPException(status_code=500, detail=f"Failed to run artifact collection on {run_command_body}: {err}")


def quarantine_host(quarantine_body: QuarantineBody) -> QuarantineResponse:
    """
    Quarantine a host.

    Args:
        quarantine_body (QuarantineBody): The body of the request.

    Returns:
        QuarantineResponse: A dictionary containing the success status and a message.
    """
    try:
        quarantine_body.artifact_name = quarantine_body.artifact_name.value
        quarantine_body.action = quarantine_body.action.value
        if quarantine_body.action == "quarantine":
            query = create_query(
                f'SELECT collect_client(client_id="{quarantine_body.velociraptor_id}", artifacts=["{quarantine_body.artifact_name}"], spec=dict(`{quarantine_body.artifact_name}`=dict())) FROM scope()',
            )
        else:
            query = create_query(
                f'SELECT collect_client(client_id="{quarantine_body.velociraptor_id}", artifacts=["{quarantine_body.artifact_name}"], spec=dict(`{quarantine_body.artifact_name}`=dict(`RemovePolicy`="Y"))) FROM scope()',
            )
        flow = universal_service.execute_query(query)
        logger.info(f"Successfully ran artifact collection on {flow}")

        artifact_key = get_artifact_key(analyzer_body=quarantine_body)

        flow_id = flow["results"][0][artifact_key]["flow_id"]
        logger.info(f"Extracted flow_id: {flow_id}")

        completed = universal_service.watch_flow_completion(flow_id)
        logger.info(f"Successfully watched flow completion on {completed}")

        results = universal_service.read_collection_results(
            client_id=quarantine_body.velociraptor_id,
            flow_id=flow_id,
            artifact=quarantine_body.artifact_name,
        )

        logger.info(f"Successfully read collection results on {results}")

        return QuarantineResponse(success=results["success"], message=results["message"], results=results["results"])
    except Exception as err:
        logger.error(f"Failed to run artifact collection on {quarantine_body}: {err}")
        raise HTTPException(status_code=500, detail=f"Failed to run artifact collection on {quarantine_body}: {err}")


######################## KEEP
# class ArtifactsService:
#     def delete_client(self, client_id: str) -> dict:
#         """
#         Delete a client from Velociraptor.

#         Args:
#             client_id (str): The ID of the client.

#         Returns:
#             dict: A dictionary with the success status and a message.
#         """
#         try:
#             query = self._create_query(
#                 f"SELECT collect_client(client_id='server', artifacts=['Server.Utils.DeleteClient'], env=dict(ClientIdList='{client_id}',ReallyDoIt='Y')) "
#                 "FROM scope()",
#             )

#             flow = self.universal_service.execute_query(query)
#             logger.info(f"Successfully ran artifact collection on {flow}")

#             # artifact_key = f"collect_client(client_id='server', artifacts=['Server.Utils.DeleteClient'], env=dict(ClientIdList='{client_id}',ReallyDoIt='Y'))"
#             flow_id = flow["results"][0][query]["flow_id"]
#             logger.info(f"Extracted flow_id: {flow_id}")

#             completed = self.universal_service.watch_flow_completion(flow_id)
#             logger.info(f"Successfully watched flow completion on {completed}")

#             return {
#                 "message": f"Successfully deleted client {client_id}",
#                 "success": True,
#             }
#         except Exception as err:
#             logger.error(f"Failed to delete client {client_id}: {err}")
#             return {
#                 "message": f"Failed to delete client {client_id}",
#                 "success": False,
#             }
