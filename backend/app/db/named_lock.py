"""A MySQL named lock, so only one CoPilot replica runs a job's tick.

The generalisation of the Talon ops poller's ``poll_lock`` (app/connectors/talon/services/talon_ops_notify.py), which
is left as it is. ``GET_LOCK(name, 0)`` (no wait) on a connection of its own, held until the block ends. The name is
the prefix and the current database (two CoPilots on one MySQL server, each with its own database, never take each
other's lock), at most 64 characters (MySQL's limit). A lock lives on the connection that took it, and a pooled
connection outlives the block: on any error taking or releasing it (or a release that does not answer 1) the
connection is invalidated, closed and never returned to the pool, which releases the lock with it.

Another database (the tests' SQLite) has no named locks: one process, so the block may run.
"""
from contextlib import asynccontextmanager
from typing import Any
from typing import AsyncIterator
from typing import Callable

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import AsyncSessionLocal

LOCK_NAME_SQL = "SELECT LEFT(CONCAT(:prefix, COALESCE(DATABASE(), '')), 64)"


def _new_session() -> AsyncSession:
    return AsyncSessionLocal()


# Tests point this at their own database
new_session: Callable[[], AsyncSession] = _new_session


@asynccontextmanager
async def mysql_named_lock(prefix: str, label: str) -> AsyncIterator[bool]:
    """Whether the block may run: the named lock ``prefix`` + DATABASE(), taken without waiting. ``label`` names the
    job in log lines."""
    session = new_session()
    try:
        if session.get_bind().dialect.name != "mysql":
            yield True
            return
        held = False
        name = None
        connection = None
        try:
            connection = await session.connection()
            name = (await session.execute(text(LOCK_NAME_SQL), {"prefix": prefix})).scalar()
            held = (await session.execute(text("SELECT GET_LOCK(:name, 0)"), {"name": name})).scalar() == 1
        except Exception as e:  # noqa: BLE001 - no lock, no tick; and no connection left holding one
            logger.error(f"{label}: the named lock could not be taken ({type(e).__name__}); skipping this run")
            held = False
            await _invalidate(connection, label)
        try:
            yield held
        finally:
            if held:
                released = None
                try:
                    released = (await session.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": name})).scalar()
                except Exception as e:  # noqa: BLE001 - invalidated below, which releases it
                    logger.warning(f"{label}: releasing the named lock failed ({type(e).__name__}); dropping the connection")
                if released != 1:
                    await _invalidate(connection, label)
    finally:
        await session.close()


async def _invalidate(connection: Any, label: str) -> None:
    """Close ``connection`` for good (never back to the pool): MySQL releases its named locks."""
    if connection is None:
        return
    try:
        await connection.invalidate()
    except Exception as e:  # noqa: BLE001 - nothing more can be done for this connection
        logger.warning(f"{label}: invalidating the named lock's connection failed ({type(e).__name__})")
