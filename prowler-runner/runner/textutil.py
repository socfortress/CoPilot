"""Bounded, cleaned text from Prowler's output and catalogs.

Everything Prowler reports about a resource (names, tags, status text) comes from
the customer's cloud and is untrusted. Control characters are removed here; other
invisible characters (bidi overrides, zero-width) are kept, because hiding them
would also hide a spoofed name: showing them safely is the UI's job.
"""

from __future__ import annotations

import re
from typing import Any

# C0 controls except tab and newline, DEL, and the C1 controls.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
ELLIPSIS = "…"


def clean_text(value: Any, limit: int) -> str:
    """`value` as text without control characters, cut to at most `limit` characters.

    A string, or a number, is kept; anything else becomes "". A cut string ends with "…".
    """
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        value = str(value)
    if not isinstance(value, str):
        return ""
    text = _CONTROL.sub("", value)
    if len(text) > limit:
        return text[: max(limit - 1, 0)] + ELLIPSIS
    return text


def http_url(value: Any, limit: int = 2048) -> str | None:
    """`value` if it is an http(s) URL of at most `limit` characters with no whitespace or controls."""
    if not isinstance(value, str) or not value or len(value) > limit:
        return None
    if _CONTROL.search(value) or any(character.isspace() for character in value):
        return None
    if not value.lower().startswith(("https://", "http://")):
        return None
    return value


def text_list(value: Any, item_limit: int, max_items: int) -> list[str]:
    """The non-empty cleaned strings of a list, each cut to `item_limit`, at most `max_items`, in order, once each."""
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = clean_text(item, item_limit)
        if text and text not in result:
            result.append(text)
            if len(result) >= max_items:
                break
    return result
