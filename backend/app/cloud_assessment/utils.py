"""Pure helpers for the cloud assessment module: text cleaning, times and schedules.

Everything Prowler reports comes from the customer's cloud (resource names, tags, status
text) and passes through copilot-prowler, which bounds and cleans it. CoPilot cleans it
again before storing it: control characters go, a lone surrogate (which MySQL can't store
and the JSON reader can produce from a ``\\ud800`` escape) becomes U+FFFD, and every value is
cut to its column. Other invisible characters are kept: showing them safely is the UI's job.
"""

import re
import unicodedata
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import List
from typing import Optional

from app.time_utils import now_utc
from app.time_utils import to_naive_utc

# C0 controls except tab and newline, DEL, and the C1 controls.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_SURROGATE = re.compile(r"[\ud800-\udfff]")
ELLIPSIS = "…"
#: Not in a name an admin types: control, format (zero-width, bidi), surrogate, private use, separators.
_UNSAFE_NAME_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Zl", "Zp"})


def utc_now() -> datetime:
    """Now, as the naive UTC the DATETIME columns hold."""
    return to_naive_utc(now_utc())


def as_utc(moment: Optional[datetime]) -> Optional[datetime]:
    """A stored (naive UTC) or aware time as an aware UTC one, for responses."""
    if moment is None:
        return None
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)


def clean_text(value: Any, limit: int) -> str:
    """``value`` as text fit for a column of ``limit`` characters.

    A string or a number is kept, anything else is "". Controls are removed, lone surrogates
    replaced, and a cut string ends with "…".
    """
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        value = str(value)
    if not isinstance(value, str):
        return ""
    text = _SURROGATE.sub("�", _CONTROL.sub("", value))
    if len(text) > limit:
        return text[: max(limit - 1, 0)] + ELLIPSIS
    return text


def clean_list(value: Any, item_limit: int, max_items: int) -> List[str]:
    """The non-empty cleaned strings of a list, each cut to ``item_limit``, at most ``max_items``, once each."""
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for item in value:
        text = clean_text(item, item_limit)
        if text and text not in result:
            result.append(text)
            if len(result) >= max_items:
                break
    return result


def http_url(value: Any, limit: int = 2048) -> Optional[str]:
    """``value`` if it is an http(s) URL of at most ``limit`` characters, with no whitespace or controls."""
    if not isinstance(value, str) or not value or len(value) > limit:
        return None
    if _CONTROL.search(value) or _SURROGATE.search(value) or any(character.isspace() for character in value):
        return None
    if not value.lower().startswith(("https://", "http://")):
        return None
    return value


def url_list(value: Any, max_items: int = 10) -> List[str]:
    urls: List[str] = []
    for item in value if isinstance(value, list) else []:
        url = http_url(item)
        if url and url not in urls:
            urls.append(url)
            if len(urls) >= max_items:
                break
    return urls


def check_name(value: str, limit: int = 100) -> str:
    """An account name as typed: trimmed, 1 to ``limit`` characters, nothing invisible. Raises ValueError."""
    text = (value or "").strip()
    if not text:
        raise ValueError("enter a name")
    if len(text) > limit:
        raise ValueError(f"a name has at most {limit} characters")
    if any(unicodedata.category(character) in _UNSAFE_NAME_CATEGORIES for character in text):
        raise ValueError("a name can't hold control or invisible characters")
    return text


def parse_time(value: Any) -> Optional[datetime]:
    """An ISO 8601 time from Prowler's output as naive UTC, or None. A time without an offset is UTC."""
    if not isinstance(value, str) or not value or len(value) > 64:
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    return to_naive_utc(moment)


# --- schedules ---------------------------------------------------------------------------------


def last_slot(schedule: str, hour: Optional[int], weekday: Optional[int], now: datetime) -> Optional[datetime]:
    """The most recent scheduled time at or before ``now`` (naive UTC), or None when there is no schedule."""
    if schedule not in ("daily", "weekly") or hour is None:
        return None
    today = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if schedule == "daily":
        return today if today <= now else today - timedelta(days=1)
    if weekday is None:
        return None
    slot = today - timedelta(days=(now.weekday() - weekday) % 7)
    return slot if slot <= now else slot - timedelta(days=7)


def next_slot(schedule: str, hour: Optional[int], weekday: Optional[int], now: datetime) -> Optional[datetime]:
    """The next scheduled time after ``now`` (naive UTC), or None."""
    slot = last_slot(schedule, hour, weekday, now)
    if slot is None:
        return None
    return slot + (timedelta(days=1) if schedule == "daily" else timedelta(days=7))


def schedule_due(
    schedule: str,
    hour: Optional[int],
    weekday: Optional[int],
    now: datetime,
    settings_changed_at: datetime,
    last_queued_at: Optional[datetime],
) -> bool:
    """Whether a scheduled scan is due: a slot has passed since the account's settings last changed
    (setting a schedule never scans at once), and no scan, of any trigger, was queued since that slot.
    A backend that was down over several slots scans once."""
    slot = last_slot(schedule, hour, weekday, now)
    if slot is None or slot < settings_changed_at:
        return False
    return last_queued_at is None or last_queued_at < slot
