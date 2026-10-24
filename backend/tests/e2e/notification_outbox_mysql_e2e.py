"""E2E for the notification outbox (migration d0b7e1a2c3f4, ``notifications/services/outbox.py``) on
real MySQL. NOT collected by pytest: it needs a live, disposable database.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \\
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \\
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \\
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \\
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    ../.venv/bin/python tests/e2e/notification_outbox_mysql_e2e.py

Point it at a throwaway instance on 13306, never at the MySQL in .env: it migrates the database
(to head, down past the outbox and up again) and writes rows for its own customer, which it
removes afterwards. Providers are a fake channel; nothing leaves the machine.

What it proves, on MySQL's locking and types (the unit tests run on SQLite):
- the migration creates the table, its unique queued key and MEDIUMTEXT event, and round-trips;
- ``INSERT … ON DUPLICATE KEY UPDATE`` keeps one queued row per key inside a caller's transaction
  without failing its commit, and the unique index refuses a plain duplicate under its name;
- the AI report and its outbox row commit together; a report that loses the race is still a
  409, and its rollback undoes its change to the queued row;
- of many concurrent guarded claims of one row (each on its own connection) exactly one wins;
- several drains and kicks at once deliver every (route, notification) exactly once;
- many concurrent ``queue()`` calls for one key leave one row;
- a row queued and kicked within the same second is delivered at once (DATETIME rounding);
- an expired lease is recovered;
- a deadlock while queueing in a caller's transaction that has already flushed a row is raised,
  not swallowed: the caller's row is gone (MySQL rolled the transaction back), and the caller
  learns it instead of "committing" nothing and notifying anyway;
- two internal routes each receive an internal event (no customer) exactly once.
"""
import asyncio
import os
import sys
from datetime import datetime
from datetime import timedelta

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

import app.notifications.services.notifications as svc  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.ai_analyst.schema.ai_analyst import SubmitReportRequest  # noqa: E402
from app.ai_analyst.services import ai_analyst as ai_svc  # noqa: E402
from app.db.db_session import SQLALCHEMY_DATABASE_URI  # noqa: E402
from app.db.universal_models import NOTIFICATION_OUTBOX_QUEUED_UNIQUE  # noqa: E402
from app.db.universal_models import CustomerNotificationRoute  # noqa: E402
from app.db.universal_models import NotificationOutbox  # noqa: E402
from app.notifications.channels import SendResult  # noqa: E402
from app.notifications.schema.events import NotificationEvent  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services import outbox  # noqa: E402
from app.notifications.services.event_builders import (  # noqa: E402
    case_task_assigned_event,
)

BEFORE = "c1298a0b1c2d"
REVISION = "d0b7e1a2c3f4"
CUSTOMER = "E2E_OUTBOX"
ALERT = 990777
JOB = "copilot-inv-990777-1"
SYNC_URL = SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql")
results = []


def check(name, passed, detail=""):
    results.append((name, passed))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def alembic_cfg() -> Config:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = Config(os.path.join(here, "alembic", "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", SYNC_URL)
    cfg.set_main_option("script_location", os.path.join(here, "alembic"))
    return cfg


class Channel:
    key = "webhook"

    def __init__(self):
        self.sent = []
        self.delay = 0.0

    async def send(self, *, route, event, message, ctx):
        name = route.name
        if self.delay:
            await asyncio.sleep(self.delay)
        self.sent.append((name, event.dedupe_key))
        return SendResult(status="sent", latency_ms=1)

    async def after_send(self, *, route, result, ctx):
        return None


def event(key, summary="e2e"):
    return NotificationEvent(
        customer_code=CUSTOMER,
        trigger=NotificationTrigger.ALERT_CREATED,
        severity=NotificationSeverity.HIGH,
        subject="E2E outbox",
        summary=summary,
        entity_id=ALERT,
        dedupe_key=key,
    )


def migration_checks():
    cfg = alembic_cfg()
    command.upgrade(cfg, "head")
    engine = create_engine(SYNC_URL)

    def shape(conn):
        unique = conn.execute(
            text(
                "SELECT non_unique FROM information_schema.statistics WHERE table_schema = DATABASE() "
                "AND table_name = 'notification_outbox' AND index_name = :n",
            ),
            {"n": NOTIFICATION_OUTBOX_QUEUED_UNIQUE},
        ).scalar()
        column = conn.execute(
            text(
                "SELECT data_type FROM information_schema.columns WHERE table_schema = DATABASE() "
                "AND table_name = 'notification_outbox' AND column_name = 'event_json'",
            ),
        ).scalar()
        indexes = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT DISTINCT index_name FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'notification_outbox'",
                ),
            )
        }
        return unique, column, indexes

    with engine.connect() as conn:
        unique, column, indexes = shape(conn)
    check("migration: queued_key is a unique index", unique == 0, f"non_unique={unique}")
    check("migration: event_json is MEDIUMTEXT", column == "mediumtext", column)
    wanted = {
        "ix_notification_outbox_status_next_attempt",
        "ix_notification_outbox_status_updated",
        "ix_notification_outbox_customer_status",
        "ix_notification_outbox_dedupe_key",
    }
    check("migration: the drain, retention and summary indexes exist", wanted <= indexes, sorted(indexes))

    command.downgrade(cfg, BEFORE)
    with engine.connect() as conn:
        gone = not conn.execute(text("SHOW TABLES LIKE 'notification_outbox'")).first()
    check("migration: the downgrade drops the table", gone)
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        unique, column, _ = shape(conn)
    check("migration: the upgrade runs again", unique == 0 and column == "mediumtext")
    engine.dispose()


async def deadlock_check(engine, factory):
    """After the review probe: the caller has flushed a row (as `submit_review` used to before
    queueing); another transaction holds the queued key and then waits on the caller's row, so
    InnoDB must kill one of them, and it picks the caller (fewer rows changed)."""
    key = "e2e:deadlock"
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE IF NOT EXISTS e2e_outbox_scratch (id INT AUTO_INCREMENT PRIMARY KEY, v VARCHAR(32))"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS e2e_outbox_heavy (id INT PRIMARY KEY)"))
        await conn.execute(text("DELETE FROM e2e_outbox_heavy"))
        await conn.execute(text("INSERT INTO e2e_outbox_heavy VALUES " + ",".join(f"({i})" for i in range(1, 2001))))
    other = await engine.connect()
    await other.begin()
    await other.execute(text("UPDATE e2e_outbox_heavy SET id = id + 100000"))
    await other.execute(
        text(
            "INSERT INTO notification_outbox (event_json, dedupe_key, queued_key, customer_code, `trigger`, status, attempts, "
            "next_attempt_at, created_at, updated_at) VALUES ('{}', :k, :k, :c, 't', 'pending', 0, NOW(), NOW(), NOW())",
        ),
        {"k": key, "c": CUSTOMER},
    )
    session = factory()
    await session.execute(text("INSERT INTO e2e_outbox_scratch (v) VALUES ('the review')"))
    flushed = (await session.execute(text("SELECT LAST_INSERT_ID()"))).scalar()

    async def other_waits_on_the_caller():
        await asyncio.sleep(0.5)
        try:
            await other.execute(text("SELECT * FROM e2e_outbox_scratch WHERE id = :i FOR UPDATE"), {"i": flushed})
            await other.commit()
        except Exception:
            await other.rollback()

    waiter = asyncio.create_task(other_waits_on_the_caller())
    raised = None
    try:
        await outbox.enqueue(event(key), session)
    except OperationalError as e:
        raised = e.orig.args[0] if e.orig is not None and e.orig.args else "?"
        await session.rollback()
    else:
        await session.commit()
    await waiter
    await session.close()
    await other.close()
    async with engine.begin() as conn:
        present = (await conn.execute(text("SELECT COUNT(*) FROM e2e_outbox_scratch WHERE id = :i"), {"i": flushed})).scalar()
        await conn.execute(text("DROP TABLE e2e_outbox_scratch"))
        await conn.execute(text("DROP TABLE e2e_outbox_heavy"))
        await conn.execute(text("DELETE FROM notification_outbox WHERE dedupe_key = :k"), {"k": key})
    check("deadlock: enqueue raises the deadlock (1213) instead of returning False", raised == 1213, f"raised={raised}")
    check("deadlock: the caller's flushed row is gone with its transaction", present == 0, f"present={present}")


async def clean(factory):
    async with factory() as session:
        for sql in (
            "DELETE FROM notification_outbox WHERE customer_code = :c OR dedupe_key LIKE 'e2e:%'",
            "DELETE FROM notification_dispatch_log WHERE customer_code = :c",
            "DELETE FROM customer_notification_route WHERE customer_code = :c",
            "DELETE FROM ai_analyst_report WHERE customer_code = :c",
            "DELETE FROM ai_analyst_job WHERE customer_code = :c",
            "DELETE FROM customers WHERE customer_code = :c",
        ):
            await session.execute(text(sql), {"c": CUSTOMER})
        await session.commit()


async def rows(factory, where="1=1", **params):
    async with factory() as session:
        result = await session.execute(select(NotificationOutbox).where(text(where)).params(**params).order_by(NotificationOutbox.id))
        return result.scalars().all()


async def main() -> int:
    migration_checks()

    engine = create_async_engine(SQLALCHEMY_DATABASE_URI, pool_size=20, max_overflow=0)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    outbox.new_session = factory
    channel = Channel()
    svc.get_channel = lambda name: channel
    settings = outbox.OutboxSettings(jitter=0.0)
    await clean(factory)

    async with factory() as session:
        await session.execute(
            text("INSERT INTO customers (customer_code, customer_name, created_at) VALUES (:c, 'E2E outbox', NOW())"),
            {"c": CUSTOMER},
        )
        for name in ("Route A", "Route B"):
            session.add(
                CustomerNotificationRoute(
                    name=name,
                    scope="customer",
                    customer_code=CUSTOMER,
                    trigger="alert_created",
                    channel="webhook",
                    destination="",
                    enabled=True,
                    min_severity="Informational",
                    recipient_mode="static",
                    config="{}",
                    created_at=datetime.utcnow(),
                    created_by="admin",
                ),
            )
        await session.commit()

    # ── one queued row per key, in the caller's transaction ──────────────────
    async with factory() as session:
        first = await outbox.enqueue(event("e2e:upsert", "first"), session)
        second = await outbox.enqueue(event("e2e:upsert", "second"), session)
        await session.commit()
    queued = await rows(factory, "dedupe_key = 'e2e:upsert'")
    check(
        "upsert: two enqueues of one key in one transaction leave one row, the newer event",
        first and second and len(queued) == 1 and NotificationEvent.model_validate_json(queued[0].event_json).summary == "second",
        f"rows={len(queued)}",
    )
    try:
        async with factory() as session:
            session.add(NotificationOutbox(event_json="{}", dedupe_key="e2e:upsert", queued_key="e2e:upsert", trigger="t"))
            await session.commit()
        refused = None
    except IntegrityError as e:
        refused = str(e.orig)
    check(
        "upsert: a plain duplicate is refused by the unique index, by name",
        bool(refused) and NOTIFICATION_OUTBOX_QUEUED_UNIQUE in refused,
        refused,
    )

    # ── within one second: queue, then kick ───────────────────────────────────
    channel.sent.clear()
    await outbox.queue(event("e2e:rounding"))
    await outbox.drain_key("e2e:rounding", settings)
    [row] = await rows(factory, "dedupe_key = 'e2e:rounding'")
    check("rounding: a row kicked the moment it is queued is delivered", row.status == "done" and len(channel.sent) == 2, row.status)

    # ── the AI report and its notification ────────────────────────────────────
    kicked = []
    ai_svc.outbox.kick = lambda e: kicked.append(e.dedupe_key)
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO ai_analyst_job (id, alert_id, customer_code, status, triggered_by, created_at) VALUES (:j, :a, :c, 'running', 'webhook', NOW())",
            ),
            {"j": JOB, "a": ALERT, "c": CUSTOMER},
        )
        await session.commit()
    request = SubmitReportRequest(
        job_id=JOB,
        alert_id=ALERT,
        customer_code=CUSTOMER,
        severity_assessment="High",
        summary="ours",
        report_markdown="# r",
        recommended_actions="a",
    )
    async with factory() as session:
        await ai_svc.submit_report(request, session)
    key = f"alert:{ALERT}:investigation_complete"
    queued = await rows(factory, "dedupe_key = :k", k=key)
    check(
        "report: the report and its queued notification committed together",
        len(queued) == 1 and queued[0].status == "pending" and kicked == [key],
        f"rows={len(queued)} kicked={kicked}",
    )

    # A second job's report races a third writer for the same job and loses.
    second_job = JOB + "b"
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO ai_analyst_job (id, alert_id, customer_code, status, triggered_by, created_at) VALUES (:j, :a, :c, 'running', 'webhook', NOW())",
            ),
            {"j": second_job, "a": ALERT, "c": CUSTOMER},
        )
        await session.commit()
    real_fields = ai_svc._alert_display_fields

    async def racing_writer(alert_id, session):
        async with factory() as other:
            await other.execute(
                text(
                    "INSERT INTO ai_analyst_report (job_id, alert_id, customer_code, summary, created_at) VALUES (:j, :a, :c, 'theirs', NOW())",
                ),
                {"j": second_job, "a": ALERT, "c": CUSTOMER},
            )
            await other.commit()
        return await real_fields(alert_id, session)

    ai_svc._alert_display_fields = racing_writer
    status = None
    try:
        async with factory() as session:
            await ai_svc.submit_report(request.model_copy(update={"job_id": second_job, "summary": "lost"}), session)
    except HTTPException as e:
        status = e.status_code
    finally:
        ai_svc._alert_display_fields = real_fields
    queued = await rows(factory, "dedupe_key = :k", k=key)
    summaries = [NotificationEvent.model_validate_json(r.event_json).summary for r in queued]
    check("report: the loser is still a 409", status == 409, status)
    check("report: its rollback undid its change to the queued notification", summaries == ["ours"], summaries)

    # ── concurrent claims of one row ──────────────────────────────────────────
    await outbox.queue(event("e2e:claim"))
    [row] = await rows(factory, "dedupe_key = 'e2e:claim'")
    claims = await asyncio.gather(*(outbox._claim(row.id, datetime.utcnow()) for _ in range(12)))
    winners = [c for c in claims if c is not None]
    check("claims: twelve concurrent claims of one row, one winner", len(winners) == 1, f"winners={len(winners)}")

    # ── concurrent drains ─────────────────────────────────────────────────────
    async with factory() as session:
        await session.execute(text("DELETE FROM notification_outbox WHERE dedupe_key LIKE 'e2e:%'"))
        await session.commit()
    channel.sent.clear()
    channel.delay = 0.01
    keys = [f"e2e:drain:{n}" for n in range(30)]
    async with factory() as session:
        for k in keys:
            await outbox.enqueue(event(k), session)
        await session.commit()
    await asyncio.gather(
        outbox.drain(settings),
        outbox.drain(settings),
        outbox.drain(settings),
        *(outbox.drain_key(k, settings) for k in keys[::3]),
    )
    drained = await rows(factory, "dedupe_key LIKE 'e2e:drain:%'")
    expected = sorted((name, k) for name in ("Route A", "Route B") for k in keys)
    check("drains: every row done", [r.status for r in drained] == ["done"] * 30, sorted({r.status for r in drained}))
    check(
        "drains: every (route, notification) sent exactly once",
        sorted(channel.sent) == expected,
        f"sent={len(channel.sent)} of {len(expected)}",
    )
    channel.delay = 0.0

    # ── concurrent queue() of one key ─────────────────────────────────────────
    outcomes = await asyncio.gather(*(outbox.queue(event("e2e:same", f"v{n}")) for n in range(10)))
    same = await rows(factory, "dedupe_key = 'e2e:same'")
    check("queue: ten concurrent queues of one key leave one row", len(same) == 1, f"rows={len(same)} queued={sum(outcomes)}/10")
    print(f"        (of the ten, {10 - sum(outcomes)} reported a failure; such an emit falls back to a direct dispatch)")

    # ── a deadlock while queueing aborts the caller's transaction: raised ─────
    await deadlock_check(engine, factory)

    # ── an internal event to two internal routes ──────────────────────────────
    channel.sent.clear()
    async with factory() as session:
        for name in ("Internal 1", "Internal 2"):
            session.add(
                CustomerNotificationRoute(
                    name=name,
                    scope="internal",
                    customer_code=None,
                    trigger="case_task_assigned",
                    channel="webhook",
                    destination="",
                    enabled=True,
                    min_severity="Informational",
                    recipient_mode="static",
                    config="{}",
                    created_at=datetime.utcnow(),
                    created_by="e2e-outbox",
                ),
            )
        await session.commit()
    task_event = case_task_assigned_event(task_id=990777, case_id=1, title="e2e", assignee="e2e-bob", actor="e2e-al")
    await outbox.queue(task_event)
    await outbox.drain_key(task_event.dedupe_key, settings)
    [row] = await rows(factory, "dedupe_key = :k", k=task_event.dedupe_key)
    check(
        "internal: each of two internal routes received the event once",
        row.status == "done" and sorted(channel.sent) == [("Internal 1", task_event.dedupe_key), ("Internal 2", task_event.dedupe_key)],
        f"{row.status} {channel.sent}",
    )
    async with factory() as session:
        await session.execute(text("DELETE FROM notification_dispatch_log WHERE dedupe_key = :k"), {"k": task_event.dedupe_key})
        await session.execute(text("DELETE FROM notification_outbox WHERE dedupe_key = :k"), {"k": task_event.dedupe_key})
        await session.execute(text("DELETE FROM customer_notification_route WHERE created_by = 'e2e-outbox'"))
        await session.commit()

    # ── an expired lease ──────────────────────────────────────────────────────
    [row] = same
    claim = await outbox._claim(row.id, datetime.utcnow())
    async with factory() as session:
        await session.execute(
            text("UPDATE notification_outbox SET updated_at = :t, claimed_at = :t WHERE id = :i"),
            {"t": datetime.utcnow() - timedelta(minutes=10), "i": row.id},
        )
        await session.commit()
    counts = await outbox.drain(settings)
    [row] = await rows(factory, "dedupe_key = 'e2e:same'")
    check(
        "lease: an abandoned claim is recovered to pending",
        claim is not None and counts["recovered"] == 1 and row.status == "pending",
        row.status,
    )

    await clean(factory)
    await engine.dispose()
    failed = [name for name, passed in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
