from typing import Dict
from typing import Optional

import httpx
from loguru import logger

from app.integrations.copilot_mcp.schema.copilot_mcp import MCPQueryRequest
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPQueryResponse
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPServerType


class MCPService:
    """Sends the AI Chatbot's queries to SOCFortress's cloud MCP servers.

    Every server is a cloud one, asked with the license key as ``x-api-key``. The local servers (the
    Wazuh indexer and manager, CoPilot's database and Velociraptor, which the ``copilot-mcp`` container
    served) were removed: questions about a deployment's own data go to Talon's chat, where Talon is
    installed.
    """

    BASE_URL = "https://mcp.socfortress.co/query"

    #: Each server's endpoint under BASE_URL.
    _ENDPOINTS: Dict[MCPServerType, str] = {
        MCPServerType.THREAT_INTEL: "threat_intel",
        MCPServerType.CYBER_NEWS: "cyber_news",
        MCPServerType.KNOWLEDGEBASE: "knowledgebase",
        MCPServerType.ATTACK_SURFACE: "attack_surface",
    }

    @classmethod
    def build_full_url(cls, mcp_server: MCPServerType) -> str:
        """
        Build the full URL for a specific MCP server type.

        Args:
            mcp_server: The MCP server type

        Returns:
            str: The full URL for the server endpoint

        Raises:
            ValueError: If the server type is not supported
        """
        endpoint = cls._ENDPOINTS.get(mcp_server)
        if not endpoint:
            raise ValueError(f"Unsupported MCP server type: {mcp_server}")
        return f"{cls.BASE_URL}/{endpoint}"

    @classmethod
    async def execute_query(cls, data: MCPQueryRequest, license_key: Optional[str] = None) -> MCPQueryResponse:
        """
        Execute a query on the MCP server the request names.

        Args:
            data: The MCP query request containing the server type and query
            license_key: The license key, sent as the x-api-key header

        Returns:
            MCPQueryResponse: The response from the MCP server (success=False when the query failed)
        """
        try:
            full_url = cls.build_full_url(data.mcp_server)

            logger.info(f"Sending MCP query to {data.mcp_server.value} at {full_url}")
            logger.debug(f"Query data: {data.model_dump()}")

            headers = {"Content-Type": "application/json"}
            if license_key:
                headers["x-api-key"] = license_key
            else:
                logger.warning(f"No license key provided for cloud service {data.mcp_server.value}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    full_url,
                    json=data.model_dump(),
                    headers=headers,
                    timeout=300,
                )

                # Raise an exception for HTTP error status codes
                response.raise_for_status()

                logger.info(f"Successfully received response from {data.mcp_server.value}: {response.json()}")
                return MCPQueryResponse(**response.json())

        except ValueError as e:
            logger.error(f"Invalid server type: {str(e)}")
            return MCPQueryResponse(message=f"Error: {str(e)}", success=False, result=None, structured_result=None, execution_time=0.0)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error when querying {data.mcp_server.value}: {str(e)}")
            return MCPQueryResponse(
                message=f"HTTP error when querying {data.mcp_server.value}: {str(e)}",
                success=False,
                result=None,
                structured_result=None,
                execution_time=0.0,
            )

        except Exception as e:
            logger.error(f"Unexpected error when querying {data.mcp_server.value}: {str(e)}")
            return MCPQueryResponse(
                message=f"Unexpected error: {str(e)}",
                success=False,
                result=None,
                structured_result=None,
                execution_time=0.0,
            )
