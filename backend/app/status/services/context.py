from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.services import ConnectorServices
from app.integrations.copilot_searches.services.wazuh_rules_cache import (
    wazuh_rules_cache,
)
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
    await wazuh_rules_cache.ensure_loaded()

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


async def build_sidebar_context(
    *,
    session: AsyncSession,
    user: User,
) -> SidebarContextResponse:
    version_fields = await _get_version_fields()

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

    indicators: List[SidebarHealthIndicator] = []
    for builder, args, kwargs in builders:
        indicator = await safe_build(builder, *args, **kwargs)
        if indicator is not None:
            indicators.append(indicator)

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
