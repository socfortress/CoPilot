"""Whether a newer talon-analyst release than the running one is out: the "<version> available"
badge beside Talon's version on the AI Analyst page's Overview banner (``GET /api/talon/health``'s
``latest_version`` and ``update_available``).

- **The newest release** is the highest plain ``X.Y.Z`` tag of ``ghcr.io/socfortress/talon-analyst-api``,
  compared as numbers (0.1.10 is newer than 0.1.9). ``latest``, ``sha-…`` and anything else that isn't
  three dot-separated integers is ignored. ``utils/ghcr_client.py`` asks GHCR, anonymously.
- **``update_available``** is true only when the newest release and the version Talon reports both
  parse as ``X.Y.Z`` and the release is the higher. Anything else (Talon unreachable, ``unknown``, a
  development version, no release found) is false.
- **Cached in-process**: an answer for 12 hours, a failed lookup for 15 minutes, one lookup at a time,
  so the page's refresh never hammers GHCR. A failure of any kind is ``None`` and one info line in
  the log, never an error on the page. The lookup runs beside the calls to Talon under a 3 s deadline
  of its own, so a slow GHCR delays the dashboard by at most that, once per cache period.
- **``TALON_RELEASE_CHECK_ENABLED=false``** (air-gapped deployments) makes no request at all.
"""
import asyncio
import os
import re
import time
from typing import Any
from typing import Iterable
from typing import Optional
from typing import Tuple

from loguru import logger

from app.connectors.talon.utils import ghcr_client

ENABLED_ENV = "TALON_RELEASE_CHECK_ENABLED"
SUCCESS_TTL_SECONDS = 12 * 60 * 60
FAILURE_TTL_SECONDS = 15 * 60
#: Three dot-separated integers, ASCII digits only, nothing before or after.
RELEASE = re.compile(r"([0-9]{1,9})\.([0-9]{1,9})\.([0-9]{1,9})")

Release = Tuple[int, int, int]


def release_check_enabled() -> bool:
    """On unless ``TALON_RELEASE_CHECK_ENABLED`` says otherwise (``false``, ``0``, ``no``, ``off``)."""
    raw = os.getenv(ENABLED_ENV)
    if raw is None or not raw.strip():
        return True
    return raw.strip().lower() in ("1", "true", "yes", "on")


def parse_release(value: Any) -> Optional[Release]:
    """``(X, Y, Z)`` for a plain ``X.Y.Z``; None for anything else."""
    if not isinstance(value, str):
        return None
    match = RELEASE.fullmatch(value)
    if match is None:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def newest_release(tags: Iterable[Any]) -> Optional[str]:
    """The highest plain ``X.Y.Z`` among ``tags``, as tagged; None when there is none."""
    best: Optional[str] = None
    best_key: Optional[Release] = None
    for tag in tags:
        key = parse_release(tag)
        if key is not None and (best_key is None or key > best_key):
            best, best_key = tag, key
    return best


def is_newer(latest: Any, running: Any) -> bool:
    """Whether ``latest`` is a newer ``X.Y.Z`` than ``running``; False unless both parse."""
    latest_key, running_key = parse_release(latest), parse_release(running)
    return latest_key is not None and running_key is not None and latest_key > running_key


def _clock() -> float:
    """Monotonic seconds (tests replace this): a clock step never keeps an entry forever."""
    return time.monotonic()


#: (expires at, the newest release or None after a failure)
_cache: Optional[Tuple[float, Optional[str]]] = None
_lock: Optional[asyncio.Lock] = None


def clear_cache() -> None:
    global _cache, _lock
    _cache = None
    _lock = None


def _fresh() -> Optional[Tuple[float, Optional[str]]]:
    return _cache if _cache is not None and _cache[0] > _clock() else None


async def _lookup() -> Optional[str]:
    try:
        latest = newest_release(await ghcr_client.fetch_tags())
    except ghcr_client.GhcrError as e:
        logger.info(f"Talon release check: {e}")
        return None
    except Exception as e:  # noqa: BLE001 - a value no check foresaw: no badge, never a failed page
        logger.info(f"Talon release check failed ({type(e).__name__})")
        return None
    if latest is None:
        logger.info("Talon release check: GHCR lists no X.Y.Z release of talon-analyst")
    return latest


async def latest_release() -> Optional[str]:
    """The newest talon-analyst release on GHCR, from the cache when it is fresh; None when the
    check is off or the lookup failed. Never raises."""
    global _cache, _lock
    if not release_check_enabled():
        return None
    cached = _fresh()
    if cached is not None:
        return cached[1]
    if _lock is None:
        _lock = asyncio.Lock()
    async with _lock:
        # Another request may have looked it up while this one waited for the lock.
        cached = _fresh()
        if cached is not None:
            return cached[1]
        latest = await _lookup()
        _cache = (_clock() + (SUCCESS_TTL_SECONDS if latest else FAILURE_TTL_SECONDS), latest)
        logger.debug(f"Talon release check: newest release {latest}")
        return latest
