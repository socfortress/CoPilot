"""Unit tests for the customer-report aggregation queries.

These run against an in-memory SQLite database. Only the ``incident_management_*``
tables are created (they use portable column types) — the wider
``universal_models`` set is skipped because it declares MySQL-only types
(``LONGTEXT``) that SQLite cannot compile.

Following the repo convention (no pytest-asyncio), each test drives the async
helpers via ``asyncio.run``.

Run with: cd backend && python -m pytest tests/test_customer_report_aggregations.py
"""
import asyncio
import os
from datetime import datetime

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import AlertTag  # noqa: E402
from app.incidents.models import AlertToTag  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.services import customer_report_aggregations as agg  # noqa: E402

CC = "TENANT_A"
DATE_FROM = datetime(2026, 5, 1, 0, 0, 0)
DATE_TO = datetime(2026, 7, 1, 0, 0, 0)


def _incident_tables():
    return [t for name, t in SQLModel.metadata.tables.items() if name.startswith("incident_management")]


async def _make_session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=_incident_tables()))
    return AsyncSession(engine)


async def _seed(session: AsyncSession) -> None:
    # Alerts: two in-window (Wazuh/OPEN, Sentinel/CLOSED), one out-of-window (ignored),
    # one for a different customer (ignored).
    alerts = [
        Alert(
            alert_name="Phish",
            alert_description="d",
            status="OPEN",
            source="Wazuh",
            customer_code=CC,
            alert_creation_time=datetime(2026, 5, 10),
        ),
        Alert(
            alert_name="Phish",
            alert_description="d",
            status="OPEN",
            source="Wazuh",
            customer_code=CC,
            alert_creation_time=datetime(2026, 6, 12),
        ),
        Alert(
            alert_name="Malware",
            alert_description="d",
            status="CLOSED",
            source="Sentinel",
            customer_code=CC,
            alert_creation_time=datetime(2026, 6, 15),
        ),
        Alert(
            alert_name="Old",
            alert_description="d",
            status="OPEN",
            source="Wazuh",
            customer_code=CC,
            alert_creation_time=datetime(2026, 1, 1),
        ),
        Alert(
            alert_name="Other",
            alert_description="d",
            status="OPEN",
            source="Wazuh",
            customer_code="TENANT_B",
            alert_creation_time=datetime(2026, 6, 1),
        ),
    ]
    session.add_all(alerts)
    await session.flush()

    tag = AlertTag(tag="Malicious")
    session.add(tag)
    await session.flush()
    session.add(AlertToTag(alert_id=alerts[0].id, tag_id=tag.id))
    session.add(AlertToTag(alert_id=alerts[1].id, tag_id=tag.id))

    # Cases: one open (created in-window), one closed-in-window, one still-open created
    # before the window (active), one closed before the window (excluded).
    cases = [
        Case(
            case_name="[RFI] Q",
            case_description="x",
            case_status="OPEN",
            customer_code=CC,
            case_creation_time=datetime(2026, 5, 20),
            case_closed_time=None,
        ),
        Case(
            case_name="Incident",
            case_description="x",
            case_status="CLOSED",
            customer_code=CC,
            case_creation_time=datetime(2026, 6, 1),
            case_closed_time=datetime(2026, 6, 20),
        ),
        Case(
            case_name="Legacy open",
            case_description="x",
            case_status="OPEN",
            customer_code=CC,
            case_creation_time=datetime(2026, 1, 1),
            case_closed_time=None,
        ),
        Case(
            case_name="Legacy closed",
            case_description="x",
            case_status="CLOSED",
            customer_code=CC,
            case_creation_time=datetime(2026, 1, 1),
            case_closed_time=datetime(2026, 2, 1),
        ),
    ]
    session.add_all(cases)
    await session.commit()


def _run(coro_factory):
    async def _wrapper():
        session = await _make_session()
        try:
            await _seed(session)
            return await coro_factory(session)
        finally:
            await session.close()

    return asyncio.run(_wrapper())


def test_count_alerts_in_window_and_tenant():
    assert _run(lambda s: agg.count_alerts(s, CC, DATE_FROM, DATE_TO)) == 3


def test_alerts_by_source():
    result = dict(_run(lambda s: agg.alerts_by_source(s, CC, DATE_FROM, DATE_TO)))
    assert result == {"Wazuh": 2, "Sentinel": 1}


def test_alerts_by_status():
    result = dict(_run(lambda s: agg.alerts_by_status(s, CC, DATE_FROM, DATE_TO)))
    assert result == {"OPEN": 2, "CLOSED": 1}


def test_top_alerts_by_name():
    result = _run(lambda s: agg.top_alerts_by_name(s, CC, DATE_FROM, DATE_TO))
    assert result[0] == ("Phish", 2)


def test_top_tags():
    result = dict(_run(lambda s: agg.top_tags(s, CC, DATE_FROM, DATE_TO)))
    assert result == {"Malicious": 2}


def test_active_case_counts():
    # Active in window: two created in-window + the legacy-open one = 3.
    assert _run(lambda s: agg.count_cases(s, CC, DATE_FROM, DATE_TO)) == 3


def test_open_closed_counts():
    open_cases, closed_cases = _run(lambda s: agg.open_closed_case_counts(s, CC, DATE_FROM, DATE_TO))
    assert (open_cases, closed_cases) == (2, 1)


def test_monthly_trend_buckets():
    trend = _run(lambda s: agg.monthly_trend(s, CC, DATE_FROM, DATE_TO))
    by_month = {row["month"]: row for row in trend}
    assert by_month["2026-05"]["alerts"] == 1
    assert by_month["2026-06"]["alerts"] == 2
    # Cases created in-window: 2026-05 (1) and 2026-06 (1).
    assert by_month["2026-05"]["cases"] == 1
    assert by_month["2026-06"]["cases"] == 1


def test_fetch_active_cases_limit_and_total():
    cases, total = _run(lambda s: agg.fetch_active_cases(s, CC, DATE_FROM, DATE_TO, limit=2))
    assert total == 3
    assert len(cases) == 2


def test_empty_period_is_safe():
    # A period entirely *before* any record exists: no alerts, and no cases
    # (nothing was created on or before date_to, so even still-open cases do not
    # count as active yet).
    empty_from = datetime(2020, 1, 1)
    empty_to = datetime(2020, 2, 1)
    assert _run(lambda s: agg.count_alerts(s, CC, empty_from, empty_to)) == 0
    assert _run(lambda s: agg.count_cases(s, CC, empty_from, empty_to)) == 0
    assert _run(lambda s: agg.monthly_trend(s, CC, empty_from, empty_to)) == []


def test_cases_reported_by_type():
    # Cases created in-window: "[RFI] Q" and "Incident" (no bracket prefix -> OTROS).
    result = _run(lambda s: agg.cases_reported_by_type(s, CC, DATE_FROM, DATE_TO))
    assert result["RFI"] == 1
    assert result["OTROS"] == 1
    assert result["INC"] == 0
    assert result["total"] == 2


def test_fetch_open_cases_excludes_closed():
    cases, total = _run(lambda s: agg.fetch_open_cases(s, CC, DATE_FROM, DATE_TO))
    # Two open cases active in the window (one created in-window, one legacy-open).
    assert total == 2
    assert all(c.case_closed_time is None for c in cases)


def test_fetch_closed_cases_only_closed_in_period():
    cases, total = _run(lambda s: agg.fetch_closed_cases(s, CC, DATE_FROM, DATE_TO))
    # Only the case closed on 2026-06-20 falls in the window (legacy closed 2026-02 does not).
    assert total == 1
    assert all(c.case_closed_time is not None for c in cases)


def test_still_open_case_counts_as_active_in_later_window():
    # A case created before the window that is still open is "active" during the
    # window (open question #3 in the issue: include still-open pre-window cases).
    future_from = datetime(2030, 1, 1)
    future_to = datetime(2030, 2, 1)
    open_cases, closed_cases = _run(lambda s: agg.open_closed_case_counts(s, CC, future_from, future_to))
    assert open_cases == 2  # the two still-open cases (one in-window-created, one legacy)
    assert closed_cases == 0
