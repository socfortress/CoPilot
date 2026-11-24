from enum import Enum
from typing import Any
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class MCPServerType(str, Enum):
    """The AI Chatbot's servers: SOCFortress's cloud MCP servers, asked with the license key.

    The chatbot used to have local servers as well (``wazuh-indexer``, ``wazuh-manager``,
    ``copilot`` and ``velociraptor``), served by the ``copilot-mcp`` container with
    deployment-wide credentials. That container was removed: those values are now refused.
    """

    THREAT_INTEL = "threat-intel"
    CYBER_NEWS = "cyber-news"
    KNOWLEDGEBASE = "knowledgebase"
    ATTACK_SURFACE = "attack-surface"


class MCPQueryRequest(BaseModel):
    """Complete MCP query request"""

    input: str = Field(..., description="The query/input to send to the MCP server")
    mcp_server: MCPServerType = Field(..., description="MCP server to use for the query")
    verbose: Optional[bool] = Field(default=True, description="Enable verbose output")

    @field_validator("mcp_server", mode="before")
    @classmethod
    def validate_mcp_server(cls, v):
        """Validate that the MCP server type is one of the allowed values"""
        if isinstance(v, str):
            # Check if the string value is valid
            valid_values = [server.value for server in MCPServerType]
            if v not in valid_values:
                raise HTTPException(status_code=400, detail=f"Invalid MCP server type: '{v}'. Must be one of: {', '.join(valid_values)}")
        return v


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


class MCPServerInfo(BaseModel):
    """Information about an available MCP server"""

    name: str = Field(..., description="The server name/identifier")
    value: str = Field(..., description="The server enum value")
    description: str = Field(..., description="Description of what this server does")
    capabilities: List[str] = Field(default=[], description="List of server capabilities")


class AvailableMCPServersResponse(BaseModel):
    """Response containing available MCP servers"""

    servers: List[MCPServerInfo] = Field(..., description="List of available MCP servers")
    total_servers: int = Field(..., description="Total number of available servers")
    message: str = Field(..., description="Response message")
    success: bool = Field(default=True, description="Whether the request was successful")


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
