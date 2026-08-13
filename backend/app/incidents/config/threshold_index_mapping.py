"""
Mapping of Graylog threshold alert SOURCE field values to OpenSearch index patterns.

Why this mapping has to exist
-----------------------------
A Graylog threshold / aggregation Event Definition does **not** include the source
index pattern in the notification payload it sends to CoPilot. We receive the
``replay_info`` (Lucene query + timerange) and the group-by fields, but *not* the
OpenSearch index the underlying messages actually live in. Graylog knows the
stream/index internally, but it is not exposed on the threshold event.

So when CoPilot needs to go back and pull the contributing events (to build the
alert asset/title and the timeline), it has to be *told* which index pattern a
given SOURCE maps to. That is the sole reason this table exists — it is not a
redundant copy of the ingest-side Incident Management Sources (those describe
per-source field-name mappings, not the physical index a replay query targets).

How a SOURCE is resolved (priority order)
-----------------------------------------
1. ``THRESHOLD_SOURCE_INDEX_MAPPING`` (.env) — a JSON object mapping a SOURCE
   value to either an index-pattern string or a ``[index_pattern, time_field]``
   pair. Lets operators add custom sources without editing code + rebuilding::

       THRESHOLD_SOURCE_INDEX_MAPPING={"bitwarden": "bitwarden-*", "dellswitch": ["dellswitch-*", "timestamp"]}

   Env entries merge over and override the built-in defaults.
2. Built-in defaults — ``wazuh`` and ``office365``, shipped for the common case.
3. Convention fallback — when a SOURCE is not found in either of the above and
   ``THRESHOLD_SOURCE_INDEX_FALLBACK_ENABLED`` is true (the default), CoPilot
   derives ``<source>-*`` with a ``timestamp`` time field. This makes most custom
   sources — whose index follows the ``<source>-*`` naming convention — resolve
   with no configuration at all. Set the flag to false for strict behavior (raise
   instead of guessing).
"""

import json
import os
from typing import Dict
from typing import Tuple

from loguru import logger

# Default OpenSearch time field for threshold replay queries. Overridable per-source
# via the second element of a THRESHOLD_SOURCE_INDEX_MAPPING entry.
DEFAULT_TIME_FIELD = "timestamp"

# Built-in SOURCE (lower-cased) -> (index_pattern, time_field) defaults. Operators
# extend this via THRESHOLD_SOURCE_INDEX_MAPPING rather than editing this dict.
BUILTIN_SOURCE_TO_INDEX_CONFIG: Dict[str, Tuple[str, str]] = {
    "wazuh": ("wazuh-*", DEFAULT_TIME_FIELD),
    "office365": ("office365-*", DEFAULT_TIME_FIELD),
}

_ENV_MAPPING_VAR = "THRESHOLD_SOURCE_INDEX_MAPPING"
_ENV_FALLBACK_VAR = "THRESHOLD_SOURCE_INDEX_FALLBACK_ENABLED"


def _parse_env_mapping() -> Dict[str, Tuple[str, str]]:
    """
    Parse THRESHOLD_SOURCE_INDEX_MAPPING (a JSON object) into a lower-cased
    ``{source: (index_pattern, time_field)}`` dict.

    Each value may be either a string (index pattern; time field defaults to
    ``timestamp``) or a ``[index_pattern, time_field]`` list/tuple. Malformed input
    is logged and skipped rather than raising, so one bad entry can't take down the
    whole threshold flow.
    """
    raw = os.getenv(_ENV_MAPPING_VAR, "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"{_ENV_MAPPING_VAR} is not valid JSON, ignoring it: {e}")
        return {}

    if not isinstance(parsed, dict):
        logger.warning(f"{_ENV_MAPPING_VAR} must be a JSON object of source -> pattern, ignoring it")
        return {}

    mapping: Dict[str, Tuple[str, str]] = {}
    for source, value in parsed.items():
        if isinstance(value, str) and value.strip():
            mapping[source.lower()] = (value.strip(), DEFAULT_TIME_FIELD)
        elif isinstance(value, (list, tuple)) and len(value) >= 1 and value[0]:
            index_pattern = str(value[0]).strip()
            time_field = str(value[1]).strip() if len(value) >= 2 and value[1] else DEFAULT_TIME_FIELD
            mapping[source.lower()] = (index_pattern, time_field)
        else:
            logger.warning(
                f"Ignoring {_ENV_MAPPING_VAR} entry for '{source}': "
                f"expected an index-pattern string or a [index_pattern, time_field] pair.",
            )
    return mapping


def _fallback_enabled() -> bool:
    """Whether an unmapped SOURCE falls back to the ``<source>-*`` convention."""
    return os.getenv(_ENV_FALLBACK_VAR, "true").strip().lower() in ("true", "1", "yes")


def get_configured_sources() -> Dict[str, Tuple[str, str]]:
    """Return the effective explicit mapping (built-in defaults with env overrides applied)."""
    return {**BUILTIN_SOURCE_TO_INDEX_CONFIG, **_parse_env_mapping()}


def get_index_config_for_source(source: str) -> Tuple[str, str]:
    """
    Look up the OpenSearch index pattern and time field for a given SOURCE value.

    Resolution order: THRESHOLD_SOURCE_INDEX_MAPPING (.env) -> built-in defaults ->
    ``<source>-*`` convention fallback (when THRESHOLD_SOURCE_INDEX_FALLBACK_ENABLED).

    Args:
        source: The SOURCE field value from the Graylog threshold alert (e.g. "wazuh", "bitwarden").

    Returns:
        Tuple of (index_pattern, time_field).

    Raises:
        ValueError: If the source is not mapped and the convention fallback is disabled.
    """
    key = source.lower()

    config = get_configured_sources().get(key)
    if config is not None:
        return config

    if _fallback_enabled():
        derived = (f"{key}-*", DEFAULT_TIME_FIELD)
        logger.info(
            f"No explicit index mapping for threshold alert source '{source}'; "
            f"using convention fallback index '{derived[0]}' (time field '{derived[1]}'). "
            f"Set {_ENV_MAPPING_VAR} to override, or {_ENV_FALLBACK_VAR}=false to disable this fallback.",
        )
        return derived

    logger.warning(
        f"No index mapping configured for threshold alert source '{source}' and the "
        f"convention fallback is disabled. Configured sources: {list(get_configured_sources().keys())}",
    )
    raise ValueError(
        f"No index mapping configured for threshold alert source '{source}'. "
        f'Add it to the {_ENV_MAPPING_VAR} env var (e.g. \'{{"{key}": "{key}-*"}}\') '
        f"or enable {_ENV_FALLBACK_VAR}.",
    )
