"""Shared fixtures for the SOC Management tests (#1187). Not collected by pytest.

In-memory SQLite with only the tables these tests touch (the wider model set declares
MySQL-only types). One ``StaticPool`` engine per test: the recorder opens sessions of
its own, and they must all see the same database.
"""

import os
from datetime import datetime
from datetime import timedelta
from typing import Optional

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.auth.models.users  # noqa: E402,F401 — registers user/role tables
import app.db.universal_models  # noqa: E402,F401 — registers customers
import app.soc_management.models.sla  # noqa: E402,F401
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.soc_management.models.sla import AlertSlaTracking  # noqa: E402
from app.soc_management.models.sla import CaseSlaTracking  # noqa: E402

T0 = datetime(2026, 9, 1, 8, 0, 0)

_TABLE_PREFIXES = ("incident_management", "soc_sla")
_TABLE_NAMES = ("user", "role", "user_customer_access", "user_tag_access", "role_tag_access", "customers", "customer_portal_sla_settings")


def _tables():
    return [
        table
        for name, table in SQLModel.metadata.tables.items()
        if name.startswith(_TABLE_PREFIXES) and name != "incident_management_customer_reports" or name in _TABLE_NAMES
    ]


class Db:
    """An in-memory database plus a session factory over it."""

    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=_tables()))
        return self

    def session(self) -> AsyncSession:
        return self.factory()

    async def dispose(self) -> None:
        await self.engine.dispose()


async def add_alert(
    session: AsyncSession,
    *,
    name: str = "Brute force",
    customer: str = "ACME",
    status: str = "OPEN",
    severity: Optional[str] = "High",
    source: str = "wazuh",
    assigned_to: Optional[str] = None,
    verdict: Optional[str] = None,
    created: datetime = T0,
) -> Alert:
    alert = Alert(
        alert_name=name,
        alert_description=name,
        status=status,
        customer_code=customer,
        source=source,
        severity=severity,
        assigned_to=assigned_to,
        verdict=verdict,
        alert_creation_time=created,
    )
    session.add(alert)
    await session.commit()
    return alert


async def add_case(
    session: AsyncSession,
    *,
    name: str = "Investigation",
    customer: str = "ACME",
    status: str = "OPEN",
    severity: Optional[str] = None,
    assigned_to: Optional[str] = None,
    created: datetime = T0,
) -> Case:
    case = Case(
        case_name=name,
        case_description=name,
        case_status=status,
        customer_code=customer,
        severity=severity,
        assigned_to=assigned_to,
        case_creation_time=created,
    )
    session.add(case)
    await session.commit()
    return case


def tracking_row(model, key: int, *, opened: datetime = T0, severity: str = "High", tracked: bool = True, **fields):
    """A tracking row with sensible defaults: High alert targets (1h ack, 8h resolve)."""
    defaults = {
        "severity": severity,
        "opened_at": opened,
        "ack_due_at": opened + timedelta(hours=1) if tracked else None,
        "resolve_due_at": opened + timedelta(hours=8) if tracked else None,
        "tracked": tracked,
        "updated_at": opened,
    }
    defaults.update(fields)
    key_name = "alert_id" if model is AlertSlaTracking else "case_id"
    return model(**{key_name: key}, **defaults)


__all__ = ["Db", "T0", "add_alert", "add_case", "tracking_row", "AlertSlaTracking", "CaseSlaTracking"]
