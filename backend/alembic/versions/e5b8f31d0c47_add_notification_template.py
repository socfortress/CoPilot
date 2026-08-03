"""add notification_template and route.template_id

Revision ID: e5b8f31d0c47
Revises: d1a7c4e2f905
Create Date: 2026-08-02 18:20:00.000000

#1037 made route.format_template real Jinja, but it stays per-route: every route
re-pastes its own copy, with no reuse and no way to offer per-language variants.
This adds the shared, named version.

See issue #1038.

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5b8f31d0c47"
down_revision: Union[str, None] = "d1a7c4e2f905"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_template",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        # NULL = usable with any trigger. Set = only offered for that one, so a
        # template written around {{assignee}} can't be attached to a trigger
        # where that variable is always empty.
        sa.Column("trigger", sa.String(length=64), nullable=True),
        # No server_default on this or `is_default`: the table is new, so there
        # are no existing rows to backfill, and the model carries Python-side
        # defaults. (The previous revision needed one only because it added a
        # NOT NULL column to a populated table.)
        sa.Column("format", sa.String(length=16), nullable=False),
        # First-class rather than smuggled into the body: email needs a subject
        # and Teams needs a card title, and neither is derivable from body text.
        sa.Column("subject_template", sa.Text(), nullable=True),
        sa.Column("body_template", sa.Text(), nullable=False),
        # NULL = shared with every customer, set = that tenant only. Same
        # convention as custom_dashboard_templates. varchar(64) against a
        # varchar(50) parent, matching the AiAnalyst* tables — MySQL only
        # requires compatible string types for an FK, not identical lengths.
        sa.Column("customer_code", sa.String(length=64), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"]),
    )
    op.create_index("ix_notification_template_trigger", "notification_template", ["trigger"])
    op.create_index("ix_notification_template_customer_code", "notification_template", ["customer_code"])
    op.create_index("ix_notification_template_created_at", "notification_template", ["created_at"])

    # Nullable FK with NO cascade, deliberately. Deleting a template must not
    # delete the routes using it — `delete_template` clears the reference and
    # reports how many routes were affected, so those routes fall back to their
    # inline template or the channel default rather than vanishing.
    op.add_column(
        "customer_notification_route",
        sa.Column("template_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_customer_notification_route_template_id", "customer_notification_route", ["template_id"])
    op.create_foreign_key(
        "fk_notification_route_template",
        "customer_notification_route",
        "notification_template",
        ["template_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drops the FK first, then the column, then the table — reverse dependency
    order, or MySQL refuses to drop a table another still references.

    Lossy only for templates themselves. Routes keep their inline
    `format_template` and channel defaults, so notifications continue after a
    downgrade; they simply stop using any shared template.
    """
    op.drop_constraint("fk_notification_route_template", "customer_notification_route", type_="foreignkey")
    op.drop_index("ix_customer_notification_route_template_id", table_name="customer_notification_route")
    op.drop_column("customer_notification_route", "template_id")

    op.drop_index("ix_notification_template_created_at", table_name="notification_template")
    op.drop_index("ix_notification_template_customer_code", table_name="notification_template")
    op.drop_index("ix_notification_template_trigger", table_name="notification_template")
    op.drop_table("notification_template")
