"""E2E for migrations a5b1c0d2e3f4 (one report per AI analyst job) and a5b1c0d2e3f5 (wider
drawer_id). NOT collected by pytest: it needs a live, disposable MySQL.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \\
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \\
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \\
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \\
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python tests/e2e/talon_connector_migrations_e2e.py

Point it at a throwaway instance on 13306, never at the MySQL in .env: it migrates the
database down and up and writes AI analyst rows.

What it proves, on real MySQL:
- duplicate reports already in the table don't stop the upgrade: the newest stays on the
  job, each older one moves to a `split-…` job, and its IOCs and reviews stay with it;
- afterwards a second report for a job is refused by the index, under the name the
  service looks for;
- a 255-character-wide drawer_id stores a long MemPalace id; narrowing it back refuses while
  such an id is stored;
- both downgrades run, and the upgrade runs again over data the downgrade allowed.
"""
import os
import sys

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.db.db_session import SQLALCHEMY_DATABASE_URI  # noqa: E402
from app.db.universal_models import REPORT_JOB_UNIQUE  # noqa: E402

BEFORE = "e1258b2c3d4e"
UNIQUE_REV = "a5b1c0d2e3f4"
DRAWER_REV = "a5b1c0d2e3f5"
CUSTOMER = "E2E_M51"
LONG_JOB = "copilot-inv-77-" + "9" * 49  # 64 characters, the column's limit
LONG_DRAWER = "drawer_" + "e2e_a_very_long_customer_code_" * 3 + "_false_positives_" + "a" * 24

URL = SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql")
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


def q(conn, sql, **params):
    return conn.execute(text(sql), params)


def clean(conn):
    q(conn, "DELETE FROM ai_analyst_palace_lesson WHERE customer_code = :c", c=CUSTOMER)
    q(
        conn,
        "DELETE ir FROM ai_analyst_ioc_review ir JOIN ai_analyst_review r ON r.id = ir.review_id WHERE r.customer_code = :c",
        c=CUSTOMER,
    )
    q(conn, "DELETE FROM ai_analyst_review WHERE customer_code = :c", c=CUSTOMER)
    q(conn, "DELETE FROM ai_analyst_ioc WHERE customer_code = :c", c=CUSTOMER)
    q(conn, "DELETE FROM ai_analyst_report WHERE customer_code = :c", c=CUSTOMER)
    q(conn, "DELETE FROM ai_analyst_job WHERE customer_code = :c", c=CUSTOMER)
    q(conn, "DELETE FROM customers WHERE customer_code = :c", c=CUSTOMER)


def add_job(conn, job_id, alert_id):
    q(
        conn,
        "INSERT INTO ai_analyst_job (id, alert_id, customer_code, status, triggered_by, template_used, created_at) "
        "VALUES (:id, :a, :c, 'completed', 'webhook', 'sysmon_event_1.txt', '2026-10-01 08:00:00')",
        id=job_id,
        a=alert_id,
        c=CUSTOMER,
    )


def add_report(conn, job_id, alert_id, created_at) -> int:
    q(
        conn,
        "INSERT INTO ai_analyst_report (job_id, alert_id, customer_code, summary, created_at) VALUES (:j, :a, :c, :s, :t)",
        j=job_id,
        a=alert_id,
        c=CUSTOMER,
        s=f"report of {job_id} at {created_at}",
        t=created_at,
    )
    return q(conn, "SELECT LAST_INSERT_ID()").scalar()


def job_of(conn, report_id):
    return q(conn, "SELECT job_id FROM ai_analyst_report WHERE id = :r", r=report_id).scalar()


def has_unique(conn) -> bool:
    return bool(
        q(
            conn,
            "SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = DATABASE() "
            "AND table_name = 'ai_analyst_report' AND index_name = :n AND non_unique = 0",
            n=REPORT_JOB_UNIQUE,
        ).scalar(),
    )


def drawer_width(conn) -> int:
    return q(
        conn,
        "SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.columns WHERE table_schema = DATABASE() "
        "AND table_name = 'ai_analyst_palace_lesson' AND column_name = 'drawer_id'",
    ).scalar()


def main() -> int:
    cfg = alembic_cfg()
    engine = create_engine(URL)

    print("== migrate to the revision before this change")
    # From wherever an earlier run left the database: up to head, clear our rows, back down.
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        clean(conn)
    command.downgrade(cfg, BEFORE)
    with engine.begin() as conn:
        q(conn, "INSERT INTO customers (customer_code, customer_name, created_at) VALUES (:c, 'E2E M5-1', NOW())", c=CUSTOMER)
        add_job(conn, "copilot-inv-70-1", 70)
        add_job(conn, "copilot-inv-71-1", 71)
        add_job(conn, LONG_JOB, 77)
        r_old = add_report(conn, "copilot-inv-70-1", 70, "2026-10-01 08:01:00")
        r_mid = add_report(conn, "copilot-inv-70-1", 70, "2026-10-01 08:02:00")
        # Planted on pre-upgrade code, where an analyst could create a job under any id for
        # their customers: an unrelated job holding the id r_mid's split would get.
        add_job(conn, f"split-{r_mid}-copilot-inv-70-1", 99)
        # A look-alike of this migration's own split (same alert, customer and note) that
        # already holds a report: reusing it would put two reports on one job.
        add_job(conn, "copilot-inv-72-1", 72)
        r72_old = add_report(conn, "copilot-inv-72-1", 72, "2026-10-01 08:07:00")
        r72_new = add_report(conn, "copilot-inv-72-1", 72, "2026-10-01 08:08:00")
        lookalike = f"split-{r72_old}-copilot-inv-72-1"
        add_job(conn, lookalike, 72)
        q(
            conn,
            "UPDATE ai_analyst_job SET error_message = :n WHERE id = :id",
            n=f"Split from job copilot-inv-72-1 by migration {UNIQUE_REV}: it held a second report for that job.",
            id=lookalike,
        )
        r_planted = add_report(conn, lookalike, 72, "2026-10-01 08:09:00")
        r_new = add_report(conn, "copilot-inv-70-1", 70, "2026-10-01 08:03:00")
        r_single = add_report(conn, "copilot-inv-71-1", 71, "2026-10-01 08:04:00")
        r_long_old = add_report(conn, LONG_JOB, 77, "2026-10-01 08:05:00")
        r_long_new = add_report(conn, LONG_JOB, 77, "2026-10-01 08:06:00")
        q(
            conn,
            "INSERT INTO ai_analyst_ioc (report_id, alert_id, customer_code, ioc_value, ioc_type, vt_verdict, created_at) "
            "VALUES (:r, 70, :c, '203.0.113.9', 'ip', 'unknown', NOW())",
            r=r_old,
            c=CUSTOMER,
        )
        q(
            conn,
            "INSERT INTO ai_analyst_review (report_id, alert_id, customer_code, reviewer_user_id, created_at) VALUES (:r, 70, :c, 1, NOW())",
            r=r_old,
            c=CUSTOMER,
        )
    check("before: no unique index on job_id", not has_unique(engine.connect()))

    print("== upgrade to head over duplicate reports")
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        check("the unique index exists", has_unique(conn))
        check("drawer_id is 255 wide", drawer_width(conn) == 255, str(drawer_width(conn)))
        check("the newest report stays on its job", job_of(conn, r_new) == "copilot-inv-70-1")
        check("a job with one report is untouched", job_of(conn, r_single) == "copilot-inv-71-1")
        check("an older duplicate moves to its own job", job_of(conn, r_old) == f"split-{r_old}-copilot-inv-70-1", job_of(conn, r_old))
        check(
            "an unrelated job already holding a split id is not used: the next suffix is",
            job_of(conn, r_mid) == f"split-{r_mid}-2-copilot-inv-70-1",
            job_of(conn, r_mid),
        )
        planted = q(conn, "SELECT alert_id FROM ai_analyst_job WHERE id = :id", id=f"split-{r_mid}-copilot-inv-70-1").scalar()
        check(
            "and the planted job is left as it was, with no report",
            planted == 99
            and q(conn, "SELECT COUNT(*) FROM ai_analyst_report WHERE job_id = :id", id=f"split-{r_mid}-copilot-inv-70-1").scalar() == 0,
        )
        check(
            "a look-alike split that already holds a report is not reused",
            job_of(conn, r72_old) == f"split-{r72_old}-2-copilot-inv-72-1"
            and job_of(conn, r72_new) == "copilot-inv-72-1"
            and job_of(conn, r_planted) == lookalike,
            job_of(conn, r72_old),
        )
        split = q(
            conn,
            "SELECT alert_id, customer_code, status, completed_at, error_message, template_used FROM ai_analyst_job WHERE id = :id",
            id=f"split-{r_old}-copilot-inv-70-1",
        ).first()
        check(
            "the split job copies the original and says where it came from",
            split is not None
            and split.alert_id == 70
            and split.customer_code == CUSTOMER
            and split.status == "completed"
            and str(split.completed_at) == "2026-10-01 08:01:00"
            and "copilot-inv-70-1" in split.error_message
            and split.template_used == "sysmon_event_1.txt",
            str(split),
        )
        long_split = job_of(conn, r_long_old)
        check(
            "a split id is cut to 64 characters",
            job_of(conn, r_long_new) == LONG_JOB
            and long_split is not None
            and len(long_split) == 64
            and long_split.startswith(f"split-{r_long_old}-"),
            long_split,
        )
        check(
            "the moved report keeps its IOCs and review",
            q(conn, "SELECT COUNT(*) FROM ai_analyst_ioc WHERE report_id = :r", r=r_old).scalar() == 1
            and q(conn, "SELECT COUNT(*) FROM ai_analyst_review WHERE report_id = :r", r=r_old).scalar() == 1,
        )
        check(
            "no job holds two reports",
            q(conn, "SELECT COUNT(*) FROM (SELECT job_id FROM ai_analyst_report GROUP BY job_id HAVING COUNT(*) > 1) d").scalar() == 0,
        )

    try:
        with engine.begin() as conn:
            add_report(conn, "copilot-inv-71-1", 71, "2026-10-01 09:00:00")
        check("a second report for a job is refused", False, "insert succeeded")
    except IntegrityError as e:
        check("a second report for a job is refused, naming the index the service matches", REPORT_JOB_UNIQUE in str(e.orig), str(e.orig))

    with engine.begin() as conn:
        q(
            conn,
            "INSERT INTO ai_analyst_palace_lesson (customer_code, lesson_type, lesson_text, durability, status, drawer_id, created_at) "
            "VALUES (:c, 'false_positives', 't', 'one_off', 'ingested', :d, NOW())",
            c=CUSTOMER,
            d=LONG_DRAWER,
        )
        stored = q(conn, "SELECT drawer_id FROM ai_analyst_palace_lesson WHERE customer_code = :c", c=CUSTOMER).scalar()
        check(f"a {len(LONG_DRAWER)}-character drawer id is stored whole", stored == LONG_DRAWER)

    print("== downgrade")
    try:
        command.downgrade(cfg, UNIQUE_REV)
        check("narrowing drawer_id refuses while a long id is stored", False, "downgrade ran")
    except RuntimeError as e:
        check("narrowing drawer_id refuses while a long id is stored", "longer" in str(e), str(e))
    with engine.begin() as conn:
        check("the refused downgrade left the column as it was", drawer_width(conn) == 255)
        q(conn, "DELETE FROM ai_analyst_palace_lesson WHERE customer_code = :c", c=CUSTOMER)
    command.downgrade(cfg, UNIQUE_REV)
    with engine.begin() as conn:
        check("drawer_id is back to 64", drawer_width(conn) == 64)
    command.downgrade(cfg, BEFORE)
    with engine.begin() as conn:
        check("the unique index is gone", not has_unique(conn))
        check("the split-off jobs stay", job_of(conn, r_old) == f"split-{r_old}-copilot-inv-70-1")
        dup = add_report(conn, "copilot-inv-71-1", 71, "2026-10-01 10:00:00")
        check("a duplicate can be written again", dup is not None)

    print("== upgrade again")
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        check("the index is back", has_unique(conn))
        # The duplicate written while downgraded is the newer report, so it keeps the job.
        check("the newer report keeps the job", job_of(conn, dup) == "copilot-inv-71-1", job_of(conn, dup))
        check("and the older one is split off", job_of(conn, r_single) == f"split-{r_single}-copilot-inv-71-1", job_of(conn, r_single))
    command.upgrade(cfg, "head")
    check("upgrading at head again is a no-op", True)

    with engine.begin() as conn:
        clean(conn)
    engine.dispose()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
