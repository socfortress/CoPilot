"""E2E for upgrade.sh: real CoPilot stacks in Docker, upgraded, re-run, rolled back.
NOT collected by pytest: run by hand. Needs Docker and the network (images are pulled), takes 30-60
minutes on Apple silicon (every image runs as linux/amd64, as on a customer's host), and leaves
nothing behind: each stack lives in its own temporary directory and is removed with its volumes.

    cd backend && /path/to/python tests/e2e/upgrade_script_e2e.py [a] [b]

Each stack is a docker-compose.yml written like the repository's before MySQL 8.4 (backend, MySQL,
MinIO; no published ports), an .env made from .env.example, a schema migrated to c0d98a0b1c2d (the
migration before 38c2e85a670a) by the backend image itself, a few customers, the copilot user on
mysql_native_password like installs first created with mysql:5.7, and a stand-in for the old backend.
On Apple silicon, MinIO is a stand-in too (see MINIO), and every other image runs as linux/amd64.

Scenario a (MySQL 8.0.46):
- refusals before anything changes: a docker-compose.yml tracked by git, a wrong root password;
- --check reports the plan and changes nothing;
- the upgrade: MySQL 8.4.13 with both flags, docker-compose.yml edited and nothing else in it, the dump
  and the archive, the backend up with 38c2e85a670a applied on 8.4, the customers kept;
- running it again changes nothing;
- --rollback: MySQL 8.0.46 again, the data as it was before the upgrade (a row written after it is
  gone), docker-compose.yml byte for byte as before;
- then the same with docker-compose.yml already updated (as `git pull` leaves it) while 8.0 still
  runs: upgraded without editing the file, and the rollback takes the image and flags back out.
Scenario b (MySQL 5.7.44): upgraded through 8.0.46 to 8.4.13, the backend up, the customers kept.
"""
import base64
import os
import platform
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "upgrade.sh"
HEAD, BEFORE_HEAD = "38c2e85a670a", "c0d98a0b1c2d"
BACKEND_IMAGE = "ghcr.io/socfortress/copilot-backend:latest"
ENV = dict(os.environ)
# MinIO is no part of the upgrade, but the backend's startup checks its buckets. Its amd64 build
# crashes under emulation (a Go netpoll SIGSEGV) and no arm64 build can be pulled any more, so on
# Apple silicon a few lines of Python answer those checks instead (S3_STUB).
MINIO = """\
    copilot-minio:
        image: ghcr.io/socfortress/minio:release.2024-09-13t20-26-02z
        environment:
            MINIO_ROOT_USER: ${MINIO_ROOT_USER}
            MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
        volumes:
            - ./data/data/minio-data:/data
        command: server /data --console-address ":9001"
        restart: always
"""
S3_STUB = """\
import signal
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # as PID 1 it would ignore docker stop

LOCATION = b'<?xml version="1.0" encoding="UTF-8"?><LocationConstraint xmlns="http://s3.amazonaws.com/doc/2006-03-01/"></LocationConstraint>'


class Handler(BaseHTTPRequestHandler):
    def reply(self, body=b""):
        self.send_response(200)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        self.reply(LOCATION)

    def do_HEAD(self):
        self.reply()

    def do_PUT(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.reply()

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("", 9000), Handler).serve_forever()
"""
if platform.machine() in ("arm64", "aarch64"):
    ENV["DOCKER_DEFAULT_PLATFORM"] = "linux/amd64"
    MINIO = """\
    copilot-minio:
        image: python:3.12-alpine
        platform: linux/arm64
        volumes:
            - ./s3-stub.py:/stub.py:ro
        command: ["python", "/stub.py"]
        restart: always
"""

COMPOSE = """\
version: "2"

services:
    copilot-backend:
        image: ghcr.io/socfortress/copilot-backend:latest
        volumes:
            - ./data/copilot-backend-data/logs:/opt/logs
            # Mount the copilot.db file to persist the database
            - ./data/data:/opt/copilot/backend/data
        env_file: .env
        depends_on:
            - copilot-mysql
        restart: always

    copilot-mysql:
        image: {mysql_image}
        environment:
            MYSQL_ROOT_PASSWORD: ${{MYSQL_ROOT_PASSWORD}}
            MYSQL_DATABASE: copilot
            MYSQL_USER: ${{MYSQL_USER}}
            MYSQL_PASSWORD: ${{MYSQL_PASSWORD}}
        volumes:
            - mysql-data:/var/lib/mysql
        restart: always

{minio}
volumes:
    mysql-data:
"""

# Holds the old backend's place: the upgrade has to stop it, and its `up -d` replaces it with the real one.
BEFORE_OVERRIDE = """\
services:
    copilot-backend:
        entrypoint: ["sh", "-c", "trap 'exit 0' TERM; while :; do sleep 1; done"]
"""

MIGRATE = f"""
from alembic import command
from alembic.config import Config
from app.db.db_session import SQLALCHEMY_DATABASE_URI
cfg = Config("alembic/alembic.ini")
cfg.set_main_option("script_location", "alembic")
cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
command.upgrade(cfg, "{BEFORE_HEAD}")
"""

results = []


def check(name, passed, detail=""):
    """Record a check; its detail is printed when it fails, or when it is one short line."""
    results.append((name, passed))
    shown = detail if detail and (not passed or (len(detail) <= 80 and "\n" not in detail)) else ""
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{shown}]" if shown else ""), flush=True)


def sh(args, cwd, check_rc=True, input=None, timeout=3600):
    result = subprocess.run(args, cwd=cwd, env=ENV, capture_output=True, text=True, input=input, timeout=timeout)
    if check_rc and result.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, args))} failed ({result.returncode}):\n{result.stdout[-3000:]}\n{result.stderr[-3000:]}")
    return result


def upgrade(project, *args, env_extra=None):
    """Run upgrade.sh; its output is kept next to the stack for a look afterwards."""
    env = dict(ENV, **(env_extra or {}))
    started = time.monotonic()
    result = subprocess.run([str(project / "upgrade.sh"), *args], cwd=project, env=env, capture_output=True, text=True, timeout=7200)
    name = "-".join(a.strip("-") for a in args) or "upgrade"
    (project / f"run-{name}-{int(time.time())}.log").write_text(result.stdout + "\n--- stderr ---\n" + result.stderr)
    print(f"     ./upgrade.sh {' '.join(args)}: exit {result.returncode} in {time.monotonic() - started:.0f}s", flush=True)
    return result


def compose(project, *args, **kwargs):
    return sh(["docker", "compose", *args], cwd=project, **kwargs)


def sql(project, statement):
    out = compose(
        project,
        "exec",
        "-T",
        "copilot-mysql",
        "sh",
        "-c",
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N -B -e "$1"',
        "sh",
        statement,
    )
    return out.stdout.strip()


def wait_mysql(project, timeout=900):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if sql(project, "SELECT 1") == "1":
                return
        except RuntimeError:
            pass
        time.sleep(3)
    raise RuntimeError("MySQL didn't come up")


PROBE = """
import urllib.error, urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:5000/", timeout=5)
except urllib.error.HTTPError:
    pass
"""


def wait_backend(project, timeout=1800):
    """Whether the backend answers HTTP, i.e. has started (its log loses uvicorn's startup line once migrations ran)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        cid = compose(project, "ps", "-q", "copilot-backend").stdout.strip()
        if cid and sh(["docker", "exec", cid, "python3", "-c", PROBE], cwd=project, check_rc=False).returncode == 0:
            return True
        time.sleep(5)
    return False


def make_env(project):
    text = (REPO / ".env.example").read_text()
    values = {
        "JWT_SECRET": secrets.token_hex(24),
        "MYSQL_URL": "copilot-mysql",
        "MYSQL_ROOT_PASSWORD": secrets.token_hex(12),
        "MYSQL_USER": "copilot",
        "MYSQL_PASSWORD": secrets.token_hex(12),
        "MINIO_URL": "copilot-minio",
        "MINIO_ROOT_USER": "admin",
        "MINIO_ROOT_PASSWORD": secrets.token_hex(12),
        "TOTP_ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode(),
        "WAF_TOKEN_ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode(),
        "SSO_STATE_SECRET": secrets.token_hex(24),
        "ANNOUNCEMENTS_ENABLED": "false",
        "TALON_RELEASE_CHECK_ENABLED": "false",
    }
    for key, value in values.items():
        text = re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.M)
    (project / ".env").write_text(text)
    return values


def insert_customer(project, code):
    """Insert a customer, filling every other NOT NULL column without a default."""
    rows = sql(
        project,
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='copilot' AND table_name='customers' "
        "AND is_nullable='NO' AND column_default IS NULL AND extra NOT LIKE '%auto_increment%'",
    )
    numbers = {"int", "bigint", "smallint", "mediumint", "tinyint", "float", "double", "decimal"}
    columns = {"customer_code": f"'{code}'"}
    for line in rows.splitlines():
        name, kind = line.split("\t")
        if name != "customer_code":
            columns[name] = "0" if kind in numbers else "'2026-01-01 00:00:00'" if kind in ("datetime", "timestamp") else "'e2e'"
    sql(project, f"INSERT INTO copilot.customers ({', '.join(columns)}) VALUES ({', '.join(columns.values())})")


def new_project(name):
    return Path(tempfile.mkdtemp(prefix=f"copilot-upgrade-{name}-"))


def build_stack(project, name, mysql_image):
    """A CoPilot directory as an install before MySQL 8.4 left it, running."""
    (project / "docker-compose.yml").write_text(COMPOSE.format(mysql_image=mysql_image, minio=MINIO))
    (project / "s3-stub.py").write_text(S3_STUB)
    (project / "before.yml").write_text(BEFORE_OVERRIDE)
    shutil.copy(SCRIPT, project / "upgrade.sh")
    values = make_env(project)
    (project / "data" / "data").mkdir(parents=True)
    print(f"\n[{name}] {mysql_image} in {project}", flush=True)
    compose(project, "up", "-d", "copilot-mysql", "copilot-minio")
    wait_mysql(project)
    compose(project, "run", "--rm", "--no-deps", "copilot-backend", "python", "-c", MIGRATE, timeout=3600)
    for code in ("E2E-A", "E2E-B", "E2E-C"):
        insert_customer(project, code)
    # As on installs first created with mysql:5.7 (where it is the default already).
    sql(project, f"ALTER USER 'copilot'@'%' IDENTIFIED WITH mysql_native_password BY '{values['MYSQL_PASSWORD']}'")
    compose(project, "-f", "docker-compose.yml", "-f", "before.yml", "up", "-d", "copilot-backend")


def teardown(project):
    compose(project, "down", "-v", "--remove-orphans", check_rc=False)
    sh(["docker", "run", "--rm", "-v", f"{project}:/p", "alpine:3", "sh", "-c", "rm -rf /p/data /p/backups"], cwd="/", check_rc=False)
    shutil.rmtree(project, ignore_errors=True)


def mysql_service(project):
    return yaml.safe_load((project / "docker-compose.yml").read_text())["services"]["copilot-mysql"]


def runs(project):
    return sorted((project / "backups").glob("upgrade-*"))


def state(run_dir):
    return dict(line.split("=", 1) for line in (run_dir / "state").read_text().splitlines() if "=" in line)


def verify_upgraded(project, label, codes):
    check(f"{label}: MySQL is 8.4.13", sql(project, "SELECT VERSION()") == "8.4.13")
    check(
        f"{label}: with both flags",
        sql(project, "SELECT @@GLOBAL.restrict_fk_on_non_standard_key") == "0"
        and sql(project, "SELECT plugin_status FROM information_schema.plugins WHERE plugin_name='mysql_native_password'") == "ACTIVE",
    )
    check(f"{label}: the backend started", wait_backend(project))
    check(f"{label}: and applied {HEAD} on 8.4", sql(project, "SELECT version_num FROM copilot.alembic_version") == HEAD)
    unique = sql(
        project,
        "SELECT MIN(non_unique) FROM information_schema.statistics WHERE table_schema='copilot' AND table_name='customers' "
        "AND index_name='ix_customers_customer_code'",
    )
    check(f"{label}: customers.customer_code is unique", unique == "0")
    have = sql(project, "SELECT GROUP_CONCAT(customer_code ORDER BY customer_code) FROM copilot.customers WHERE customer_code LIKE 'E2E-%'")
    check(f"{label}: the customers are kept", have == ",".join(codes), have)
    check(
        f"{label}: copilot still logs in with mysql_native_password",
        sql(project, "SELECT plugin FROM mysql.user WHERE user='copilot'") == "mysql_native_password",
    )


def scenario_a():
    project = new_project("a")
    try:
        build_stack(project, "a", "mysql:8.0.46-debian")
        original = (project / "docker-compose.yml").read_bytes()
        # Refusals, before anything changes.
        sh(["git", "init", "-q"], cwd=project)
        sh(["git", "add", "docker-compose.yml"], cwd=project)
        sh(["git", "-c", "user.name=e2e", "-c", "user.email=e2e@example.invalid", "commit", "-qm", "compose"], cwd=project)
        refused = upgrade(project, "--yes")
        check("a git-tracked old docker-compose.yml is refused", refused.returncode == 1 and "git pull" in refused.stderr)
        shutil.rmtree(project / ".git")
        wrong = upgrade(project, "--check", env_extra={"COPILOT_MYSQL_ROOT_PASSWORD": "not-the-password"})
        check("a wrong root password is refused", wrong.returncode == 1 and "Can't log in to MySQL" in wrong.stderr)
        checked = upgrade(project, "--check")
        check("--check passes and shows the plan", checked.returncode == 0 and "8.0.46 -> 8.4.13" in checked.stdout, checked.stderr[-300:])
        check(
            "... and changes nothing",
            (project / "docker-compose.yml").read_bytes() == original
            and sql(project, "SELECT VERSION()") == "8.0.46"
            and not runs(project),
        )

        # The upgrade.
        done = upgrade(project, "--yes")
        check("the upgrade succeeds", done.returncode == 0, done.stderr[-500:])
        run_dir = runs(project)[-1]
        mysql = mysql_service(project)
        check(
            "docker-compose.yml runs mysql:8.4.13 with the flags",
            mysql["image"] == "mysql:8.4.13"
            and mysql["command"]
            == [
                "--restrict-fk-on-non-standard-key=OFF",
                "--mysql-native-password=ON",
            ],
        )
        edited = yaml.safe_load((project / "docker-compose.yml").read_text())
        expected = yaml.safe_load(original.decode())
        expected["services"]["copilot-mysql"].update(image="mysql:8.4.13", command=edited["services"]["copilot-mysql"]["command"])
        check("... and nothing else in it changed", edited == expected)
        check("the old file is kept in the run", (run_dir / "docker-compose.yml.before").read_bytes() == original)
        dump = sh(["sh", "-c", f"gzip -dc '{run_dir}/mysql-all-databases.sql.gz' | tail -n1"], cwd=project).stdout
        check("the dump is complete", dump.startswith("-- Dump completed"))
        check("the data archive is there", (run_dir / "mysql-data.tar.gz").stat().st_size > 1_000_000)
        check("the run is recorded as completed", state(run_dir).get("STATUS") == "completed")
        verify_upgraded(project, "after the upgrade", ["E2E-A", "E2E-B", "E2E-C"])
        insert_customer(project, "E2E-AFTER")

        # Again: nothing to do.
        edited_bytes = (project / "docker-compose.yml").read_bytes()
        again = upgrade(project, "--yes")
        check("running it again succeeds", again.returncode == 0, again.stderr[-500:])
        check(
            "... keeps MySQL 8.4.13 and docker-compose.yml",
            "stays on 8.4.13" in again.stdout and (project / "docker-compose.yml").read_bytes() == edited_bytes,
        )
        check("... and archives nothing", not (runs(project)[-1] / "mysql-data.tar.gz").exists())

        # Rollback (to the newest run with an archive: the first one, not the re-run).
        back = upgrade(project, "--rollback", "--yes")
        check("--rollback succeeds", back.returncode == 0, back.stderr[-500:])
        wait_mysql(project)
        check("MySQL is 8.0.46 again", sql(project, "SELECT VERSION()") == "8.0.46")
        check("docker-compose.yml is byte for byte as before", (project / "docker-compose.yml").read_bytes() == original)
        have = sql(
            project,
            "SELECT GROUP_CONCAT(customer_code ORDER BY customer_code) FROM copilot.customers WHERE customer_code LIKE 'E2E-%'",
        )
        check("the data is as before the upgrade (E2E-AFTER is gone)", have == "E2E-A,E2E-B,E2E-C", have)
        check("the backend starts on it", wait_backend(project))

        # docker-compose.yml already updated (git pull) while MySQL 8.0 still runs.
        updated = sh(
            ["bash", "-c", 'source "$1"; set +eu; compose_mysql_rewrite "$2" mysql:8.4.13 add', "x", str(SCRIPT), "docker-compose.yml"],
            cwd=project,
        ).stdout
        (project / "docker-compose.yml").write_text(updated)
        pulled = upgrade(project, "--yes")
        check("with the new docker-compose.yml already in place, the upgrade succeeds", pulled.returncode == 0, pulled.stderr[-500:])
        check(
            "... without editing it",
            (project / "docker-compose.yml").read_text() == updated and state(runs(project)[-1]).get("COMPOSE_PATCHED") == "0",
        )
        verify_upgraded(project, "after that upgrade", ["E2E-A", "E2E-B", "E2E-C"])
        back = upgrade(project, "--rollback", "--yes")
        check("its rollback succeeds", back.returncode == 0, back.stderr[-500:])
        wait_mysql(project)
        mysql = mysql_service(project)
        check("... and takes the image and flags back out", mysql["image"] == "mysql:8.0.46-debian" and "command" not in mysql)
        check("... MySQL 8.0.46 again", sql(project, "SELECT VERSION()") == "8.0.46")
    finally:
        teardown(project)


def scenario_b():
    project = new_project("b")
    try:
        build_stack(project, "b", "mysql:5.7.44")
        checked = upgrade(project, "--check")
        check(
            "5.7: --check plans two steps",
            checked.returncode == 0 and "5.7.44 -> 8.0.46 -> 8.4.13" in checked.stdout,
            checked.stderr[-300:],
        )
        done = upgrade(project, "--yes")
        check("5.7: the upgrade succeeds", done.returncode == 0, done.stderr[-500:])
        run_dir = runs(project)[-1]
        check("5.7: through 8.0.46", (run_dir / "mysql-8.0.46.log").exists() and state(run_dir).get("NEW_VERSION") == "8.4.13")
        verify_upgraded(project, "5.7", ["E2E-A", "E2E-B", "E2E-C"])
    finally:
        teardown(project)


def stop(signum, _frame):
    raise KeyboardInterrupt(f"signal {signum}")  # so each scenario's finally tears its stack down


def main() -> int:
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    wanted = sys.argv[1:] or ["a", "b"]
    for name in wanted:
        {"a": scenario_a, "b": scenario_b}[name]()
    failed = [name for name, passed in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    for name in failed:
        print(f"  FAILED: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
