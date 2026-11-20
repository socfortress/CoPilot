"""MySQL 8.4: what the compose stack and the migrations need to keep CoPilot's schema working.

CoPilot's foreign keys to ``customers.customer_code`` and ``agents.agent_id`` point at
non-unique indexes. MySQL 8.4 refuses new ones, and ALTERs on those two tables, unless
``restrict_fk_on_non_standard_key`` is off: the compose stack starts MySQL with it off, and
every connection Alembic opens switches it off for its session (``app/db/mysql_compat.py``),
so an external MySQL 8.4 works too. ``tests/e2e/mysql_84_upgrade_e2e.py`` runs it all against
real servers.

Run with: cd backend && python -m pytest tests/test_mysql_84_compat.py
"""

import ast
import re
from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy import event

from app.db import mysql_compat
from app.db.mysql_compat import FK_RESTRICTION
from app.db.mysql_compat import install_fk_relaxation
from app.db.mysql_compat import relax_fk_restriction

BACKEND = Path(__file__).resolve().parents[1]
COMPOSE = BACKEND.parent / "docker-compose.yml"
ENV_PY = BACKEND / "alembic" / "env.py"


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql):
        self.connection.executed.append(sql)
        if self.connection.fail_on and self.connection.fail_on in sql:
            raise RuntimeError("simulated failure")

    def fetchone(self):
        return self.connection.row

    def close(self):
        self.connection.closed_cursors += 1


class FakeConnection:
    """A DBAPI connection answering SHOW SESSION VARIABLES with ``row``."""

    def __init__(self, row, fail_on=None):
        self.row = row
        self.fail_on = fail_on
        self.executed = []
        self.closed_cursors = 0

    def cursor(self):
        return FakeCursor(self)


def _compose_mysql():
    services = yaml.safe_load(COMPOSE.read_text())["services"]
    return services["copilot-mysql"]


def test_compose_runs_mysql_84_lts():
    assert re.fullmatch(r"mysql:8\.4\.\d+", _compose_mysql()["image"]), _compose_mysql()["image"]


def test_compose_allows_foreign_keys_to_non_unique_keys():
    assert "--restrict-fk-on-non-standard-key=OFF" in _compose_mysql()["command"]


def test_compose_keeps_users_from_the_old_mysql_57_image_working():
    assert "--mysql-native-password=ON" in _compose_mysql()["command"]


def test_relaxes_the_restriction_on_mysql_84():
    connection = FakeConnection((FK_RESTRICTION, "ON"))

    assert relax_fk_restriction(connection) is True
    assert connection.executed == [
        f"SHOW SESSION VARIABLES LIKE '{FK_RESTRICTION}'",
        f"SET SESSION {FK_RESTRICTION} = OFF",
    ]
    assert connection.closed_cursors == 1


def test_does_nothing_on_a_server_without_the_variable():
    # MySQL 8.0 and MariaDB: SHOW ... LIKE answers no row, and no SET is sent.
    connection = FakeConnection(None)

    assert relax_fk_restriction(connection) is False
    assert connection.executed == [f"SHOW SESSION VARIABLES LIKE '{FK_RESTRICTION}'"]
    assert connection.closed_cursors == 1


def test_does_nothing_when_the_server_already_allows_them():
    connection = FakeConnection((FK_RESTRICTION, "OFF"))

    assert relax_fk_restriction(connection) is False
    assert len(connection.executed) == 1


def test_closes_the_cursor_when_the_server_refuses():
    connection = FakeConnection((FK_RESTRICTION, "ON"), fail_on="SET SESSION")

    with pytest.raises(RuntimeError):
        relax_fk_restriction(connection)
    assert connection.closed_cursors == 1


def test_a_failure_never_stops_the_migrations():
    # The hook logs and returns: migrations then run exactly as they would without it.
    connection = FakeConnection(None, fail_on="SHOW SESSION")

    mysql_compat._relax_on_connect(connection, None)

    assert connection.executed == [f"SHOW SESSION VARIABLES LIKE '{FK_RESTRICTION}'"]


def test_installs_on_a_mysql_engine_only():
    mysql_engine = create_engine("mysql+pymysql://user:pass@127.0.0.1:1/copilot")
    sqlite_engine = create_engine("sqlite://")
    try:
        install_fk_relaxation(mysql_engine)
        install_fk_relaxation(mysql_engine)  # a second call is a no-op
        install_fk_relaxation(sqlite_engine)

        assert event.contains(mysql_engine, "connect", mysql_compat._relax_on_connect)
        assert not event.contains(sqlite_engine, "connect", mysql_compat._relax_on_connect)
    finally:
        mysql_engine.dispose()
        sqlite_engine.dispose()


def test_alembic_relaxes_the_restriction_before_it_connects():
    tree = ast.parse(ENV_PY.read_text())
    online = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_migrations_online")
    installs = [
        node.lineno
        for node in ast.walk(online)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", None) == "install_fk_relaxation"
        and [getattr(arg, "id", None) for arg in node.args] == ["connectable"]
    ]
    connects = [node.lineno for node in ast.walk(online) if isinstance(node, ast.With)]

    assert installs, "run_migrations_online must call install_fk_relaxation(connectable)"
    assert connects and min(installs) < min(connects), "install it before the first connection is opened"
