"""Evaluating one SLA clock, and summarising many into compliance.

A clock is ``(opened_at, due_at, achieved_at)`` read against ``now``:

- no ``due_at``                   → NOT_TRACKED (no promise for that severity)
- achieved on or before due       → MET
- achieved after due              → BREACHED
- not achieved, already past due  → BREACHED (it cannot be met any more)
- not achieved, in the last quarter of its window → AT_RISK
- otherwise                       → ON_TRACK

**Compliance is met ÷ (met + breached).** Items still on track have no outcome yet and
stay out of both sides: counting them as met would make compliance improve whenever
the SOC falls behind on closing things, which is exactly backwards (the same reasoning
as the false-positive rate dividing by *reviewed* alerts, #1085).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable
from typing import Optional

#: The share of a clock's window left at which an open item turns AT_RISK.
AT_RISK_FRACTION = 0.25


class SlaState(str, Enum):
    MET = "met"
    BREACHED = "breached"
    AT_RISK = "at_risk"
    ON_TRACK = "on_track"
    NOT_TRACKED = "not_tracked"


def evaluate(opened_at: datetime, due_at: Optional[datetime], achieved_at: Optional[datetime], now: datetime) -> SlaState:
    if due_at is None:
        return SlaState.NOT_TRACKED
    if achieved_at is not None:
        return SlaState.MET if achieved_at <= due_at else SlaState.BREACHED
    if now > due_at:
        return SlaState.BREACHED
    window = (due_at - opened_at).total_seconds()
    remaining = (due_at - now).total_seconds()
    if window > 0 and remaining <= window * AT_RISK_FRACTION:
        return SlaState.AT_RISK
    return SlaState.ON_TRACK


def overdue_seconds(due_at: Optional[datetime], achieved_at: Optional[datetime], now: datetime) -> Optional[float]:
    """How far past due the clock is (or was, when achieved late). ``None`` when not late."""
    if due_at is None:
        return None
    reference = achieved_at or now
    late = (reference - due_at).total_seconds()
    return late if late > 0 else None


@dataclass(frozen=True)
class Compliance:
    met: int = 0
    breached: int = 0
    at_risk: int = 0
    on_track: int = 0
    not_tracked: int = 0

    @property
    def decided(self) -> int:
        return self.met + self.breached

    @property
    def rate(self) -> Optional[float]:
        """Percentage met, one decimal; ``None`` when no clock has an outcome yet."""
        if not self.decided:
            return None
        return round(self.met * 100.0 / self.decided, 1)


def summarize(states: Iterable[SlaState]) -> Compliance:
    counts = {state: 0 for state in SlaState}
    for state in states:
        counts[state] += 1
    return Compliance(
        met=counts[SlaState.MET],
        breached=counts[SlaState.BREACHED],
        at_risk=counts[SlaState.AT_RISK],
        on_track=counts[SlaState.ON_TRACK],
        not_tracked=counts[SlaState.NOT_TRACKED],
    )
