from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from app.incidents.services.alert_severity import SEVERITY_LEVELS
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.domain.policy import TargetSource
from app.soc_management.domain.policy import validate_minutes


class PolicyCell(BaseModel):
    """One resolved cell: the targets that apply, and which scope they come from."""

    entity: SlaEntity
    severity: str
    ack_minutes: Optional[int] = None
    resolve_minutes: Optional[int] = None
    #: True: the targets count business hours of the customer's calendar.
    business_hours: bool = False
    source: TargetSource


class PolicyMatrix(BaseModel):
    #: ``None`` for the global policy.
    customer_code: Optional[str] = None
    cells: List[PolicyCell]


class PolicyOverride(BaseModel):
    customer_code: str
    cells: int
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class PolicyCellIn(BaseModel):
    """A cell as the editor submits it.

    ``inherit=True`` stores nothing for the cell, so it follows the next scope out
    (global for a customer, the built-in default for global). Otherwise the two targets
    are stored as given — ``None`` meaning "no promise on this clock".
    """

    entity: SlaEntity
    severity: str
    inherit: bool = False
    ack_minutes: Optional[int] = None
    resolve_minutes: Optional[int] = None
    business_hours: bool = False

    @field_validator("severity")
    @classmethod
    def _known_severity(cls, value: str) -> str:
        if value not in SEVERITY_LEVELS:
            raise ValueError(f"Expected one of {', '.join(SEVERITY_LEVELS)}")
        return value

    @field_validator("ack_minutes", "resolve_minutes")
    @classmethod
    def _minutes(cls, value: Optional[int]) -> Optional[int]:
        return validate_minutes(value)

    @model_validator(mode="after")
    def _ack_not_after_resolve(self) -> "PolicyCellIn":
        # Resolving an item also ends its response clock, so a response target longer
        # than the resolution target could never be the one that breaches: a typo.
        if (
            not self.inherit
            and self.ack_minutes is not None
            and self.resolve_minutes is not None
            and self.ack_minutes > self.resolve_minutes
        ):
            raise ValueError(f"{self.entity.value} {self.severity}: the acknowledge target cannot be longer than the resolve target")
        return self


class PolicyUpdateRequest(BaseModel):
    #: ``None`` edits the global policy; a code edits that customer's overrides.
    customer_code: Optional[str] = None
    cells: List[PolicyCellIn] = Field(default_factory=list)
    #: Recompute the due times of items still open in this scope. Clocks already met or
    #: breached keep the due time they were judged against.
    apply_to_open: bool = False

    @model_validator(mode="after")
    def _one_cell_per_slot(self) -> "PolicyUpdateRequest":
        seen = set()
        for cell in self.cells:
            slot = (cell.entity, cell.severity)
            if slot in seen:
                raise ValueError(f"Duplicate cell {cell.entity.value} / {cell.severity}")
            seen.add(slot)
        return self


class PolicyResponse(BaseModel):
    success: bool = True
    message: str = ""
    policy: PolicyMatrix
    #: Open items whose due times moved (``apply_to_open``); 0 otherwise.
    retargeted: int = 0


class PolicyOverridesResponse(BaseModel):
    success: bool = True
    message: str = ""
    overrides: List[PolicyOverride]
