"""Shared background-refresh behaviour for the Detections Catalog caches.

Every catalog cache used to load lazily on first access, inside whichever request
happened to arrive on a cold or expired cache. The measurements for #1072 showed
what that costs: `/catalog/stories` at 167s and `/catalog/stats` at 139s, with
only ~3% of it event-loop stall — the rest was a user request sitting on a GitHub
download. Worse, requests arriving during a load queued on the same lock, so the
second pair waited for the first pair to finish waiting.

This mixin gives all four caches the same contract:

* `ensure_fresh_nonblocking()` — never waits. Returns immediately; if the data is
  stale it starts a refresh in the background for the next caller.
* `schedule_background_refresh()` — idempotent, so a burst of requests on a cold
  cache starts *one* download rather than one each.
* `is_loading` — lets the response tell the UI "still loading" instead of
  presenting an empty snapshot as though it were the answer.

The host class supplies `is_stale` and `refresh()`; `refresh()` is expected to
handle its own failures, as all four already do.
"""

import asyncio
from typing import Optional

from loguru import logger


class BackgroundRefreshMixin:
    """Adds non-blocking refresh to a cache exposing `is_stale` and `refresh()`."""

    # Declared for type-checkers; the attribute is created lazily so the mixin
    # needs no cooperation from each cache's __init__.
    _refresh_task: Optional[asyncio.Task] = None

    @property
    def is_loading(self) -> bool:
        """True while a background refresh is in flight."""
        task = getattr(self, "_refresh_task", None)
        return task is not None and not task.done()

    async def ensure_fresh_nonblocking(self) -> None:
        """Trigger a refresh if the data is stale, without making anyone wait."""
        if not self.is_stale:
            return
        self.schedule_background_refresh()

    def schedule_background_refresh(self) -> None:
        """Start a refresh as a detached task, at most one at a time."""
        if self.is_loading:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Called outside an event loop (imports, sync tooling) — nothing to do.
            return
        self._refresh_task = loop.create_task(self._background_refresh())

    async def _background_refresh(self) -> None:
        name = type(self).__name__
        try:
            await self.refresh()
        except Exception as exc:  # noqa: BLE001 — a refresh must never escape into a request
            logger.warning(f"Background refresh of {name} failed: {exc}")
        finally:
            self._refresh_task = None
