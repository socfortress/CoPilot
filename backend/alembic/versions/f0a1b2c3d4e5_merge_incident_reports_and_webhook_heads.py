"""Merge incident-reports and notification-webhook migration heads

Two migrations branched from 649e1a544188 and produced parallel heads:
- e1f2a3b4c5d6 (incident-management customer reports + visible_to_customer)
- a7b8c9d0e1f2 (add webhook channel to notification route)

This is an empty merge revision that joins them into a single head so
``alembic upgrade head`` has an unambiguous target again. It performs no schema
changes of its own.

Revision ID: f0a1b2c3d4e5
Revises: e1f2a3b4c5d6, a7b8c9d0e1f2
Create Date: 2026-07-21 10:00:00.000000

"""
from typing import Sequence
from typing import Union

# revision identifiers, used by Alembic.
revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = ("e1f2a3b4c5d6", "a7b8c9d0e1f2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
