"""Reporting periods and the buckets their trends are drawn in.

Periods are half-open, ``[start, end)``, in naive UTC — the convention of every
timestamp column in the database. A period's *previous* period is the same length
immediately before it, which is what the dashboard's "vs previous" deltas compare to.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import List

#: A year and a day, so "this time last year to now" still fits.
MAX_PERIOD = timedelta(days=366)


class Bucket(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError("The period must start before it ends")

    @property
    def length(self) -> timedelta:
        return self.end - self.start

    def previous(self) -> "Period":
        return Period(self.start - self.length, self.start)

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment < self.end


def requested_period(start: datetime, end: datetime) -> Period:
    """A period a caller asked for: the internal invariant plus the reporting cap.

    The cap belongs to requests, not to ``Period``: the dashboard internally loads the
    requested period *and* its predecessor, which may well span two years.
    """
    period = Period(start, end)
    if period.length > MAX_PERIOD:
        raise ValueError("The period cannot be longer than 366 days")
    return period


def auto_bucket(period: Period) -> Bucket:
    """Roughly 24–60 points whatever the range: hourly for a day, monthly for a year."""
    days = period.length.total_seconds() / 86400
    if days <= 2:
        return Bucket.HOUR
    if days <= 62:
        return Bucket.DAY
    if days <= 182:
        return Bucket.WEEK
    return Bucket.MONTH


def floor_to(moment: datetime, bucket: Bucket) -> datetime:
    if bucket is Bucket.HOUR:
        return moment.replace(minute=0, second=0, microsecond=0)
    day = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    if bucket is Bucket.DAY:
        return day
    if bucket is Bucket.WEEK:
        return day - timedelta(days=day.weekday())  # ISO weeks start on Monday
    return day.replace(day=1)


def next_start(moment: datetime, bucket: Bucket) -> datetime:
    if bucket is Bucket.HOUR:
        return moment + timedelta(hours=1)
    if bucket is Bucket.DAY:
        return moment + timedelta(days=1)
    if bucket is Bucket.WEEK:
        return moment + timedelta(weeks=1)
    if moment.month == 12:
        return moment.replace(year=moment.year + 1, month=1)
    return moment.replace(month=moment.month + 1)


def bucket_starts(period: Period, bucket: Bucket) -> List[datetime]:
    """The start of every bucket the period touches, oldest first."""
    starts: List[datetime] = []
    cursor = floor_to(period.start, bucket)
    while cursor < period.end:
        starts.append(cursor)
        cursor = next_start(cursor, bucket)
    return starts
