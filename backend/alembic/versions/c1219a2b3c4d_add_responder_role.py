"""Add the responder role (#1219)

Revision ID: c1219a2b3c4d
Revises: c1215a7b8d9e
Create Date: 2026-10-10 00:00:00.000000

A responder is an analyst who may also run response actions on their assigned
customers. Roles used to be inserted at startup by name, taking whatever id the
insertion order gave them; this seeds every missing role with its RoleEnum id, so on a
fresh database the responder's id 5 cannot push admin off id 1. An existing deployment
only gains the responder row. No data changes otherwise.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1219a2b3c4d"
down_revision: Union[str, None] = "c1215a7b8d9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLES = [
    (1, "admin", "Administrator"),
    (2, "analyst", "SOC Analyst"),
    (3, "scheduler", "Scheduler for automated tasks"),
    (4, "customer_user", "Customer user with limited access to their own data"),
    (5, "responder", "SOC Analyst who may also run response actions on their assigned customers"),
]


def upgrade() -> None:
    bind = op.get_bind()
    taken_names = {row[0] for row in bind.execute(sa.text("SELECT name FROM role"))}
    taken_ids = {row[0] for row in bind.execute(sa.text("SELECT id FROM role"))}
    for role_id, name, description in ROLES:
        if name in taken_names:
            continue
        if role_id in taken_ids:
            raise RuntimeError(f"Cannot add role '{name}': id {role_id} is already used by another role")
        bind.execute(
            sa.text("INSERT INTO role (id, name, description) VALUES (:id, :name, :description)"),
            {"id": role_id, "name": name, "description": description},
        )


def downgrade() -> None:
    bind = op.get_bind()
    in_use = bind.execute(sa.text("SELECT COUNT(*) FROM `user` WHERE role_id = 5")).scalar()
    if in_use:
        raise RuntimeError(f"Cannot remove the responder role: {in_use} user(s) still have it")
    bind.execute(sa.text("DELETE FROM role_tag_access WHERE role_id = 5"))
    bind.execute(sa.text("DELETE FROM role WHERE id = 5 AND name = 'responder'"))
