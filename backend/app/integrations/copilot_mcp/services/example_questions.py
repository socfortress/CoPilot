from typing import Dict, List
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPServerType, ExampleQuestion, MCPServerInfo

class ExampleQuestionsService:
    """Service for managing example questions for different MCP servers"""

    # Define example questions for each MCP server type
    _EXAMPLE_QUESTIONS: Dict[MCPServerType, List[ExampleQuestion]] = {
        MCPServerType.COPILOT: [
            ExampleQuestion(
                question="How many alerts do I have for customerA?",
                description="Get the total count of alerts for a specific customer",
                category="alerts"
            ),
            ExampleQuestion(
                question="What customer has the highest number of alerts?",
                description="Find the customer with the most alerts in the system",
                category="alerts"
            ),
            ExampleQuestion(
                question="Show me the latest critical alerts from the past 24 hours",
                description="Retrieve recent high-priority security alerts",
                category="alerts"
            ),
            ExampleQuestion(
                question="What are the top 5 most common alert types?",
                description="Analyze alert patterns to identify frequent security events",
                category="analytics"
            ),
            ExampleQuestion(
                question="How many active customers do we have?",
                description="Get the count of currently active customers in the system",
                category="customers"
            ),
            ExampleQuestion(
                question="Show me incident trends for the past week",
                description="Display incident statistics and trends over time",
                category="incidents"
            ),
        ],

        MCPServerType.WAZUH_MANAGER: [
            ExampleQuestion(
                question="What is the status of agent endpoint123?",
                description="Check the current operational status of a specific Wazuh agent",
                category="agents"
            ),
            ExampleQuestion(
                question="What are the open ports on endpoint123?",
                description="List all open network ports detected on a specific endpoint",
                category="network"
            ),
            ExampleQuestion(
                question="What software is installed on endpoint123?",
                description="Get inventory of installed software packages on an endpoint",
                category="inventory"
            ),
            ExampleQuestion(
                question="Show me all disconnected agents",
                description="List agents that are currently offline or disconnected",
                category="agents"
            ),
            ExampleQuestion(
                question="What are the latest security events from agent endpoint123?",
                description="Retrieve recent security events and alerts from a specific agent",
                category="security"
            ),
            ExampleQuestion(
                question="How many agents are currently online?",
                description="Get the count of active and connected Wazuh agents",
                category="agents"
            ),
            ExampleQuestion(
                question="What vulnerabilities were detected on endpoint123?",
                description="List security vulnerabilities found during scans",
                category="vulnerabilities"
            ),
        ],

        MCPServerType.WAZUH_INDEXER: [
            ExampleQuestion(
                question="What is the cluster health status?",
                description="Check the overall health and status of the Wazuh indexer cluster",
                category="health"
            ),
            ExampleQuestion(
                question="How many documents are indexed today?",
                description="Get the count of new documents added to the index",
                category="indexing"
            ),
            ExampleQuestion(
                question="What are the most frequent log sources?",
                description="Analyze which systems are generating the most log data",
                category="analytics"
            ),
            ExampleQuestion(
                question="Show me index storage usage statistics",
                description="Display disk usage and storage metrics for indices",
                category="storage"
            ),
            ExampleQuestion(
                question="What indices have the highest document count?",
                description="List indices sorted by number of documents",
                category="indexing"
            ),
            ExampleQuestion(
                question="Are there any failed index operations?",
                description="Check for indexing errors or failed operations",
                category="errors"
            ),
        ],

        MCPServerType.VELOCIRAPTOR: [
            ExampleQuestion(
                question="Show me all running processes on endpoint DESKTOP-ABC123",
                description="List all currently running processes on a specific endpoint",
                category="processes"
            ),
            ExampleQuestion(
                question="What files were created in the last 24 hours on endpoint DESKTOP-ABC123?",
                description="Find recently created files on a specific endpoint for forensic analysis",
                category="filesystem"
            ),
            ExampleQuestion(
                question="List all network connections on endpoint DESKTOP-ABC123",
                description="Display active and recent network connections from an endpoint",
                category="network"
            ),
            ExampleQuestion(
                question="What artifacts are available for Windows.System.Users?",
                description="Show available user account artifacts and information",
                category="artifacts"
            ),
            ExampleQuestion(
                question="Hunt for suspicious PowerShell executions across all endpoints",
                description="Search for potentially malicious PowerShell activity across the fleet",
                category="hunting"
            ),
            ExampleQuestion(
                question="Show me the registry keys modified in the last week on endpoint DESKTOP-ABC123",
                description="Track registry changes for security investigation",
                category="registry"
            ),
            ExampleQuestion(
                question="What scheduled tasks exist on endpoint DESKTOP-ABC123?",
                description="List all scheduled tasks for persistence analysis",
                category="persistence"
            ),
            ExampleQuestion(
                question="Find all executables in the Downloads folder across all endpoints",
                description="Hunt for potentially suspicious executable files in user download directories",
                category="hunting"
            ),
            ExampleQuestion(
                question="Show me the startup programs on endpoint DESKTOP-ABC123",
                description="List programs that start automatically with the system",
                category="persistence"
            ),
            ExampleQuestion(
                question="What browser artifacts can I collect from endpoint DESKTOP-ABC123?",
                description="Gather web browser history, downloads, and other forensic artifacts",
                category="artifacts"
            ),
            ExampleQuestion(
                question="Hunt for indicators of lateral movement across the network",
                description="Search for signs of attackers moving between systems",
                category="hunting"
            ),
            ExampleQuestion(
                question="Show me all USB devices connected to endpoint DESKTOP-ABC123",
                description="List USB device connection history for investigation",
                category="hardware"
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
                "Dashboard data retrieval"
            ]
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
                "Vulnerability assessment",
                "Security event investigation"
            ]
        ),
        MCPServerType.WAZUH_INDEXER: MCPServerInfo(
            name="Wazuh Indexer",
            value=MCPServerType.WAZUH_INDEXER.value,
            description="Query the Wazuh Indexer for log analysis, search operations, and cluster health monitoring",
            capabilities=[
                "Log data search and analysis",
                "Index management and statistics",
                "Cluster health monitoring",
                "Document count and storage metrics",
                "Search performance analysis",
                "Data source analytics"
            ]
        ),
        MCPServerType.VELOCIRAPTOR: MCPServerInfo(
            name="Velociraptor",
            value=MCPServerType.VELOCIRAPTOR.value,
            description="Digital forensics and incident response platform for endpoint monitoring and threat hunting",
            capabilities=[
                "Live endpoint forensics",
                "Artifact collection and analysis",
                "Threat hunting across endpoints",
                "Process and network monitoring",
                "File system analysis",
                "Registry investigation",
                "Persistence mechanism detection",
                "Lateral movement hunting",
                "Browser artifact collection",
                "Hardware device tracking"
            ]
        )
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
