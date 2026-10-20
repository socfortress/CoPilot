"""The migration scripts must have exactly one head.

The backend runs ``alembic upgrade head`` at startup (``app.db.db_setup.apply_migrations``),
which refuses to run when two migrations branch from the same parent, so the backend
never starts. Two PRs that each add a migration on the same parent pass their own tests;
this test fails on the second one's merge instead of at deploy time.
"""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[1]


def test_migrations_have_a_single_head() -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    assert len(heads) == 1, f"multiple alembic heads, add a merge revision: {sorted(heads)}"
