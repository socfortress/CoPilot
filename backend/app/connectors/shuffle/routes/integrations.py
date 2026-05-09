import httpx
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
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

# Hop-by-hop headers MUST NOT be forwarded across a proxy boundary
# (RFC 7230 §6.1). We strip them in both directions so the response we
# return doesn't carry stale framing/encoding metadata that the upstream
# server already consumed.
_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    # Stripped for our case specifically: httpx already decoded the body,
    # so re-emitting these would mislead the browser into trying to decode
    # again or expect a different framing.
    "content-encoding",
    "content-length",
}


@shuffle_integrations_router.get(
    "/credentials",
    response_model=ShuffleConnectorCredentialsResponse,
    description="Return the Shuffle connector base URL + API key for the embedded MCP picker.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_shuffle_connector_credentials(
    session: AsyncSession = Depends(get_db),
) -> ShuffleConnectorCredentialsResponse:
    """Return the Shuffle creds the frontend needs to talk to our
    same-origin proxy below. We expose the deployment-wide
    `connector_api_key` (the embed sends it as Bearer auth on every
    proxied request — the proxy validates it matches the stored key
    before forwarding) and `base_url='/api/shuffle/proxy'` (so the
    package never crosses origins). The real Shuffle URL stays
    server-side; the browser only ever talks to CoPilot."""
    info = await get_connector_info_from_db("Shuffle", session)
    if not info:
        raise HTTPException(status_code=404, detail="Shuffle connector is not configured.")
    api_key = info.get("connector_api_key")
    real_base_url = info.get("connector_url")
    if not api_key or not real_base_url:
        raise HTTPException(
            status_code=400,
            detail="Shuffle connector is missing connector_url or connector_api_key.",
        )
    return ShuffleConnectorCredentialsResponse(
        success=True,
        message="Shuffle connector credentials retrieved.",
        # Frontend uses this as the embed's `apiBaseUrl` — all browser-side
        # XHR is same-origin via the proxy below. Path must match the
        # proxy route's actual mount point (the integrations router is
        # itself prefixed at `/shuffle/integrations`).
        base_url="/api/shuffle/integrations/proxy",
        api_key=api_key,
    )


@shuffle_integrations_router.api_route(
    "/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    description=(
        "Same-origin proxy for `<ShuffleMCP>` / `<TryMcpSection>` XHR. The "
        "browser-side embed configures its `apiBaseUrl` at this path and "
        "sends the deployment-wide `connector_api_key` as Bearer auth. We "
        "validate that against the stored connector record, then forward "
        "the request to `connector_url + path` server-side. Avoids the "
        "CORS preflight rejection from hosted Shuffle backends."
    ),
)
async def shuffle_proxy(
    path: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Response:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer authorization for Shuffle proxy.")
    token = auth.removeprefix("Bearer ")

    info = await get_connector_info_from_db("Shuffle", session)
    if not info:
        raise HTTPException(status_code=404, detail="Shuffle connector is not configured.")
    expected = info.get("connector_api_key")
    real_base_url = (info.get("connector_url") or "").rstrip("/")
    if not expected or not real_base_url:
        raise HTTPException(
            status_code=400,
            detail="Shuffle connector is missing connector_url or connector_api_key.",
        )
    # Constant-time-ish equality is overkill here (this isn't a public
    # endpoint and the token is the same one the caller fetched seconds
    # ago via /credentials), but cheap.
    if token != expected:
        raise HTTPException(status_code=403, detail="Shuffle proxy token does not match connector key.")

    target = f"{real_base_url}/{path}"
    forward_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP_HEADERS and k.lower() != "host"
    }
    body = await request.body()

    logger.info(f"Shuffle proxy → {request.method} {target}")
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            upstream = await client.request(
                method=request.method,
                url=target,
                params=request.query_params,
                content=body,
                headers=forward_headers,
            )
    except httpx.RequestError as e:
        logger.error(f"Shuffle proxy upstream error: {e}")
        raise HTTPException(status_code=502, detail=f"Upstream Shuffle request failed: {e}")

    response_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
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
