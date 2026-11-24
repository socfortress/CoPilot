"""The cloud assessment tables (#1328): the models and migration c1328a0b1c2d must describe the same tables.

No database: the migration's ``upgrade()`` runs against a recorder standing in for Alembic's
``op``, and what it would create is compared with the SQLModel tables. Alembic's autogenerate
reads the models, so a drift here would surface later as a surprise migration.
``tests/e2e/cloud_assessment_migration_e2e.py`` runs the real thing on MySQL.
"""
import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa

from app.cloud_assessment.models.cloud_assessment import CloudAssessmentAccount
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentCheckResult
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentFinding
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentScan

BACKEND = Path(__file__).resolve().parents[1]
MIGRATION = BACKEND / "alembic" / "versions" / "c1328a0b1c2d_add_cloud_assessment_tables.py"
MODELS = {model.__tablename__: model.__table__ for model in (CloudAssessmentAccount, CloudAssessmentScan, CloudAssessmentCheckResult, CloudAssessmentFinding)}


class RecordingOp:
    def __init__(self):
        self.tables = {}
        self.indexes = {}
        self.dropped = []

    def create_table(self, name, *elements):
        self.tables[name] = elements

    def create_index(self, name, table, columns, unique=False):
        self.indexes[name] = (table, tuple(columns), unique)

    def drop_table(self, name):
        self.dropped.append(name)


@pytest.fixture(scope="module")
def migration():
    spec = importlib.util.spec_from_file_location("migration_c1328a0b1c2d", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def recorded(migration):
    op = RecordingOp()
    migration.op = op
    migration.upgrade()
    migration.downgrade()
    return op


def kind(column_type) -> tuple:
    """A column type as the database sees it: its SQL family and, for strings, its length."""
    if isinstance(column_type, sa.types.TypeDecorator):  # SQLModel's AutoString
        column_type = column_type.impl
    for family in (sa.BigInteger, sa.SmallInteger, sa.Integer, sa.Boolean, sa.DateTime, sa.JSON, sa.Text, sa.String):
        if isinstance(column_type, family):
            return (family.__name__, getattr(column_type, "length", None) if family is sa.String else None)
    raise AssertionError(f"unexpected type {column_type!r}")


def default(column) -> str | None:
    return None if column.server_default is None else str(column.server_default.arg)


def test_the_migration_chains_off_the_head_it_was_written_on(migration):
    assert migration.revision == "c1328a0b1c2d"
    assert migration.down_revision == "38c2e85a670a"


def test_it_creates_the_four_tables_and_drops_them_children_first(recorded):
    assert list(recorded.tables) == ["cloud_assessment_account", "cloud_assessment_scan", "cloud_assessment_check_result", "cloud_assessment_finding"]
    assert recorded.dropped == list(reversed(list(recorded.tables)))


@pytest.mark.parametrize("table", list(MODELS))
def test_columns_match_the_model(recorded, table):
    migrated = {element.name: element for element in recorded.tables[table] if isinstance(element, sa.Column)}
    model = {column.name: column for column in MODELS[table].columns}
    assert list(migrated) == list(model), "the same columns, in the same order"
    for name, column in model.items():
        assert kind(migrated[name].type) == kind(column.type), name
        assert migrated[name].nullable == column.nullable, name
        assert default(migrated[name]) == default(column), name
    primary_key = [element for element in recorded.tables[table] if isinstance(element, sa.PrimaryKeyConstraint)]
    assert [list(constraint._pending_colargs) for constraint in primary_key] == [[column.name for column in MODELS[table].primary_key]]


@pytest.mark.parametrize("table", list(MODELS))
def test_keys_and_indexes_match_the_model(recorded, table):
    elements = recorded.tables[table]
    migrated_fks = {
        (tuple(element.column_keys), next(iter(element.elements)).target_fullname, element.ondelete)
        for element in elements
        if isinstance(element, sa.ForeignKeyConstraint)
    }
    model_fks = {((fk.parent.name,), fk.target_fullname, fk.ondelete) for fk in MODELS[table].foreign_keys}
    assert migrated_fks == model_fks

    migrated_uniques = {(element.name, tuple(element._pending_colargs)) for element in elements if isinstance(element, sa.UniqueConstraint)}
    model_uniques = {
        (constraint.name, tuple(column.name for column in constraint.columns))
        for constraint in MODELS[table].constraints
        if isinstance(constraint, sa.UniqueConstraint)
    }
    assert migrated_uniques == model_uniques

    migrated_indexes = {name: (columns, unique) for name, (owner, columns, unique) in recorded.indexes.items() if owner == table}
    model_indexes = {index.name: (tuple(column.name for column in index.columns), bool(index.unique)) for index in MODELS[table].indexes}
    assert migrated_indexes == model_indexes


def test_every_table_belongs_to_a_customer_and_goes_with_it():
    assert {(fk.target_fullname, fk.ondelete) for fk in MODELS["cloud_assessment_account"].foreign_keys} == {("customers.customer_code", "CASCADE")}
    assert {(fk.target_fullname, fk.ondelete) for fk in MODELS["cloud_assessment_scan"].foreign_keys} == {("cloud_assessment_account.id", "CASCADE")}
    for table in ("cloud_assessment_check_result", "cloud_assessment_finding"):
        assert {(fk.target_fullname, fk.ondelete) for fk in MODELS[table].foreign_keys} == {("cloud_assessment_scan.id", "CASCADE")}


def test_alembic_sees_the_models():
    # A model in a new file is invisible to autogenerate unless env.py imports it.
    source = (BACKEND / "alembic" / "env.py").read_text()
    for model in ("CloudAssessmentAccount", "CloudAssessmentScan", "CloudAssessmentCheckResult", "CloudAssessmentFinding"):
        assert f"from app.cloud_assessment.models.cloud_assessment import {model}" in source


def test_no_column_is_named_after_a_mysql_reserved_word():
    reserved = {"check", "trigger", "references", "key", "keys", "index", "order", "group", "range", "condition", "usage", "database"}
    for table in MODELS.values():
        assert not reserved & {column.name for column in table.columns}, table.name
