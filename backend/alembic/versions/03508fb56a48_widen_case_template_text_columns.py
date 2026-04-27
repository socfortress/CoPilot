"""Widen case template text columns to TEXT

Revision ID: 03508fb56a48
Revises: 6ba5c2887ec5
Create Date: 2026-04-26 19:30:00.000000

The previous autogenerate (6ba5c2887ec5) materialized several free-form
text columns as VARCHAR(255) because SQLModel's ``sa_column=Text`` form
isn't picked up cleanly by alembic's type inference. This migration
widens them to TEXT so analysts can paste multi-paragraph guidelines
and log snippets / command output without truncation.

Affected columns:
- incident_management_case_template.description
- incident_management_case_template_task.description
- incident_management_case_template_task.guidelines
- incident_management_case_task.description
- incident_management_case_task.guidelines
- incident_management_case_task.evidence_comment

Non-destructive: the tables are introduced empty in 6ba5c2887ec5, so
no data is at risk.
"""

from typing import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "03508fb56a48"
down_revision: Union[str, None] = "6ba5c2887ec5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table_name, column_name, nullable) — every column should be widened to TEXT.
_WIDEN_COLUMNS = [
    ("incident_management_case_template", "description", True),
    ("incident_management_case_template_task", "description", True),
    ("incident_management_case_template_task", "guidelines", True),
    ("incident_management_case_task", "description", True),
    ("incident_management_case_task", "guidelines", True),
    ("incident_management_case_task", "evidence_comment", True),
]


def upgrade() -> None:
    for table, column, nullable in _WIDEN_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=nullable,
        )


def downgrade() -> None:
    # Reverses the widening. Will fail if any row contains a value longer
    # than 255 characters; that's intentional — losing data on downgrade
    # would be worse than refusing to run.
    for table, column, nullable in _WIDEN_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=nullable,
        )
