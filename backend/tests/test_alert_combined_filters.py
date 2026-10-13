"""``GET /incidents/db_operations/alerts/filter``: combined criteria, a date range, and one
visibility for the page and its count (#1245).

The count used to skip tag RBAC that the page applied, so ``total_filtered`` could count
alerts the user cannot see (phantom pages, and a hint of what is hidden). Mocked
session; no database. The SQL runs for real in tests/e2e/alert_filters_e2e.py.

Run with: cd backend && python -m pytest tests/test_alert_combined_filters.py
"""

import asyncio
import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import literal  # noqa: E402

import app.incidents.routes.db_operations as routes  # noqa: E402
import app.incidents.services.db_operations as dbo  # noqa: E402
from app.time_utils import to_naive_utc  # noqa: E402

USER = SimpleNamespace(id=7, username="acme.viewer", role_id=4)


def _sql(clauses) -> str:
    return " AND ".join(str(clause.compile(compile_kwargs={"literal_binds": True})) for clause in clauses)


# ── criteria ──────────────────────────────────────────────────────────────


def test_no_criteria_add_no_clause():
    assert dbo._alert_criteria() == []


def test_every_criterion_combines():
    clauses = dbo._alert_criteria(
        alert_title="login",
        status="OPEN",
        source="wazuh",
        asset_name="web-01",
        tags=["phishing", "vip"],
        date_from=datetime(2026, 10, 1),
        date_to=datetime(2026, 10, 13, 23, 59, 59),
    )
    sql = _sql(clauses)
    assert len(clauses) == 7
    assert "alert_name LIKE '%login%'" in sql
    assert "status = 'OPEN'" in sql and "source = 'wazuh'" in sql and "asset_name = 'web-01'" in sql
    assert "tag IN ('phishing', 'vip')" in sql  # any of the tags
    assert "alert_creation_time >= '2026-10-01 00:00:00'" in sql
    assert "alert_creation_time <= '2026-10-13 23:59:59'" in sql


def test_a_range_may_be_open_on_either_side():
    assert "alert_creation_time >=" in _sql(dbo._alert_criteria(date_from=datetime(2026, 10, 1)))
    assert "alert_creation_time <=" in _sql(dbo._alert_criteria(date_to=datetime(2026, 10, 1)))


def test_aware_times_become_naive_utc_like_the_column():
    rome = timezone(timedelta(hours=2))
    assert to_naive_utc(datetime(2026, 10, 1, 0, 0, tzinfo=rome)) == datetime(2026, 9, 30, 22, 0)
    assert to_naive_utc(datetime(2026, 10, 1, 9, 0)) == datetime(2026, 10, 1, 9, 0)
    assert to_naive_utc(None) is None


# ── the count shares the page's visibility ────────────────────────────────


def test_the_count_applies_the_visibility_it_is_given():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=3)))
    marker = literal("VISIBILITY") == literal("VISIBILITY")

    total = asyncio.run(dbo.alerts_total_multiple_filters(db=session, status="OPEN", visibility=[marker]))

    assert total == 3
    sql = str(session.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "'VISIBILITY' = 'VISIBILITY'" in sql and "status = 'OPEN'" in sql


def test_the_page_uses_the_given_visibility_instead_of_its_own_tag_check():
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    marker = literal("VISIBILITY") == literal("VISIBILITY")

    with patch.object(dbo.tag_access_handler, "build_alert_query_filters", AsyncMock()) as own_tag_check:
        asyncio.run(dbo.list_alerts_multiple_filters(db=session, user=USER, visibility=[marker]))

    own_tag_check.assert_not_awaited()
    sql = str(session.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "'VISIBILITY' = 'VISIBILITY'" in sql


def test_tag_visibility_compiles_inside_a_query_that_joins_the_tag_table():
    """A tag-restricted analyst's EXISTS clauses must correlate on Alert only.

    The filtered list joins AlertToTag for its tag criterion; auto-correlation took
    that table out of the subquery too and every such list failed with
    "returned no FROM clauses" (found by tests/e2e/alert_filters_e2e.py).
    """
    restricted = {"accessible_tags": {5}, "include_untagged": True, "default_tag_id": None}
    with (
        patch.object(dbo.customer_access_handler, "resolve_effective_customers", AsyncMock(return_value=["ACME"])),
        patch.object(dbo.tag_access_handler, "build_alert_query_filters", AsyncMock(return_value=restricted)),
    ):
        visibility = asyncio.run(dbo.alert_visibility_filters_for_user(USER, AsyncMock()))

    query = (
        dbo.select(dbo.Alert)
        .join(dbo.AlertToTag, dbo.AlertToTag.alert_id == dbo.Alert.id, isouter=True)
        .join(dbo.AlertTag, dbo.AlertToTag.tag_id == dbo.AlertTag.id, isouter=True)
        .where(*visibility)
    )
    sql = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert sql.count("FROM incident_management_alert_to_tag") == 2  # one per EXISTS


# ── the route ─────────────────────────────────────────────────────────────


def _call(**params):
    defaults = dict(
        assigned_to=None,
        alert_title=None,
        customer_codes=None,
        source=None,
        asset_name=None,
        status=None,
        tags=None,
        ioc_value=None,
        verdict=None,
        verdict_reason=None,
        date_from=None,
        date_to=None,
        page=1,
        page_size=25,
        order="desc",
        current_user=USER,
        db=AsyncMock(),
    )
    return asyncio.run(routes.list_alerts_multiple_filters_endpoint(**{**defaults, **params}))


def _patched(visibility):
    listed = AsyncMock(return_value=[])
    counted = AsyncMock(return_value=0)
    patches = [
        patch.object(routes, "alert_visibility_filters_for_user", AsyncMock(return_value=visibility)),
        patch.object(routes, "list_alerts_multiple_filters", listed),
        patch.object(routes, "alerts_total_multiple_filters", counted),
        patch.object(routes, "alert_status_counts_for_user", AsyncMock(return_value=dbo.StatusCounts())),
    ]
    return patches, listed, counted


def _run_with(visibility, **params):
    patches, listed, counted = _patched(visibility)
    for p in patches:
        p.start()
    try:
        response = _call(**params)
    finally:
        for p in patches:
            p.stop()
    return response, listed, counted


def test_page_and_count_get_the_same_visibility_and_criteria():
    visibility = ["<customers and tags>"]
    _, listed, counted = _run_with(visibility, status="OPEN", tags=["vip"], date_from=datetime(2026, 10, 1))

    for call in (listed, counted):
        kwargs = call.await_args.kwargs
        assert kwargs["visibility"] is visibility
        assert (kwargs["status"], kwargs["tags"], kwargs["date_from"]) == ("OPEN", ["vip"], datetime(2026, 10, 1))


def test_the_route_turns_aware_dates_into_naive_utc():
    rome = timezone(timedelta(hours=2))
    _, listed, _ = _run_with([], date_from=datetime(2026, 10, 1, 0, 0, tzinfo=rome))
    assert listed.await_args.kwargs["date_from"] == datetime(2026, 9, 30, 22, 0)


def test_a_user_who_sees_nothing_gets_an_empty_page_without_querying():
    response, listed, counted = _run_with(None, status="OPEN")
    assert (response.alerts, response.total_filtered) == ([], 0)
    listed.assert_not_awaited()
    counted.assert_not_awaited()


def test_a_reversed_range_is_refused():
    with pytest.raises(HTTPException) as exc:
        _call(date_from=datetime(2026, 10, 13), date_to=datetime(2026, 10, 1))
    assert exc.value.status_code == 422
