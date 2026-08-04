"""Deleting a notification route keeps its dispatch history (#1057).

Deleting any route that had ever dispatched failed with

    (1048, "Column 'route_id' cannot be null")
    UPDATE notification_dispatch_log SET route_id=%s WHERE ... id = %s

Two stacked causes, and fixing either alone leaves the bug:

1. **The ORM nullified the children.** `CustomerNotificationRoute.dispatches`
   was a plain one-to-many with no cascade configured, so `session.delete(route)`
   loaded the collection and tried to de-associate each row by setting
   `route_id = NULL` — a column declared NOT NULL.

2. **The foreign key would have refused anyway.** It was ON DELETE NO ACTION,
   so even with the ORM silenced MySQL would have rejected the delete.

The fix removes both: `route_id` is now a plain indexed column with no FK, and
neither side of the relationship exists. The log is append-only evidence of what
was sent to whom, so it deliberately outlives the route that wrote it — which is
what the delete dialog has always promised.

Only a route that had **never dispatched** could be deleted before, which is why
this survived: every test route was freshly created.

Uses a real in-memory SQLite database, because the bug was in what the ORM
emitted on flush. A mocked session cannot express it — `session.delete` would
just be an AsyncMock that records the call and never issues the UPDATE.

Run with: cd backend && python -m pytest tests/test_notification_route_deletion.py
"""

import asyncio
import os
from datetime import datetime

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from sqlalchemy import inspect as sa_inspect  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.notifications.services.notifications as svc  # noqa: E402
from app.db.universal_models import CustomerNotificationRoute  # noqa: E402
from app.db.universal_models import NotificationDispatchLog  # noqa: E402

CC = "TENANT_A"

# `customers` and `customer_shuffle_integration` are here only because the route
# still has many-to-one relationships to them, which SQLAlchemy resolves while
# processing the delete. They hold no rows in these tests.
_TABLES = [
    "customer_notification_route",
    "notification_dispatch_log",
    "customers",
    "customer_shuffle_integration",
]


async def _make_session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [SQLModel.metadata.tables[t] for t in _TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
    # expire_on_commit=False matches the app's AsyncSessionLocal; the default
    # would expire attributes on commit and refresh them synchronously on next
    # access, which is MissingGreenlet under asyncio.
    return AsyncSession(engine, expire_on_commit=False)


def _route(scope="customer", customer_code=CC):
    return CustomerNotificationRoute(
        name="Test Email",
        scope=scope,
        customer_code=customer_code,
        trigger="alert_created",
        channel="resend",
        destination="",
        enabled=True,
        min_severity="Informational",
        recipient_mode="static",
        config="{}",
        created_at=datetime(2026, 8, 4, 12, 0, 0),
        created_by="admin",
    )


def _log(route_id, dedupe_key):
    return NotificationDispatchLog(
        customer_code=CC,
        alert_id=14,
        entity_type="alert",
        entity_id=14,
        dedupe_key=dedupe_key,
        route_id=route_id,
        trigger="alert_created",
        status="sent",
        dispatched_at=datetime(2026, 8, 4, 12, 5, 0),
    )


async def _seed_route_with_history(session, *, scope="customer", customer_code=CC, entries=3):
    route = _route(scope=scope, customer_code=customer_code)
    session.add(route)
    await session.commit()
    session.add_all([_log(route.id, f"alert:14:{i}") for i in range(entries)])
    await session.commit()
    return route.id


def _run(coro_factory):
    async def run():
        session = await _make_session()
        try:
            return await coro_factory(session)
        finally:
            await session.close()

    return asyncio.run(run())


async def _remaining_logs(session):
    return list((await session.execute(select(NotificationDispatchLog))).scalars().all())


# ── the model shape the fix depends on ────────────────────────────────────


def test_route_id_is_not_a_foreign_key():
    """A real FK makes the retention promise impossible: ON DELETE NO ACTION
    refuses the delete, and any cascade that permits it destroys or blanks the
    audit row. Same convention as incident_management_*.customer_code."""
    fks = SQLModel.metadata.tables["notification_dispatch_log"].c.route_id.foreign_keys

    assert not fks


def test_route_id_is_still_not_null():
    """Attribution has to survive the route. An orphaned row that cannot say
    which route sent it is not much of an audit trail."""
    assert SQLModel.metadata.tables["notification_dispatch_log"].c.route_id.nullable is False


def test_route_id_is_still_indexed():
    """The dispatch-log view filters on it; dropping the FK must not drop the
    index that made those queries cheap."""
    indexed = {tuple(ix.columns.keys()) for ix in SQLModel.metadata.tables["notification_dispatch_log"].indexes}

    assert ("route_id",) in indexed


def test_neither_side_of_the_route_relationship_exists():
    """Their mere existence was cause #1: SQLAlchemy loaded the collection on
    delete and nullified it. Neither was ever traversed."""
    assert not hasattr(CustomerNotificationRoute, "dispatches")
    assert "route" not in sa_inspect(NotificationDispatchLog).relationships


# ── the actual deletion ───────────────────────────────────────────────────


def test_deleting_a_route_with_history_succeeds():
    """The reported bug. Before the fix this raised IntegrityError."""

    async def scenario(session):
        route_id = await _seed_route_with_history(session)
        await svc.delete_route(route_id, CC, session)
        return (await session.get(CustomerNotificationRoute, route_id)), await _remaining_logs(session)

    route, logs = _run(scenario)

    assert route is None
    assert len(logs) == 3


def test_the_log_rows_keep_pointing_at_the_deleted_route():
    """ "Dispatch log entries will be retained" — with attribution intact, so the
    history still answers "which route sent this"."""

    async def scenario(session):
        route_id = await _seed_route_with_history(session)
        await svc.delete_route(route_id, CC, session)
        return route_id, await _remaining_logs(session)

    route_id, logs = _run(scenario)

    assert {log.route_id for log in logs} == {route_id}
    assert all(log.status == "sent" for log in logs)


def test_deleting_an_internal_route_with_history_succeeds():
    """The same defect, reached through the other endpoint. Internal routes are
    where assignment notifications land, so they accumulate history fastest."""

    async def scenario(session):
        route_id = await _seed_route_with_history(session, scope="internal", customer_code=None)
        await svc.delete_internal_route(route_id, session)
        return (await session.get(CustomerNotificationRoute, route_id)), await _remaining_logs(session)

    route, logs = _run(scenario)

    assert route is None
    assert len(logs) == 3


def test_deleting_a_route_that_never_dispatched_still_works():
    """The only case that worked before — it must keep working."""

    async def scenario(session):
        route = _route()
        session.add(route)
        await session.commit()
        await svc.delete_route(route.id, CC, session)
        return await session.get(CustomerNotificationRoute, route.id)

    assert _run(scenario) is None


def test_another_routes_history_is_untouched():
    """Deleting one route must not disturb a sibling's log rows."""

    async def scenario(session):
        doomed = await _seed_route_with_history(session, entries=2)
        keeper = await _seed_route_with_history(session, entries=4)
        await svc.delete_route(doomed, CC, session)
        logs = await _remaining_logs(session)
        return keeper, doomed, logs

    keeper, doomed, logs = _run(scenario)

    assert len([log for log in logs if log.route_id == keeper]) == 4
    assert len([log for log in logs if log.route_id == doomed]) == 2


def test_deleting_a_route_from_the_wrong_customer_is_still_a_404():
    """The tenant check happens before the delete; loosening the FK must not
    loosen that."""
    from fastapi import HTTPException

    async def scenario(session):
        route_id = await _seed_route_with_history(session)
        with pytest.raises(HTTPException) as exc:
            await svc.delete_route(route_id, "SOMEONE_ELSE", session)
        return exc.value.status_code, await _remaining_logs(session)

    status, logs = _run(scenario)

    assert status == 404
    assert len(logs) == 3, "a refused delete must not touch the history either"
