"""What a case's status change does to the alerts linked to it.

Pure, so the rules are readable in one place and testable without a database:

- closing the case closes every linked alert;
- reopening a closed case reopens every linked alert — to ``IN_PROGRESS`` (the SOC is on
  it), or to ``PENDING_CUSTOMER`` when the case reopens waiting on the customer;
- a case that starts waiting on the customer takes its *active* alerts with it, so their
  SLA clocks stop together with the case's (#1187);
- a case the SOC picks back up brings back only the alerts that were waiting with it.

Any other transition leaves the alerts alone, as before.
"""

from dataclasses import dataclass
from typing import FrozenSet
from typing import Optional

OPEN = "OPEN"
IN_PROGRESS = "IN_PROGRESS"
PENDING_CUSTOMER = "PENDING_CUSTOMER"
CLOSED = "CLOSED"

_ACTIVE = frozenset({OPEN, IN_PROGRESS})


@dataclass(frozen=True)
class AlertCascade:
    to_status: str
    #: Only alerts currently in one of these statuses move; ``None`` moves every alert.
    from_statuses: Optional[FrozenSet[str]] = None

    def applies_to(self, alert_status: Optional[str]) -> bool:
        return self.from_statuses is None or alert_status in self.from_statuses


def cascade_for(old_status: Optional[str], new_status: str) -> Optional[AlertCascade]:
    if new_status == CLOSED:
        return AlertCascade(CLOSED) if old_status != CLOSED else None
    if old_status == CLOSED:
        return AlertCascade(PENDING_CUSTOMER if new_status == PENDING_CUSTOMER else IN_PROGRESS)
    if new_status == PENDING_CUSTOMER and old_status != PENDING_CUSTOMER:
        return AlertCascade(PENDING_CUSTOMER, _ACTIVE)
    if old_status == PENDING_CUSTOMER and new_status in _ACTIVE:
        return AlertCascade(IN_PROGRESS, frozenset({PENDING_CUSTOMER}))
    return None
