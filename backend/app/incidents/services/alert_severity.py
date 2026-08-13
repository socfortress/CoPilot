"""Resolving an alert's severity.

`Alert.severity` is nullable, and NULL means **"the source did not tell us"** —
not "unimportant". Wazuh alerts carry a rule level we map from; Office 365,
CrowdStrike, Carbon Black, Huntress and the rest carry no equivalent, so their
alerts land NULL.

Before this existed, that gap was invisible: severity was derived at ingest, used
for the notification, and discarded. An alert from a non-Wazuh source resolved to
`Medium` inside the notification builder, which meant a route gating at *High and
above* silently dropped every one of them.

**Resolution happens here, at read time, not at ingest.** Stamping the fallback
onto the row would freeze it: changing `DEFAULT_ALERT_SEVERITY` would then only
affect alerts created afterwards, and there would be no way to distinguish "the
source said Medium" from "we guessed Medium". Keeping NULL preserves that
distinction and makes the setting take effect immediately, including for alerts
already in the database.

Every read path must come through `severity_of` so they cannot disagree.
"""

from __future__ import annotations

import os
from typing import Any
from typing import Optional

from loguru import logger

#: Ordered least-to-most severe. Mirrors NotificationSeverity in the
#: notifications schema; kept here as plain strings so the incidents module
#: doesn't depend on the notifications one.
SEVERITY_LEVELS = ("Informational", "Low", "Medium", "High", "Critical")

#: Applied when a source gives us nothing.
#:
#: High rather than Critical: loud enough that an unmapped source is never
#: silently suppressed by a sensible route, while leaving "Critical only" as a
#: filter that still means something. A blanket Critical would make min_severity
#: useless for exactly the sources that most need triage — and would remove the
#: main brake on the Resend monthly quota, where severity gating is what stops
#: 1,000 emails evaporating.
#:
#: Deployment-wide and configurable: a SOC that would rather over-notify sets
#: DEFAULT_ALERT_SEVERITY=Critical and changes nothing else.
FALLBACK_SEVERITY = "High"

_ENV_VAR = "DEFAULT_ALERT_SEVERITY"


def default_severity() -> str:
    """The deployment's fallback for alerts whose source gave no severity.

    Read per call rather than cached at import: tests and a future settings UI
    both want to change it without a restart, and this is not a hot path
    relative to the database read that precedes it.

    An unrecognised value falls back rather than raising — a typo in the
    environment should not take down alert ingestion.
    """
    configured = (os.getenv(_ENV_VAR) or "").strip()
    if not configured:
        return FALLBACK_SEVERITY

    for level in SEVERITY_LEVELS:
        if configured.lower() == level.lower():
            return level

    logger.warning(
        f"{_ENV_VAR}={configured!r} is not one of {SEVERITY_LEVELS}; " f"falling back to {FALLBACK_SEVERITY}.",
    )
    return FALLBACK_SEVERITY


def normalize_severity(value: Optional[str]) -> Optional[str]:
    """Coerce a source-supplied severity onto our vocabulary, or None.

    Case-insensitive, because sources are inconsistent about it. Returns None
    for anything unrecognised so the caller stores NULL and the alert resolves
    to the deployment default — better than persisting a value nothing can
    filter on.
    """
    if not value:
        return None
    for level in SEVERITY_LEVELS:
        if str(value).strip().lower() == level.lower():
            return level
    return None


def severity_of(alert: Any) -> str:
    """This alert's effective severity — stored value, or the deployment default.

    Takes the alert (or anything with a `.severity`) rather than the raw string,
    so call sites read as a question about the alert and can't accidentally skip
    the fallback.
    """
    stored = normalize_severity(getattr(alert, "severity", None))
    return stored or default_severity()


def severity_rank(severity: Optional[str]) -> int:
    """Position in SEVERITY_LEVELS, for comparisons. Unknown sorts lowest.

    Callers comparing against a threshold should pass `severity_of(alert)`, not
    `alert.severity` — otherwise a NULL-severity alert ranks below Informational
    and is dropped by every filter, which is the bug this module exists to fix.
    """
    normalized = normalize_severity(severity)
    return SEVERITY_LEVELS.index(normalized) if normalized else -1
