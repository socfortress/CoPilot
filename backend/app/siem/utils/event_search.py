"""The rules of event search's memory (#1258) that need no database."""

from typing import Protocol

from app.time_utils import to_naive_utc

SAVED_LIMIT = 50
RECENT_LIMIT = 10


class SearchLike(Protocol):
    source_name: str
    query: str
    time_mode: str
    time_amount: int
    time_unit: str
    time_from: object
    time_to: object


def _naive(moment):
    # Stored times are naive UTC; requested ones carry an offset.
    return to_naive_utc(moment) if moment is not None and getattr(moment, "tzinfo", None) else moment


def same_search(a: SearchLike, b: SearchLike) -> bool:
    """Two searches are the same when they ask for the same events, whatever the page size."""
    if (a.source_name, a.query.strip(), a.time_mode) != (b.source_name, b.query.strip(), b.time_mode):
        return False
    if a.time_mode == "absolute":
        return (_naive(a.time_from), _naive(a.time_to)) == (_naive(b.time_from), _naive(b.time_to))
    return (a.time_amount, a.time_unit) == (b.time_amount, b.time_unit)
