"""add instance_name to customer integrations and their metadata

Revision ID: 4c460eb540ee
Revises: 76f5e57eb47a
Create Date: 2026-09-15 15:41:02.118374

A customer may hold several Microsoft 365 tenants — an MSSP customer with
subsidiaries, acquisitions or a legacy environment (see issue #1117). Until now
`customer_integrations` allowed one row per `(customer_code,
integration_service_name)`, so the only way to monitor a second tenant was to
create a second CoPilot customer, which fragments that customer's incidents,
assets and reporting.

`instance_name` is what tells a customer's configurations of the same
integration apart. Each instance carries its own credentials and is provisioned
into its own Graylog index set and stream and its own Grafana datasource, folder
and dashboards, which is why the metadata table needs the column too — one row
per provisioned instance rather than one per customer and integration.

Nullable with no default, deliberately:

- NULL is "the customer's single, unnamed instance". Every existing row becomes
  that, and both `(customer_code, integration_name, NULL)` and the resources it
  already owns keep meaning exactly what they did before — no backfill, no
  renaming of a live Graylog index prefix, no re-provisioning.
- Application code compares the column with `IS NULL` rather than `= NULL`
  (`instance_name_matches` in `app/integrations/routes.py`), so the unnamed
  instance stays selectable.

No unique constraint is added. Uniqueness over
`(customer_code, integration_name, instance_name)` has always been enforced in
the route layer (`check_existing_customer_integration`), and only integrations
listed in `MULTI_INSTANCE_INTEGRATIONS` are allowed more than one row at all; a
database constraint would additionally have to encode that allowlist, and MySQL
treats NULLs as distinct in a unique index anyway, so it would not prevent the
one case the route layer cares most about — two unnamed instances.

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c460eb540ee"
down_revision: Union[str, None] = "76f5e57eb47a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_integrations",
        sa.Column("instance_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "customer_integrations_meta",
        sa.Column("instance_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Collapse every customer back to one configuration per integration.

    A customer who has been given a second Microsoft 365 tenant keeps both rows
    after this runs, and they become indistinguishable to every lookup — the
    state this revision exists to avoid. Delete the extra instances through the
    UI before downgrading, or the surviving row is whichever one a given query
    happens to return first.

    The Graylog and Grafana resources those instances own are not touched here;
    removing them is the delete-integration path's job, not a migration's.
    """
    op.drop_column("customer_integrations_meta", "instance_name")
    op.drop_column("customer_integrations", "instance_name")
