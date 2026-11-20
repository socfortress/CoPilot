"""Unique ``customers.customer_code`` (migration 38c2e85a670a).

44 foreign keys point at ``customers.customer_code``. With its index unique, MySQL 8.4 treats every
one of them as a standard key, whatever ``restrict_fk_on_non_standard_key`` says. The model declares
the same unique index the migration builds, so autogenerate sees no difference.
``agents.agent_id`` deliberately stays non-unique: a Wazuh agent id is unique per manager only.
``tests/e2e/unique_tenant_keys_e2e.py`` runs the migration against real MySQL 8.0 and 8.4.

Run with: cd backend && python -m pytest tests/test_unique_tenant_keys.py
"""

import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.db.universal_models import Agents
from app.db.universal_models import Customers

MIGRATION_PATH = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "38c2e85a670a_unique_customer_code.py"
ALTER = "ALTER TABLE `customers` DROP INDEX `ix_customers_customer_code`, ADD {kind} `ix_customers_customer_code` (`customer_code`)"


def load_migration():
    spec = importlib.util.spec_from_file_location("migration_38c2e85a670a", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeOp:
    """Stands in for ``alembic.op``: records every statement instead of running it."""

    def __init__(self, dialect="mysql"):
        self.dialect = dialect
        self.statements = []

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name=self.dialect))

    def execute(self, sql):
        self.statements.append(sql)


@pytest.fixture
def migration(monkeypatch):
    module = load_migration()
    fake = FakeOp()
    state = SimpleNamespace(shape=[(1, "customer_code")], duplicates=[])
    monkeypatch.setattr(module, "op", fake)
    monkeypatch.setattr(module, "index_shape", lambda: state.shape)
    monkeypatch.setattr(module, "duplicate_values", lambda: state.duplicates)
    return SimpleNamespace(module=module, op=fake, state=state)


def _index(model, name):
    return {index.name: index for index in model.__table__.indexes}.get(name)


def test_the_model_declares_the_index_the_migration_builds():
    index = _index(Customers, "ix_customers_customer_code")
    assert index is not None and index.unique
    assert [column.name for column in index.columns] == ["customer_code"]


def test_agent_ids_stay_non_unique():
    # A Wazuh agent id is unique per manager only: two customers' agents may share one.
    index = _index(Agents, "ix_agents_agent_id")
    assert index is not None and not index.unique


def test_makes_the_index_unique(migration):
    migration.module.upgrade()

    assert migration.op.statements == [ALTER.format(kind="UNIQUE INDEX")]


def test_an_index_already_unique_is_left_alone(migration):
    migration.state.shape = [(0, "customer_code")]

    migration.module.upgrade()

    assert migration.op.statements == []


def test_duplicates_leave_it_non_unique_and_the_warning_says_how_to_fix_it(migration, caplog):
    migration.state.duplicates = ["ACME", "Globex"]

    with caplog.at_level(logging.WARNING, logger="alembic.runtime.migration"):
        migration.module.upgrade()

    assert migration.op.statements == []
    warning = caplog.records[-1].getMessage()
    assert "customers.customer_code holds duplicate values ('ACME', 'Globex')" in warning
    assert warning.endswith(
        "run: ALTER TABLE customers DROP INDEX ix_customers_customer_code, ADD UNIQUE INDEX ix_customers_customer_code (customer_code)",
    )


@pytest.mark.parametrize("shape", [[], [(1, "customer_code"), (1, "customer_name")]])
def test_a_missing_or_wider_index_is_left_alone_with_a_warning(migration, caplog, shape):
    migration.state.shape = shape

    with caplog.at_level(logging.WARNING, logger="alembic.runtime.migration"):
        migration.module.upgrade()

    assert migration.op.statements == []
    assert "left as it is" in caplog.records[-1].getMessage()


def test_does_nothing_on_another_database(migration):
    migration.op.dialect = "sqlite"

    migration.module.upgrade()
    migration.module.downgrade()

    assert migration.op.statements == []


def test_downgrade_puts_the_non_unique_index_back(migration):
    migration.state.shape = [(0, "customer_code")]

    migration.module.downgrade()

    assert migration.op.statements == [ALTER.format(kind="INDEX")]


def test_downgrade_leaves_an_index_the_upgrade_skipped(migration):
    migration.module.downgrade()

    assert migration.op.statements == []
