"""``POST /incidents/db_operations/alerts/verdict-state`` (#1239): many alerts' verdicts in one call.

UBA follows the verdicts of every incident alert it created; one ``GET /alert/{id}`` each meant one
request (and the full alert with comments, assets and IoCs) per alert per poll. What this pins:

- only the verdict fields, for the requested ids, in one query;
- visibility is ``alert_visibility_filters_for_user``: an alert the caller may not see is reported
  exactly like one that does not exist, so ids cannot be probed across tenants;
- "sees nothing" (``None``) short-circuits instead of running an unfiltered query;
- the id list is bounded.

In-memory SQLite, no MySQL. Run with: cd backend && python -m pytest tests/test_alert_verdict_state.py
"""

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.incidents.routes.db_operations as routes  # noqa: E402
import app.incidents.services.db_operations as services  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.schema.db_operations import MAX_VERDICT_STATE_ALERTS  # noqa: E402
from app.incidents.schema.db_operations import AlertVerdictStateRequest  # noqa: E402

ANALYST = SimpleNamespace(id=2, username="ana", role_id=2)
JUDGED_AT = datetime(2026, 10, 13, 9, 30)


async def _session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    tables = [t for name, t in SQLModel.metadata.tables.items() if name.startswith("incident_management")]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
    session = AsyncSession(engine)
    for customer, verdict in [("acme", "FALSE_POSITIVE"), ("acme", None), ("other", "TRUE_POSITIVE")]:
        session.add(
            Alert(
                alert_name="UBA: jdoe",
                alert_description="d",
                status="OPEN",
                source="uba",
                customer_code=customer,
                alert_creation_time=datetime(2026, 10, 13),
                verdict=verdict,
                verdict_reason="AUTHORIZED_USER" if verdict == "FALSE_POSITIVE" else None,
                verdict_by="ana" if verdict else None,
                verdict_at=JUDGED_AT if verdict else None,
            ),
        )
    await session.commit()
    return session


def _states(alert_ids, visibility):
    """Run the service with ``alert_visibility_filters_for_user`` returning ``visibility(Alert)``."""

    async def run():
        session = await _session()
        with patch.object(services, "alert_visibility_filters_for_user", AsyncMock(return_value=visibility(Alert))):
            return await services.alert_verdict_states(alert_ids, ANALYST, session)

    return asyncio.run(run())


def test_only_the_verdict_fields_of_the_requested_alerts():
    rows, missing = _states([1, 2], lambda _: [])
    assert missing == []
    assert [(r.id, r.verdict, r.verdict_reason, r.verdict_by, r.verdict_at) for r in rows] == [
        (1, "FALSE_POSITIVE", "AUTHORIZED_USER", "ana", JUDGED_AT),
        (2, None, None, None, None),
    ]


def test_another_tenants_alert_reads_like_one_that_does_not_exist():
    rows, missing = _states([3, 1, 999], lambda alert: [alert.customer_code.in_(["acme"])])
    assert [r.id for r in rows] == [1]
    assert missing == [3, 999]  # not visible and nonexistent, alike, in the order asked


def test_a_caller_who_sees_nothing_gets_everything_missing_without_a_query():
    async def run():
        db = AsyncMock()
        with patch.object(services, "alert_visibility_filters_for_user", AsyncMock(return_value=None)):
            result = await services.alert_verdict_states([1, 2, 2], ANALYST, db)
        db.execute.assert_not_awaited()
        return result

    assert asyncio.run(run()) == ([], [1, 2])


def test_the_id_list_is_bounded():
    AlertVerdictStateRequest(alert_ids=list(range(MAX_VERDICT_STATE_ALERTS)))
    with pytest.raises(ValidationError):
        AlertVerdictStateRequest(alert_ids=list(range(MAX_VERDICT_STATE_ALERTS + 1)))
    with pytest.raises(ValidationError):
        AlertVerdictStateRequest(alert_ids=[])


def test_the_route_returns_states_and_missing():
    rows = [SimpleNamespace(id=1, verdict="TRUE_POSITIVE", verdict_reason=None, verdict_note=None, verdict_by="ana", verdict_at=JUDGED_AT)]
    with patch.object(routes, "alert_verdict_states", AsyncMock(return_value=(rows, [7]))) as service:
        response = asyncio.run(routes.get_alert_verdict_states_endpoint(AlertVerdictStateRequest(alert_ids=[1, 7]), ANALYST, AsyncMock()))
    assert service.await_args.args[:2] == ([1, 7], ANALYST)
    assert [(a.id, a.verdict, a.verdict_by) for a in response.alerts] == [(1, "TRUE_POSITIVE", "ana")]
    assert response.missing == [7] and response.success


def test_the_route_is_for_the_soc_not_the_portal():
    from fastapi.routing import APIRoute

    from copilot import app
    from tests.test_customer_user_write_allowlist import _route_scopes

    [route] = [r for r in app.routes if isinstance(r, APIRoute) and r.path == "/api/incidents/db_operations/alerts/verdict-state"]
    assert route.methods == {"POST"}
    assert _route_scopes(route.dependant) == {"admin", "analyst"}
