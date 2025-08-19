from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.routes.auth import AuthHandler
from app.db.db_session import get_db
from app.integrations.copilot_mcp.schema.copilot_mcp import AvailableMCPServersResponse
from app.integrations.copilot_mcp.schema.copilot_mcp import ExampleQuestionsResponse
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPQueryRequest
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPQueryResponse
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPServerType
from app.integrations.copilot_mcp.services.copilot_mcp import MCPService
from app.integrations.copilot_mcp.services.example_questions import (
    ExampleQuestionsService,
)
from app.middleware.license import get_license
from app.middleware.license import is_feature_enabled

copilot_mcp_router = APIRouter()
auth_handler = AuthHandler()


@copilot_mcp_router.get(
    "/servers",
    response_model=AvailableMCPServersResponse,
    description="Get list of available MCP servers",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_available_mcp_servers() -> AvailableMCPServersResponse:
    """
    Retrieve a list of all available MCP servers with their capabilities.

    This endpoint provides information about all MCP servers that can be
    queried, including their descriptions and capabilities to help users
    understand what each server can do.

    Returns:
        AvailableMCPServersResponse: List of available MCP servers with metadata
    """
    logger.info("Fetching available MCP servers")

    try:
        servers = ExampleQuestionsService.get_available_servers()

        logger.info(f"Found {len(servers)} available MCP servers")

        return AvailableMCPServersResponse(
            servers=servers,
            total_servers=len(servers),
            message="Successfully retrieved available MCP servers",
            success=True,
        )

    except Exception as e:
        logger.error(f"Error fetching available MCP servers: {str(e)}")
        return AvailableMCPServersResponse(servers=[], total_servers=0, message=f"Error retrieving MCP servers: {str(e)}", success=False)


@copilot_mcp_router.get(
    "/servers/{mcp_server}",
    response_model=dict,
    description="Get detailed information about a specific MCP server",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_mcp_server_details(mcp_server: MCPServerType) -> dict:
    """
    Get detailed information about a specific MCP server.

    Args:
        mcp_server: The MCP server to get details for

    Returns:
        Dictionary containing detailed server information
    """
    logger.info(f"Fetching details for MCP server: {mcp_server.value}")

    try:
        server_info = ExampleQuestionsService.get_server_info(mcp_server)

        if not server_info:
            return {"server": mcp_server.value, "message": f"Server information not found for {mcp_server.value}", "success": False}

        # Get additional context like available categories and question count
        categories = ExampleQuestionsService.get_available_categories(mcp_server)
        total_questions = len(ExampleQuestionsService.get_example_questions(mcp_server))

        return {
            "server": server_info.dict(),
            "available_categories": categories,
            "total_example_questions": total_questions,
            "message": f"Successfully retrieved details for {mcp_server.value}",
            "success": True,
        }

    except Exception as e:
        logger.error(f"Error fetching details for {mcp_server.value}: {str(e)}")
        return {"server": mcp_server.value, "message": f"Error retrieving server details: {str(e)}", "success": False}


@copilot_mcp_router.get(
    "/example-questions",
    response_model=ExampleQuestionsResponse,
    description="Get example questions for a specific MCP server",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_example_questions(
    mcp_server: MCPServerType = Query(..., description="MCP server to get example questions for"),
    category: Optional[str] = Query(None, description="Filter questions by category"),
) -> ExampleQuestionsResponse:
    """
    Retrieve example questions that users can ask for a specific MCP server.

    This endpoint provides users with sample queries they can use to interact
    with different MCP servers, helping them understand the capabilities and
    available operations for each server type.

    Args:
        mcp_server: The MCP server type to get questions for
        category: Optional category filter (e.g., 'alerts', 'agents', 'health')

    Returns:
        ExampleQuestionsResponse: List of example questions with metadata
    """
    logger.info(f"Fetching example questions for MCP server: {mcp_server.value}")

    try:
        # Get questions, optionally filtered by category
        if category:
            questions = ExampleQuestionsService.get_questions_by_category(mcp_server, category)
            logger.info(f"Found {len(questions)} questions in category '{category}' for {mcp_server.value}")
        else:
            questions = ExampleQuestionsService.get_example_questions(mcp_server)
            logger.info(f"Found {len(questions)} total questions for {mcp_server.value}")

        return ExampleQuestionsResponse(
            mcp_server=mcp_server,
            questions=questions,
            total_questions=len(questions),
            message=f"Successfully retrieved example questions for {mcp_server.value}",
            success=True,
        )

    except Exception as e:
        logger.error(f"Error fetching example questions for {mcp_server.value}: {str(e)}")
        return ExampleQuestionsResponse(
            mcp_server=mcp_server,
            questions=[],
            total_questions=0,
            message=f"Error retrieving example questions: {str(e)}",
            success=False,
        )


@copilot_mcp_router.get(
    "/categories",
    description="Get available question categories for a specific MCP server",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_question_categories(mcp_server: MCPServerType = Query(..., description="MCP server to get categories for")) -> dict:
    """
    Get available question categories for a specific MCP server.

    Args:
        mcp_server: The MCP server type to get categories for

    Returns:
        Dictionary containing the available categories
    """
    logger.info(f"Fetching question categories for MCP server: {mcp_server.value}")

    try:
        categories = ExampleQuestionsService.get_available_categories(mcp_server)

        return {
            "mcp_server": mcp_server.value,
            "categories": categories,
            "total_categories": len(categories),
            "message": f"Successfully retrieved categories for {mcp_server.value}",
            "success": True,
        }

    except Exception as e:
        logger.error(f"Error fetching categories for {mcp_server.value}: {str(e)}")
        return {
            "mcp_server": mcp_server.value,
            "categories": [],
            "total_categories": 0,
            "message": f"Error retrieving categories: {str(e)}",
            "success": False,
        }


@copilot_mcp_router.post(
    "/query",
    description="Process a query to the appropriate MCP server",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def query_mcp(request: MCPQueryRequest, session: AsyncSession = Depends(get_db)) -> MCPQueryResponse:
    """
    Process a query to the MCP agent and return structured response.
    Routes the query to the appropriate MCP server based on the selected server type.
    """
    logger.info(f"Processing MCP query for server: {request.mcp_server.value}")

    license_key = None

    # Check if it's a cloud service and get license key if needed
    if MCPService.is_cloud_service(request.mcp_server):
        try:
            await is_feature_enabled("SOCFORTRESS AI", session=session)

            # Will raise HTTPException(404) if no license record exists
            license_info = await get_license(session)
            license_key = license_info.license_key

            # If a license record exists but the key is missing, mirror get_license behavior
            if not license_key:
                raise HTTPException(status_code=404, detail="No license found. A license must be created first.")

            logger.info(f"Retrieved license key for cloud service {request.mcp_server.value}")

        except HTTPException as http_exc:
            # Surface the HTTPException unchanged
            raise http_exc
        except Exception as e:
            # Unexpected errors -> 500
            logger.error(f"Failed to get license key for cloud service: {str(e)}")
            raise HTTPException(status_code=500, detail=f"License validation failed: {str(e)}")

    # Use the modular service to execute the query
    return await MCPService.execute_query(request, license_key=license_key)
