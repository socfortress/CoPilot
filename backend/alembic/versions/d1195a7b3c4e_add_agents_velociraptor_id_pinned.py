"""add agents.velociraptor_id_pinned

Revision ID: d1195a7b3c4e
Revises: f1187c3d4e5f
Create Date: 2026-10-04 10:00:00.000000

A Velociraptor id entered by hand on an agent did not survive the next agent
sync when another customer had a client with the same hostname: the sync
matched by hostname and overwrote it with the other tenant's client (#1195).

`velociraptor_id_pinned` marks an id as set by an analyst. The sync then
resolves that agent by client id only. `PUT /agents/{agent_id}/update` sets it,
`PUT /agents/{agent_id}/velociraptor/unpin` clears it.

Every existing row starts unpinned (`server_default` 0): there is no record of
which stored ids were typed in by hand, so ids set before this revision are
treated as automatically matched until they are saved again.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1195a7b3c4e"
down_revision: Union[str, None] = "f1187c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("velociraptor_id_pinned", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("agents", "velociraptor_id_pinned")
