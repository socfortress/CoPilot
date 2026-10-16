"""E2E for Talon v2 action approvals (talon-analyst M5-11a). NOT collected by pytest: it needs a live,
disposable MySQL.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \\
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \\
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \\
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \\
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python -c "from app.db.db_setup import apply_migrations; apply_migrations()"
    .venv/bin/python tests/e2e/talon_actions_e2e.py

Point it at a throwaway instance on 13306, never at the MySQL in .env: it turns the "Talon v2"
setting on there, and migrates the action table down and up.

Real routers, real JWTs, real MySQL; talon-analyst is the unit tests' ``FakeTalon`` (its records
kept by talon-analyst's rules) and Velociraptor is a recorder, so nothing real is ever run.

  A) the migrations: ``talon_action_request`` exists with its unique ``copilot_ref`` and ``agents``
     has the re-check's three indexes; down past both drops them, up recreates them; one head
  B) two approvals of one quarantine racing past the refresh together: the guarded update lets
     one through, the other is a 409; one claim, one run (five rounds)
  C) the host re-check under ``SELECT … FOR UPDATE``, on MySQL: a second agent whose name differs
     only in case refuses the run (``lower()``), and one the column's collation treats as equal
     does too (``agents.hostname`` is ``utf8mb4_0900_as_cs`` on a fresh schema, so an accent
     differs there, as it does for the quarantine route's own lookup)
  D) the audit rows: approve and execute, plus the quarantine route's own ``response.quarantine``
  E) a result the inline tries couldn't post is posted by the job, once
  F) during a slow quarantine (index-backed locks): an UPDATE of another agent and an INSERT of a
     new one don't wait, and EXPLAIN shows each re-check query uses an index (in A)
  G) a host whose rows another transaction holds fails closed within the 5 s lock wait, and the
     pooled connections keep the server's own lock wait
"""
import asyncio
import os
import sys
from datetime import datetime
from datetime import timedelta
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import APIRouter  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import inspect as sa_inspect  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.dialects import mysql as mysql_dialect  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.connectors.velociraptor.routes.artifacts as artifact_routes  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonActionRequest  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings  # noqa: E402
from app.connectors.talon.services import talon_action_execution as execution  # noqa: E402
from app.connectors.talon.services import talon_action_sync as sync  # noqa: E402
from app.connectors.talon.services import talon_actions as actions  # noqa: E402
from app.connectors.talon.utils import v2_client  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    QuarantineResponse,
)
from app.db.db_session import SQLALCHEMY_DATABASE_URI  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from tests.test_talon_actions import FakeTalon  # noqa: E402

PASSWORD = "E2ePassw0rd!x"
CUST_A = "E2E_TA"
ADMIN, RESP_1, RESP_2 = "e2e_ta_admin", "e2e_ta_resp1", "e2e_ta_resp2"
USERS = ((ADMIN, 1), (RESP_1, 5), (RESP_2, 5))
HOST = "e2e-ta-host"
VID = "C.00000000000e2e01"
REV, DOWN_REV = "d5b11a2b3c4d", "d54a0c1b2e3f"  # the index migration, and before both of this PR's
CONNECTOR = {"connector_url": "http://talon.invalid", "connector_api_key": "k", "connector_verified": True}
NOW = datetime(2026, 10, 16, 8, 0)
URL = SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql")
AGENT_INDEXES = ("ix_agents_hostname", "ix_agents_lower_hostname", "ix_agents_velociraptor_client")
results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def alembic_cfg() -> Config:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = Config(os.path.join(here, "alembic", "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", URL)
    cfg.set_main_option("script_location", os.path.join(here, "alembic"))
    return cfg


def section_a():
    print("\n=== A) the migration ===")
    cfg = alembic_cfg()
    heads = ScriptDirectory.from_config(cfg).get_heads()
    check("one alembic head, this PR's index migration", heads == [REV], str(heads))
    engine = create_engine(URL)

    def table():
        insp = sa_inspect(engine)
        if "talon_action_request" not in insp.get_table_names():
            return None
        uniques = {tuple(u["column_names"]) for u in insp.get_unique_constraints("talon_action_request")}
        uniques |= {tuple(i["column_names"]) for i in insp.get_indexes("talon_action_request") if i.get("unique")}
        return uniques

    def agent_indexes():
        return {i["name"] for i in sa_inspect(engine).get_indexes("agents")} & set(AGENT_INDEXES)

    check("table exists with a unique copilot_ref", ("copilot_ref",) in (table() or set()), str(table()))
    check("agents has the re-check's three indexes", agent_indexes() == set(AGENT_INDEXES), str(sorted(agent_indexes())))
    command.downgrade(cfg, DOWN_REV)
    check("down past both migrations drops the table and the indexes", table() is None and not agent_indexes())
    command.upgrade(cfg, "head")
    check("up again recreates them", ("copilot_ref",) in (table() or set()) and agent_indexes() == set(AGENT_INDEXES))
    with engine.connect() as conn:
        version = conn.execute(text("SELECT VERSION()")).scalar()
        for n, query in enumerate(execution.host_lock_queries(HOST, VID)):
            sql = str(query.compile(dialect=mysql_dialect.dialect(), compile_kwargs={"literal_binds": True}))
            plan = [dict(r._mapping) for r in conn.execute(text("EXPLAIN " + sql))]
            check(
                f"re-check query {n + 1} is an index lookup (MySQL {version})",
                all(r["type"] != "ALL" and r["key"] in AGENT_INDEXES for r in plan),
                ", ".join(f"type={r['type']} key={r['key']}" for r in plan),
            )
    engine.dispose()


async def cleanup(s: AsyncSession):
    await s.execute(delete(TalonActionRequest).where(TalonActionRequest.customer_code == CUST_A))
    for name, _ in USERS:
        u = (await s.execute(select(User).where(User.username == name))).scalars().first()
        if u:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == u.id))
            await s.delete(u)
    await s.execute(delete(Agents).where(Agents.customer_code == CUST_A))
    await s.commit()
    await s.execute(delete(Customers).where(Customers.customer_code == CUST_A))
    await s.commit()


def agent(hostname, agent_id, vid=VID):
    return Agents(
        agent_id=agent_id,
        ip_address="10.0.9.1",
        os="Windows",
        hostname=hostname,
        label=hostname,
        critical_asset=False,
        customer_code=CUST_A,
        quarantined=False,
        velociraptor_id=vid,
        velociraptor_org="root",
        wazuh_last_seen=NOW,
        velociraptor_last_seen=NOW,
        wazuh_agent_version="4.x",
        velociraptor_agent_version="0.7",
    )


async def seed():
    auth = AuthHandler()
    async with AsyncSession(async_engine) as s:
        await cleanup(s)
        s.add(Customers(customer_code=CUST_A, customer_name="E2E Talon actions", customer_type="MSSP", logo_file=""))
        await s.commit()
        s.add(agent(HOST, "e2eta1"))
        pw = auth.get_password_hash(PASSWORD)
        for name, role in USERS:
            s.add(User(username=name, password=pw, email=f"{name}@example.com", role_id=role))
        row = (await s.execute(select(TalonConnectorSettings).where(TalonConnectorSettings.connector_name == "Talon"))).scalars().first()
        if row is None:
            s.add(TalonConnectorSettings(connector_name="Talon", v2_enabled=True))
        else:
            row.v2_enabled = True
        await s.commit()
        for name in (RESP_1, RESP_2):
            u = (await s.execute(select(User).where(User.username == name))).scalars().one()
            s.add(UserCustomerAccess(user_id=u.id, customer_code=CUST_A))
        await s.commit()
        ids = {name: (await s.execute(select(User.id).where(User.username == name))).scalars().one() for name, _ in USERS}
    return ids


def build_app():
    from app.routers import talon

    api = APIRouter()
    api.include_router(talon.router)
    app = FastAPI()
    app.include_router(api)
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    return app


async def row(rid):
    async with AsyncSession(async_engine) as s:
        return await s.get(TalonActionRequest, rid)


async def main():
    ids = await seed()
    app = build_app()
    auth = AuthHandler()
    tokens = {name: await auth.encode_token(name) for name, _ in USERS}
    talon = FakeTalon()
    velociraptor = AsyncMock(return_value=QuarantineResponse(success=True, message="Quarantine scheduled", results=None))

    def H(name):
        return {"Authorization": f"Bearer {tokens[name]}"}

    def new_client(timeout):
        return httpx.AsyncClient(transport=httpx.MockTransport(talon.handler), timeout=timeout)

    def proposal():
        return talon.add(
            "quarantine_host",
            customer=CUST_A,
            user=str(ids[RESP_1]),
            target={"customer_code": CUST_A, "agent_id": "e2eta1", "velociraptor_id": VID, "hostname": HOST},
            args={"hostname": HOST, "velociraptor_id": VID, "action": "quarantine", "artifact_name": "Windows.Remediation.Quarantine"},
        )

    artifacts = type("A", (), {"artifacts": [type("N", (), {"name": "Windows.Remediation.Quarantine"})()]})()
    with patch.object(v2_client, "_new_client", new_client), patch.object(
        v2_client,
        "_connector",
        AsyncMock(return_value=CONNECTOR),
    ), patch.object(
        artifact_routes,
        "quarantine_host",
        velociraptor,
    ), patch.object(
        artifact_routes,
        "get_all_artifacts_for_hostname",
        AsyncMock(return_value=artifacts),
    ), patch.object(
        actions,
        "INLINE_PAUSES",
        (0, 0),
    ):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://e2e") as client:
            print("\n=== B) two racing approvals run once ===")
            for round_ in range(5):
                rid = proposal()
                arrived = []
                both = asyncio.Event()

                async def hold_gets(request, rid=rid, arrived=arrived, both=both):
                    if request.method == "GET" and rid in request.url.path:
                        arrived.append(1)
                        if len(arrived) >= 2:
                            both.set()
                        await asyncio.wait_for(both.wait(), timeout=10)
                    return None

                talon.intercept = hold_gets
                before = velociraptor.await_count
                first, second = await asyncio.gather(
                    client.post(f"/talon/actions/{rid}/approve", headers=H(RESP_1)),
                    client.post(f"/talon/actions/{rid}/approve", headers=H(RESP_2)),
                )
                statuses = sorted([first.status_code, second.status_code])
                claimed = [b for b in talon.outcome_posts(rid) if b["outcome"] == "approved"]
                stored = await row(rid)
                check(
                    f"round {round_ + 1}: one 200, one 409; one claim; one run",
                    statuses == [200, 409] and len(claimed) == 1 and velociraptor.await_count - before == 1 and stored.state == "executed",
                    f"{statuses}, claims={len(claimed)}, runs={velociraptor.await_count - before}, state={stored.state}",
                )
            talon.intercept = None

            print("\n=== C) the host re-check on MySQL's collation ===")
            async with AsyncSession(async_engine) as s:
                collation = (
                    await s.execute(
                        text(
                            "SELECT COLLATION_NAME FROM information_schema.COLUMNS "
                            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'agents' AND COLUMN_NAME = 'hostname'",
                        ),
                    )
                ).scalar()
            # A name differing only in case is refused by lower(), whatever the column's collation
            # (this schema's is case-sensitive, so the route's own lookup wouldn't conflate them);
            # one the collation treats as equal is refused by the collation half of the check.
            variants = [("E2E-TA-HOST", "e2eta2", "refused")]
            accent_equal = collation is not None and "_ai" in collation
            variants.append(("e2e-tà-host", "e2eta3", "refused" if accent_equal else "runs"))
            for variant, agent_id, expected in variants:
                async with AsyncSession(async_engine) as s:
                    s.add(agent(variant, agent_id, vid="C.00000000000e2e09"))
                    await s.commit()
                rid = proposal()
                before = velociraptor.await_count
                response = await client.post(f"/talon/actions/{rid}/approve", headers=H(RESP_1))
                stored = await row(rid)
                message = (stored.execution_result or {}).get("message")
                if expected == "refused":
                    passed = stored.state == "failed" and velociraptor.await_count == before and "exactly one agent" in (message or "")
                else:  # the collation tells the names apart, as the route's own lookup does
                    passed = stored.state == "executed" and velociraptor.await_count == before + 1
                check(
                    f"a second agent named {variant!r} ({collation}): {expected}",
                    response.status_code == 200 and passed,
                    f"{response.status_code} {stored.state} {message}",
                )
                async with AsyncSession(async_engine) as s:
                    await s.execute(delete(Agents).where(Agents.agent_id == agent_id))
                    await s.commit()

            print("\n=== D) the audit rows ===")
            rid = proposal()
            await client.post(f"/talon/actions/{rid}/approve", headers=H(RESP_2))
            async with AsyncSession(async_engine) as s:
                mine = (await s.execute(select(AuditLog).where(AuditLog.entity_id == rid))).scalars().all()
                route = (
                    (
                        await s.execute(
                            select(AuditLog).where(
                                AuditLog.action == "response.quarantine",
                                AuditLog.actor_username == RESP_2,
                                AuditLog.entity_id == HOST,
                            ),
                        )
                    )
                    .scalars()
                    .all()
                )
            got = sorted((a.action, a.result) for a in mine)
            check(
                "talon_action.approve and .execute, with the customer and copilot_ref",
                got == [("talon_action.approve", "success"), ("talon_action.execute", "success")]
                and all(a.customer_code == CUST_A and a.new_value["copilot_ref"].startswith("copilot-") for a in mine),
                str(got),
            )
            check("the quarantine route's own response.quarantine", len(route) >= 1, str(len(route)))

            print("\n=== E) the job posts what the inline tries couldn't ===")
            left = {"n": 3}

            async def results_down(request):
                if request.url.path.endswith("/outcome") and b'"executed"' in request.content and left["n"] > 0:
                    left["n"] -= 1
                    raise httpx.ConnectError("down")
                return None

            talon.intercept = results_down
            rid = proposal()
            await client.post(f"/talon/actions/{rid}/approve", headers=H(RESP_1))
            waiting = await row(rid)
            counts = await actions.run_outcome_job(now=sync.utcnow() + timedelta(minutes=2))
            again = await actions.run_outcome_job(now=sync.utcnow() + timedelta(minutes=10))
            done = await row(rid)
            check(
                "posted by the job, once",
                waiting.outcome_posted_at is None and counts["posted"] == 1 and again["posted"] == 0 and done.outcome_posted_at is not None,
                f"{counts} {again}",
            )
            talon.intercept = None

            print("\n=== F) a slow Talon quarantine locks only its host ===")
            # Neighbours bound the locked gaps (InnoDB's next-key locks, REPEATABLE READ), as other
            # agents do on a real deployment.
            async with AsyncSession(async_engine) as s:
                s.add_all(
                    [
                        agent("e2e-ta-hosz", "e2eta-nb", vid="C.00000000000e2e03"),
                        agent("e2e-ta-other", "e2eta-ot", vid="C.00000000000e2e05"),
                    ],
                )
                await s.commit()

            async def slow_quarantine(body):
                await asyncio.sleep(4)
                return QuarantineResponse(success=True, message="Quarantine scheduled", results=None)

            velociraptor.side_effect = slow_quarantine
            rid = proposal()
            running = asyncio.create_task(client.post(f"/talon/actions/{rid}/approve", headers=H(RESP_1)))
            while getattr(await row(rid), "state", None) != "executing" or velociraptor.await_count == 0:
                await asyncio.sleep(0.05)
            await asyncio.sleep(0.5)  # inside the route's run, the host's rows locked

            async def timed(work):
                started = asyncio.get_running_loop().time()
                try:
                    async with AsyncSession(async_engine) as s:
                        await work(s)
                        await s.commit()
                    return asyncio.get_running_loop().time() - started, None
                except Exception as e:  # noqa: BLE001 - reported as the check's detail
                    return asyncio.get_running_loop().time() - started, type(e).__name__

            async def touch_other(s):
                await s.execute(update(Agents).where(Agents.agent_id == "e2eta-ot").values(quarantined=True, label="touched"))

            async def add_new(s):
                s.add(agent("e2e-tz-new", "e2eta-new", vid="C.ffffffff0000e2e1"))

            updated, update_error = await timed(touch_other)
            inserted, insert_error = await timed(add_new)
            still_running = not running.done()
            response = await running
            velociraptor.side_effect = None
            check(
                "another agent's UPDATE doesn't wait for the run",
                update_error is None and updated < 1.5 and still_running,
                f"{updated:.2f}s {update_error}",
            )
            check(
                "a new agent's INSERT doesn't wait for the run",
                insert_error is None and inserted < 1.5,
                f"{inserted:.2f}s {insert_error}",
            )
            check(
                "and the run itself completes",
                response.status_code == 200 and (await row(rid)).state == "executed",
                str(response.status_code),
            )

            print("\n=== G) a locked host fails closed quickly ===")
            async with AsyncSession(async_engine) as holder:
                await holder.execute(select(Agents).where(Agents.agent_id == "e2eta1").with_for_update())
                rid = proposal()
                before = velociraptor.await_count
                started = asyncio.get_running_loop().time()
                response = await client.post(f"/talon/actions/{rid}/approve", headers=H(RESP_1))
                took = asyncio.get_running_loop().time() - started
                await holder.rollback()
            stored = await row(rid)
            check(
                "the re-check gives up within ~5 s, runs nothing, and says why",
                stored.state == "failed"
                and velociraptor.await_count == before
                and took < 15
                and "being changed" in (stored.execution_result or {}).get("message", ""),
                f"{took:.1f}s {stored.state} {(stored.execution_result or {}).get('message')}",
            )
            async with AsyncSession(async_engine) as s:
                wait = (await s.execute(text("SELECT @@SESSION.innodb_lock_wait_timeout, @@GLOBAL.innodb_lock_wait_timeout"))).one()
            check("pooled connections keep the server's lock wait", wait[0] == wait[1], str(tuple(wait)))

    async with AsyncSession(async_engine) as s:
        await cleanup(s)
        await s.execute(delete(AuditLog).where(AuditLog.customer_code == CUST_A))
        await s.commit()


if __name__ == "__main__":
    section_a()
    asyncio.run(main())
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    sys.exit(1 if failed else 0)
