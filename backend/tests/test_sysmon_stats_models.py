"""The Sysmon noise statistics' two tables: the models and migration d7a4c2e91b3f agree, the customer FK cascades, and
the migration hangs off the previous head (tests/test_alembic_single_head.py keeps the head single).

Run with: cd backend && python -m pytest tests/test_sysmon_stats_models.py
"""
import importlib.util
import os
from pathlib import Path

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import sqlalchemy as sa  # noqa: E402

from app.db.universal_models import SysmonStatsCustomerSettings  # noqa: E402
from app.db.universal_models import SysmonStatsIdentity  # noqa: E402

MIGRATION = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "d7a4c2e91b3f_add_sysmon_stats_tables.py"


def _migration_tables():
    spec = importlib.util.spec_from_file_location("_m", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    created = {}

    class Op:
        def create_table(self, name, *columns):
            created[name] = [c for c in columns if isinstance(c, sa.Column)], [c for c in columns if isinstance(c, sa.ForeignKeyConstraint)]

        def create_index(self, name, table, cols, unique=False):
            created.setdefault("_indexes", []).append((table, tuple(cols), unique))

    module.op = Op()
    module.upgrade()
    return module, created


def test_the_migration_matches_the_models():
    module, created = _migration_tables()
    assert module.down_revision == "c1328a0b1c2d"
    for model in (SysmonStatsCustomerSettings, SysmonStatsIdentity):
        table = model.__table__
        columns, _ = created[table.name]
        assert {c.name for c in columns} == {c.name for c in table.columns}, table.name
        for column in columns:
            assert column.nullable == table.columns[column.name].nullable or column.primary_key, (table.name, column.name)
    _, fks = created["sysmon_stats_customer_settings"]
    (fk,) = fks
    assert fk.ondelete == "CASCADE" and [e.target_fullname for e in fk.elements] == ["customers.customer_code"]
    assert ("sysmon_stats_customer_settings", ("customer_code",), True) in created["_indexes"]
    (model_fk,) = SysmonStatsCustomerSettings.__table__.foreign_keys
    assert model_fk.ondelete == "CASCADE"
    assert "Dropping the table loses" in MIGRATION.read_text() or "every opt-out" in MIGRATION.read_text()
