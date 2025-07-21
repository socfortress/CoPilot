import httpx
from typing import Dict
from loguru import logger

from app.integrations.copilot_mcp.schema.copilot_mcp import (
    MCPQueryRequest,
    MCPQueryResponse,
    MCPServerType,
)

class MCPService:
    """Service for handling MCP queries with modular server routing"""

    # Define the mapping of MCP server types to their endpoint paths
    _SERVER_ENDPOINTS: Dict[MCPServerType, str] = {
        MCPServerType.WAZUH_INDEXER: "opensearch-query",
        MCPServerType.WAZUH_MANAGER: "wazuh-query",
        MCPServerType.COPILOT: "mysql-query",
        MCPServerType.VELOCIRAPTOR: "velociraptor-query",
    }

    # Base URL for the copilot-mcp service
    _BASE_URL = "http://10.255.255.5/mcp"

    @classmethod
    def get_endpoint_for_server(cls, mcp_server: MCPServerType) -> str:
        """
        Get the endpoint path for a specific MCP server type.

        Args:
            mcp_server: The MCP server type

        Returns:
            str: The endpoint path for the server

        Raises:
            ValueError: If the server type is not supported
        """
        endpoint = cls._SERVER_ENDPOINTS.get(mcp_server)
        if not endpoint:
            raise ValueError(f"Unsupported MCP server type: {mcp_server}")
        return endpoint

    @classmethod
    def build_full_url(cls, mcp_server: MCPServerType) -> str:
        """
        Build the full URL for a specific MCP server type.

        Args:
            mcp_server: The MCP server type

        Returns:
            str: The full URL for the server endpoint
        """
        endpoint = cls.get_endpoint_for_server(mcp_server)
        return f"{cls._BASE_URL}/{endpoint}"

    @classmethod
    async def execute_query(cls, data: MCPQueryRequest) -> MCPQueryResponse:
        """
        Execute a query on the appropriate MCP server based on the request.

        Args:
            data: The MCP query request containing the server type and query

        Returns:
            MCPQueryResponse: The response from the MCP server

        Raises:
            httpx.HTTPError: If the HTTP request fails
            ValueError: If the server type is not supported
        """
        try:
            # Get the full URL for the specified server
            full_url = cls.build_full_url(data.mcp_server)

            logger.info(f"Sending MCP query to {data.mcp_server.value} at {full_url}")
            logger.debug(f"Query data: {data.dict()}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    full_url,
                    json=data.dict(),
                    timeout=120,
                )

                # Raise an exception for HTTP error status codes
                response.raise_for_status()

                logger.info(f"Successfully received response from {data.mcp_server.value}")
                return MCPQueryResponse(**response.json())

        except ValueError as e:
            logger.error(f"Invalid server type: {str(e)}")
            return MCPQueryResponse(
                message=f"Error: {str(e)}",
                success=False,
                result=None,
                structured_result=None,
                execution_time=0.0
            )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error when querying {data.mcp_server.value}: {str(e)}")
            return MCPQueryResponse(
                message=f"HTTP error when querying {data.mcp_server.value}: {str(e)}",
                success=False,
                result=None,
                structured_result=None,
                execution_time=0.0
            )

        except Exception as e:
            logger.error(f"Unexpected error when querying {data.mcp_server.value}: {str(e)}")
            return MCPQueryResponse(
                message=f"Unexpected error: {str(e)}",
                success=False,
                result=None,
                structured_result=None,
                execution_time=0.0
            )

# Convenience function to maintain backward compatibility
async def post_to_copilot_mcp(data: MCPQueryRequest) -> MCPQueryResponse:
    """
    Send a POST request to the appropriate copilot-mcp endpoint based on server type.

    This function maintains backward compatibility while using the new modular service.

    Args:
        data: The MCP query request

    Returns:
        MCPQueryResponse: The response from the MCP server
    """
    return await MCPService.execute_query(data)
