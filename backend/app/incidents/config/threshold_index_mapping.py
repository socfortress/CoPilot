"""
Mapping of Graylog threshold alert SOURCE field values to OpenSearch index patterns.

When a threshold alert arrives from Graylog, the SOURCE custom field (e.g. "wazuh", "DELLSWITCH")
is used to determine which OpenSearch index pattern to query for the underlying events.

Add new entries here as new source types are configured in Graylog threshold alert definitions.
"""

from typing import Dict
from typing import Tuple

from loguru import logger

# Maps SOURCE field value (case-insensitive lookup) to (index_pattern, time_field)
SOURCE_TO_INDEX_CONFIG: Dict[str, Tuple[str, str]] = {
    "wazuh": ("wazuh-*", "timestamp"),
    "office365": ("office365-*", "timestamp"),
}


def get_index_config_for_source(source: str) -> Tuple[str, str]:
    """
    Look up the OpenSearch index pattern and time field for a given SOURCE value.

    Args:
        source: The SOURCE field value from the Graylog threshold alert (e.g. "wazuh", "DELLSWITCH").

    Returns:
        Tuple of (index_pattern, time_field).

    Raises:
        ValueError: If the source is not mapped.
    """
    config = SOURCE_TO_INDEX_CONFIG.get(source.lower())
    if config is None:
        logger.warning(
            f"No index mapping configured for threshold alert source '{source}'. "
            f"Available sources: {list(SOURCE_TO_INDEX_CONFIG.keys())}",
        )
        raise ValueError(
            f"No index mapping configured for threshold alert source '{source}'. "
            f"Add an entry to SOURCE_TO_INDEX_CONFIG in threshold_index_mapping.py.",
        )
    return config
