"""Aggregation tests for false-positive reporting (issue #1085, phase 2).

These run against an in-memory SQLite database, following the convention in
`test_customer_report_aggregations.py`: only the `incident_management_*` tables are
created (the wider `universal_models` set declares MySQL-only types), and each test drives
the async helpers via `asyncio.run` since the repo does not use pytest-asyncio.

The invariant under test throughout is that rates are computed against *reviewed* alerts,
never against everything ingested. Dividing by total would make the false-positive rate
improve every time the SOC fell behind on triage, which is exactly backwards.

Run with: cd backend && python -m pytest tests/test_verdict_stats.py
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
from app.incidents.services import verdict_stats as vs  # noqa: E402

CC = "TENANT_A"
CC_B = "TENANT_B"
DATE_FROM = datetime(2026, 5, 1)
DATE_TO = datetime(2026, 8, 1)


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


def _alert(name, customer, created, verdict=None, reason=None):
    return Alert(
        alert_name=name,
        alert_description="d",
        status="CLOSED",
        source="Wazuh",
        customer_code=customer,
        alert_creation_time=created,
        verdict=verdict,
        verdict_reason=reason,
    )


async def _seed(session: AsyncSession) -> None:
    session.add_all(
        [
            # TENANT_A, May: "Backup job" is a noisy detection — 3 FP, 1 TP.
            _alert("Backup job", CC, datetime(2026, 5, 3), "FALSE_POSITIVE", "RULE_TOO_SENSITIVE"),
            _alert("Backup job", CC, datetime(2026, 5, 4), "FALSE_POSITIVE", "RULE_TOO_SENSITIVE"),
            _alert("Backup job", CC, datetime(2026, 5, 5), "FALSE_POSITIVE", "KNOWN_APPLICATION"),
            _alert("Backup job", CC, datetime(2026, 5, 6), "TRUE_POSITIVE"),
            # TENANT_A, June: a genuine detection, plus two never triaged.
            _alert("Ransomware note", CC, datetime(2026, 6, 2), "TRUE_POSITIVE"),
            _alert("Ransomware note", CC, datetime(2026, 6, 3)),
            _alert("Port scan", CC, datetime(2026, 6, 4)),
            # TENANT_B: one FP out of two triaged.
            _alert("Vendor agent", CC_B, datetime(2026, 6, 9), "FALSE_POSITIVE", "KNOWN_APPLICATION"),
            _alert("Vendor agent", CC_B, datetime(2026, 6, 10), "TRUE_POSITIVE"),
            # Outside the window — must be ignored everywhere.
            _alert("Backup job", CC, datetime(2026, 1, 1), "FALSE_POSITIVE", "OTHER"),
        ],
    )
    await session.commit()


def _run(coro_fn):
    async def _inner():
        session = await _make_session()
        await _seed(session)
        try:
            return await coro_fn(session)
        finally:
            await session.close()

    return asyncio.run(_inner())


# --- verdict_counts ---------------------------------------------------------------


def test_counts_are_scoped_to_customer_and_window():
    counts = _run(lambda s: vs.verdict_counts(s, [CC], DATE_FROM, DATE_TO))
    assert counts["total"] == 7  # the January alert is outside the window
    assert counts["false_positive"] == 3
    assert counts["true_positive"] == 2
    assert counts["untriaged"] == 2
    assert counts["reviewed"] == 5


def test_false_positive_rate_divides_by_reviewed_not_total():
    """The invariant. 3 FP of 5 reviewed is 60%; of 7 total it would be 42.9%, and that
    number would improve every time the SOC fell behind on triage."""
    counts = _run(lambda s: vs.verdict_counts(s, [CC], DATE_FROM, DATE_TO))
    assert counts["false_positive_rate"] == 60.0
    assert counts["coverage_rate"] == 71.4  # 5 of 7 triaged


def test_rates_are_none_when_nothing_was_triaged():
    """None rather than 0.0: a period with no triage has no rate, and 0.0 would read as
    "no false positives" instead of "no data"."""

    async def _empty(session):
        session.add(_alert("Untriaged only", "TENANT_C", datetime(2026, 6, 1)))
        await session.commit()
        return await vs.verdict_counts(session, ["TENANT_C"], DATE_FROM, DATE_TO)

    counts = _run(_empty)
    assert counts["reviewed"] == 0
    assert counts["false_positive_rate"] is None
    assert counts["coverage_rate"] == 0.0


def test_none_customer_codes_spans_every_tenant():
    counts = _run(lambda s: vs.verdict_counts(s, None, DATE_FROM, DATE_TO))
    assert counts["false_positive"] == 4  # 3 from TENANT_A + 1 from TENANT_B
    assert counts["reviewed"] == 7


# --- by reason --------------------------------------------------------------------


def test_reasons_ranked_and_scoped_to_false_positives():
    rows = _run(lambda s: vs.false_positives_by_reason(s, [CC], DATE_FROM, DATE_TO))
    assert rows == [("RULE_TOO_SENSITIVE", 2), ("KNOWN_APPLICATION", 1)]


def test_reason_labels_fall_back_to_the_raw_value():
    assert vs.false_positive_reason_label("RULE_TOO_SENSITIVE") == "Detection rule too sensitive"
    assert vs.false_positive_reason_label("A_REASON_ADDED_LATER") == "A_REASON_ADDED_LATER"
    assert vs.false_positive_reason_label(None) == "Unspecified"


# --- by alert name (the tuning list) ----------------------------------------------


def test_tuning_list_reports_count_and_rate_per_detection():
    rows = _run(lambda s: vs.top_false_positives_by_alert_name(s, [CC], DATE_FROM, DATE_TO))
    assert len(rows) == 1  # only "Backup job" produced false positives
    name, fp, reviewed, rate = rows[0]
    assert name == "Backup job"
    assert fp == 3
    assert reviewed == 4  # 3 FP + 1 TP, in-window only
    assert rate == 75.0


def test_tuning_list_excludes_detections_with_no_false_positives():
    """A detection that fired and was confirmed real must not appear on a tuning list."""
    rows = _run(lambda s: vs.top_false_positives_by_alert_name(s, [CC], DATE_FROM, DATE_TO))
    assert "Ransomware note" not in [row[0] for row in rows]


# --- by customer ------------------------------------------------------------------


def test_by_customer_ranks_by_rate_not_raw_count():
    """A small, badly-tuned tenant must not hide behind a large quiet one.

    TENANT_NOISY has a single false positive against TENANT_A's three, so ordering by raw
    count would put it last — but every alert it triaged was a false positive, which is
    the tenant actually worth looking at.
    """

    async def _with_noisy_tenant(session):
        session.add(_alert("All noise", "TENANT_NOISY", datetime(2026, 6, 1), "FALSE_POSITIVE", "OTHER"))
        await session.commit()
        return await vs.false_positives_by_customer(session, None, DATE_FROM, DATE_TO)

    rows = _run(_with_noisy_tenant)
    by_code = {row[0]: row for row in rows}
    assert by_code[CC][1:] == (3, 5, 60.0)
    assert by_code[CC_B][1:] == (1, 2, 50.0)
    assert by_code["TENANT_NOISY"][1:] == (1, 1, 100.0)

    # Ordered by rate descending, so the one-alert tenant leads despite the lowest count.
    assert [row[0] for row in rows] == ["TENANT_NOISY", CC, CC_B]


def test_by_customer_excludes_tenants_with_nothing_triaged():
    """Showing an untriaged tenant at 0% would misreport "not looked at" as "clean"."""

    async def _with_quiet_tenant(session):
        session.add(_alert("Nothing triaged", "TENANT_QUIET", datetime(2026, 6, 1)))
        await session.commit()
        return await vs.false_positives_by_customer(session, None, DATE_FROM, DATE_TO)

    rows = _run(_with_quiet_tenant)
    assert "TENANT_QUIET" not in [row[0] for row in rows]


# --- trend ------------------------------------------------------------------------


def test_trend_buckets_by_month_in_order():
    trend = _run(lambda s: vs.false_positive_trend(s, [CC], DATE_FROM, DATE_TO))
    assert [point["month"] for point in trend] == ["2026-05", "2026-06"]

    may = trend[0]
    assert may["false_positive"] == 3
    assert may["true_positive"] == 1
    assert may["false_positive_rate"] == 75.0

    june = trend[1]
    assert june["false_positive"] == 0
    assert june["true_positive"] == 1
    assert june["untriaged"] == 2
    assert june["false_positive_rate"] == 0.0


def test_trend_month_with_no_triage_has_a_null_rate():
    """So a gap in triage renders as a gap, not as a month with no false positives."""

    async def _untriaged_month(session):
        session.add(_alert("Later", "TENANT_D", datetime(2026, 7, 5)))
        await session.commit()
        return await vs.false_positive_trend(session, ["TENANT_D"], DATE_FROM, DATE_TO)

    trend = _run(_untriaged_month)
    assert trend[0]["month"] == "2026-07"
    assert trend[0]["false_positive_rate"] is None
