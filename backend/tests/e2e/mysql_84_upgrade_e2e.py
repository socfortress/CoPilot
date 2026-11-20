"""E2E for the move to MySQL 8.4: an existing database upgraded in place, and a fresh install
on a MySQL 8.4 that has none of the compose stack's flags. NOT collected by pytest: run by hand.
It needs Docker, starts its own throwaway servers on 127.0.0.1:13316 and removes them after.

    cd backend && PYTHONPATH=$PWD .venv/bin/python tests/e2e/mysql_84_upgrade_e2e.py

About 3 minutes (``mysql:8.0.46-debian`` has no arm64 build, so on Apple silicon it runs emulated).

What it proves:

A. An install on the image docker-compose.yml shipped before (``mysql:8.0.46-debian``), migrated
   to head, seeded, with its ``copilot`` user on ``mysql_native_password`` as a database first
   created by ``mysql:5.7`` has, then restarted on docker-compose.yml's own image and flags:
   - the documented backup command dumps it (docs/getting-started/install-upgrade.mdx);
   - MySQL upgrades it in place, and every table holds the same rows, byte for byte;
   - the ``copilot`` user still logs in, with PyMySQL and aiomysql;
   - startup's migrations are a no-op, and a later migration that alters ``customers`` and
     ``agents`` and adds foreign keys to ``customers.customer_code`` and ``agents.agent_id``
     applies and rolls back.
B. A fresh install on the same image without any flag (a MySQL 8.4 of the customer's own):
   - every migration applies from an empty database (against the pre-fix tree the first one stops
     with ERROR 6125), and the later migration of A applies and rolls back;
   - the server itself still refuses such a key (one to ``agents.agent_id``) outside the
     migrations: only their own sessions are relaxed;
   - ``mysql_native_password`` is off there, which is why compose turns it on.
"""
import asyncio
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PORT = 13316
os.environ.setdefault("MYSQL_URL", f"127.0.0.1:{PORT}")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")
assert os.environ["MYSQL_URL"] == f"127.0.0.1:{PORT}", "refusing to run against anything but this script's own server"

import aiomysql  # noqa: E402
import pymysql  # noqa: E402
import yaml  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from app.db.db_session import SQLALCHEMY_DATABASE_URI  # noqa: E402
from app.db.db_setup import apply_migrations  # noqa: E402

BACKEND = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((BACKEND.parent / "docker-compose.yml").read_text())["services"]["copilot-mysql"]
OLD_IMAGE = "mysql:8.0.46-debian"  # docker-compose.yml's image before MySQL 8.4
NEW_IMAGE = COMPOSE["image"]
NEW_FLAGS = list(COMPOSE.get("command") or [])
CONTAINER = "copilot-e2e-mysql84"
VOLUMES = ("copilot-e2e-mysql84-upgrade", "copilot-e2e-mysql84-fresh")
ROOT = {"host": "127.0.0.1", "port": PORT, "user": "root", "password": os.environ["MYSQL_ROOT_PASSWORD"]}
APP = {"host": "127.0.0.1", "port": PORT, "user": "copilot", "password": os.environ["MYSQL_PASSWORD"], "db": "copilot"}

FUTURE_REVISION = '''"""e2e only: what a later CoPilot migration may do on MySQL 8.4."""
import sqlalchemy as sa
from alembic import op

revision = "e2e_mysql84_future"
down_revision = "{down}"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("customers", sa.Column("e2e_mysql84", sa.Integer(), nullable=True))
    op.add_column("agents", sa.Column("e2e_mysql84", sa.Integer(), nullable=True))
    op.create_table(
        "e2e_mysql84_fk",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_code", sa.String(50), sa.ForeignKey("customers.customer_code", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(256), sa.ForeignKey("agents.agent_id"), nullable=True),
    )


def downgrade():
    op.drop_table("e2e_mysql84_fk")
    op.drop_column("agents", "e2e_mysql84")
    op.drop_column("customers", "e2e_mysql84")
'''

results = []


def check(name, passed, detail=""):
    results.append((name, passed))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def docker(*args, check_rc=True, **kwargs):
    return subprocess.run(["docker", *args], check=check_rc, capture_output=True, **kwargs)


def start(image, volume, flags=(), platform=None):
    docker("rm", "-f", CONTAINER, check_rc=False)
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
        f"{volume}:/var/lib/mysql",
        *env,
        image,
        *flags,
    )
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        try:
            pymysql.connect(**ROOT, connect_timeout=3).close()
            return
        except pymysql.MySQLError:
            if docker("inspect", "-f", "{{.State.Running}}", CONTAINER).stdout.strip() != b"true":
                sys.exit(f"{image} stopped: {docker('logs', CONTAINER, check_rc=False).stderr.decode()[-2000:]}")
            time.sleep(2)
    sys.exit(f"{image} did not accept connections in time")


def stop():
    with pymysql.connect(**ROOT) as conn, conn.cursor() as cur:
        cur.execute("SET GLOBAL innodb_fast_shutdown = 0")  # a clean shutdown before a major upgrade
    docker("stop", "-t", "300", CONTAINER)
    docker("rm", CONTAINER)


def query(sql, args=None, who=ROOT):
    with pymysql.connect(**who, connect_timeout=10) as conn, conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def server_version_id(version):
    major, minor, patch = (int(x) for x in re.match(r"(\d+)\.(\d+)\.(\d+)", version).groups())
    return f"{major}{minor:02d}{patch:02d}"


def fingerprint():
    """Every copilot table: (row count, SHA-256 of its rows in primary-key order)."""
    tables = [
        r[0] for r in query("SELECT table_name FROM information_schema.tables WHERE table_schema='copilot' AND table_type='BASE TABLE'")
    ]
    prints = {}
    with pymysql.connect(**ROOT, database="copilot") as conn, conn.cursor() as cur:
        for table in sorted(tables):
            cur.execute(
                "SELECT column_name FROM information_schema.key_column_usage "
                "WHERE table_schema='copilot' AND table_name=%s AND constraint_name='PRIMARY' ORDER BY ordinal_position",
                (table,),
            )
            keys = [r[0] for r in cur.fetchall()] or None
            order = ", ".join(f"`{k}`" for k in keys) if keys else "1"
            cur.execute(f"SELECT * FROM `{table}` ORDER BY {order}")
            rows = cur.fetchall()
            prints[table] = (len(rows), hashlib.sha256(repr(rows).encode()).hexdigest())
    return prints


def migrations_head():
    rows = query("SELECT version_num FROM copilot.alembic_version")
    return rows[0][0] if rows else None


def later_migration_round_trip():
    """Apply, then roll back, a revision that does what later CoPilot migrations do."""
    with tempfile.TemporaryDirectory() as tmp:
        scripts = Path(tmp) / "alembic"
        shutil.copytree(BACKEND / "alembic", scripts, ignore=shutil.ignore_patterns("__pycache__"))
        cfg = Config(str(scripts / "alembic.ini"))
        cfg.set_main_option("script_location", str(scripts))
        cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
        head = ScriptDirectory.from_config(cfg).get_current_head()
        (scripts / "versions" / "e2e_mysql84_future.py").write_text(FUTURE_REVISION.format(down=head))
        try:
            command.upgrade(cfg, "e2e_mysql84_future")
            made = query(
                "SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema='copilot' AND table_name='e2e_mysql84_fk'",
            )[0][0]
            command.downgrade(cfg, head)
        except Exception as e:  # report it as a failed check, with MySQL's own error
            return False, f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"
        gone = not query("SELECT 1 FROM information_schema.tables WHERE table_schema='copilot' AND table_name='e2e_mysql84_fk'")
        return made == 2 and gone and migrations_head() == head, f"2 foreign keys added and removed, back at {head}"


async def aiomysql_login():
    conn = await aiomysql.connect(host=APP["host"], port=PORT, user=APP["user"], password=APP["password"], db="copilot")
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT CURRENT_USER()")
            return (await cur.fetchone())[0]
    finally:
        conn.close()


def non_standard_keys():
    return query(
        "SELECT COUNT(*) FROM information_schema.key_column_usage k WHERE k.table_schema='copilot' "
        "AND k.referenced_table_name IS NOT NULL AND NOT EXISTS (SELECT 1 FROM information_schema.statistics s "
        "WHERE s.table_schema='copilot' AND s.table_name=k.referenced_table_name AND s.non_unique=0 "
        "AND s.column_name=k.referenced_column_name AND s.seq_in_index=1 AND NOT EXISTS (SELECT 1 FROM "
        "information_schema.statistics s2 WHERE s2.table_schema='copilot' AND s2.table_name=s.table_name "
        "AND s2.index_name=s.index_name AND s2.seq_in_index=2))",
    )[0][0]


def upgrade_of_an_existing_install():
    print(f"\nA. {OLD_IMAGE} -> {NEW_IMAGE} {' '.join(NEW_FLAGS)}")
    check("docker-compose.yml runs MySQL 8.4", bool(re.fullmatch(r"mysql:8\.4\.\d+", NEW_IMAGE)), NEW_IMAGE)
    start(OLD_IMAGE, VOLUMES[0], platform="linux/amd64")
    apply_migrations()
    # The seeds refuse any server but :13306 unless told: this one is this script's own.
    seed_env = {**os.environ, "E2E_ALLOW_ANY_DB": "1"}
    for seed in ("portal_overview_seed.py", "soc_management_seed.py"):
        done = subprocess.run([sys.executable, str(BACKEND / "tests" / "e2e" / seed), "seed"], capture_output=True, env=seed_env)
        if done.returncode:
            sys.exit(f"{seed} failed: {done.stderr.decode()[-2000:]}")
    query("ALTER USER 'copilot'@'%%' IDENTIFIED WITH mysql_native_password BY %s", (APP["password"],))
    head = migrations_head()
    before = fingerprint()
    rows = sum(count for count, _ in before.values())
    print(f"     {len(before)} tables, {rows} rows, migrations at {head}, copilot on mysql_native_password")

    dump = docker(
        "exec",
        CONTAINER,
        "sh",
        "-c",
        'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --all-databases --single-transaction --routines --events',
    ).stdout
    check(
        "the documented backup command dumps every table with its rows",
        b"CREATE TABLE `customers`" in dump and b"INSERT INTO `incident_management_alert`" in dump,
        f"{len(dump) // 1024} KB",
    )
    old_version = query("SELECT VERSION()")[0][0]
    stop()

    start(NEW_IMAGE, VOLUMES[0], flags=NEW_FLAGS)
    version = query("SELECT VERSION()")[0][0]
    logs = docker("logs", CONTAINER).stderr.decode() + docker("logs", CONTAINER).stdout.decode()
    upgraded = f"Server upgrade from '{server_version_id(old_version)}' to '{server_version_id(version)}' completed" in logs
    check("MySQL upgraded the 8.0 data in place", upgraded and NEW_IMAGE.endswith(version), f"{old_version} -> {version}")
    after = fingerprint()
    changed = [t for t in before if before[t] != after.get(t)]
    check(
        "every table holds the same rows",
        not changed and set(before) == set(after),
        f"{rows} rows" if not changed else f"changed: {changed[:5]}",
    )
    check("the native-password copilot user logs in with PyMySQL", query("SELECT CURRENT_USER()", who=APP)[0][0] == "copilot@%")
    check("... and with aiomysql", asyncio.run(aiomysql_login()) == "copilot@%")
    plugin = query("SELECT plugin_status FROM information_schema.plugins WHERE plugin_name='mysql_native_password'")
    restrict = query("SELECT @@GLOBAL.restrict_fk_on_non_standard_key")[0][0]
    check("compose's flags are in effect", plugin == (("ACTIVE",),) and restrict == 0, f"native password {plugin}, restriction {restrict}")
    apply_migrations()
    check("startup's migrations are a no-op", migrations_head() == head, head)
    ok, detail = later_migration_round_trip()
    check("a later migration altering customers and agents applies and rolls back", ok, detail)
    docker("rm", "-f", CONTAINER)


def fresh_install_without_flags():
    print(f"\nB. a fresh install on {NEW_IMAGE}, no flags (a MySQL 8.4 of the customer's own)")
    start(NEW_IMAGE, VOLUMES[1])
    try:
        apply_migrations()
        check("every migration applies to an empty database", migrations_head() is not None, migrations_head())
    except Exception as e:
        check("every migration applies to an empty database", False, f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")
        return
    print(f"     {non_standard_keys()} foreign keys point at a non-unique index")
    ok, detail = later_migration_round_trip()
    check("a later migration altering customers and agents applies and rolls back", ok, detail)
    try:
        # agents.agent_id: customers.customer_code is unique since 38c2e85a670a, so a key to it is standard.
        query(
            "CREATE TABLE e2e_mysql84_plain (agent_id VARCHAR(256), FOREIGN KEY (agent_id) REFERENCES agents (agent_id))",
            who=APP,
        )
        refused = "created"
    except pymysql.MySQLError as e:
        refused = e.args[0]
    check("outside the migrations the server still refuses such a key", refused == 6125, f"ERROR {refused}")
    plugin = query("SELECT plugin_status FROM information_schema.plugins WHERE plugin_name='mysql_native_password'")
    check("mysql_native_password is off without compose's flag", plugin == (("DISABLED",),), str(plugin))


def main() -> int:
    try:
        upgrade_of_an_existing_install()
        fresh_install_without_flags()
    finally:
        docker("rm", "-f", CONTAINER, check_rc=False)
        for volume in VOLUMES:
            docker("volume", "rm", volume, check_rc=False)
    failed = [name for name, passed in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    for name in failed:
        print(f"  FAILED: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
