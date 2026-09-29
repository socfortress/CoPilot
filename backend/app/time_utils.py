from datetime import datetime
from datetime import timezone


def now_utc() -> datetime:
    """The current time as a timezone-aware UTC datetime.

    Replaces ``datetime.utcnow()``, deprecated since Python 3.12 because it returns a
    naive value that is easily mistaken for local time. Written to a naive ``DATETIME``
    column it is stored as the same UTC wall-clock time ``utcnow()`` produced.
    """
    return datetime.now(timezone.utc)
