from fastapi import HTTPException
from loguru import logger

from app.connectors.velociraptor.schema.artifacts import CollectArtifactResponse
from app.connectors.velociraptor.schema.flows import FlowClientSession
from app.connectors.velociraptor.schema.flows import FlowResponse
from app.connectors.velociraptor.schema.flows import RetrieveFlowRequest
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


async def get_flows(velociraptor_id: str, velociraptor_org: str = "root") -> FlowResponse:
    """
    Get all artifacts from Velociraptor.

    Returns:
        ArtifactsResponse: A dictionary containing the artifacts.
    """
    logger.info("Fetching artifacts from Velociraptor")
    velociraptor_service = await UniversalService.create("Velociraptor")
    query = create_query(
        f"SELECT * FROM flows(client_id='{velociraptor_id}')",
    )
    all_flows = velociraptor_service.execute_query(query, org_id=velociraptor_org)
    logger.info(f"all_flows: {all_flows}")
    flows = [FlowClientSession(**flow) for flow in all_flows["results"]]
    logger.info(f"flows: {flows}")
    try:
        if all_flows["success"]:
            flows = [FlowClientSession(**flow) for flow in all_flows["results"]]
            logger.info(f"flows: {flows}")
            return FlowResponse(
                success=True,
                message="All flows retrieved.",
                results=flows,
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve flows from Velociraptor: {all_flows['message']}",
            )
    except Exception as e:
        logger.error(f"Failed to retrieve flows from Velociraptor: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve flows from Velociraptor: {e}",
        )


async def get_flow(retrieve_flow_request: RetrieveFlowRequest, velociraptor_org: str = "root"):
    """
    Get all artifacts from Velociraptor.

    Returns:
        ArtifactsResponse: A dictionary containing the artifacts.
    """
    logger.info("Fetching artifacts from Velociraptor")
    velociraptor_service = await UniversalService.create("Velociraptor")
    query = create_query(
        f"SELECT * FROM flow_results(client_id='{retrieve_flow_request.client_id}', flow_id='{retrieve_flow_request.session_id}')",
    )
    flow_results = velociraptor_service.execute_query(query, org_id=velociraptor_org)
    logger.info(f"flow_results: {flow_results}")
    try:
        if flow_results["success"]:
            return CollectArtifactResponse(
                success=flow_results["success"],
                message=flow_results["message"],
                results=flow_results["results"],
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve flow results from Velociraptor: {flow_results['message']}",
            )
    except Exception as e:
        logger.error(f"Failed to retrieve flow results from Velociraptor: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve flow results from Velociraptor: {e}",
        )
