"""SLA targets: what each severity of alert and case is promised, and how that resolves.

A target has two clocks, both measured from the moment the item reached CoPilot:

- **acknowledge** — the first response by the SOC (see ``lifecycle.RESPONSE_ACTIONS``);
- **resolve**     — the item being closed.

Either may be ``None``, meaning "no promise for this severity": the item is then
``NOT_TRACKED`` on that clock and excluded from compliance rather than counted as met.

Resolution is per cell (entity × severity), most specific first:

    customer override  →  global policy  →  built-in default

A row is a whole cell: a customer override for *High alerts* replaces both clocks of
that cell — and whether they count business hours — never one of them. Keeping the unit of override equal to the unit the UI
edits is what makes "which number applies here?" answerable at a glance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict
from typing import Iterable
from typing import Mapping
from typing import Optional

from app.incidents.services.alert_severity import SEVERITY_LEVELS
from app.soc_management.domain.calendar import CONTINUOUS
from app.soc_management.domain.calendar import ClockBasis


class SlaEntity(str, Enum):
    ALERT = "alert"
    CASE = "case"


class TargetSource(str, Enum):
    """Where a cell's targets came from — shown next to every number in the policy editor."""

    CUSTOMER = "customer"
    GLOBAL = "global"
    DEFAULT = "default"


#: Severities most-severe first: the order every table in the dashboard uses.
SEVERITIES_DESC = tuple(reversed(SEVERITY_LEVELS))

#: Upper bound for a single target. A year is already absurd for an SLA; anything above
#: it is a typo (minutes entered as seconds) rather than a policy.
MAX_TARGET_MINUTES = 365 * 24 * 60


@dataclass(frozen=True)
class SlaTargets:
    ack_minutes: Optional[int]
    resolve_minutes: Optional[int]
    source: TargetSource = TargetSource.DEFAULT
    #: The targets count business hours of the customer's calendar, not wall-clock time.
    business_hours: bool = False

    def ack_due(self, opened_at: datetime, clock: ClockBasis = CONTINUOUS) -> Optional[datetime]:
        return _due(opened_at, self.ack_minutes, clock)

    def resolve_due(self, opened_at: datetime, clock: ClockBasis = CONTINUOUS) -> Optional[datetime]:
        return _due(opened_at, self.resolve_minutes, clock)


def _due(opened_at: datetime, minutes: Optional[int], clock: ClockBasis) -> Optional[datetime]:
    return clock.add(opened_at, minutes * 60) if minutes is not None else None


def _targets(ack_minutes: Optional[int], resolve_minutes: Optional[int]) -> SlaTargets:
    return SlaTargets(ack_minutes=ack_minutes, resolve_minutes=resolve_minutes, source=TargetSource.DEFAULT)


_HOUR = 60
_DAY = 24 * _HOUR

#: What a fresh deployment promises before anyone configures a policy.
#:
#: Alerts are triage work and run on hours; cases are investigations and run on days.
#: Informational carries no promise by default: it is the severity a SOC deliberately
#: leaves for when there is time, and a target there would only manufacture breaches.
BUILTIN_TARGETS: Mapping[SlaEntity, Mapping[str, SlaTargets]] = {
    SlaEntity.ALERT: {
        "Critical": _targets(15, 4 * _HOUR),
        "High": _targets(1 * _HOUR, 8 * _HOUR),
        "Medium": _targets(4 * _HOUR, 1 * _DAY),
        "Low": _targets(8 * _HOUR, 3 * _DAY),
        "Informational": _targets(None, None),
    },
    SlaEntity.CASE: {
        "Critical": _targets(30, 1 * _DAY),
        "High": _targets(1 * _HOUR, 3 * _DAY),
        "Medium": _targets(4 * _HOUR, 7 * _DAY),
        "Low": _targets(1 * _DAY, 14 * _DAY),
        "Informational": _targets(None, None),
    },
}


@dataclass(frozen=True)
class PolicyRow:
    """A stored policy cell, decoupled from the ORM so resolution stays pure.

    ``customer_code=None`` is the global policy.
    """

    customer_code: Optional[str]
    entity: SlaEntity
    severity: str
    ack_minutes: Optional[int]
    resolve_minutes: Optional[int]
    business_hours: bool = False


def builtin_targets(entity: SlaEntity, severity: str) -> SlaTargets:
    """The default for a cell. An unknown severity gets no promise rather than an error."""
    return BUILTIN_TARGETS[entity].get(severity, _targets(None, None))


def resolve_targets(
    entity: SlaEntity,
    severity: str,
    customer_code: Optional[str],
    rows: Iterable[PolicyRow],
) -> SlaTargets:
    """The targets that apply to one item: customer override, else global, else default."""
    global_row: Optional[PolicyRow] = None
    for row in rows:
        if row.entity != entity or row.severity != severity:
            continue
        if customer_code is not None and row.customer_code == customer_code:
            return SlaTargets(row.ack_minutes, row.resolve_minutes, TargetSource.CUSTOMER, row.business_hours)
        if row.customer_code is None:
            global_row = row
    if global_row is not None:
        return SlaTargets(global_row.ack_minutes, global_row.resolve_minutes, TargetSource.GLOBAL, global_row.business_hours)
    return builtin_targets(entity, severity)


def effective_matrix(
    customer_code: Optional[str],
    rows: Iterable[PolicyRow],
) -> Dict[SlaEntity, Dict[str, SlaTargets]]:
    """Every cell of a scope as it would resolve — what the policy editor renders."""
    materialised = list(rows)
    return {
        entity: {severity: resolve_targets(entity, severity, customer_code, materialised) for severity in SEVERITIES_DESC}
        for entity in SlaEntity
    }


def validate_minutes(value: Optional[int]) -> Optional[int]:
    """``None`` (no promise) or a whole number of minutes in (0, MAX_TARGET_MINUTES]."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Targets are whole minutes")
    if value <= 0:
        raise ValueError("Targets must be greater than zero; leave a target empty for no promise")
    if value > MAX_TARGET_MINUTES:
        raise ValueError(f"Targets cannot exceed {MAX_TARGET_MINUTES} minutes (one year)")
    return value
