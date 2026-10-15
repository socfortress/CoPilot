"""widen ai_analyst_palace_lesson.drawer_id to 255

Revision ID: a5b1c0d2e3f5
Revises: a5b1c0d2e3f4
Create Date: 2026-10-15 12:05:00.000000

MemPalace drawer ids are `drawer_<wing>_<room>_<24 hex>`, and the wing is the customer code,
so a long customer code gave an id over the column's 64 characters and the lesson drainer
could not store it. 255 holds any customer code (`customers.customer_code` is 50).

Widening keeps every value. The downgrade refuses while a stored id is longer than 64, since
narrowing would cut it and the sweeper could then never forget that drawer.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5b1c0d2e3f5"
down_revision: Union[str, None] = "a5b1c0d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LESSONS = "ai_analyst_palace_lesson"


def upgrade() -> None:
    op.alter_column(LESSONS, "drawer_id", existing_type=sa.String(length=64), type_=sa.String(length=255), existing_nullable=True)


def downgrade() -> None:
    too_long = op.get_bind().execute(sa.text(f"SELECT COUNT(*) FROM {LESSONS} WHERE CHAR_LENGTH(drawer_id) > 64")).scalar()
    if too_long:
        raise RuntimeError(f"Cannot narrow {LESSONS}.drawer_id to 64: {too_long} stored drawer id(s) are longer")
    op.alter_column(LESSONS, "drawer_id", existing_type=sa.String(length=255), type_=sa.String(length=64), existing_nullable=True)
