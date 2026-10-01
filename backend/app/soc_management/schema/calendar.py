from datetime import date
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

from app.soc_management.domain.calendar import BusinessCalendar

#: ``{"mon": [["09:00", "17:00"]], "tue": [...], …}`` — a missing or empty day is closed.
WeekIn = Dict[str, List[List[str]]]


class CalendarIn(BaseModel):
    #: ``None`` edits the deployment's calendar; a code edits that customer's.
    customer_code: Optional[str] = None
    timezone: str = "UTC"
    week: WeekIn = Field(default_factory=dict)
    holidays: List[date] = Field(default_factory=list)
    #: Recompute the due times of open business-hours items in this scope.
    apply_to_open: bool = False

    @model_validator(mode="after")
    def _valid_calendar(self) -> "CalendarIn":
        self.to_domain()  # raises ValueError with a readable reason
        return self

    def to_domain(self) -> BusinessCalendar:
        for windows in self.week.values():
            for window in windows:
                if len(window) != 2:
                    raise ValueError("A working window is a [start, end] pair of HH:MM times")
        return BusinessCalendar.from_dict(
            {"timezone": self.timezone, "week": self.week, "holidays": [d.isoformat() for d in self.holidays]},
        )


class CalendarOut(BaseModel):
    customer_code: Optional[str] = None
    #: Where the calendar in force comes from.
    source: Literal["customer", "global", "default"]
    timezone: str
    week: WeekIn
    holidays: List[str]


class CalendarResponse(BaseModel):
    success: bool = True
    message: str = ""
    calendar: CalendarOut
    #: Customers with a calendar of their own (for the scope picker).
    customers_with_calendar: List[str] = Field(default_factory=list)
    retargeted: int = 0
