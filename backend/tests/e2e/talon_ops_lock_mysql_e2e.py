"""E2E for the Talon ops poller's named lock (``talon_ops_notify.poll_lock``; plan OJ-5, review L1/L3)
on real MySQL. NOT collected by pytest: it needs a live, disposable database. From the reviewer's
``lock_probe.py``.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \\
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \\
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \\
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \\
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python tests/e2e/talon_ops_lock_mysql_e2e.py

Point it at a throwaway instance, never at the MySQL in .env. It touches no table.

What it proves:
- while one tick holds the lock, a second tick (another connection) doesn't;
- once released, the lock can be taken again;
- the lock's name carries the database's name (two CoPilots on one server don't share it);
- a RELEASE_LOCK that fails drops the connection rather than pooling it, so another replica gets the
  lock straight away and nobody holds it (before the fix, a pooled connection kept it).
"""
import asyncio
import os
import sys

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.connectors.talon.services import talon_ops_notify as notify  # noqa: E402
from app.db.db_session import SQLALCHEMY_DATABASE_URI  # noqa: E402
from app.notifications.services import outbox  # noqa: E402

results = []


def check(name, passed, detail=""):
    results.append((name, passed))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def main() -> int:
    # A small pool, as a replica has: a connection kept by a failed release would be reused.
    engine = create_async_engine(SQLALCHEMY_DATABASE_URI, pool_size=2, max_overflow=0)
    outbox.new_session = lambda: AsyncSession(engine, expire_on_commit=False)
    other = create_async_engine(SQLALCHEMY_DATABASE_URI)  # another replica
    try:
        async with engine.connect() as conn:
            name = (await conn.execute(text(notify.LOCK_NAME_SQL), {"prefix": notify.LOCK_PREFIX})).scalar()
            database = (await conn.execute(text("SELECT DATABASE()"))).scalar()
        check("the lock is named for this database", name == f"{notify.LOCK_PREFIX}{database}"[:64], name)

        async with notify.poll_lock() as first:
            async with notify.poll_lock() as second:
                check("a second tick doesn't hold it while the first does", first is True and second is False, f"{first} {second}")
        async with notify.poll_lock() as again:
            check("after the release it can be taken again", again is True)

        original = AsyncSession.execute

        async def flaky(self, statement, *args, **kwargs):
            if "RELEASE_LOCK" in str(statement):
                raise RuntimeError("simulated release failure")
            return await original(self, statement, *args, **kwargs)

        AsyncSession.execute = flaky
        try:
            async with notify.poll_lock() as held:
                pass
        finally:
            AsyncSession.execute = original
        check("the tick with a failing release held the lock", held is True)
        async with other.connect() as conn:
            got = (await conn.execute(text("SELECT GET_LOCK(:n, 0)"), {"n": name})).scalar()
            holder = (await conn.execute(text("SELECT IS_USED_LOCK(:n)"), {"n": name})).scalar()
            mine = (await conn.execute(text("SELECT CONNECTION_ID()"))).scalar()
            await conn.execute(text("SELECT RELEASE_LOCK(:n)"), {"n": name})
        check("after a failed release another replica gets the lock at once", got == 1 and holder == mine, f"got={got} holder={holder}")
    finally:
        await other.dispose()
        await engine.dispose()

    failed = [name for name, passed in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
