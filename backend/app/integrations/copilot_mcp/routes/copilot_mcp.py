from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.routes.auth import AuthHandler
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPQueryRequest, MCPQueryResponse

copilot_mcp_router = APIRouter()
auth_handler = AuthHandler()


@copilot_mcp_router.post(
    "/query",
    description="Get all disabled rules",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def query_mcp(
    request: MCPQueryRequest
) -> MCPQueryResponse:
    """
    Process a query to the MCP agent and return structured response.
    """
    logger.info("Processing MCP query.")

    # Here you would typically call the MCP agent with the request data
    # For now, we will return a mock response
    response = MCPQueryResponse(
        message="MCP query executed successfully",
        success=True,
        result="### MCP Agent Response\n\n- **Query Processed**: Successfully\n- **Agent Status**: Active\n- **Response Type**: Mock Response\n- **Processing Time**: < 1ms\n\n### Analysis\nThis is a mock response from the MCP agent. The agent analyzed the incoming query and generated this structured response. In a production environment, this would contain actual analysis results from the MCP agent processing.",
        structured_result={
            "response": "### MCP Agent Response\n\n- **Query Processed**: Successfully\n- **Agent Status**: Active\n- **Response Type**: Mock Response\n- **Processing Time**: < 1ms\n\n### Analysis\nThis is a mock response from the MCP agent. The agent analyzed the incoming query and generated this structured response. In a production environment, this would contain actual analysis results from the MCP agent processing.",
            "thinking_process": "1. Received the MCP query request with the specified parameters.\n2. Analyzed the query structure and determined the appropriate response format.\n3. Generated a mock response that demonstrates the expected output structure for future MCP agent integration."
        },
        execution_time=0.001
    )

    return response
