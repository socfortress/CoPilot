import asyncio
import json
import os
from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.connectors.influxdb.schema.alerts import AlertStatus
from app.connectors.influxdb.schema.alerts import GetInfluxDBAlertQueryParams
from app.connectors.influxdb.services.alerts import get_influxdb_alerts
from app.connectors.services import ConnectorServices
from app.connectors.wazuh_indexer.services.monitoring import cluster_healthcheck
from app.data_store.data_store_session import create_session as create_minio_session
from app.db.universal_models import AiAnalystJob
from app.db.universal_models import AiAnalystPalaceLesson
from app.db.universal_models import LicenseCache
from app.db.universal_models import NotificationDispatchLog
from app.incidents.models import Alert
from app.incidents.models import AlertTag
from app.incidents.models import AlertToTag
from app.incidents.models import Case
from app.incidents.services.tag_access import get_tag_access_settings
from app.middleware.customer_access import customer_access_handler
from app.middleware.license import get_license
from app.schedulers.models.scheduler import JobMetadata
from app.schedulers.scheduler import get_scheduler_instance
from app.status.schema.context import SidebarHealthIndicator

_SEVERITY_TAGS = {"critical", "high", "medium", "low"}
_AGENT_SYNC_JOB_ID = "agent_sync"
_NOTIFICATION_LOOKBACK_HOURS = 24


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


def _preview_items(items: List[str], limit: int = 3) -> str:
    if not items:
        return ""
    preview = ", ".join(items[:limit])
    if len(items) > limit:
        preview = f"{preview}, +{len(items) - limit} more"
    return preview


def _customer_filter(accessible_customers: List[str]):
    if "*" in accessible_customers:
        return None
    if not accessible_customers:
        return Alert.customer_code.in_([])
    return Alert.customer_code.in_(accessible_customers)


def _case_customer_filter(accessible_customers: List[str]):
    if "*" in accessible_customers:
        return None
    if not accessible_customers:
        return Case.customer_code.in_([])
    return Case.customer_code.in_(accessible_customers)


async def _find_connector(session: AsyncSession, name: str):
    connectors = await ConnectorServices.fetch_all_connectors(session=session)
    return next((connector for connector in connectors if connector.connector_name == name), None)


def _connector_status_indicator(
    *,
    connector_id: str,
    label: str,
    connector,
    category: str,
) -> SidebarHealthIndicator:
    if connector is None:
        return SidebarHealthIndicator(
            id=connector_id,
            status="warning",
            label=label,
            detail="Connector not found in deployment catalog.",
            count=1,
            category=category,
        )
    if connector.connector_enabled and not connector.connector_configured:
        return SidebarHealthIndicator(
            id=connector_id,
            status="error",
            label=label,
            detail="Enabled but not configured.",
            count=1,
            category=category,
        )
    if connector.connector_configured and not connector.connector_verified:
        return SidebarHealthIndicator(
            id=connector_id,
            status="error",
            label=label,
            detail="Configured but verification failed.",
            count=1,
            category=category,
        )
    if not connector.connector_configured:
        return SidebarHealthIndicator(
            id=connector_id,
            status="warning",
            label=label,
            detail="Not configured.",
            count=0,
            category=category,
        )
    return SidebarHealthIndicator(
        id=connector_id,
        status="ok",
        label=label,
        detail="Configured and verified.",
        count=0,
        category=category,
    )


async def build_open_alerts_indicator(session: AsyncSession, user: User) -> SidebarHealthIndicator:
    accessible_customers = await customer_access_handler.get_user_accessible_customers(user, session)
    filters = [
        Alert.status == "OPEN",
        or_(Alert.assigned_to.is_(None), Alert.assigned_to == ""),
    ]
    customer_clause = _customer_filter(accessible_customers)
    if customer_clause is not None:
        filters.append(customer_clause)

    total_result = await session.execute(select(func.count()).select_from(Alert).where(*filters))
    total = int(total_result.scalar() or 0)

    if total == 0:
        return SidebarHealthIndicator(
            id="open_alerts",
            status="ok",
            label="Open alerts",
            detail="No unassigned open alerts.",
            count=0,
            category="triage",
        )

    severity_result = await session.execute(
        select(AlertTag.tag, func.count(func.distinct(Alert.id)))
        .join(AlertToTag, AlertToTag.tag_id == AlertTag.id)
        .join(Alert, Alert.id == AlertToTag.alert_id)
        .where(*filters)
        .group_by(AlertTag.tag),
    )
    severity_parts: List[str] = []
    other_count = total
    for tag, count in severity_result.all():
        if str(tag).lower() in _SEVERITY_TAGS:
            severity_parts.append(f"{tag}: {count}")
            other_count -= int(count)
    if other_count > 0:
        severity_parts.append(f"other: {other_count}")

    status = "error" if total >= 20 else "warning"
    return SidebarHealthIndicator(
        id="open_alerts",
        status=status,
        label="Open alerts",
        detail=f"{total} unassigned — {_preview_items(severity_parts, limit=4)}",
        count=total,
        category="triage",
    )


async def build_my_open_cases_indicator(session: AsyncSession, user: User) -> SidebarHealthIndicator:
    accessible_customers = await customer_access_handler.get_user_accessible_customers(user, session)
    filters = [
        Case.assigned_to == user.username,
        Case.case_status.in_(["OPEN", "IN_PROGRESS"]),
    ]
    customer_clause = _case_customer_filter(accessible_customers)
    if customer_clause is not None:
        filters.append(customer_clause)

    result = await session.execute(select(func.count()).select_from(Case).where(*filters))
    count = int(result.scalar() or 0)

    if count == 0:
        return SidebarHealthIndicator(
            id="my_open_cases",
            status="ok",
            label="My cases",
            detail="No open cases assigned to you.",
            count=0,
            category="triage",
        )

    return SidebarHealthIndicator(
        id="my_open_cases",
        status="warning" if count >= 5 else "ok",
        label="My cases",
        detail=f"{count} open case{'s' if count != 1 else ''} assigned to you.",
        count=count,
        category="triage",
    )


async def build_tag_rbac_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    settings = await get_tag_access_settings(session)
    if settings is None or not settings.enabled:
        return SidebarHealthIndicator(
            id="tag_rbac",
            status="ok",
            label="Tag RBAC",
            detail="Tag-based access control is disabled.",
            count=0,
            category="triage",
        )

    behavior = settings.untagged_alert_behavior.replace("_", " ")
    return SidebarHealthIndicator(
        id="tag_rbac",
        status="warning",
        label="Tag RBAC",
        detail=f"Active — untagged alerts: {behavior}.",
        count=1,
        category="triage",
    )


async def build_ai_analyst_jobs_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    running_result = await session.execute(
        select(func.count()).select_from(AiAnalystJob).where(AiAnalystJob.status == "running"),
    )
    failed_result = await session.execute(
        select(func.count()).select_from(AiAnalystJob).where(AiAnalystJob.status == "failed"),
    )
    running = int(running_result.scalar() or 0)
    failed = int(failed_result.scalar() or 0)

    if failed == 0 and running == 0:
        return SidebarHealthIndicator(
            id="ai_analyst_jobs",
            status="ok",
            label="AI Analyst",
            detail="No running or failed investigations.",
            count=0,
            category="ai",
        )

    detail_parts = []
    if running:
        detail_parts.append(f"{running} running")
    if failed:
        detail_parts.append(f"{failed} failed")

    return SidebarHealthIndicator(
        id="ai_analyst_jobs",
        status="error" if failed else "warning",
        label="AI Analyst",
        detail=", ".join(detail_parts),
        count=failed or running,
        category="ai",
    )


async def build_mem_palace_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    pending_result = await session.execute(
        select(func.count()).select_from(AiAnalystPalaceLesson).where(AiAnalystPalaceLesson.status == "pending"),
    )
    failed_result = await session.execute(
        select(func.count()).select_from(AiAnalystPalaceLesson).where(AiAnalystPalaceLesson.status == "failed"),
    )
    pending = int(pending_result.scalar() or 0)
    failed = int(failed_result.scalar() or 0)

    if pending == 0 and failed == 0:
        return SidebarHealthIndicator(
            id="mem_palace",
            status="ok",
            label="MemPalace queue",
            detail="No pending or failed lessons.",
            count=0,
            category="ai",
        )

    detail_parts = []
    if pending:
        detail_parts.append(f"{pending} pending")
    if failed:
        detail_parts.append(f"{failed} failed")

    return SidebarHealthIndicator(
        id="mem_palace",
        status="error" if failed else "warning",
        label="MemPalace queue",
        detail=", ".join(detail_parts),
        count=failed or pending,
        category="ai",
    )


async def build_notification_dispatch_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    since = datetime.utcnow() - timedelta(hours=_NOTIFICATION_LOOKBACK_HOURS)
    result = await session.execute(
        select(func.count())
        .select_from(NotificationDispatchLog)
        .where(
            NotificationDispatchLog.status == "failed",
            NotificationDispatchLog.dispatched_at >= since,
        ),
    )
    count = int(result.scalar() or 0)

    if count == 0:
        return SidebarHealthIndicator(
            id="notification_dispatch",
            status="ok",
            label="Notifications",
            detail=f"No failed dispatches in the last {_NOTIFICATION_LOOKBACK_HOURS}h.",
            count=0,
            category="operations",
        )

    return SidebarHealthIndicator(
        id="notification_dispatch",
        status="error" if count >= 3 else "warning",
        label="Notifications",
        detail=f"{count} failed dispatch{'es' if count != 1 else ''} in the last {_NOTIFICATION_LOOKBACK_HOURS}h.",
        count=count,
        category="operations",
    )


async def build_talon_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    connector = await _find_connector(session, "Talon")
    return _connector_status_indicator(
        connector_id="talon",
        label="Talon",
        connector=connector,
        category="infrastructure",
    )


async def build_core_soc_tools_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    issues: List[str] = []
    for name in ("Graylog", "Velociraptor"):
        connector = await _find_connector(session, name)
        if connector is None:
            issues.append(f"{name} missing")
        elif connector.connector_enabled and not connector.connector_configured:
            issues.append(f"{name} not configured")
        elif connector.connector_configured and not connector.connector_verified:
            issues.append(name)

    count = len(issues)
    if count == 0:
        return SidebarHealthIndicator(
            id="core_soc_tools",
            status="ok",
            label="Core SOC tools",
            detail="Graylog and Velociraptor are healthy.",
            count=0,
            category="infrastructure",
        )

    return SidebarHealthIndicator(
        id="core_soc_tools",
        status="error" if count >= 2 else "warning",
        label="Core SOC tools",
        detail=_preview_items(issues),
        count=count,
        category="infrastructure",
    )


async def build_wazuh_indexer_indicator() -> SidebarHealthIndicator:
    try:
        response = await cluster_healthcheck()
        if isinstance(response, dict):
            raise RuntimeError(response.get("message", "Cluster health unavailable"))

        cluster = response.cluster_health
        if cluster is None:
            return SidebarHealthIndicator(
                id="wazuh_indexer",
                status="error",
                label="Wazuh indexer",
                detail="Cluster health payload missing.",
                count=1,
                category="infrastructure",
            )

        status_value = str(cluster.status).lower()
        if status_value == "green":
            return SidebarHealthIndicator(
                id="wazuh_indexer",
                status="ok",
                label="Wazuh indexer",
                detail=f"Cluster {cluster.cluster_name} is green.",
                count=0,
                category="infrastructure",
            )
        if status_value == "yellow":
            return SidebarHealthIndicator(
                id="wazuh_indexer",
                status="warning",
                label="Wazuh indexer",
                detail=f"Cluster {cluster.cluster_name} is yellow.",
                count=1,
                category="infrastructure",
            )
        return SidebarHealthIndicator(
            id="wazuh_indexer",
            status="error",
            label="Wazuh indexer",
            detail=f"Cluster {cluster.cluster_name} is {status_value}.",
            count=1,
            category="infrastructure",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Wazuh indexer health check failed: {exc}")
        return SidebarHealthIndicator(
            id="wazuh_indexer",
            status="error",
            label="Wazuh indexer",
            detail="Indexer cluster health is unavailable.",
            count=1,
            category="infrastructure",
        )


async def build_influx_health_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    try:
        response = await get_influxdb_alerts(
            GetInfluxDBAlertQueryParams(
                days=1,
                status=AlertStatus.ACTIVE,
                exclude_ok=True,
                latest_only=True,
                limit=200,
            ),
            session,
        )
        if not response.success:
            return SidebarHealthIndicator(
                id="influx_health",
                status="warning",
                label="Healthchecks",
                detail=response.message or "InfluxDB healthchecks unavailable.",
                count=0,
                category="infrastructure",
            )

        critical_count = sum(1 for alert in response.alerts if str(alert.severity).lower() in {"critical", "error"})
        warn_count = sum(1 for alert in response.alerts if str(alert.severity).lower() == "warn")

        if critical_count == 0 and warn_count == 0:
            return SidebarHealthIndicator(
                id="influx_health",
                status="ok",
                label="Healthchecks",
                detail="No active critical InfluxDB alerts.",
                count=0,
                category="infrastructure",
            )

        detail_parts = []
        if critical_count:
            detail_parts.append(f"{critical_count} critical/error")
        if warn_count:
            detail_parts.append(f"{warn_count} warning")

        return SidebarHealthIndicator(
            id="influx_health",
            status="error" if critical_count else "warning",
            label="Healthchecks",
            detail=f"Active alerts: {', '.join(detail_parts)}.",
            count=critical_count or warn_count,
            category="infrastructure",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Influx health indicator failed: {exc}")
        return SidebarHealthIndicator(
            id="influx_health",
            status="warning",
            label="Healthchecks",
            detail="Unable to query InfluxDB healthchecks.",
            count=0,
            category="infrastructure",
        )


def _parse_license_expiry(expires_raw) -> Optional[datetime]:
    if expires_raw is None:
        return None
    if isinstance(expires_raw, datetime):
        return expires_raw.replace(tzinfo=None) if expires_raw.tzinfo else expires_raw
    if not isinstance(expires_raw, str):
        return None

    normalized = expires_raw.replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(expires_raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


async def _get_license_days_until_expiry(session: AsyncSession) -> Optional[int]:
    license_row = await get_license(session, raise_on_missing=False)
    if license_row is None:
        return None

    result = await session.execute(
        select(LicenseCache).where(LicenseCache.license_key == license_row.license_key).order_by(LicenseCache.cached_at.desc()).limit(1),
    )
    cached = result.scalars().first()
    if cached is None or not cached.license_data:
        return None

    try:
        payload = json.loads(cached.license_data)
    except json.JSONDecodeError:
        return None

    license_obj = None
    if isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("license"), dict):
        license_obj = payload["data"]["license"]
    elif isinstance(payload.get("license"), dict):
        license_obj = payload["license"]

    if license_obj is None:
        return None

    expires_raw = license_obj.get("expires")
    expires_at = _parse_license_expiry(expires_raw)
    if expires_at is None:
        return None

    return (expires_at - datetime.utcnow()).days


async def build_license_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    days_left = await _get_license_days_until_expiry(session)
    if days_left is None:
        return SidebarHealthIndicator(
            id="license",
            status="ok",
            label="License",
            detail="License expiry not available from cache.",
            count=0,
            category="platform",
        )

    if days_left < 0:
        return SidebarHealthIndicator(
            id="license",
            status="error",
            label="License",
            detail="License has expired.",
            count=1,
            category="platform",
        )
    if days_left <= 7:
        return SidebarHealthIndicator(
            id="license",
            status="error",
            label="License",
            detail=f"Expires in {days_left} day{'s' if days_left != 1 else ''}.",
            count=days_left,
            category="platform",
        )
    if days_left <= 30:
        return SidebarHealthIndicator(
            id="license",
            status="warning",
            label="License",
            detail=f"Expires in {days_left} days.",
            count=days_left,
            category="platform",
        )

    return SidebarHealthIndicator(
        id="license",
        status="ok",
        label="License",
        detail=f"Valid for {days_left} more days.",
        count=0,
        category="platform",
    )


async def build_agent_sync_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    scheduler = await get_scheduler_instance()
    now = datetime.utcnow()
    metadata_result = await session.execute(select(JobMetadata).filter_by(job_id=_AGENT_SYNC_JOB_ID))
    metadata = metadata_result.scalars().first()

    if metadata is None:
        return SidebarHealthIndicator(
            id="agent_sync",
            status="warning",
            label="Agent sync",
            detail="Scheduler metadata for agent sync is missing.",
            count=1,
            category="operations",
        )

    if not metadata.enabled:
        return SidebarHealthIndicator(
            id="agent_sync",
            status="warning",
            label="Agent sync",
            detail="Agent sync job is disabled.",
            count=0,
            category="operations",
        )

    job = next((item for item in scheduler.get_jobs() if item.id == _AGENT_SYNC_JOB_ID), None)
    if job is None:
        return SidebarHealthIndicator(
            id="agent_sync",
            status="error",
            label="Agent sync",
            detail="Agent sync is enabled but not scheduled.",
            count=1,
            category="operations",
        )

    if _is_scheduler_job_stale(
        last_success=metadata.last_success,
        time_interval_minutes=metadata.time_interval,
        now=now,
    ):
        last_success = metadata.last_success.isoformat() if metadata.last_success else "never"
        return SidebarHealthIndicator(
            id="agent_sync",
            status="error",
            label="Agent sync",
            detail=f"Last success: {last_success}.",
            count=1,
            category="operations",
        )

    last_success = metadata.last_success.isoformat() if metadata.last_success else "unknown"
    return SidebarHealthIndicator(
        id="agent_sync",
        status="ok",
        label="Agent sync",
        detail=f"Last success: {last_success}.",
        count=0,
        category="operations",
    )


async def build_platform_storage_indicator(session: AsyncSession) -> SidebarHealthIndicator:
    issues: List[str] = []

    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        issues.append(f"Database unreachable ({exc.__class__.__name__})")

    try:
        client = await create_minio_session()
        await asyncio.wait_for(client.list_buckets(), timeout=5.0)
    except Exception as exc:  # noqa: BLE001
        issues.append(f"MinIO unreachable ({exc.__class__.__name__})")

    count = len(issues)
    if count == 0:
        return SidebarHealthIndicator(
            id="platform_storage",
            status="ok",
            label="Platform storage",
            detail="Database and MinIO are reachable.",
            count=0,
            category="platform",
        )

    return SidebarHealthIndicator(
        id="platform_storage",
        status="error",
        label="Platform storage",
        detail=_preview_items(issues, limit=2),
        count=count,
        category="platform",
    )


async def build_scheduler_indicator_excluding_agent_sync(session: AsyncSession) -> SidebarHealthIndicator:
    scheduler = await get_scheduler_instance()
    now = datetime.utcnow()
    stale_jobs: List[str] = []

    for job in scheduler.get_jobs():
        if job.id == _AGENT_SYNC_JOB_ID:
            continue
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
            category="operations",
        )

    return SidebarHealthIndicator(
        id="scheduler",
        status="warning" if count == 1 else "error",
        label="Scheduler",
        detail=_preview_items(stale_jobs),
        count=count,
        category="operations",
    )


def get_environment_name() -> str:
    return os.getenv("ENVIRONMENT", "PRODUCTION")


async def safe_build(builder, *args, **kwargs) -> Optional[SidebarHealthIndicator]:
    try:
        return await builder(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Sidebar indicator {builder.__name__} failed: {exc}")
        return None
