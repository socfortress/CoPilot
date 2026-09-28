"""Process-wide cache of resolved Customer Portal branding.

``resolve_effective_branding`` reads the global settings row and a customer's
override row — both carrying a LONGTEXT base64 logo — and it runs on every portal
boot and login, every logo fetch and every branded PDF report. Branding changes only
when an operator saves it, which makes it safe to cache the same way connector
credentials are (``app/connectors/cache.py``):

* every write path invalidates right after its commit (``update_portal_settings``,
  ``set_customer_branding``, ``remove_customer_branding``);
* the TTL is only a backstop for edits that bypass those paths (the table edited
  directly, another backend process).

Invalidation is always *all* entries, never one customer: a change to the global
defaults changes the resolved branding of every customer that inherits a field.

``BRANDING_CACHE_TTL_SECONDS=0`` disables the cache.
"""

import os
import time
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple

from loguru import logger

from app.customer_portal.schema.branding import EffectiveBranding


def _ttl_seconds() -> int:
    raw = os.getenv("BRANDING_CACHE_TTL_SECONDS", "600")
    try:
        return max(int(raw), 0)
    except ValueError:
        logger.warning(f"BRANDING_CACHE_TTL_SECONDS={raw!r} is not an integer; falling back to 600s")
        return 600


TTL_SECONDS = _ttl_seconds()

# customer_code (None = the global defaults) -> (stored at, resolved branding).
# `time.monotonic`, not wall time: a clock step backwards must not keep an entry forever.
_entries: Dict[Optional[str], Tuple[float, EffectiveBranding]] = {}


async def get_or_load(customer_code: Optional[str], loader: Callable[[], Awaitable[EffectiveBranding]]) -> EffectiveBranding:
    """Resolved branding for ``customer_code``, loading it at most once per TTL.

    Hands out a copy, so a caller that mutates its result cannot change what the
    next caller sees.
    """
    if TTL_SECONDS:
        entry = _entries.get(customer_code)
        if entry is not None and time.monotonic() - entry[0] < TTL_SECONDS:
            return entry[1].model_copy()

    branding = await loader()
    if TTL_SECONDS:
        _entries[customer_code] = (time.monotonic(), branding.model_copy())
    return branding


def invalidate_all() -> None:
    """Forget every entry. Call after committing any write to either branding table."""
    _entries.clear()
