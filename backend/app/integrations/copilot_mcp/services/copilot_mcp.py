from typing import Dict, Optional
from enum import Enum

import httpx
from loguru import logger

from app.integrations.copilot_mcp.schema.copilot_mcp import MCPQueryRequest
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPQueryResponse
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPServerType


class MCPServiceType(str, Enum):
    """Enumeration of MCP service deployment types"""
    LOCAL = "local"
    CLOUD = "cloud"


class MCPServerConfig:
    """Configuration for MCP server endpoints"""

    def __init__(self, service_type: MCPServiceType, endpoint: str):
        self.service_type = service_type
        self.endpoint = endpoint


class MCPService:
    """Service for handling MCP queries with modular server routing"""

    # Base URLs for different service types
    _BASE_URLS = {
        MCPServiceType.LOCAL: "http://copilot-mcp/mcp",
        MCPServiceType.CLOUD: "https://mcp.socfortress.co/query",
    }

    # Define the mapping of MCP server types to their configurations
    _SERVER_CONFIGS: Dict[MCPServerType, MCPServerConfig] = {
        # Local services
        MCPServerType.WAZUH_INDEXER: MCPServerConfig(MCPServiceType.LOCAL, "opensearch-query"),
        MCPServerType.WAZUH_MANAGER: MCPServerConfig(MCPServiceType.LOCAL, "wazuh-query"),
        MCPServerType.COPILOT: MCPServerConfig(MCPServiceType.LOCAL, "mysql-query"),
        MCPServerType.VELOCIRAPTOR: MCPServerConfig(MCPServiceType.LOCAL, "velociraptor-query"),

        # Cloud services
        MCPServerType.THREAT_INTEL: MCPServerConfig(MCPServiceType.CLOUD, "threat_intel"),
    }

    @classmethod
    def get_server_config(cls, mcp_server: MCPServerType) -> MCPServerConfig:
        """
        Get the configuration for a specific MCP server type.

        Args:
            mcp_server: The MCP server type

        Returns:
            MCPServerConfig: The configuration for the server

        Raises:
            ValueError: If the server type is not supported
        """
        config = cls._SERVER_CONFIGS.get(mcp_server)
        if not config:
            raise ValueError(f"Unsupported MCP server type: {mcp_server}")
        return config

    @classmethod
    def build_full_url(cls, mcp_server: MCPServerType) -> str:
        """
        Build the full URL for a specific MCP server type.

        Args:
            mcp_server: The MCP server type

        Returns:
            str: The full URL for the server endpoint
        """
        config = cls.get_server_config(mcp_server)
        base_url = cls._BASE_URLS[config.service_type]
        return f"{base_url}/{config.endpoint}"

    @classmethod
    def is_cloud_service(cls, mcp_server: MCPServerType) -> bool:
        """
        Check if the MCP server is a cloud service.

        Args:
            mcp_server: The MCP server type

        Returns:
            bool: True if it's a cloud service, False if local
        """
        config = cls.get_server_config(mcp_server)
        return config.service_type == MCPServiceType.CLOUD

    @classmethod
    async def execute_query(cls, data: MCPQueryRequest, license_key: Optional[str] = None) -> MCPQueryResponse:
        """
        Execute a query on the appropriate MCP server based on the request.

        Args:
            data: The MCP query request containing the server type and query
            license_key: Optional license key for cloud services authentication

        Returns:
            MCPQueryResponse: The response from the MCP server

        Raises:
            httpx.HTTPError: If the HTTP request fails
            ValueError: If the server type is not supported
        """
        try:
            # Get the full URL for the specified server
            full_url = cls.build_full_url(data.mcp_server)
            is_cloud = cls.is_cloud_service(data.mcp_server)

            logger.info(f"Sending MCP query to {data.mcp_server.value} ({'cloud' if is_cloud else 'local'}) at {full_url}")
            logger.debug(f"Query data: {data.dict()}")

            # Set different timeout for cloud vs local services
            timeout = 180 if is_cloud else 120

            # Prepare headers
            headers = {"Content-Type": "application/json"}

            # Add license key as x-api-key header for cloud services
            if is_cloud and license_key:
                headers["x-api-key"] = license_key
                logger.debug("Added x-api-key header for cloud service")
            elif is_cloud and not license_key:
                logger.warning(f"No license key provided for cloud service {data.mcp_server.value}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    full_url,
                    json=data.dict(),
                    headers=headers,
                    timeout=timeout,
                )

                # Raise an exception for HTTP error status codes
                response.raise_for_status()

                logger.info(f"Successfully received response from {data.mcp_server.value}: {response.json()}")
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


    @classmethod
    def add_local_service(cls, server_type: MCPServerType, endpoint: str) -> None:
        """
        Add a new local MCP service.

        Args:
            server_type: The MCP server type enum
            endpoint: The endpoint path for the local service
        """
        cls._SERVER_CONFIGS[server_type] = MCPServerConfig(MCPServiceType.LOCAL, endpoint)

    @classmethod
    def add_cloud_service(cls, server_type: MCPServerType, endpoint: str) -> None:
        """
        Add a new cloud MCP service.

        Args:
            server_type: The MCP server type enum
            endpoint: The endpoint path for the cloud service
        """
        cls._SERVER_CONFIGS[server_type] = MCPServerConfig(MCPServiceType.CLOUD, endpoint)

    @classmethod
    def get_service_info(cls) -> Dict[str, Dict[str, str]]:
        """
        Get information about all configured services.

        Returns:
            Dict containing service information grouped by type
        """
        local_services = {}
        cloud_services = {}

        for server_type, config in cls._SERVER_CONFIGS.items():
            service_info = {
                "endpoint": config.endpoint,
                "full_url": cls.build_full_url(server_type)
            }

            if config.service_type == MCPServiceType.LOCAL:
                local_services[server_type.value] = service_info
            else:
                cloud_services[server_type.value] = service_info

        return {
            "local": local_services,
            "cloud": cloud_services
        }


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
