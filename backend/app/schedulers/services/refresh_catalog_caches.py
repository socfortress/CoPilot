"""Keep the Detections Catalog's content caches warm (#1072).

The catalog reads from three in-memory caches, all of which load lazily on first
access. Whoever triggers a cold load pays for it inside their request:

* ``rules_cache``   — CoPilot Searches corpus, fetched from GitHub (TTL 30 min)
* ``mitre_matrix``  — MITRE ATT&CK STIX bundle, tens of MB from GitHub with a
  120s client timeout (TTL 24h)
* ``wazuh_rules_cache`` — handled by its own job, see refresh_wazuh_rules_cache

With none of them warmed, `/catalog/stories` was measured at **130 seconds** and
`/catalog/stats` at 76s — and only ~2% of that was event-loop stall, i.e. it was
almost entirely a user request sitting on a GitHub download.

`ensure_loaded()` rather than `refresh()` on purpose: it respects each cache's
own TTL, so this job is a no-op most of the time and does real work exactly when
a cache is about to go stale — always off the request path. The MITRE bundle in
particular must not be re-downloaded every 15 minutes.
"""

from loguru import logger

from app.integrations.copilot_searches.services.copilot_searches import rules_cache
from app.integrations.copilot_searches.services.mitre_coverage import mitre_matrix


async def refresh_catalog_caches() -> None:
    """Load the catalog's GitHub-backed caches if their TTL has expired.

    Each cache is handled independently: GitHub being unreachable for one must
    not stop the other from refreshing, and neither may fail the scheduler job.
    """
    for name, cache in (("CoPilot Searches rules", rules_cache), ("MITRE ATT&CK matrix", mitre_matrix)):
        if not cache.is_stale:
            logger.debug(f"{name} cache is still fresh, skipping")
            continue
        try:
            logger.info(f"Refreshing the {name} cache (stale)")
            await cache.ensure_loaded()
            logger.info(f"{name} cache refreshed")
        except Exception as exc:  # noqa: BLE001 — a cold GitHub must not kill the job
            logger.warning(f"Could not refresh the {name} cache: {exc}. Serving the previous snapshot.")


async def warm_catalog_caches() -> None:
    """Startup warm-up for every catalog cache, including the Wazuh ruleset.

    Detached from startup by the caller: none of these are needed for the app to
    serve traffic, and the Wazuh load alone can take 80–110s.
    """
    # Imported here rather than at module scope so this module stays importable
    # in environments where the wazuh_manager package is unusable (unit tests).
    from app.integrations.copilot_searches.services.wazuh_rules_cache import (
        wazuh_rules_cache,
    )

    await refresh_catalog_caches()

    try:
        await wazuh_rules_cache.ensure_loaded()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not warm the Wazuh rules cache at startup: {exc}")

    # The sidebar's InfluxDB indicator is refreshed on the same principle: filled
    # in here so the first sidebar load after a restart already has a value.
    from app.schedulers.services.refresh_sidebar_health import refresh_sidebar_health

    await refresh_sidebar_health()
