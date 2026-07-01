from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.services import ConnectorServices
from app.integrations.copilot_searches.services.wazuh_rules_cache import (
    wazuh_rules_cache,
)
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.scheduler import get_scheduler_instance
from app.status.schema.context import SidebarContextResponse
from app.status.schema.context import SidebarHealthIndicator
from app.version.services.version import CURRENT_VERSION
from app.version.services.version import check_version_outdated

_VERSION_CACHE: Optional[dict] = None
_VERSION_CACHE_AT: Optional[datetime] = None
_VERSION_CACHE_MINUTES = 30


def _is_scheduler_job_stale(
    *,
    last_success: Optional[datetime],
    time_interval_minutes: int,
    now: datetime,
) -> bool:
    if time_interval_minutes <= 0:
        return False
    if last_success is None:
        return True
    threshold = timedelta(minutes=time_interval_minutes * 2)
    return (now - last_success) > threshold


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
            detail="All enabled connectors are configured and verified.",
            count=0,
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
    )


async def _build_scheduler_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    scheduler = await get_scheduler_instance()
    now = datetime.utcnow()
    stale_jobs: List[str] = []

    for job in scheduler.get_jobs():
        result = await session.execute(select(JobMetadata).filter_by(job_id=job.id))
        metadata = result.scalars().first()
        if metadata is None or not metadata.enabled:
            continue
        if _is_scheduler_job_stale(
            last_success=metadata.last_success,
            time_interval_minutes=metadata.time_interval,
            now=now,
        ):
            stale_jobs.append(job.id)

    count = len(stale_jobs)
    if count == 0:
        return SidebarHealthIndicator(
            id="scheduler",
            status="ok",
            label="Scheduler",
            detail="All enabled jobs ran within their expected interval.",
            count=0,
        )

    preview = ", ".join(stale_jobs[:3])
    if count > 3:
        preview = f"{preview}, +{count - 3} more"

    return SidebarHealthIndicator(
        id="scheduler",
        status="warning" if count == 1 else "error",
        label="Scheduler",
        detail=preview,
        count=count,
    )


async def _build_wazuh_catalog_indicator() -> SidebarHealthIndicator:
    await wazuh_rules_cache.ensure_loaded()

    if wazuh_rules_cache.is_available:
        return SidebarHealthIndicator(
            id="wazuh_catalog",
            status="ok",
            label="Wazuh catalog",
            detail=f"{wazuh_rules_cache.rules_count} rules loaded.",
            count=0,
        )

    reason = wazuh_rules_cache.unavailable_reason or "Wazuh Manager rules are unavailable."
    return SidebarHealthIndicator(
        id="wazuh_catalog",
        status="error",
        label="Wazuh catalog",
        detail=reason,
        count=1,
    )


async def build_sidebar_context(
    *,
    session: AsyncSession,
    user: User,
) -> SidebarContextResponse:
    version_fields = await _get_version_fields()
    indicators: List[SidebarHealthIndicator] = []

    is_admin = user.role_id == RoleEnum.admin.value
    is_analyst_or_admin = user.role_id in (RoleEnum.admin.value, RoleEnum.analyst.value)

    if is_admin:
        indicators.append(await _build_connector_indicator(session))
    if is_analyst_or_admin:
        indicators.append(await _build_scheduler_indicator(session))
    indicators.append(await _build_wazuh_catalog_indicator())

    return SidebarContextResponse(
        success=True,
        message="Sidebar context loaded",
        current_version=version_fields["current_version"],
        latest_version=version_fields.get("latest_version"),
        is_outdated=version_fields.get("is_outdated", False),
        release_url=version_fields.get("release_url"),
        indicators=indicators,
    )
