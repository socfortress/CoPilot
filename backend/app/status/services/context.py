import asyncio
import time
from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.services import ConnectorServices
from app.db.db_session import get_db_session
from app.integrations.copilot_searches.services.wazuh_rules_cache import (
    wazuh_rules_cache,
)
from app.middleware.performance import performance_registry
from app.status.schema.context import SidebarContextResponse
from app.status.schema.context import SidebarHealthIndicator
from app.status.services.context_indicators import build_agent_sync_indicator
from app.status.services.context_indicators import build_ai_analyst_jobs_indicator
from app.status.services.context_indicators import build_core_soc_tools_indicator
from app.status.services.context_indicators import build_influx_health_indicator
from app.status.services.context_indicators import build_license_indicator
from app.status.services.context_indicators import build_mem_palace_indicator
from app.status.services.context_indicators import build_my_open_cases_indicator
from app.status.services.context_indicators import build_notification_dispatch_indicator
from app.status.services.context_indicators import build_open_alerts_indicator
from app.status.services.context_indicators import build_platform_storage_indicator
from app.status.services.context_indicators import (
    build_scheduler_indicator_excluding_agent_sync,
)
from app.status.services.context_indicators import build_tag_rbac_indicator
from app.status.services.context_indicators import build_talon_indicator
from app.status.services.context_indicators import build_wazuh_indexer_indicator
from app.status.services.context_indicators import get_environment_name
from app.status.services.context_indicators import safe_build
from app.version.services.version import CURRENT_VERSION
from app.version.services.version import check_version_outdated

_VERSION_CACHE: Optional[dict] = None
_VERSION_CACHE_AT: Optional[datetime] = None
_VERSION_CACHE_MINUTES = 30

# Only attribute per-indicator time when the sidebar was actually slow, so a
# healthy request adds nothing to the session log.
INDICATOR_TIMING_LOG_MS = 1000.0

# How many indicators may hold a database connection at once. One sidebar
# request must not be able to drain the pool (DB_POOL_SIZE + DB_MAX_OVERFLOW)
# while other requests are in flight.
INDICATOR_CONCURRENCY = 6

# The background refresh is deliberately gentler than the request path. It runs
# fourteen builders while real requests are being served, and a measured
# collision tripled a sidebar request's latency: nobody is waiting for this job,
# so it takes fewer connections and finishes a little later.
SHARED_REFRESH_CONCURRENCY = 3


async def _get_version_fields() -> dict:
    global _VERSION_CACHE
    global _VERSION_CACHE_AT

    now = datetime.utcnow()
    if (
        _VERSION_CACHE is not None
        and _VERSION_CACHE_AT is not None
        and (now - _VERSION_CACHE_AT) < timedelta(minutes=_VERSION_CACHE_MINUTES)
    ):
        return _VERSION_CACHE

    try:
        version_check = await check_version_outdated()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Sidebar version check failed: {exc}")
        version_check = {
            "current_version": CURRENT_VERSION,
            "latest_version": None,
            "is_outdated": False,
            "release_url": None,
        }

    _VERSION_CACHE = {
        "current_version": version_check.get("current_version", CURRENT_VERSION),
        "latest_version": version_check.get("latest_version"),
        "is_outdated": bool(version_check.get("is_outdated")),
        "release_url": version_check.get("release_url"),
    }
    _VERSION_CACHE_AT = now
    return _VERSION_CACHE


async def _build_connector_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    connectors = await ConnectorServices.fetch_all_connectors(session=session)
    issues: List[str] = []
    for connector in connectors:
        name = connector.connector_name
        if connector.connector_name in {"Talon", "Graylog", "Velociraptor"}:
            continue
        if connector.connector_enabled and not connector.connector_configured:
            issues.append(f"{name} (not configured)")
        elif connector.connector_configured and not connector.connector_verified:
            issues.append(name)

    count = len(issues)
    if count == 0:
        return SidebarHealthIndicator(
            id="connectors",
            status="ok",
            label="Connectors",
            detail="All other enabled connectors are configured and verified.",
            count=0,
            category="infrastructure",
        )

    preview = ", ".join(issues[:3])
    if count > 3:
        preview = f"{preview}, +{count - 3} more"

    return SidebarHealthIndicator(
        id="connectors",
        status="warning" if count <= 2 else "error",
        label="Connectors",
        detail=preview,
        count=count,
        category="infrastructure",
    )


async def _build_wazuh_catalog_indicator() -> SidebarHealthIndicator:
    # Never block the sidebar on a ruleset download: a cold refresh measured
    # 80-110s against a real Wazuh Manager, and this indicator only reports the
    # cache's state. Show what we have; the refresh lands for the next caller.
    await wazuh_rules_cache.ensure_fresh_nonblocking()

    if wazuh_rules_cache.rules_count == 0 and wazuh_rules_cache.unavailable_reason is None:
        return SidebarHealthIndicator(
            id="wazuh_catalog",
            status="ok",
            label="Wazuh catalog",
            detail="Loading the Wazuh ruleset…",
            count=0,
            category="infrastructure",
        )

    if wazuh_rules_cache.is_available:
        return SidebarHealthIndicator(
            id="wazuh_catalog",
            status="ok",
            label="Wazuh catalog",
            detail=f"{wazuh_rules_cache.rules_count} rules loaded.",
            count=0,
            category="infrastructure",
        )

    reason = wazuh_rules_cache.unavailable_reason or "Wazuh Manager rules are unavailable."
    return SidebarHealthIndicator(
        id="wazuh_catalog",
        status="error",
        label="Wazuh catalog",
        detail=reason,
        count=1,
        category="infrastructure",
    )


async def _run_with_own_session(builder, args, kwargs):
    """Run a builder on a session of its own.

    A single AsyncSession cannot serve two operations at once — concurrent use
    raises, or worse, interleaves results silently. Since every builder now runs
    concurrently, none of them may use the caller's session: each takes a private
    one for its lifetime and returns it immediately.
    """
    if args and isinstance(args[0], AsyncSession):
        async with get_db_session() as own_session:
            return await safe_build(builder, own_session, *args[1:], **kwargs)
    return await safe_build(builder, *args, **kwargs)


async def _gather_indicators(builders) -> List[SidebarHealthIndicator]:
    """Run every indicator concurrently, each on its own database session.

    History, because the shape here is not arbitrary (#1072):

    1. Originally all ~14 builders were awaited in a `for` loop, so the request
       cost the *sum* of them — measured at 15s.
    2. Then the external ones fanned out while the DB-bound ones stayed
       sequential, because they shared the caller's AsyncSession (one session
       cannot serve concurrent operations) and the pool was SQLAlchemy's default
       5+10. That took the sidebar to ~6s, and the per-builder timings then
       showed the sequential DB group *was* the remaining 4.9s.
    3. With the pool raised (20+20), every builder now gets its own session and
       runs concurrently — bounded by a semaphore so one sidebar request cannot
       take the whole pool while other requests are being served.

    The bound is what keeps this safe: without it, a handful of simultaneous
    sidebar loads would each ask for a dozen connections and starve everything
    else, which looks like a slow database rather than a self-inflicted queue.

    Results are reassembled in declaration order, because the sidebar renders
    them in the order they are listed.
    """
    results: dict = {}
    timings: List[tuple] = []
    limiter = asyncio.Semaphore(INDICATOR_CONCURRENCY)

    async def run_one(index, builder, args, kwargs):
        started = time.perf_counter()
        try:
            async with limiter:
                results[index] = await _run_with_own_session(builder, args, kwargs)
        finally:
            timings.append((builder.__name__, (time.perf_counter() - started) * 1000.0))

    started = time.perf_counter()
    await asyncio.gather(
        *[run_one(index, builder, args, kwargs) for index, (builder, args, kwargs) in enumerate(builders)],
    )
    total_ms = (time.perf_counter() - started) * 1000.0
    # Kept in the record for continuity with earlier sessions, where it measured
    # the sequential DB group. Nothing is sequential now, so it is always 0.
    sequential_ms = 0.0

    _record_indicator_timings(total_ms, sequential_ms, timings)

    return [results[index] for index in sorted(results) if results[index] is not None]


def _record_indicator_timings(total_ms: float, sequential_ms: float, timings: List[tuple]) -> None:
    """Log which indicators actually cost the time, when the request was slow.

    Gated on a threshold so a healthy sidebar adds nothing to the session file.
    Without this the only way to attribute the remaining seconds is guesswork —
    and the whole point of #1072's instrumentation is not guessing.
    """
    if total_ms < INDICATOR_TIMING_LOG_MS:
        return

    slowest = sorted(timings, key=lambda item: item[1], reverse=True)
    performance_registry.record_event(
        "sidebar_indicators",
        {
            "total_ms": round(total_ms, 1),
            # How much of the total is the DB group, which is deliberately
            # sequential (one shared AsyncSession). If this dominates, the next
            # lever is the connection pool, not more concurrency.
            "sequential_group_ms": round(sequential_ms, 1),
            "builders": [{"name": name, "ms": round(ms, 1)} for name, ms in slowest],
        },
    )
    top = ", ".join(f"{name}={ms:.0f}ms" for name, ms in slowest[:4])
    logger.info(f"Sidebar context took {total_ms:.0f}ms (DB group {sequential_ms:.0f}ms). Slowest: {top}")


# Sidebar indicators split in two by what they depend on (#1072).
#
# Twelve of them are deployment-wide: the same answer for every user, every time.
# Recomputing them inside each request is what kept the sidebar at ~3s even after
# the fan-out — not one slow builder, but a dozen database round-trips contending
# for connections. They are now assembled by a scheduled job and served from
# memory.
#
# Two are genuinely per-user (whose alerts, whose cases) and are still computed
# live. Two queries per request instead of fourteen.
#
# `audiences` mirrors the role gating that used to live in build_sidebar_context;
# order in this list is the order the sidebar renders.
_SHARED_BUILDERS = [
    (build_tag_rbac_indicator, True, {"analyst"}),
    (build_ai_analyst_jobs_indicator, True, {"analyst"}),
    (build_mem_palace_indicator, True, {"analyst"}),
    (build_notification_dispatch_indicator, True, {"analyst"}),
    (build_scheduler_indicator_excluding_agent_sync, True, {"analyst"}),
    (build_agent_sync_indicator, True, {"analyst"}),
    (build_talon_indicator, True, {"analyst"}),
    (build_core_soc_tools_indicator, True, {"analyst"}),
    (build_wazuh_indexer_indicator, False, {"analyst"}),
    (_build_wazuh_catalog_indicator, False, {"analyst", "customer"}),
    (build_influx_health_indicator, True, {"analyst"}),
    (_build_connector_indicator, True, {"admin"}),
    (build_license_indicator, True, {"admin"}),
    (build_platform_storage_indicator, True, {"admin"}),
]

# Kept comfortably longer than the refresh interval so a missed job run cannot
# blank the sidebar; a stale read also triggers a background refresh.
#
# Both this and the job interval were doubled after measuring the refresh
# colliding with a request: the job holds up to SHARED_REFRESH_CONCURRENCY connections
# for ~3s, and when that landed on top of a sidebar request the request's own two
# queries went from ~0.5s to ~1.6s each. Health indicators do not move on a
# minute scale, so refreshing half as often costs nothing and halves the chance
# of that collision.
SHARED_INDICATORS_TTL_SECONDS = 600

_shared_indicators: Optional[List[SidebarHealthIndicator]] = None
_shared_indicators_at: Optional[datetime] = None
_shared_audiences: List[set] = []
_shared_refresh_lock = asyncio.Lock()
_shared_refresh_task: Optional[asyncio.Task] = None


def _shared_indicators_are_fresh() -> bool:
    if _shared_indicators is None or _shared_indicators_at is None:
        return False
    return datetime.utcnow() - _shared_indicators_at < timedelta(seconds=SHARED_INDICATORS_TTL_SECONDS)


async def refresh_shared_indicators() -> None:
    """Recompute every deployment-wide indicator. Called by the scheduler.

    This is the only place that pays for them. It runs them concurrently on
    private sessions, exactly as the request path used to.
    """
    global _shared_indicators
    global _shared_indicators_at
    global _shared_audiences

    if _shared_refresh_lock.locked():
        return

    async with _shared_refresh_lock:
        builders = [(builder, ((None,) if needs_session else ()), {}) for builder, needs_session, _ in _SHARED_BUILDERS]
        indicators, audiences = await _gather_shared(builders)
        _shared_indicators = indicators
        _shared_audiences = audiences
        _shared_indicators_at = datetime.utcnow()


async def _gather_shared(builders):
    """Run the shared builders and keep each one's audience alongside its result."""
    results: dict = {}
    timings: List[tuple] = []
    limiter = asyncio.Semaphore(SHARED_REFRESH_CONCURRENCY)

    async def run_one(index, builder, args, kwargs):
        started = time.perf_counter()
        try:
            async with limiter:
                # A `None` placeholder means "this builder wants a session"; it is
                # replaced by a private one inside _run_with_own_session.
                if args and args[0] is None:
                    async with get_db_session() as own_session:
                        results[index] = await safe_build(builder, own_session, *args[1:], **kwargs)
                else:
                    results[index] = await safe_build(builder, *args, **kwargs)
        finally:
            timings.append((builder.__name__, (time.perf_counter() - started) * 1000.0))

    started = time.perf_counter()
    await asyncio.gather(*[run_one(i, b, a, k) for i, (b, a, k) in enumerate(builders)])
    _record_indicator_timings((time.perf_counter() - started) * 1000.0, 0.0, timings)

    indicators, audiences = [], []
    for index, (_, _, audience) in enumerate(_SHARED_BUILDERS):
        indicator = results.get(index)
        if indicator is not None:
            indicators.append(indicator)
            audiences.append(audience)
    return indicators, audiences


def _schedule_shared_refresh() -> None:
    """Start a refresh in the background, at most one at a time."""
    global _shared_refresh_task

    if _shared_refresh_task is not None and not _shared_refresh_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    async def run():
        global _shared_refresh_task
        try:
            await refresh_shared_indicators()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Background sidebar indicator refresh failed: {exc}")
        finally:
            _shared_refresh_task = None

    _shared_refresh_task = loop.create_task(run())


def _visible_shared_indicators(audience_tags: set) -> List[SidebarHealthIndicator]:
    """The cached indicators this role may see, in declaration order."""
    if _shared_indicators is None:
        return []
    return [indicator for indicator, audience in zip(_shared_indicators, _shared_audiences) if audience & audience_tags]


async def build_sidebar_context(
    *,
    session: AsyncSession,
    user: User,
) -> SidebarContextResponse:
    is_admin = user.role_id == RoleEnum.admin.value
    is_analyst_or_admin = user.role_id in (RoleEnum.admin.value, RoleEnum.analyst.value)
    is_customer_user = user.role_id == RoleEnum.customer_user.value

    audience_tags = set()
    if is_analyst_or_admin:
        audience_tags.add("analyst")
    if is_customer_user:
        audience_tags.add("customer")
    if is_admin:
        audience_tags.add("admin")

    # Only the per-user indicators are computed live.
    personal_builders = []
    if is_analyst_or_admin or is_customer_user:
        personal_builders = [
            (build_open_alerts_indicator, (session, user), {}),
            (build_my_open_cases_indicator, (session, user), {}),
        ]

    if not _shared_indicators_are_fresh():
        # Never wait for it: a cold or stale set is filled in for the next caller
        # while this request serves what is already known.
        _schedule_shared_refresh()

    version_fields, personal = await asyncio.gather(
        _get_version_fields(),
        _gather_indicators(personal_builders),
    )

    indicators = personal + _visible_shared_indicators(audience_tags)

    return SidebarContextResponse(
        success=True,
        message="Sidebar context loaded",
        current_version=version_fields["current_version"],
        latest_version=version_fields.get("latest_version"),
        is_outdated=version_fields.get("is_outdated", False),
        release_url=version_fields.get("release_url"),
        environment=get_environment_name(),
        indicators=indicators,
    )
