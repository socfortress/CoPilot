"""E2E for migration 38c2e85a670a (unique ``customers.customer_code``) on real MySQL 8.0 and 8.4.
NOT collected by pytest: run by hand. It needs Docker, starts its own throwaway servers on
127.0.0.1:13317 and removes them after.

    cd backend && PYTHONPATH=$PWD .venv/bin/python tests/e2e/unique_tenant_keys_e2e.py

About 3 minutes (``mysql:8.0.46-debian`` has no arm64 build, so on Apple silicon it runs emulated).

What it proves, on ``mysql:8.0.46-debian`` (docker-compose.yml's image before MySQL 8.4) and on
``mysql:8.4.13`` with ``--restrict-fk-on-non-standard-key=OFF`` (as docker-compose.yml runs it):
- the whole chain applies and the index is unique: of the foreign keys pointing at a non-unique
  index, only the 2 to ``agents.agent_id`` are left, which stays non-unique on purpose;
- on 8.4 with the restriction back ON, a plain connection alters ``customers`` and adds a foreign
  key to ``customers.customer_code`` (against the pre-migration schema both fail, with ERROR 1553
  and 6125), while an ALTER on ``agents`` is still refused (ERROR 1553);
- the downgrade puts the non-unique index back;
- with duplicates (``E2E-DUP`` and ``e2e-dup`` are one value to the collation), the migration still
  reaches head, leaves the index non-unique and names them, and the statement its warning gives
  works once they are resolved.
"""
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PORT = 13317
os.environ.setdefault("MYSQL_URL", f"127.0.0.1:{PORT}")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")
assert os.environ["MYSQL_URL"] == f"127.0.0.1:{PORT}", "refusing to run against anything but this script's own server"

import pymysql  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.db.db_session import SQLALCHEMY_DATABASE_URI  # noqa: E402

BACKEND = Path(__file__).resolve().parents[2]
REVISION, PREVIOUS = "38c2e85a670a", "c0d98a0b1c2d"
SERVERS = (
    ("mysql:8.0.46-debian", "linux/amd64", []),
    ("mysql:8.4.13", None, ["--restrict-fk-on-non-standard-key=OFF"]),
)
CONTAINER, VOLUME = "copilot-e2e-unique-keys", "copilot-e2e-unique-keys"
ROOT = {"host": "127.0.0.1", "port": PORT, "user": "root", "password": os.environ["MYSQL_ROOT_PASSWORD"]}
APP = {"host": "127.0.0.1", "port": PORT, "user": "copilot", "password": os.environ["MYSQL_PASSWORD"], "database": "copilot"}

results = []
warnings = []


class Collect(logging.Handler):
    def emit(self, record):
        warnings.append(record.getMessage())
        print(f"     migration warning: {record.getMessage()[:160]}")


logging.getLogger("alembic.runtime.migration").addHandler(Collect(level=logging.WARNING))


def check(name, passed, detail=""):
    results.append((name, passed))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def docker(*args, check_rc=True):
    return subprocess.run(["docker", *args], check=check_rc, capture_output=True)


def start(image, platform, flags):
    docker("rm", "-f", CONTAINER, check_rc=False)
    docker("volume", "rm", VOLUME, check_rc=False)
    env = ["-e", "MYSQL_ROOT_PASSWORD=" + ROOT["password"], "-e", "MYSQL_DATABASE=copilot"]
    env += ["-e", "MYSQL_USER=copilot", "-e", "MYSQL_PASSWORD=" + APP["password"]]
    platform_args = ["--platform", platform] if platform else []
    docker(
        "run",
        "-d",
        "--name",
        CONTAINER,
        *platform_args,
        "-p",
        f"127.0.0.1:{PORT}:3306",
        "-v",
        f"{VOLUME}:/var/lib/mysql",
        *env,
        image,
        *flags,
    )
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        try:
            pymysql.connect(**APP, connect_timeout=3).close()
            return
        except pymysql.MySQLError:
            time.sleep(2)
    sys.exit(f"{image} did not accept connections in time")


def query(sql, args=None, who=ROOT):
    with pymysql.connect(**who, connect_timeout=10, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def refused(sql):
    """None if ``sql`` runs as the app's user on a fresh connection, else the MySQL error number."""
    try:
        query(sql, who=APP)
        return None
    except pymysql.MySQLError as e:
        return e.args[0]


def alembic(action, target):
    # No ini file: env.py then skips fileConfig, which would reset the logger the warnings are collected from.
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
    getattr(command, action)(cfg, target)
    return query("SELECT version_num FROM copilot.alembic_version")[0][0]


def unique(table, index):
    rows = query(
        "SELECT MIN(non_unique) FROM information_schema.statistics WHERE table_schema='copilot' AND table_name=%s AND index_name=%s",
        (table, index),
    )
    return rows[0][0] == 0


def customer_code_unique():
    return unique("customers", "ix_customers_customer_code")


def non_standard_keys():
    """Foreign keys whose referenced column is not alone in a unique index, by referenced column."""
    return query(
        "SELECT CONCAT(k.referenced_table_name, '.', k.referenced_column_name), COUNT(*) FROM information_schema.key_column_usage k "
        "WHERE k.table_schema='copilot' AND k.referenced_table_name IS NOT NULL AND NOT EXISTS (SELECT 1 FROM "
        "information_schema.statistics s WHERE s.table_schema='copilot' AND s.table_name=k.referenced_table_name AND s.non_unique=0 "
        "AND s.column_name=k.referenced_column_name AND s.seq_in_index=1 AND NOT EXISTS (SELECT 1 FROM "
        "information_schema.statistics s2 WHERE s2.table_schema='copilot' AND s2.table_name=s.table_name "
        "AND s2.index_name=s.index_name AND s2.seq_in_index=2)) GROUP BY 1 ORDER BY 1",
    )


def insert_customer(code):
    """Insert a customer, filling every other NOT NULL column without a default."""
    columns = query(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='copilot' AND table_name='customers' "
        "AND is_nullable='NO' AND column_default IS NULL AND extra NOT LIKE '%%auto_increment%%'",
    )
    numbers = ("int", "bigint", "smallint", "mediumint", "tinyint", "float", "double", "decimal")
    fill = {**{kind: 0 for kind in numbers}, "datetime": "2026-01-01 00:00:00", "timestamp": "2026-01-01 00:00:00", "date": "2026-01-01"}
    row = {name: fill.get(kind, "e2e") for name, kind in columns}
    row["customer_code"] = code
    names = ", ".join(f"`{name}`" for name in row)
    query(f"INSERT INTO copilot.customers ({names}) VALUES ({', '.join(['%s'] * len(row))})", list(row.values()))


def run(image, platform, flags):
    print(f"\n{image} {' '.join(flags)}")
    start(image, platform, flags)
    version = alembic("upgrade", "head")
    check("the whole chain applies", version == REVISION, version)
    check("customers.customer_code is unique", customer_code_unique())
    left = dict(non_standard_keys())
    check("only the 2 keys to agents.agent_id still point at a non-unique index", left == {"agents.agent_id": 2}, str(left))
    check("agents.agent_id stays non-unique", not unique("agents", "ix_agents_agent_id"))

    if image.startswith("mysql:8.4"):
        query("SET GLOBAL restrict_fk_on_non_standard_key = ON")
        alter_customers = refused("ALTER TABLE customers ADD COLUMN e2e_unique INT NULL")
        new_key = refused(
            "CREATE TABLE e2e_unique_fk (id INT PRIMARY KEY, customer_code VARCHAR(50) NOT NULL, "
            "FOREIGN KEY (customer_code) REFERENCES customers (customer_code))",
        )
        alter_agents = refused("ALTER TABLE agents ADD COLUMN e2e_unique INT NULL")
        check(
            "with the restriction ON, an ALTER on customers and a new key to customer_code work",
            alter_customers is None and new_key is None,
            f"alter {alter_customers}, key {new_key}",
        )
        check("... while an ALTER on agents is still refused", alter_agents == 1553, f"ERROR {alter_agents}")
        query("SET GLOBAL restrict_fk_on_non_standard_key = OFF")  # the downgrade needs it, as before this migration
        for sql in ("DROP TABLE IF EXISTS e2e_unique_fk", "ALTER TABLE customers DROP COLUMN e2e_unique"):
            query(sql, who=APP)

    version = alembic("downgrade", PREVIOUS)
    check("the downgrade puts the non-unique index back", version == PREVIOUS and not customer_code_unique())

    insert_customer("E2E-DUP")
    insert_customer("e2e-dup")
    warnings.clear()
    version = alembic("upgrade", "head")
    named = [w for w in warnings if "duplicate values" in w]
    check("with duplicates the migration reaches head and leaves the index non-unique", version == REVISION and not customer_code_unique())
    check(
        "... and its warning names them",
        len(named) == 1 and "'E2E-DUP'" in named[0],
        named[0].split(", so")[0] if named else "no warning",
    )
    query("DELETE FROM copilot.customers WHERE customer_code = 'e2e-dup' COLLATE utf8mb4_bin")
    if named:
        query(re.search(r"run: (ALTER TABLE .*)$", named[0]).group(1).replace("ALTER TABLE ", "ALTER TABLE copilot."))
    check("once resolved, the statement the warning gives makes it unique", customer_code_unique())
    docker("rm", "-f", CONTAINER)


def main() -> int:
    try:
        for server in SERVERS:
            run(*server)
    finally:
        docker("rm", "-f", CONTAINER, check_rc=False)
        docker("volume", "rm", VOLUME, check_rc=False)
    failed = [name for name, passed in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    for name in failed:
        print(f"  FAILED: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
