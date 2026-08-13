"""Shared helpers for enriching CoPilot → Shuffle notification payloads.

Both the automatic alert path (`app/incidents/services/incident_alert.py`) and
the analyst-driven case path (`app/incidents/services/incident_case.py`) send
payloads to a customer's Shuffle workflow. Downstream consumers (Teams Adaptive
Cards, ticketing) benefit from a couple of normalized fields that neither path
guaranteed before — a numeric `rule_level` and a human-readable `severity`
label. Keeping the derivation here means both paths map identically. See
GitHub issue #980.
"""
from typing import Any
from typing import Optional


def extract_rule_level(context: Optional[dict]) -> Optional[int]:
    """Pull the Wazuh rule level (1-15) out of an alert context dict.

    Tries the Graylog-flat convention (`rule_level`) first, then the nested
    Wazuh-vanilla shape (`rule.level`). Returns None when neither is present or
    the value can't be coerced to an int, so callers can leave the field null
    rather than guess.
    """
    if not context:
        return None

    candidate: Any = context.get("rule_level")
    if candidate is None:
        rule = context.get("rule")
        if isinstance(rule, dict):
            candidate = rule.get("level")

    if candidate is None:
        return None

    try:
        return int(candidate)
    except (TypeError, ValueError):
        return None


def severity_from_rule_level(rule_level: Optional[int]) -> Optional[str]:
    """Map a Wazuh rule level to a normalized severity label.

    | rule_level | severity  |
    |------------|-----------|
    | 12-15      | Critical  |
    | 8-11       | High      |
    | 4-7        | Medium    |
    | 1-3        | Low       |

    Returns None when `rule_level` is None so downstream tools can distinguish
    "no level available" from a real severity band.
    """
    if rule_level is None:
        return None
    if rule_level >= 12:
        return "Critical"
    if rule_level >= 8:
        return "High"
    if rule_level >= 4:
        return "Medium"
    return "Low"
