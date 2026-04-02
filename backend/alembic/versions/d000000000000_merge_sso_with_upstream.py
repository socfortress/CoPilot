"""merge SSO/TOTP migrations with upstream head

Revision ID: d000000000000
Revises: c3d4e5f6a7b8, 895843b96397
Create Date: 2026-03-25 00:00:00.000000

"""
from typing import Union

# revision identifiers, used by Alembic.
revision: str = "d000000000000"
down_revision: Union[str, None] = ("c3d4e5f6a7b8", "895843b96397")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
