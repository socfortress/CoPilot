"""SLA notices: which clocks have just turned at risk or breached, and must say so once.

A notice is owed when a running clock is in a state nobody has been told about yet. The
tracking row remembers what was told in four write-once stamps
(``{ack,resolve}_{at_risk,breached}_notified_at``), so each clock produces at most one
"at risk" and one "breached" notice over its whole life — a scheduler that runs every
two minutes must not message the SOC every two minutes.

Two rules beyond "state changed":

- **A breach also settles the at-risk notice.** A clock that jumps straight to breached
  (the scheduler was down, or the target is shorter than its interval) says so once, as
  a breach, and never sends a stale "at risk" afterwards.
- **Old news is stamped, not sent.** A clock that breached long before anyone could
  have told (the first run after an upgrade, a scheduler outage) is marked as handled
  silently: a burst of week-old breaches buries the one that matters today.

A paused clock is owed nothing — waiting on the customer is not the SOC running late.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Callable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple

from app.soc_management.domain.analytics import ItemFact
from app.soc_management.domain.sla import SlaState

#: A breach older than this when first noticed is stamped without a message.
STALE_AFTER = timedelta(hours=24)


class NoticeKind(str, Enum):
    AT_RISK = "at_risk"
    BREACHED = "breached"


class SlaClock(str, Enum):
    ACK = "ack"
    RESOLVE = "resolve"

    @property
    def label(self) -> str:
        return "acknowledge" if self is SlaClock.ACK else "resolve"


def stamp_column(clock: SlaClock, kind: NoticeKind) -> str:
    return f"{clock.value}_{kind.value}_notified_at"


STAMP_COLUMNS: Tuple[str, ...] = tuple(stamp_column(clock, kind) for clock in SlaClock for kind in NoticeKind)


@dataclass(frozen=True)
class Notice:
    clock: SlaClock
    kind: NoticeKind
    due_at: datetime
    #: Stamp it but send nothing (see "old news" above).
    silent: bool = False

    @property
    def column(self) -> str:
        return stamp_column(self.clock, self.kind)

    @property
    def settles(self) -> Tuple[str, ...]:
        """Further stamps this notice makes moot: a breach settles the at-risk notice."""
        return (stamp_column(self.clock, NoticeKind.AT_RISK),) if self.kind is NoticeKind.BREACHED else ()


def _running(fact: ItemFact) -> List[Tuple[SlaClock, Optional[datetime], Callable[[datetime], SlaState]]]:
    """The clocks still running, with their due time and state."""
    clocks = []
    if fact.ack_achieved_at is None:
        clocks.append((SlaClock.ACK, fact.ack_due_at, fact.ack_state))
    if fact.resolved_at is None:
        clocks.append((SlaClock.RESOLVE, fact.resolve_due_at, fact.resolve_state))
    return clocks


def notices_for(fact: ItemFact, stamps: Mapping[str, Optional[datetime]], now: datetime) -> List[Notice]:
    """The notices ``fact`` owes at ``now``, given what its stamps say was already told."""
    if not fact.tracked or not fact.is_open:
        return []
    owed: List[Notice] = []
    for clock, due_at, state_at in _running(fact):
        if due_at is None:
            continue
        state = state_at(now)
        if state is SlaState.BREACHED and stamps.get(stamp_column(clock, NoticeKind.BREACHED)) is None:
            owed.append(Notice(clock, NoticeKind.BREACHED, due_at, silent=now - due_at > STALE_AFTER))
        elif state is SlaState.AT_RISK and stamps.get(stamp_column(clock, NoticeKind.AT_RISK)) is None:
            owed.append(Notice(clock, NoticeKind.AT_RISK, due_at))
    return owed
