"""E2E for the per-alert cap's guarded UPDATE (talon-analyst plan AP-2a, ``talon_triggers.reserve``)
on real MySQL or MariaDB. NOT collected by pytest: it needs a live, disposable database.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \\
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \\
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \\
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \\
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python tests/e2e/talon_alert_cap_mysql_e2e.py

Point it at a throwaway instance, never at the MySQL in .env. It uses the migrated
``talon_automation_alert_cap`` and removes only its own row; on an unmigrated database it
creates the table and drops it again.

What it proves:
- many reservations at once, each on its own connection, take exactly ``PER_ALERT_CAP`` slots;
- a passed window restarts at one start: MySQL assigns ``SET`` left to right, so ``starts`` must be
  assigned before ``window_started_at`` (with the order reversed, the row would read 3 starts);
- the new window then fills and refuses as before.
"""
import asyncio
import os
import sys
from datetime import timedelta

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import inspect  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.connectors.talon.models.talon_v2 import TalonAutomationAlertCap  # noqa: E402
from app.connectors.talon.services import talon_triggers  # noqa: E402
from app.db.db_session import SQLALCHEMY_DATABASE_URI  # noqa: E402

ALERT = 990001
results = []


def check(name, passed, detail=""):
    results.append((name, passed))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def main() -> int:
    engine = create_async_engine(SQLALCHEMY_DATABASE_URI, pool_size=10, max_overflow=0)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    talon_triggers.new_session = factory
    table = TalonAutomationAlertCap.__table__
    binding = talon_triggers.Binding(alert_id=ALERT, customer_code="E2E_AP2A", trigger_id=1, source="pipeline", user_id=None, username=None)

    async def one():
        try:
            await talon_triggers.reserve(binding)
            return 200
        except HTTPException as e:
            return e.status_code

    async def row():
        async with factory() as session:
            return await session.get(TalonAutomationAlertCap, ALERT)

    # On a migrated database the table is the migration's (c2a2a0b1d3e4): use it and remove only
    # this test's row, so alembic_version keeps matching the schema for the suites run after.
    async with engine.begin() as conn:
        existed = await conn.run_sync(lambda c: inspect(c).has_table(table.name))

    async def clear():
        async with engine.begin() as conn:
            if existed:
                await conn.execute(delete(table).where(table.c.alert_id == ALERT))
            else:
                await conn.run_sync(lambda c: table.drop(c, checkfirst=True))

    try:
        await clear()
        if not existed:
            async with engine.begin() as conn:
                await conn.run_sync(lambda c: table.create(c))
        outcomes = sorted(await asyncio.gather(*(one() for _ in range(8))))
        cap = talon_triggers.PER_ALERT_CAP
        check("8 concurrent reservations take exactly the cap", outcomes == [200] * cap + [429] * (8 - cap), str(outcomes))
        check("the row counts the cap", (await row()).starts == cap)

        async with factory() as session:
            old = talon_triggers.utcnow() - talon_triggers.WINDOW - timedelta(minutes=5)
            await session.execute(
                update(TalonAutomationAlertCap).where(TalonAutomationAlertCap.alert_id == ALERT).values(window_started_at=old),
            )
            await session.commit()
        first = await one()
        current = await row()
        fresh = current.window_started_at > talon_triggers.utcnow() - timedelta(minutes=1)
        check("a passed window restarts at one start", first == 200 and current.starts == 1 and fresh, f"starts={current.starts}")
        rest = [await one() for _ in range(cap)]
        check("the new window fills and refuses", rest == [200] * (cap - 1) + [429], str(rest))
    finally:
        await clear()
        await engine.dispose()

    failed = [name for name, passed in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
