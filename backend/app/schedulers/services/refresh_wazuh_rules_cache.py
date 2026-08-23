"""Keep the Wazuh ruleset cache warm so no user request ever loads it (#1072).

A cold `wazuh_rules_cache.refresh()` pulls the entire ruleset in one call. On a
real deployment that measured 80–110 seconds, and every request that happened to
find the cache stale inherited the whole of it — `/catalog/stories` was recorded
at 114s, and the sidebar's catalog indicator dragged a piece of page furniture
into the same territory.

Refreshing on a schedule moves that cost off the request path entirely: requests
read whatever snapshot exists, and this job is the only thing that ever waits.
The interval is deliberately shorter than `CACHE_TTL_MINUTES`, so the cache is
renewed before it can go stale under a user.
"""

from loguru import logger

from app.integrations.copilot_searches.services.wazuh_rules_cache import (
    wazuh_rules_cache,
)


async def refresh_wazuh_rules_cache() -> None:
    """Reload the Wazuh ruleset into the in-process cache.

    Never raises: `refresh()` captures connector failures in
    `unavailable_reason` and keeps the previous snapshot, so a Wazuh outage
    degrades the catalog rather than failing the scheduler job.
    """
    logger.info("Scheduled refresh of the Wazuh rules cache starting")
    count = await wazuh_rules_cache.refresh()

    if wazuh_rules_cache.is_available:
        logger.info(f"Scheduled refresh of the Wazuh rules cache completed: {count} rules")
    else:
        logger.warning(
            f"Scheduled refresh of the Wazuh rules cache could not reach Wazuh: {wazuh_rules_cache.unavailable_reason}. "
            f"Serving the previous snapshot ({count} rules).",
        )
