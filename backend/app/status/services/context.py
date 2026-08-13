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


async def build_sidebar_context(
    *,
    session: AsyncSession,
    user: User,
) -> SidebarContextResponse:
    is_admin = user.role_id == RoleEnum.admin.value
    is_analyst_or_admin = user.role_id in (RoleEnum.admin.value, RoleEnum.analyst.value)
    is_customer_user = user.role_id == RoleEnum.customer_user.value

    builders = []

    if is_analyst_or_admin or is_customer_user:
        builders.extend(
            [
                (build_open_alerts_indicator, (session, user), {}),
                (build_my_open_cases_indicator, (session, user), {}),
            ],
        )

    if is_analyst_or_admin:
        builders.extend(
            [
                (build_tag_rbac_indicator, (session,), {}),
                (build_ai_analyst_jobs_indicator, (session,), {}),
                (build_mem_palace_indicator, (session,), {}),
                (build_notification_dispatch_indicator, (session,), {}),
                (build_scheduler_indicator_excluding_agent_sync, (session,), {}),
                (build_agent_sync_indicator, (session,), {}),
                (build_talon_indicator, (session,), {}),
                (build_core_soc_tools_indicator, (session,), {}),
                (build_wazuh_indexer_indicator, (), {}),
                (_build_wazuh_catalog_indicator, (), {}),
                (build_influx_health_indicator, (session,), {}),
            ],
        )
    elif is_customer_user:
        builders.append((_build_wazuh_catalog_indicator, (), {}))

    if is_admin:
        builders.extend(
            [
                (_build_connector_indicator, (session,), {}),
                (build_license_indicator, (session,), {}),
                (build_platform_storage_indicator, (session,), {}),
            ],
        )

    # The version check is an outbound GitHub call (cached 30 min, 5s timeout). It
    # used to be awaited before the builders even started, so on a cache miss the
    # whole sidebar waited for it before doing anything else.
    version_fields, indicators = await asyncio.gather(
        _get_version_fields(),
        _gather_indicators(builders),
    )

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
