"""Merge Talon collect-start and customer-portal activity migration heads

Two migrations branched from f1282a0b1c2d and produced parallel heads:
- e4b2c0d1a7f3 (Talon v2 collection start gate, #1287)
- f1284a0b1c2d (customer portal activity settings, #1288)

This is an empty merge revision that joins them into a single head so
``alembic upgrade head`` has an unambiguous target again. It performs no schema
changes of its own.

Revision ID: f1289a0b1c2d
Revises: e4b2c0d1a7f3, f1284a0b1c2d
Create Date: 2026-10-20 21:40:00.000000

"""
from typing import Sequence
from typing import Union

# revision identifiers, used by Alembic.
revision: str = "f1289a0b1c2d"
down_revision: Union[str, Sequence[str], None] = ("e4b2c0d1a7f3", "f1284a0b1c2d")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
