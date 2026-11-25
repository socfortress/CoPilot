"""Settings of the weekly Sysmon noise statistics: environment variables read at call time, and the constants."""
import os
from typing import Optional
from typing import Tuple

import httpx
from loguru import logger

from app.active_response.schema.sysmon_default_sync import SyncMode
from app.active_response.schema.sysmon_stats import SharingMode
from app.active_response.services.sysmon_default_sync import service_url
from app.active_response.services.sysmon_default_sync import sync_mode

JOB_ID = "send_sysmon_stats"
REPORT_PATH = "/v1/sysmon/report"
WITHDRAW_PATH = "/v1/sysmon/report/withdraw"
NOT_ENABLED_DETAIL = "reports are not enabled"

# Report caps (the contract's; contract_v1.py holds the validator's own copies)
MAX_PATTERNS = 70
MAX_FIELDS = 5
MAX_VALUE_LEN = 1024
MAX_RULENAME_LEN = 256
MAX_REPORT_BYTES = 1_572_864
MAX_WITHDRAW_BYTES = 4096
MAX_REPORT_ENDPOINTS = 1_000_000
MAX_PATTERN_EVENTS = 10**9
# A raw value longer than this is dropped before any regex runs on it
MAX_RAW_VALUE_LEN = 4096

# Indexer query sizes
PAIRS_TOTAL = 40
PAIRS_PER_EVENT = 10
STAGE1_ACTOR_SIZE = 25
STAGE0_LABELS_SIZE = 1000
# The customer's computers' names read in stage 1 (only to learn its host names and own domains)
STAGE1_COMPUTERS_SIZE = 500
BUCKET_BUDGET = 20_000
PRECISION_REPORT = 3000
PRECISION_LEAF = 1000
SERVER_TIMEOUT_MARGIN_SECONDS = 5
METADATA_TIMEOUT_SECONDS = 30

# Deadlines (seconds)
TICK_DEADLINE = 1800
CUSTOMER_DEADLINE = 300

# HTTP
HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
REPORT_DEADLINE = 60.0
PROBE_DEADLINE = 15.0
WITHDRAW_DEADLINE = 60.0
MAX_ANSWER_BYTES = 64 * 1024

# The service drops a customer's reports for 120 s after its withdraw; CoPilot waits longer before sending again
REOPTIN_DELAY = 180
# Weeks kept in stats-state.json
STATE_WEEKS_KEPT = 4
# SOCFortress releases remembered for the report's "config" field
RELEASES_KEPT = 20

DEFAULT_INDEX_PATTERN = "wazuh-*,-wazuh-monitoring-*,-wazuh-statistics-*,-wazuh-states-*,-wazuh-vulnerabilities-*,-wazuh-archives-*"
MAX_INDEX_PATTERN_LENGTH = 1000

_ON_VALUES = frozenset({"on", "true", "1", "yes", "enabled"})
_OFF_VALUES = frozenset({"off", "false", "0", "no", "disabled"})


def sharing_mode() -> Tuple[SharingMode, Optional[str]]:
    """
    SYSMON_STATS_SHARING, read at call time, and the raw value when CoPilot does not know it.

    Unset (or empty), it follows SYSMON_DEFAULT_SYNC: a CoPilot that does not pull from SOCFortress does not report to it
    either. A value CoPilot does not know is "off": the kill switch fails closed.
    """
    raw = os.getenv("SYSMON_STATS_SHARING")
    if raw is None or not raw.strip():
        default_sync, _ = sync_mode()
        return (SharingMode.OFF if default_sync is SyncMode.OFF else SharingMode.ON), None
    value = raw.strip().lower()
    if value in _ON_VALUES:
        return SharingMode.ON, None
    if value in _OFF_VALUES:
        return SharingMode.OFF, None
    return SharingMode.OFF, raw.strip()[:64]


def sharing_on() -> bool:
    return sharing_mode()[0] is SharingMode.ON


def _int_env(name: str, default: int, low: int, high: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning(f"{name}={raw[:32]!r} is not a whole number; using {default}")
        return default
    return max(low, min(high, value))


def max_rule_level() -> int:
    """SYSMON_STATS_MAX_RULE_LEVEL: only events of alerts at or below this Wazuh rule level are reported (0..5, default 5:
    only ever stricter). Levels 6 and up are attack-relevant: they are never sent."""
    return _int_env("SYSMON_STATS_MAX_RULE_LEVEL", 5, 0, 5)


def min_endpoints() -> int:
    """SYSMON_STATS_MIN_ENDPOINTS: a pattern seen on fewer of the customer's endpoints is never sent (3..1000, default 3:
    only ever stricter)."""
    return _int_env("SYSMON_STATS_MIN_ENDPOINTS", 3, 3, 1000)


def query_timeout() -> int:
    """SYSMON_STATS_QUERY_TIMEOUT_SECONDS: the budget of one indexer search (10..300, default 60)."""
    return _int_env("SYSMON_STATS_QUERY_TIMEOUT_SECONDS", 60, 10, 300)


def max_customers_per_tick() -> int:
    """SYSMON_STATS_MAX_CUSTOMERS_PER_TICK: customers collected and sent in one tick (1..200, default 50)."""
    return _int_env("SYSMON_STATS_MAX_CUSTOMERS_PER_TICK", 50, 1, 200)


def index_pattern() -> str:
    """SYSMON_STATS_INDEX_PATTERN, or the default when unset or unusable (it travels in the URL path)."""
    raw = (os.getenv("SYSMON_STATS_INDEX_PATTERN") or "").strip()
    if not raw:
        return DEFAULT_INDEX_PATTERN
    if len(raw) > MAX_INDEX_PATTERN_LENGTH or any(ch.isspace() or ord(ch) < 32 for ch in raw) or not raw.strip(","):
        logger.warning("SYSMON_STATS_INDEX_PATTERN is not a usable index pattern; using the default")
        return DEFAULT_INDEX_PATTERN
    return raw


def base_url() -> str:
    """SOCFORTRESS_SYSMON_SYNC_URL (shared with the default sync), without a trailing slash."""
    return service_url()


def endpoint_url(base: str, path: str) -> Tuple[Optional[str], Optional[str]]:
    """The URL of a report route, or why the service URL cannot be used. https only; plain http only to this host
    (testing); no user name, query or fragment."""
    try:
        url = httpx.URL(base)
    except (httpx.InvalidURL, TypeError, ValueError) as e:
        return None, f"SOCFORTRESS_SYSMON_SYNC_URL is not a URL ({type(e).__name__})."
    if not url.host:
        return None, "SOCFORTRESS_SYSMON_SYNC_URL has no host."
    if url.scheme != "https" and not (url.scheme == "http" and url.host in ("localhost", "127.0.0.1", "::1")):
        return None, "SOCFORTRESS_SYSMON_SYNC_URL must be an https URL: this CoPilot's license key is sent with each report."
    if url.userinfo or url.query or url.fragment:
        return None, "SOCFORTRESS_SYSMON_SYNC_URL must have no user name, query or fragment."
    return base + path, None
