"""The time an SLA clock runs on: around the clock, or business hours only.

A clock basis answers two questions, and SLA arithmetic needs nothing else:

- ``add(start, seconds)``      — when does a target of ``seconds`` expire?
- ``elapsed(start, end)``      — how much of a target did ``[start, end)`` use?

``CONTINUOUS`` is wall-clock time (24/7). ``BusinessCalendar`` counts only the working
windows of a week in a timezone, skipping holidays — so "4 business hours" opened on
Friday at 16:00 in Rome expires on Monday at 12:00 Rome time.

All instants in and out are **naive UTC**, the convention of every timestamp column.
Working windows are defined in local time and converted per day, so a daylight-saving
change moves the UTC window, never the local one.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import timezone
from typing import Dict
from typing import FrozenSet
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Protocol
from typing import Sequence
from typing import Tuple
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

Window = Tuple[time, time]

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

#: Guard against a calendar with no working time at all: adding a target to it would
#: never end. Two years of searching is far beyond any SLA.
_MAX_SEARCH_DAYS = 731


class ClockBasis(Protocol):
    business_hours: bool

    def add(self, start: datetime, seconds: float) -> datetime:
        ...

    def elapsed(self, start: datetime, end: datetime) -> float:
        ...


class ContinuousClock:
    """24/7: a target runs on wall-clock time."""

    business_hours = False

    def add(self, start: datetime, seconds: float) -> datetime:
        return start + timedelta(seconds=seconds)

    def elapsed(self, start: datetime, end: datetime) -> float:
        return max(0.0, (end - start).total_seconds())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ContinuousClock)

    def __hash__(self) -> int:
        return hash("continuous")


CONTINUOUS = ContinuousClock()


def _validate_windows(windows: Sequence[Window]) -> Tuple[Window, ...]:
    ordered = sorted(windows)
    for start, end in ordered:
        if start >= end:
            raise ValueError(f"A working window must start before it ends ({start:%H:%M}–{end:%H:%M})")
    for (_, previous_end), (next_start, _) in zip(ordered, ordered[1:]):
        if next_start < previous_end:
            raise ValueError("Working windows of one day must not overlap")
    return tuple(ordered)


@dataclass(frozen=True)
class BusinessCalendar:
    """Working windows per weekday (0 = Monday) in ``timezone``, minus ``holidays``.

    A day may have several windows (a lunch break is two of them); a weekday with no
    windows is closed. Midnight-spanning shifts are expressed as two windows on two days.
    """

    timezone: str = "UTC"
    week: Mapping[int, Tuple[Window, ...]] = field(default_factory=dict)
    holidays: FrozenSet[date] = frozenset()

    business_hours = True

    def __post_init__(self) -> None:
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError(f"Unknown timezone {self.timezone!r}") from e
        normalised = {}
        for weekday, windows in self.week.items():
            if not 0 <= weekday <= 6:
                raise ValueError("Weekdays are 0 (Monday) to 6 (Sunday)")
            if windows:
                normalised[weekday] = _validate_windows(windows)
        object.__setattr__(self, "week", normalised)
        object.__setattr__(self, "holidays", frozenset(self.holidays))
        if not normalised:
            raise ValueError("A business calendar needs at least one working window")

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def windows_on(self, day: date) -> List[Tuple[datetime, datetime]]:
        """The working windows of a local ``day``, as naive-UTC intervals."""
        if day in self.holidays:
            return []
        zone = self.zone
        out = []
        for start, end in self.week.get(day.weekday(), ()):
            out.append((_to_utc(datetime.combine(day, start), zone), _to_utc(datetime.combine(day, end), zone)))
        return out

    def _local_day(self, moment: datetime) -> date:
        return moment.replace(tzinfo=timezone.utc).astimezone(self.zone).date()

    def add(self, start: datetime, seconds: float) -> datetime:
        """The instant at which ``seconds`` of working time after ``start`` have run."""
        remaining = max(0.0, seconds)
        day = self._local_day(start) - timedelta(days=1)  # a window of yesterday may run past local midnight
        for _ in range(_MAX_SEARCH_DAYS):
            for window_start, window_end in self.windows_on(day):
                begin = max(window_start, start)
                if begin >= window_end:
                    continue
                available = (window_end - begin).total_seconds()
                if remaining <= available:
                    return begin + timedelta(seconds=remaining)
                remaining -= available
            day += timedelta(days=1)
        raise ValueError("The business calendar has no working time within two years")

    def elapsed(self, start: datetime, end: datetime) -> float:
        """Working seconds inside ``[start, end)``."""
        if end <= start:
            return 0.0
        total = 0.0
        day = self._local_day(start) - timedelta(days=1)
        last = self._local_day(end)
        while day <= last:
            for window_start, window_end in self.windows_on(day):
                overlap = (min(window_end, end) - max(window_start, start)).total_seconds()
                if overlap > 0:
                    total += overlap
            day += timedelta(days=1)
        return total

    # ── serialisation (the shape stored in soc_sla_calendar and sent by the API) ──

    def to_dict(self) -> Dict[str, object]:
        return {
            "timezone": self.timezone,
            "week": {WEEKDAYS[d]: [[f"{s:%H:%M}", f"{e:%H:%M}"] for s, e in self.week.get(d, ())] for d in range(7)},
            "holidays": sorted(day.isoformat() for day in self.holidays),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "BusinessCalendar":
        week_in = data.get("week") or {}
        week: Dict[int, Tuple[Window, ...]] = {}
        for name, windows in dict(week_in).items():  # type: ignore[arg-type]
            if name not in WEEKDAYS:
                raise ValueError(f"Unknown weekday {name!r}")
            week[WEEKDAYS.index(name)] = tuple((_parse_time(start), _parse_time(end)) for start, end in windows or [])
        holidays = frozenset(date.fromisoformat(str(day)) for day in (data.get("holidays") or []))  # type: ignore[union-attr]
        return cls(timezone=str(data.get("timezone") or "UTC"), week=week, holidays=holidays)


def _parse_time(value: str) -> time:
    try:
        hours, minutes = str(value).split(":")
        return time(int(hours), int(minutes))
    except ValueError as e:
        raise ValueError(f"Times are HH:MM, got {value!r}") from e


def _to_utc(local: datetime, zone: ZoneInfo) -> datetime:
    return local.replace(tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)


def office_hours(
    timezone_name: str = "UTC",
    start: time = time(9),
    end: time = time(17),
    days: Iterable[int] = range(5),
) -> BusinessCalendar:
    return BusinessCalendar(timezone=timezone_name, week={day: ((start, end),) for day in days})


#: Used for business-hours targets when nobody configured a calendar: Monday to Friday,
#: 09:00–17:00 UTC. Deliberately plain — an operator turning business hours on is told
#: to set the real one.
DEFAULT_CALENDAR = office_hours()


def clock_for(business_hours: bool, calendar: Optional[BusinessCalendar]) -> ClockBasis:
    return (calendar or DEFAULT_CALENDAR) if business_hours else CONTINUOUS


@dataclass(frozen=True)
class CalendarBook:
    """Every calendar a question needs, resolved per customer: its own, else the global one,
    else ``DEFAULT_CALENDAR``."""

    global_calendar: Optional[BusinessCalendar] = None
    by_customer: Mapping[str, BusinessCalendar] = field(default_factory=dict)

    def for_customer(self, customer_code: Optional[str]) -> BusinessCalendar:
        if customer_code and customer_code in self.by_customer:
            return self.by_customer[customer_code]
        return self.global_calendar or DEFAULT_CALENDAR

    def source(self, customer_code: Optional[str]) -> str:
        if customer_code and customer_code in self.by_customer:
            return "customer"
        return "global" if self.global_calendar else "default"

    def clock(self, customer_code: Optional[str], business_hours: bool) -> ClockBasis:
        return self.for_customer(customer_code) if business_hours else CONTINUOUS
