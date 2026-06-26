"""Audit-log retention — the scheduled prune job (issue #943, Phase 2).

The audit_log table is append-only at the application layer (no purge endpoint). To keep it
from growing without bound, a daily APScheduler job deletes rows older than a configurable
retention window.

Retention is controlled by the AUDIT_LOG_RETENTION_DAYS env var (default 90). Because this is
a compliance audit trail, deployments whose framework mandates a longer minimum should raise
this value; a value <= 0 disables pruning entirely (keep everything forever).
"""
import os
from datetime import datetime
from datetime import timedelta

from loguru import logger
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditLog
from app.db.db_session import async_engine

DEFAULT_AUDIT_LOG_RETENTION_DAYS = 90


def get_retention_days() -> int:
    """Resolve the retention window from AUDIT_LOG_RETENTION_DAYS (default 90).

    Returns 0 (pruning disabled / keep forever) when the value is <= 0. Falls back to the
    default on an unparseable value.
    """
    raw = os.getenv("AUDIT_LOG_RETENTION_DAYS", str(DEFAULT_AUDIT_LOG_RETENTION_DAYS))
    try:
        days = int(raw)
    except (TypeError, ValueError):
        logger.warning(f"Invalid AUDIT_LOG_RETENTION_DAYS={raw!r}; using default {DEFAULT_AUDIT_LOG_RETENTION_DAYS}")
        return DEFAULT_AUDIT_LOG_RETENTION_DAYS
    return days if days > 0 else 0


async def prune_audit_log() -> None:
    """Scheduled job: delete audit_log rows older than the configured retention window."""
    days = get_retention_days()
    if days <= 0:
        logger.info("Audit-log pruning disabled (AUDIT_LOG_RETENTION_DAYS <= 0); keeping all rows")
        return

    cutoff = datetime.utcnow() - timedelta(days=days)
    async with AsyncSession(async_engine) as session:
        result = await session.execute(delete(AuditLog).where(AuditLog.timestamp < cutoff))
        await session.commit()
        deleted = result.rowcount if result.rowcount is not None else 0
        logger.info(f"Audit-log prune: deleted {deleted} row(s) older than {days} days (before {cutoff.isoformat()}Z)")
