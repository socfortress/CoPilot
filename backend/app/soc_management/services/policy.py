"""Reading and writing the SLA policy.

The policy table is tiny (at most 10 cells per scope), so every read loads the rows a
question needs and resolution happens in ``domain/policy.py``. There is deliberately no
cache: a policy save must take effect for the very next alert ingested, and one indexed
read per opened item is not where ingest spends its time.
"""

from __future__ import annotations

from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence

from sqlalchemy import delete
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.soc_management.clock import utc_now
from app.soc_management.domain.policy import PolicyRow
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.domain.policy import SlaTargets
from app.soc_management.domain.policy import effective_matrix
from app.soc_management.domain.policy import resolve_targets
from app.soc_management.models.sla import SlaPolicy
from app.soc_management.schema.policy import PolicyCell
from app.soc_management.schema.policy import PolicyCellIn
from app.soc_management.schema.policy import PolicyMatrix
from app.soc_management.schema.policy import PolicyOverride


def _to_row(policy: SlaPolicy) -> PolicyRow:
    return PolicyRow(
        customer_code=policy.customer_code,
        entity=SlaEntity(policy.entity_type),
        severity=policy.severity,
        ack_minutes=policy.ack_minutes,
        resolve_minutes=policy.resolve_minutes,
    )


async def load_rows(session: AsyncSession, customer_codes: Optional[Iterable[str]] = None) -> List[PolicyRow]:
    """The global rows plus the overrides of ``customer_codes`` (every override when ``None``)."""
    query = select(SlaPolicy)
    if customer_codes is not None:
        codes = [code for code in customer_codes if code]
        scope = SlaPolicy.customer_code.is_(None)
        if codes:
            scope = or_(scope, SlaPolicy.customer_code.in_(codes))
        query = query.where(scope)
    result = await session.execute(query)
    return [_to_row(policy) for policy in result.scalars().all()]


async def targets_for(session: AsyncSession, entity: SlaEntity, severity: str, customer_code: Optional[str]) -> SlaTargets:
    rows = await load_rows(session, [customer_code] if customer_code else [])
    return resolve_targets(entity, severity, customer_code, rows)


def _matrix(customer_code: Optional[str], rows: Sequence[PolicyRow]) -> PolicyMatrix:
    resolved = effective_matrix(customer_code, rows)
    cells = [
        PolicyCell(
            entity=entity,
            severity=severity,
            ack_minutes=targets.ack_minutes,
            resolve_minutes=targets.resolve_minutes,
            source=targets.source,
        )
        for entity, by_severity in resolved.items()
        for severity, targets in by_severity.items()
    ]
    return PolicyMatrix(customer_code=customer_code, cells=cells)


async def get_matrix(session: AsyncSession, customer_code: Optional[str]) -> PolicyMatrix:
    """Every cell of a scope as it resolves, each labelled with where its value comes from."""
    rows = await load_rows(session, [customer_code] if customer_code else [])
    return _matrix(customer_code, rows)


async def replace_scope(
    session: AsyncSession,
    customer_code: Optional[str],
    cells: Sequence[PolicyCellIn],
    actor: Optional[str],
) -> PolicyMatrix:
    """Make a scope's stored cells exactly ``cells`` (an inheriting cell stores nothing).

    Replace rather than upsert: the editor always submits the whole matrix of a scope, so
    "what is stored" equals "what was saved" by construction — no stale cell left from an
    earlier edit, and no reliance on a unique index MySQL does not enforce for NULL scope.
    Does not commit: the route commits once the re-target (if asked) is done too.
    """
    await session.execute(delete(SlaPolicy).where(_scope_clause(customer_code)))
    now = utc_now()
    for cell in cells:
        if cell.inherit:
            continue
        session.add(
            SlaPolicy(
                customer_code=customer_code,
                entity_type=cell.entity.value,
                severity=cell.severity,
                ack_minutes=cell.ack_minutes,
                resolve_minutes=cell.resolve_minutes,
                updated_at=now,
                updated_by=actor,
            ),
        )
    await session.flush()
    return await get_matrix(session, customer_code)


async def clear_scope(session: AsyncSession, customer_code: str) -> int:
    """Remove a customer's overrides; the customer falls back to the global policy."""
    result = await session.execute(delete(SlaPolicy).where(SlaPolicy.customer_code == customer_code))
    return result.rowcount or 0


async def list_overrides(session: AsyncSession, customer_codes: Optional[Sequence[str]] = None) -> List[PolicyOverride]:
    """Customers with at least one overridden cell, for the scope picker's markers."""
    query = select(SlaPolicy.customer_code, SlaPolicy.updated_at, SlaPolicy.updated_by).where(SlaPolicy.customer_code.is_not(None))
    if customer_codes is not None:
        if not customer_codes:
            return []
        query = query.where(SlaPolicy.customer_code.in_(list(customer_codes)))
    result = await session.execute(query)
    by_code: dict = {}
    for code, updated_at, updated_by in result.all():
        current = by_code.get(code)
        if current is None:
            by_code[code] = PolicyOverride(customer_code=code, cells=1, updated_at=updated_at, updated_by=updated_by)
            continue
        current.cells += 1
        if updated_at and (current.updated_at is None or updated_at > current.updated_at):
            current.updated_at, current.updated_by = updated_at, updated_by
    return sorted(by_code.values(), key=lambda override: override.customer_code)


def _scope_clause(customer_code: Optional[str]):
    return SlaPolicy.customer_code.is_(None) if customer_code is None else SlaPolicy.customer_code == customer_code
