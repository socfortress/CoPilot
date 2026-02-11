from enum import Enum
from typing import Optional

from loguru import logger


class GraylogContext(Enum):
    """
    Enum to define the context/purpose for Graylog connections.

    WAZUH: Default Graylog instance for Wazuh and third-party integrations (Graylog01)
    NETWORK: Graylog instance for network logs and syslog ingestion (Graylog02)
    """
    WAZUH = "Graylog"
    NETWORK = "Graylog-Network"


# Mapping of specific use cases to their Graylog context
CONTEXT_MAPPING = {
    # Network-related integrations -> Graylog-Network
    "sonicwall": GraylogContext.NETWORK,
    "syslog": GraylogContext.NETWORK,
    "firewall": GraylogContext.NETWORK,
    "network": GraylogContext.NETWORK,
    # Wazuh/default integrations -> Graylog (default)
    "wazuh": GraylogContext.WAZUH,
    "default": GraylogContext.WAZUH,
}


def get_graylog_connector_name(
    context: Optional[GraylogContext] = None,
    use_case: Optional[str] = None,
) -> str:
    """
    Returns the appropriate Graylog connector name based on context or use case.

    Args:
        context (Optional[GraylogContext]): The explicit context to use.
        use_case (Optional[str]): A string identifier for the use case (e.g., "sonicwall", "wazuh").
            Will be used to look up the appropriate context if no explicit context is provided.

    Returns:
        str: The connector name to use for database lookup.

    Examples:
        >>> get_graylog_connector_name(context=GraylogContext.NETWORK)
        'Graylog-Network'
        >>> get_graylog_connector_name(use_case="sonicwall")
        'Graylog-Network'
        >>> get_graylog_connector_name()
        'Graylog'
    """
    if context is not None:
        logger.debug(f"Using explicit Graylog context: {context.value}")
        return context.value

    if use_case is not None:
        use_case_lower = use_case.lower()
        mapped_context = CONTEXT_MAPPING.get(use_case_lower, GraylogContext.WAZUH)
        logger.debug(f"Mapped use case '{use_case}' to Graylog context: {mapped_context.value}")
        return mapped_context.value

    # Default to primary Graylog
    logger.debug("Using default Graylog context")
    return GraylogContext.WAZUH.value


def is_network_graylog_configured() -> bool:
    """
    Helper function to check if the network Graylog connector exists.
    This can be used to gracefully fall back to the default Graylog if needed.

    Returns:
        bool: True if Graylog-Network connector is configured.
    """
    # This would need to be implemented with a DB check
    # For now, return True assuming it's configured
    return True
