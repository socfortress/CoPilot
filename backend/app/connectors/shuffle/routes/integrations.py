from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.shuffle.schema.integrations import ExecuteWorkflowRequest
from app.connectors.shuffle.schema.integrations import IntegrationRequest
from app.connectors.shuffle.schema.integrations import ShuffleConnectorCredentialsResponse
from app.connectors.shuffle.services.integrations import execute_integration
from app.connectors.shuffle.services.integrations import execute_workflow
from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db

shuffle_integrations_router = APIRouter()


@shuffle_integrations_router.get(
    "/credentials",
    response_model=ShuffleConnectorCredentialsResponse,
    description="Return the Shuffle connector base URL + API key for the embedded MCP picker.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_shuffle_connector_credentials(
    session: AsyncSession = Depends(get_db),
) -> ShuffleConnectorCredentialsResponse:
    """Read the Shuffle row from the deployment-wide `connectors` table and
    return just the URL + API key. The frontend feeds these into
    `<ShuffleMCP>` (and `<TryMcpSection>`) so the embed can fetch the
    customer's private/authenticated apps directly from Shuffle's backend.
    The same data is already exposed to admin/analyst users via the generic
    `GET /connectors/{id}` route — this endpoint just narrows the response
    to what the embeds actually need."""
    info = await get_connector_info_from_db("Shuffle", session)
    if not info:
        raise HTTPException(status_code=404, detail="Shuffle connector is not configured.")
    api_key = info.get("connector_api_key")
    base_url = info.get("connector_url")
    if not api_key or not base_url:
        raise HTTPException(
            status_code=400,
            detail="Shuffle connector is missing connector_url or connector_api_key.",
        )
    return ShuffleConnectorCredentialsResponse(
        success=True,
        message="Shuffle connector credentials retrieved.",
        base_url=base_url,
        api_key=api_key,
    )


@shuffle_integrations_router.post(
    "/execute",
    description="Execute a Shuffle Integration.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def execute_integration_route(request: IntegrationRequest):
    """
    Execute a workflow.

    Args:
        request (IntegrationRequest): The request object containing the workflow ID.

    Returns:
        dict: The response containing the execution ID.
    """
    logger.info("Executing workflow")
    return await execute_integration(request)


@shuffle_integrations_router.post(
    "/invoke-workflow",
    description="Invoke a Shuffle Workflow.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def invoke_workflow_route(request: ExecuteWorkflowRequest):
    """
    Execute a workflow.

    Args:
        request (IntegrationRequest): The request object containing the workflow ID.

    Returns:
        dict: The response containing the execution ID.
    """
    logger.info("Executing workflow")
    return await execute_workflow(request)
