from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from enum import Enum

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator
from fastapi import HTTPException

class MCPServerType(str, Enum):
    """Enumeration of available MCP servers"""
    WAZUH_INDEXER = "wazuh-indexer"
    WAZUH_MANAGER = "wazuh-manager"
    COPILOT = "copilot"

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

    input: str = Field(..., description="The query/input to send to the MCP server")
    mcp_server: MCPServerType = Field(..., description="MCP server to use for the query")
    verbose: Optional[bool] = Field(default=True, description="Enable verbose output")

    @validator('mcp_server', pre=True)
    def validate_mcp_server(cls, v):
        """Validate that the MCP server type is one of the allowed values"""
        if isinstance(v, str):
            # Check if the string value is valid
            valid_values = [server.value for server in MCPServerType]
            if v not in valid_values:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid MCP server type: '{v}'. Must be one of: {', '.join(valid_values)}"
                )
        return v


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


class ExampleQuestion(BaseModel):
    """Single example question with metadata"""

    question: str = Field(..., description="The example question text")
    description: Optional[str] = Field(None, description="Brief description of what this question does")
    category: Optional[str] = Field(None, description="Category of the question (e.g., 'alerts', 'agents', 'health')")

class ExampleQuestionsResponse(BaseModel):
    """Response containing example questions for a specific MCP server"""

    mcp_server: MCPServerType = Field(..., description="The MCP server these questions are for")
    questions: List[ExampleQuestion] = Field(..., description="List of example questions")
    total_questions: int = Field(..., description="Total number of example questions")
    message: str = Field(..., description="Response message")
    success: bool = Field(default=True, description="Whether the request was successful")
