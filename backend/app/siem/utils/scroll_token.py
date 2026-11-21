"""Event search's "next page" token, bound to the search it continues (#1258).

The indexer's scroll id names a search context and nothing else: whoever presents one reads
the next page of that search, whatever tenant it was run for. Scroll ids also travel in a GET
query string (proxy and access logs) and are built from per-node counters. So the API never
hands one out bare: it hands out the scroll id signed together with the customer and the
event source it was opened for, and continues a scroll only for the same pair.
"""

import hashlib
import hmac
import json
from typing import Iterable
from typing import Optional

_SEPARATOR = "."  # never part of a scroll id, which is base64
_PURPOSE = b"siem-event-scroll"


def _mac(scroll_id: str, customer_code: str, source_name: str, secret: str) -> str:
    message = b"\x00".join((_PURPOSE, customer_code.encode(), source_name.encode(), scroll_id.encode()))
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def sign_scroll(scroll_id: Optional[str], customer_code: str, source_name: str, secret: str) -> Optional[str]:
    """The token handed to the client for `scroll_id`; `None` stays `None` (no next page)."""
    if not scroll_id:
        return None
    return f"{scroll_id}{_SEPARATOR}{_mac(scroll_id, customer_code, source_name, secret)}"


def open_scroll(token: str, customer_code: str, source_name: str, secret: str) -> Optional[str]:
    """The scroll id inside `token`, or `None` when it was not issued for this customer and source."""
    scroll_id, separator, mac = token.rpartition(_SEPARATOR)
    if not separator or not scroll_id:
        return None
    if not hmac.compare_digest(mac, _mac(scroll_id, customer_code, source_name, secret)):
        return None
    return scroll_id


# ── a search across several sources (#1356) ──────────────────────────────────
#
# The token names the set of sources, not their order, under its own purpose: a token handed out
# for one source never continues a search of several, nor the other way round.

_MULTI_PURPOSE = b"siem-event-scroll-multi"


def _multi_mac(scroll_id: str, customer_code: str, source_names: Iterable[str], secret: str) -> str:
    names = json.dumps(sorted(set(source_names)), separators=(",", ":"), ensure_ascii=False)
    message = b"\x00".join((_MULTI_PURPOSE, customer_code.encode(), names.encode(), scroll_id.encode()))
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def sign_multi_scroll(scroll_id: Optional[str], customer_code: str, source_names: Iterable[str], secret: str) -> Optional[str]:
    """The token handed to the client for a search of ``source_names``; ``None`` stays ``None``."""
    if not scroll_id:
        return None
    return f"{scroll_id}{_SEPARATOR}{_multi_mac(scroll_id, customer_code, source_names, secret)}"


def open_multi_scroll(token: str, customer_code: str, source_names: Iterable[str], secret: str) -> Optional[str]:
    """The scroll id inside ``token``, or ``None`` when it was not issued for this customer and set of sources."""
    scroll_id, separator, mac = token.rpartition(_SEPARATOR)
    if not separator or not scroll_id:
        return None
    if not hmac.compare_digest(mac, _multi_mac(scroll_id, customer_code, source_names, secret)):
        return None
    return scroll_id
