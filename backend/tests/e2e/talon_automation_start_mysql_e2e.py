"""E2E for the automated start's reservation (talon-analyst plan AP-2,
``talon_automation.reserve_start``) on real MySQL or MariaDB. NOT collected by pytest: it needs a
live, disposable database.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \\
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \\
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \\
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \\
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python tests/e2e/talon_automation_start_mysql_e2e.py

Point it at a throwaway instance, never at the MySQL in .env: it creates and drops
``talon_connector_settings``, ``talon_automation_policy``, ``talon_automation_start``,
``talon_automation_alert_cap`` and ``audit_log``.

What it proves, each reservation on its own connection, all at once:
- one customer's reservations on many alerts and hosts take exactly its per-customer cap (the
  policy row's ``FOR UPDATE`` serializes them, so the counts can't race), with no deadlock;
- one host's reservations across alerts take exactly the per-host cap;
- two customers' reservations don't wait on each other's caps;
- every reservation has its start row and its audit row, and a refused one leaves neither and gives
  its alert's slot back;
- a policy turned off while reservations wait for its lock stops the ones after it.
"""
import asyncio
import os
import sys

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

from types import SimpleNamespace  # noqa: E402

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import func  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonAutomationAlertCap  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonAutomationPolicy  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonAutomationStart  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings  # noqa: E402
from app.connectors.talon.services import talon_automation as automation  # noqa: E402
from app.connectors.talon.services import talon_triggers  # noqa: E402
from app.db.db_session import SQLALCHEMY_DATABASE_URI  # noqa: E402

USER = SimpleNamespace(id=20, username="talon-analyst")
TABLES = [
    TalonConnectorSettings.__table__,
    TalonAutomationPolicy.__table__,
    TalonAutomationStart.__table__,
    TalonAutomationAlertCap.__table__,
    AuditLog.__table__,
]
results = []


def check(name, passed, detail=""):
    results.append((name, passed))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def main() -> int:
    engine = create_async_engine(SQLALCHEMY_DATABASE_URI, pool_size=20, max_overflow=0)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    talon_triggers.new_session = factory

    async def reserve(customer, alert_id, client):
        binding = talon_triggers.Binding(
            alert_id=alert_id,
            customer_code=customer,
            trigger_id=1,
            source="pipeline",
            user_id=None,
            username=None,
        )
        try:
            await automation.reserve_start(
                user=USER,
                binding=binding,
                customer_code=customer,
                hostname=f"host-{client[-4:]}",
                client=client,
                level=1,
                artifact="Windows.System.Pslist",
                parameters=(),
                job_id="e2e",
                request=None,
            )
            return 200
        except HTTPException as e:
            return e.status_code, e.detail

    async def count(model, *where):
        async with factory() as session:
            return (await session.execute(select(func.count()).select_from(model).where(*where))).scalar_one()

    async def reset(**policies):
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: [t.drop(c, checkfirst=True) for t in reversed(TABLES)])
            await conn.run_sync(lambda c: [t.create(c) for t in TABLES])
        async with factory() as session:
            session.add(TalonConnectorSettings(connector_name="Talon", automation_enabled=True))
            for code, caps in policies.items():
                session.add(TalonAutomationPolicy(customer_code=code, level_1_mode="auto", caps=caps))
            await session.commit()

    try:
        # One customer, 12 alerts on 12 hosts at once: exactly its per-customer cap.
        await reset(E2E_A={"per_customer_hour": 5})
        outcomes = await asyncio.gather(*(reserve("E2E_A", 1000 + i, f"C.{i:016x}") for i in range(12)))
        ok = [o for o in outcomes if o == 200]
        refused = {o[1] for o in outcomes if o != 200}
        check(
            "12 concurrent reservations for one customer take exactly its cap",
            len(ok) == 5 and refused == {automation.CUSTOMER_CAP},
            str(outcomes),
        )
        check("each has its start row and audit row", await count(TalonAutomationStart) == 5 == await count(AuditLog))
        slots = await count(TalonAutomationAlertCap, TalonAutomationAlertCap.starts == 1)
        check("the refused ones gave their alert's slot back", slots == 5, f"slots={slots}")

        # One host, 10 alerts at once: exactly the per-host cap.
        await reset(E2E_A={"per_host_hour": 3})
        outcomes = await asyncio.gather(*(reserve("E2E_A", 2000 + i, "C.00000000000000aa") for i in range(10)))
        check(
            "10 concurrent reservations on one host take exactly the host cap",
            outcomes.count(200) == 3 and {o[1] for o in outcomes if o != 200} == {automation.HOST_CAP},
            str(outcomes),
        )

        # Two customers at once: each fills its own cap.
        await reset(E2E_A={"per_customer_hour": 3}, E2E_B={"per_customer_hour": 4})
        outcomes = await asyncio.gather(
            *(reserve("E2E_A", 3000 + i, f"C.a{i:015x}") for i in range(8)),
            *(reserve("E2E_B", 4000 + i, f"C.b{i:015x}") for i in range(8)),
        )
        check("two customers fill their own caps", outcomes[:8].count(200) == 3 and outcomes[8:].count(200) == 4, str(outcomes))

        # A policy turned off while others wait for its lock.
        await reset(E2E_A=None)
        async with factory() as admin:
            await admin.execute(select(TalonAutomationPolicy).where(TalonAutomationPolicy.customer_code == "E2E_A").with_for_update())
            waiting = [asyncio.create_task(reserve("E2E_A", 5000 + i, f"C.c{i:015x}")) for i in range(4)]
            await asyncio.sleep(1.0)
            await admin.execute(
                update(TalonAutomationPolicy).where(TalonAutomationPolicy.customer_code == "E2E_A").values(level_1_mode="off"),
            )
            await admin.commit()
        outcomes = await asyncio.gather(*waiting)
        check(
            "reservations waiting on the lock see the policy turned off",
            all(o != 200 and o[1] == automation.LEVEL_OFF for o in outcomes) and await count(TalonAutomationStart) == 0,
            str(outcomes),
        )
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: [t.drop(c, checkfirst=True) for t in reversed(TABLES)])
        await engine.dispose()

    failed = [name for name, passed in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
