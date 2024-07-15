"""Add alert tags

Revision ID: ba98bd0e3967
Revises: 1501739c6898
Create Date: 2024-07-15 11:31:37.990149

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ba98bd0e3967"
down_revision: Union[str, None] = "1501739c6898"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "incident_management_alerttag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "incident_management_alert_to_tag",
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["incident_management_alert.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["incident_management_alerttag.id"],
        ),
        sa.PrimaryKeyConstraint("alert_id", "tag_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("incident_management_alert_to_tag")
    op.drop_table("incident_management_alerttag")
    # ### end Alembic commands ###
