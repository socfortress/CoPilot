"""The one place SOC Management reads the time.

Every timestamp column is a naive ``DATETIME`` holding UTC, and SLA arithmetic compares
Python datetimes read back from them, so "now" must be naive UTC too: an aware value
would raise on the first comparison with a stored one.
"""

from datetime import datetime

from app.time_utils import now_utc


def utc_now() -> datetime:
    return now_utc().replace(tzinfo=None)
