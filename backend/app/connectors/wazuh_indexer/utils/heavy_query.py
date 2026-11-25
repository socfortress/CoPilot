"""One heavy indexer search at a time, across every CoPilot feature that runs aggregations in the background.

The Wazuh indexer serves other dashboards too (#1319): the firing-stats refresh and its customer slices
(app/integrations/copilot_searches/services/wazuh_firing_stats_cache.py) and the weekly Sysmon noise statistics
(app/active_response/services/sysmon_stats/) take this one slot for each search, so their aggregations never run side by
side. The slot is bound to the running event loop: a new loop (tests, a restart of the app's loop) gets a fresh one.
"""
import asyncio
from typing import Optional

_heavy_slot: Optional[asyncio.Semaphore] = None
_heavy_slot_loop: Optional[asyncio.AbstractEventLoop] = None


def heavy_query_slot() -> asyncio.Semaphore:
    """The process-wide slot for one heavy search (``async with heavy_query_slot(): ...``)."""
    global _heavy_slot, _heavy_slot_loop
    loop = asyncio.get_running_loop()
    if _heavy_slot is None or _heavy_slot_loop is not loop:
        _heavy_slot = asyncio.Semaphore(1)
        _heavy_slot_loop = loop
    return _heavy_slot
