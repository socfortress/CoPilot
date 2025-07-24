from typing import Dict
from typing import List

from app.integrations.copilot_mcp.schema.copilot_mcp import ExampleQuestion
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPServerInfo
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPServerType


class ExampleQuestionsService:
    """Service for managing example questions for different MCP servers"""

    # Define example questions for each MCP server type
    _EXAMPLE_QUESTIONS: Dict[MCPServerType, List[ExampleQuestion]] = {
        MCPServerType.COPILOT: [
            ExampleQuestion(
                question="How many alerts do I have for customerA?",
                description="Get the total count of alerts for a specific customer",
                category="alerts",
            ),
            ExampleQuestion(
                question="What customer has the highest number of alerts?",
                description="Find the customer with the most alerts in the system",
                category="alerts",
            ),
            ExampleQuestion(
                question="Show me spotted iocs for customerA",
                description="Retrieve recent high-priority security alerts",
                category="alerts",
            ),
            ExampleQuestion(
                question="What are the top 5 most common alert sources?",
                description="Analyze alert patterns to identify frequent security events",
                category="analytics",
            ),
            ExampleQuestion(
                question="How many active customers do we have?",
                description="Get the count of currently active customers in the system",
                category="customers",
            ),
            ExampleQuestion(
                question="Show me endpoint status for customerA",
                description="Display endpoint status.",
                category="endpoints",
            ),
        ],
        MCPServerType.WAZUH_MANAGER: [
            ExampleQuestion(
                question="What is the status of agent endpoint123?",
                description="Check the current operational status of a specific Wazuh agent",
                category="agents",
            ),
            ExampleQuestion(
                question="What are the SCA findings for endpoint123?",
                description="Retrieve the Software Composition Analysis (SCA) findings for a specific endpoint",
                category="agents",
            ),
            ExampleQuestion(
                question="What are the open ports on endpoint123?",
                description="List all open network ports detected on a specific endpoint",
                category="network",
            ),
            ExampleQuestion(
                question="What software is installed on endpoint123?",
                description="Get inventory of installed software packages on an endpoint",
                category="inventory",
            ),
            ExampleQuestion(
                question="Show me all disconnected agents",
                description="List agents that are currently offline or disconnected",
                category="agents",
            ),
            ExampleQuestion(
                question="Do I have any sysmon event 1 detection rules?",
                description="Check for specific security rules related to Sysmon event 1",
                category="rules",
            ),
        ],
        MCPServerType.WAZUH_INDEXER: [
            ExampleQuestion(
                question="What is the cluster health status?",
                description="Check the overall health and status of the Wazuh indexer cluster",
                category="health",
            ),
            ExampleQuestion(
                question="What are the most critical vulnerabilities for `agent_name`: endpoint123 from the index pattern `wazuh-states-vulnerabilities-*`??",
                description="Get critical vulnerabilities for a specific agent from the Wazuh index",
                category="vulnerabilities",
            ),
            ExampleQuestion(
                question="Has the agent named `agent_name` made any dns requests to `evil.com` within the index pattern `wazuh-customerA*`?",
                description="Search for DNS requests made by a specific agent to a known malicious domain",
                category="search",
            ),
            ExampleQuestion(
                question="Has the agent named `agent_name` had any rule_group3 `authentication_failed` within the index name: `wazuh-customerA*`?",
                description="Check for authentication failures in a specific index for a given agent",
                category="search",
            ),
            ExampleQuestion(
                question="How much diskspace is the `wazuh-customerA*` indices consuming?",
                description="Get the disk space usage for all indices related to customerA",
                category="indexing",
            ),
        ],
        MCPServerType.VELOCIRAPTOR: [
            ExampleQuestion(
                question="What users have logged onto endpoint123 in the last 30 days?",
                description="List all users who have logged onto a specific endpoint within the last 30 days",
                category="users",
            ),
            ExampleQuestion(
                question="List all network connections on endpoint123",
                description="Display active and recent network connections from an endpoint",
                category="network",
            ),
            ExampleQuestion(
                question="What artifacts are available for checking browser activity?",
                description="Show available artifacts for browser activity analysis",
                category="artifacts",
            ),
            ExampleQuestion(
                question="What scheduled tasks exist on endpoint123?",
                description="List all scheduled tasks for persistence analysis",
                category="persistence",
            ),
            ExampleQuestion(
                question="Find all executables in the Downloads folder across all endpoints",
                description="Hunt for potentially suspicious executable files in user download directories",
                category="hunting",
            ),
            ExampleQuestion(
                question="Show me the startup programs on endpoint DESKTOP-ABC123",
                description="List programs that start automatically with the system",
                category="persistence",
            ),
            ExampleQuestion(
                question="What browser artifacts can I collect from endpoint DESKTOP-ABC123?",
                description="Gather web browser history, downloads, and other forensic artifacts",
                category="artifacts",
            ),
            ExampleQuestion(
                question="Hunt for indicators of lateral movement across the network",
                description="Search for signs of attackers moving between systems",
                category="hunting",
            ),
            ExampleQuestion(
                question="Show me all USB devices connected to endpoint DESKTOP-ABC123",
                description="List USB device connection history for investigation",
                category="hardware",
            ),
        ],
    }

    # Define server information with descriptions and capabilities
    _SERVER_INFO: Dict[MCPServerType, MCPServerInfo] = {
        MCPServerType.COPILOT: MCPServerInfo(
            name="CoPilot",
            value=MCPServerType.COPILOT.value,
            description="Query customer data, alerts, incidents, and analytics from the CoPilot platform",
            capabilities=[
                "Customer management queries",
                "Alert analysis and filtering",
                "Incident tracking and trends",
                "Security analytics and reporting",
                "Dashboard data retrieval",
            ],
        ),
        MCPServerType.WAZUH_MANAGER: MCPServerInfo(
            name="Wazuh Manager",
            value=MCPServerType.WAZUH_MANAGER.value,
            description="Interact with Wazuh Manager for agent management, security monitoring, and endpoint analysis",
            capabilities=[
                "Agent status monitoring",
                "Endpoint security scanning",
                "Software inventory management",
                "Network port analysis",
            ],
        ),
        MCPServerType.WAZUH_INDEXER: MCPServerInfo(
            name="Wazuh Indexer",
            value=MCPServerType.WAZUH_INDEXER.value,
            description="Query the Wazuh Indexer for log analysis, search operations, and cluster health monitoring",
            capabilities=[
                "Log data search and analysis",
                "Index management and statistics",
                "Cluster health monitoring",
                "Vulnerability assessment",
            ],
        ),
        MCPServerType.VELOCIRAPTOR: MCPServerInfo(
            name="Velociraptor",
            value=MCPServerType.VELOCIRAPTOR.value,
            description="Digital forensics and incident response platform for endpoint monitoring and threat hunting",
            capabilities=[
                "Live endpoint forensics",
                "Artifact collection and analysis",
                "Process and network monitoring",
                "Persistence mechanism detection",
                "Lateral movement hunting",
                "Browser artifact collection",
                "Hardware device tracking",
            ],
        ),
    }

    @classmethod
    def get_example_questions(cls, mcp_server: MCPServerType) -> List[ExampleQuestion]:
        """
        Get example questions for a specific MCP server type.

        Args:
            mcp_server: The MCP server type to get questions for

        Returns:
            List of example questions for the specified server
        """
        return cls._EXAMPLE_QUESTIONS.get(mcp_server, [])

    @classmethod
    def get_questions_by_category(cls, mcp_server: MCPServerType, category: str) -> List[ExampleQuestion]:
        """
        Get example questions for a specific MCP server type filtered by category.

        Args:
            mcp_server: The MCP server type to get questions for
            category: The category to filter by

        Returns:
            List of example questions filtered by category
        """
        all_questions = cls.get_example_questions(mcp_server)
        return [q for q in all_questions if q.category == category]

    @classmethod
    def get_available_categories(cls, mcp_server: MCPServerType) -> List[str]:
        """
        Get available categories for a specific MCP server type.

        Args:
            mcp_server: The MCP server type to get categories for

        Returns:
            List of unique categories available for the server
        """
        questions = cls.get_example_questions(mcp_server)
        categories = {q.category for q in questions if q.category}
        return sorted(list(categories))

    @classmethod
    def add_example_question(cls, mcp_server: MCPServerType, question: ExampleQuestion) -> None:
        """
        Add a new example question to a specific MCP server type.

        Args:
            mcp_server: The MCP server type to add the question to
            question: The example question to add
        """
        if mcp_server not in cls._EXAMPLE_QUESTIONS:
            cls._EXAMPLE_QUESTIONS[mcp_server] = []
        cls._EXAMPLE_QUESTIONS[mcp_server].append(question)

    @classmethod
    def get_available_servers(cls) -> List[MCPServerInfo]:
        """
        Get information about all available MCP servers.

        Returns:
            List of MCPServerInfo objects containing server details
        """
        return list(cls._SERVER_INFO.values())

    @classmethod
    def get_server_info(cls, mcp_server: MCPServerType) -> MCPServerInfo:
        """
        Get detailed information about a specific MCP server.

        Args:
            mcp_server: The MCP server type to get information for

        Returns:
            MCPServerInfo object with server details
        """
        return cls._SERVER_INFO.get(mcp_server)
