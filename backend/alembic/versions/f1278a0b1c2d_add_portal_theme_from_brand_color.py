"""add theme_from_brand_color to the customer portal branding

Revision ID: f1278a0b1c2d
Revises: d5b11a2b3c4d
Create Date: 2026-10-19 15:00:00.000000

Whether the Customer Portal's interface takes the brand color as its primary color
(#1278), chosen in CoPilot. `customer_portal_settings.theme_from_brand_color` is the
global choice (not null, false: nothing changes until an operator opts in);
`customer_portal_branding.theme_from_brand_color` is a customer's override (null
inherits the global choice). The downgrade drops both columns.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1278a0b1c2d"
down_revision: Union[str, None] = "d5b11a2b3c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_portal_settings",
        sa.Column("theme_from_brand_color", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("customer_portal_branding", sa.Column("theme_from_brand_color", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("customer_portal_branding", "theme_from_brand_color")
    op.drop_column("customer_portal_settings", "theme_from_brand_color")
