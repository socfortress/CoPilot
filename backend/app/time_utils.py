from datetime import datetime
from datetime import timezone
from typing import Optional


def now_utc() -> datetime:
    """The current time as a timezone-aware UTC datetime.

    Replaces ``datetime.utcnow()``, deprecated since Python 3.12 because it returns a
    naive value that is easily mistaken for local time. Written to a naive ``DATETIME``
    column it is stored as the same UTC wall-clock time ``utcnow()`` produced.
    """
    return datetime.now(timezone.utc)


def to_naive_utc(moment: Optional[datetime]) -> Optional[datetime]:
    """``moment`` as the naive UTC the ``DATETIME`` columns hold.

    A timezone-aware value is converted to UTC; a naive one is taken to be UTC already.
    """
    if moment is None or moment.tzinfo is None:
        return moment
    return moment.astimezone(timezone.utc).replace(tzinfo=None)
