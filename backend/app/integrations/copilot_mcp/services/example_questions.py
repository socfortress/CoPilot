from typing import Dict, List
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPServerType, ExampleQuestion

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
