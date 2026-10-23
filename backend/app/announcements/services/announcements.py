"""SOCFortress announcements shown in the analyst console ("What's new").

SOCFortress publishes a JSON feed (``ANNOUNCEMENTS_FEED_URL``, by default
``feed.json`` in the public ``socfortress/copilot-announcements`` repository). The
backend fetches it, never the browser, so analysts' browsers make no third-party call
for the feed and a deployment whose browsers have no internet still gets it.

* The feed is cached in-process for ``ANNOUNCEMENTS_CACHE_TTL_SECONDS`` (default one
  hour), one fetch at a time; a failed fetch is remembered for five minutes, so an
  unreachable feed costs one 5 s timeout per five minutes, not one per page load.
* A failure of any kind (unreachable, not JSON, too large, wrong shape) is an empty
  list, logged, never an error to the console: announcements are not worth a red toast.
* Every item is validated on its own (``FeedAnnouncement``); a bad one is dropped.
* What a user is sent is filtered here: published and not expired, their role in the
  item's audience (a responder also sees items for analysts), this CoPilot's version
  within the item's range, and no ``promotion`` when ``ANNOUNCEMENTS_HIDE_PROMOTIONS``.
* ``ANNOUNCEMENTS_ENABLED=false`` (air-gapped deployments) makes no request at all.

Which items a user has already seen is kept in their browser, not here.
"""
import asyncio
import json
import os
import time
from datetime import datetime
from typing import AsyncIterator
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

import httpx
from loguru import logger
from packaging.version import Version
from pydantic import ValidationError

from app.announcements.schema.announcements import AnnouncementCategory
from app.announcements.schema.announcements import AnnouncementOut
from app.announcements.schema.announcements import AnnouncementsResponse
from app.announcements.schema.announcements import FeedAnnouncement
from app.auth.models.users import effective_roles
from app.time_utils import now_utc
from app.version.services.version import CURRENT_VERSION

DEFAULT_FEED_URL = "https://raw.githubusercontent.com/socfortress/copilot-announcements/main/feed.json"
FETCH_TIMEOUT_SECONDS = 5.0
MAX_FEED_BYTES = 512 * 1024
MAX_FEED_ITEMS = 200
MAX_VISIBLE_ITEMS = 50
FAILURE_TTL_SECONDS = 300
SUPPORTED_FEED_VERSION = 1


class FeedError(Exception):
    """The feed could not be read or is not a feed. The message is for the log only."""


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _ttl_seconds() -> int:
    raw = os.getenv("ANNOUNCEMENTS_CACHE_TTL_SECONDS", "3600")
    try:
        return max(int(raw), 0)
    except ValueError:
        logger.warning(f"ANNOUNCEMENTS_CACHE_TTL_SECONDS={raw!r} is not an integer; falling back to 3600s")
        return 3600


def announcements_enabled() -> bool:
    return _env_flag("ANNOUNCEMENTS_ENABLED", True)


def feed_url() -> str:
    return (os.getenv("ANNOUNCEMENTS_FEED_URL") or "").strip() or DEFAULT_FEED_URL


def hide_promotions() -> bool:
    return _env_flag("ANNOUNCEMENTS_HIDE_PROMOTIONS", False)


def parse_feed(raw: bytes) -> List[FeedAnnouncement]:
    """The valid items of a feed document, first occurrence of an id winning."""
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as e:
        raise FeedError("the feed is not JSON") from e
    if not isinstance(document, dict) or not isinstance(document.get("announcements"), list):
        raise FeedError("the feed has no 'announcements' list")
    feed_version = document.get("version", SUPPORTED_FEED_VERSION)
    if feed_version != SUPPORTED_FEED_VERSION:
        raise FeedError(f"unsupported feed version {feed_version!r}")

    items: List[FeedAnnouncement] = []
    seen = set()
    dropped = 0
    for entry in document["announcements"][:MAX_FEED_ITEMS]:
        try:
            item = FeedAnnouncement.model_validate(entry)
        except ValidationError as e:
            dropped += 1
            ident = entry.get("id") if isinstance(entry, dict) else None
            logger.warning(f"Announcements feed: dropped item {ident!r}: {e.error_count()} invalid field(s)")
            continue
        if item.id in seen:
            dropped += 1
            logger.warning(f"Announcements feed: dropped duplicate id {item.id!r}")
            continue
        seen.add(item.id)
        items.append(item)
    if dropped:
        logger.info(f"Announcements feed: {len(items)} item(s) kept, {dropped} dropped")
    return items


async def _raw(response: httpx.Response) -> AsyncIterator[bytes]:
    """The raw bytes. A response already read into memory (an in-process transport's, never a
    network one's) is its content, which for an identity body is the raw bytes."""
    if response.is_stream_consumed:
        yield response.content
        return
    async for chunk in response.aiter_raw():
        yield chunk


async def fetch_feed(url: str, transport: Optional[httpx.AsyncBaseTransport] = None) -> List[FeedAnnouncement]:
    """Fetch and parse the feed, reading at most ``MAX_FEED_BYTES`` raw bytes.

    It asks for an uncompressed body and refuses an encoded one, so the cap counts the
    bytes actually held in memory (a compressed body would be inflated before any cap).
    """
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": f"SOCFortress-CoPilot/{CURRENT_VERSION}",
    }
    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT_SECONDS,
        follow_redirects=True,
        max_redirects=3,
        headers=headers,
        transport=transport,
    ) as client:
        async with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise FeedError(f"the feed answered HTTP {response.status_code}")
            encodings = [t.strip().lower() for v in response.headers.get_list("content-encoding") for t in v.split(",")]
            if any(e not in ("", "identity") for e in encodings):
                raise FeedError("the feed answered with a compressed body")
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > MAX_FEED_BYTES:
                raise FeedError("the feed is larger than 512 KB")
            body = bytearray()
            async for chunk in _raw(response):
                body.extend(chunk)
                if len(body) > MAX_FEED_BYTES:
                    raise FeedError("the feed is larger than 512 KB")
    return parse_feed(bytes(body))


# url -> (stored at, items). Monotonic time, so a clock step never keeps an entry forever.
# A failed fetch is stored as an empty list with a shorter life (FAILURE_TTL_SECONDS).
_cache: dict = {}
_lock = asyncio.Lock()


def clear_cache() -> None:
    _cache.clear()


async def get_feed_items(transport: Optional[httpx.AsyncBaseTransport] = None) -> List[FeedAnnouncement]:
    """The feed's valid items, from the cache when it is fresh."""
    url = feed_url()
    ttl = _ttl_seconds()

    def fresh() -> Optional[List[FeedAnnouncement]]:
        entry: Optional[Tuple[float, List[FeedAnnouncement], bool]] = _cache.get(url)
        if entry is None:
            return None
        stored_at, items, ok = entry
        life = ttl if ok else min(ttl, FAILURE_TTL_SECONDS)
        return items if time.monotonic() - stored_at < life else None

    cached = fresh()
    if cached is not None:
        return cached
    async with _lock:
        # Another request may have fetched it while this one waited for the lock.
        cached = fresh()
        if cached is not None:
            return cached
        try:
            items = await fetch_feed(url, transport=transport)
            ok = True
        except (FeedError, httpx.HTTPError) as e:
            logger.warning(f"Announcements feed unavailable: {e}")
            items, ok = [], False
        if ttl:
            _cache[url] = (time.monotonic(), items, ok)
        return items


def _in_version_range(item: FeedAnnouncement, current: Version) -> bool:
    if item.min_version is not None and current < Version(item.min_version):
        return False
    if item.max_version is not None and current > Version(item.max_version):
        return False
    return True


def visible_announcements(
    items: Iterable[FeedAnnouncement],
    role_id: int,
    now: Optional[datetime] = None,
    current_version: str = CURRENT_VERSION,
    without_promotions: bool = False,
) -> List[AnnouncementOut]:
    """The items this user should see, newest first."""
    now = now or now_utc()
    try:
        roles = {role.name for role in effective_roles(role_id)}
    except ValueError:
        return []
    version = Version(current_version)
    visible = [
        item
        for item in items
        if item.published_at <= now
        and (item.expires_at is None or item.expires_at > now)
        and roles.intersection(item.audience)
        and _in_version_range(item, version)
        and not (without_promotions and item.category == AnnouncementCategory.PROMOTION)
    ]
    visible.sort(key=lambda item: item.published_at, reverse=True)
    return [AnnouncementOut.model_validate(item.model_dump()) for item in visible[:MAX_VISIBLE_ITEMS]]


async def announcements_for(role_id: int) -> AnnouncementsResponse:
    if not announcements_enabled():
        return AnnouncementsResponse(success=True, message="Announcements are turned off", enabled=False)
    items = await get_feed_items()
    visible = visible_announcements(items, role_id, without_promotions=hide_promotions())
    return AnnouncementsResponse(
        success=True,
        message=f"{len(visible)} announcement(s)",
        enabled=True,
        announcements=visible,
    )
