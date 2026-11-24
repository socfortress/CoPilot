from typing import Dict
from typing import List

from app.integrations.copilot_mcp.schema.copilot_mcp import ExampleQuestion
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPServerInfo
from app.integrations.copilot_mcp.schema.copilot_mcp import MCPServerType


class ExampleQuestionsService:
    """Service for managing example questions for different MCP servers"""

    # Define example questions for each MCP server type
    _EXAMPLE_QUESTIONS: Dict[MCPServerType, List[ExampleQuestion]] = {
        MCPServerType.THREAT_INTEL: [
            ExampleQuestion(
                question="What is the IP reputation for 8.8.8.8?",
                description="Retrieve the IP reputation for a specific IP address",
                category="threat_intel",
            ),
            ExampleQuestion(
                question="What is the domain analysis for example.com?",
                description="Get threat intelligence data for a specific domain",
                category="threat_intel",
            ),
            ExampleQuestion(
                question="What is the file hash analysis for 1234567890abcdef1234567890abcdef?",
                description="Analyze a file hash for malware or other threats",
                category="threat_intel",
            ),
        ],
        MCPServerType.CYBER_NEWS: [
            ExampleQuestion(
                question="What are the latest cyber threat headlines?",
                description="Retrieve the most recent headlines related to cyber threats",
                category="cyber_news",
            ),
            ExampleQuestion(
                question="What vulnerabilities were disclosed this week?",
                description="Get a list of vulnerabilities that were made public in the last week",
                category="cyber_news",
            ),
            ExampleQuestion(
                question="Who are the top threat actors currently?",
                description="Identify the most active threat actors based on recent intelligence",
                category="cyber_news",
            ),
        ],
        MCPServerType.KNOWLEDGEBASE: [
            ExampleQuestion(
                question="How would I configure the Office365 API Integration?",
                description="Configure the Office365 API Integration for optimal performance",
                category="knowledgebase",
            ),
            ExampleQuestion(
                question="How can I create a new index set in Graylog?",
                description="Get best practices for creating index sets in Graylog",
                category="knowledgebase",
            ),
            ExampleQuestion(
                question="How do I upgrade CoPilot?",
                description="Follow these steps to upgrade your CoPilot installation",
                category="knowledgebase",
            ),
        ],
        MCPServerType.ATTACK_SURFACE: [
            ExampleQuestion(
                question="Search for breaches related to email example@company.com",
                description="Explore data breaches involving the specified email address",
                category="attack_surface",
            ),
            ExampleQuestion(
                question="Search for exposures regarding service.example.com",
                description="Explore data exposures involving the specified service",
                category="attack_surface",
            ),
            ExampleQuestion(
                question="Has the password `password123` been exposed?",
                description="Check if a specific password has been involved in any data breaches",
                category="attack_surface",
            ),
        ],
    }

    # Define server information with descriptions and capabilities
    _SERVER_INFO: Dict[MCPServerType, MCPServerInfo] = {
        MCPServerType.THREAT_INTEL: MCPServerInfo(
            name="Threat Intel",
            value=MCPServerType.THREAT_INTEL.value,
            description="Access threat intelligence data, such as IP reputation scores and malware indicators",
            capabilities=[
                "Threat intelligence lookups",
                "IP and domain reputation scoring",
                "File hash and URL analysis",
            ],
        ),
        MCPServerType.CYBER_NEWS: MCPServerInfo(
            name="Cyber News",
            value=MCPServerType.CYBER_NEWS.value,
            description="Access the latest news and updates related to cyber threats and vulnerabilities",
            capabilities=[
                "Vulnerability disclosure tracking",
            ],
        ),
        MCPServerType.KNOWLEDGEBASE: MCPServerInfo(
            name="Knowledgebase",
            value=MCPServerType.KNOWLEDGEBASE.value,
            description="Access documentation and guides for using CoPilot and its integrations",
            capabilities=[
                "Configuration guides",
                "Best practices",
                "Troubleshooting tips",
            ],
        ),
        MCPServerType.ATTACK_SURFACE: MCPServerInfo(
            name="Attack Surface",
            value=MCPServerType.ATTACK_SURFACE.value,
            description="Analyze and manage the attack surface of your organization",
            capabilities=[
                "Attack surface mapping",
                "Exposure management",
                "Risk assessment",
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
