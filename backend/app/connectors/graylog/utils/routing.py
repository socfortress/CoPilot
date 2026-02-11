from contextvars import ContextVar
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


# Context variable to hold the current Graylog context
_graylog_context: ContextVar[Optional[GraylogContext]] = ContextVar(
    "graylog_context",
    default=None,
)


def set_graylog_context(context: GraylogContext) -> None:
    """
    Sets the Graylog context for the current async context.
    This should be called at the route/entry point level.

    Args:
        context (GraylogContext): The Graylog context to use for subsequent calls.
    """
    logger.debug(f"Setting Graylog context to: {context.value}")
    _graylog_context.set(context)


def clear_graylog_context() -> None:
    """
    Clears the Graylog context, reverting to default behavior.
    """
    logger.debug("Clearing Graylog context")
    _graylog_context.set(None)


def get_current_graylog_connector() -> str:
    """
    Gets the current Graylog connector name based on the context.
    Falls back to the default "Graylog" if no context is set.

    Returns:
        str: The connector name to use.
    """
    context = _graylog_context.get()
    if context is not None:
        return context.value
    return GraylogContext.WAZUH.value


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
    If neither is provided, checks for a context variable, then falls back to default.

    Args:
        context (Optional[GraylogContext]): The explicit context to use.
        use_case (Optional[str]): A string identifier for the use case.

    Returns:
        str: The connector name to use for database lookup.
    """
    if context is not None:
        return context.value

    if use_case is not None:
        use_case_lower = use_case.lower()
        mapped_context = CONTEXT_MAPPING.get(use_case_lower, GraylogContext.WAZUH)
        return mapped_context.value

    # Fall back to context variable or default
    return get_current_graylog_connector()
