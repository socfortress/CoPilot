from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class MCPServerConfig(BaseModel):
    """Configuration for MCP server connection"""

    name: str = Field(..., description="Name of the MCP server")
    transport: str = Field(default="sse", description="Transport type (sse, stdio)")
    url: Optional[str] = Field(
        default=None,
        description="URL for the MCP server endpoint (for sse transport)",
    )
    command: Optional[str] = Field(
        default=None,
        description="Command to run (for stdio transport)",
    )
    args: Optional[List[str]] = Field(
        default=None,
        description="Arguments for the command (for stdio transport)",
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Headers for authentication",
    )
    env: Optional[Dict[str, str]] = Field(
        default=None,
        description="Environment variables for the process",
    )


class MCPQuery(BaseModel):
    """Query request for MCP server"""

    input: str = Field(..., description="The query/input to send to the MCP server")
    server_name: str = Field(
        default="opensearch-mcp-server",
        description="Name of the MCP server to use",
    )
    verbose: bool = Field(default=True, description="Enable verbose output")


class MCPQueryRequest(BaseModel):
    """Complete MCP query request"""

    query: MCPQuery
    integration: str = Field(..., example="opensearch")


class VulnerabilityInfo(BaseModel):
    """Structured vulnerability information"""

    agent_name: Optional[str] = Field(None, description="Name of the agent")
    vulnerability_id: Optional[str] = Field(
        None,
        description="Vulnerability identifier",
    )
    score: Optional[float] = Field(None, description="Vulnerability score")
    severity: Optional[str] = Field(None, description="Vulnerability severity level")
    description: Optional[str] = Field(None, description="Vulnerability description")
    cve_id: Optional[str] = Field(None, description="CVE identifier if available")


class ClusterHealthInfo(BaseModel):
    """Structured cluster health information"""

    status: Optional[str] = Field(
        None,
        description="Cluster status (green, yellow, red)",
    )
    number_of_nodes: Optional[int] = Field(None, description="Total number of nodes")
    active_primary_shards: Optional[int] = Field(
        None,
        description="Number of active primary shards",
    )
    active_shards: Optional[int] = Field(
        None,
        description="Total number of active shards",
    )
    relocating_shards: Optional[int] = Field(
        None,
        description="Number of relocating shards",
    )
    initializing_shards: Optional[int] = Field(
        None,
        description="Number of initializing shards",
    )
    unassigned_shards: Optional[int] = Field(
        None,
        description="Number of unassigned shards",
    )


class StructuredAgentResponse(BaseModel):
    """Structured response from the MCP agent with consistent format"""

    response: str = Field(
        ...,
        description="Human-readable response in markdown format - the main answer to the user's query",
    )
    thinking_process: Optional[str] = Field(
        None,
        description="Agent's step-by-step reasoning and exploration process",
    )


class MCPQueryResponse(BaseModel):
    """Response from MCP query"""

    message: str
    success: bool
    result: Optional[Any] = Field(None, description="The result from the MCP agent")
    structured_result: Optional[StructuredAgentResponse] = Field(
        None,
        description="Structured response from agent",
    )
    execution_time: Optional[float] = Field(
        None,
        description="Time taken to execute the query",
    )
