"""Which Graylog objects UBA setup made for a customer (``uba_provisioned_resource``, #1241).

Setup records every object it creates or finds by title; rollback reads the records to
know what the customer owns and marks what it removed. A rollback of a customer set up
before the table existed records its objects as ``adopted`` when it removes them.
"""

from dataclasses import dataclass
from typing import Iterable
from typing import List
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.universal_models import UbaProvisionedResource
from app.time_utils import now_utc

FEED_STREAM = "feed_stream"
ROUTING_RULE = "routing_rule"
ROUTING_PIPELINE = "routing_pipeline"
OUTPUT = "output"
ALERTS_STREAM = "alerts_stream"
ALERTS_INPUT = "alerts_input"
WAZUH_RULES = "wazuh_rules"


@dataclass
class Owned:
    kind: str
    graylog_id: str
    title: str
    source: Optional[str] = None
    shared: bool = False
    origin: str = "created"  # created | found | adopted


async def record(session: AsyncSession, customer_code: str, items: Iterable[Owned]) -> None:
    """Insert or refresh the customer's records (no commit). A row is keyed by its Graylog id: a
    title changed since setup keeps pointing at the same object."""
    items = list(items)
    if not items:
        return
    rows = await session.execute(select(UbaProvisionedResource).where(UbaProvisionedResource.customer_code == customer_code))
    existing = {(r.kind, r.graylog_id): r for r in rows.scalars().all()}
    now = now_utc()
    for item in items:
        row = existing.get((item.kind, item.graylog_id))
        if row is None:
            row = UbaProvisionedResource(
                customer_code=customer_code,
                kind=item.kind,
                graylog_id=item.graylog_id,
                title=item.title,
                source=item.source,
                shared=item.shared,
                origin=item.origin,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            existing[(item.kind, item.graylog_id)] = row
        else:
            row.title, row.source, row.shared, row.updated_at = item.title, item.source, item.shared, now
            row.removed_at = row.removed_by_rollback_id = None


async def active(session: AsyncSession, customer_code: Optional[str] = None) -> List[UbaProvisionedResource]:
    """Records not removed yet: one customer's, or every customer's."""
    query = select(UbaProvisionedResource).where(UbaProvisionedResource.removed_at.is_(None))
    if customer_code is not None:
        query = query.where(UbaProvisionedResource.customer_code == customer_code)
    return list((await session.execute(query)).scalars().all())


async def mark_removed(session: AsyncSession, customer_code: str, items: Iterable[Owned], rollback_id: int) -> None:
    """Mark removed objects, recording (``adopted``) those setup never recorded (no commit)."""
    items = list(items)
    await record(session, customer_code, [i for i in items if i.origin == "adopted"])
    keys = {(i.kind, i.graylog_id) for i in items}
    rows = await session.execute(select(UbaProvisionedResource).where(UbaProvisionedResource.customer_code == customer_code))
    now = now_utc()
    for row in rows.scalars().all():
        if (row.kind, row.graylog_id) in keys:
            row.removed_at, row.removed_by_rollback_id = now, rollback_id
