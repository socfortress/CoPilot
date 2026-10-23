"""The Talon Memory tab (``/api/talon/memory/...``): what talon-analyst remembers about a customer
(its MemPalace drawers, the asset timeline) and the caller's own chat memory, relayed from
talon-analyst's ``/v2/memory`` API, plus forgetting what may be forgotten.

talon-analyst trusts CoPilot here: it is asked with the connector's API key alone, so every rule
about who may see what is applied in this module, before Talon is asked:

- **Tenancy.** The customer in the path must match talon-analyst's grammar, be one the caller may
  see (``get_user_accessible_customers``: an admin by ``role_id`` sees every customer, anyone else
  their assigned ones, #1219: no assignment, no customer) and be a real ``customers`` row, exactly
  as written (MySQL compares codes case-insensitively, talon-analyst's tenant keys don't). In that
  order, so a scoped analyst learns nothing about whether a customer they lack exists.
- **Chat memory is the caller's own** (decision 2): the user id sent is always ``str(user.id)``,
  the id CoPilot sends talon-analyst as ``X-Talon-User`` everywhere else; no request field names it.
- **Forgetting** (decision 1): only a customer's one-off review lessons and chat ``remember``
  lessons, never an investigation's own record or a durable lesson, and only one of the caller's own
  chat memories. CoPilot reads the drawer first and refuses unless talon-analyst says it is
  ``forgettable`` *and* its source is one of those two *and* it isn't durable; talon-analyst checks
  again. The actor sent is the CoPilot username. Every attempt, refused or not, is audited
  (``talon_memory.forget``).
- **Owners are checked here too** (defence in depth; talon-analyst checks them as well). A MemPalace
  id is ``drawer_<wing>_<room>_<24 hex>``. On a customer route it must fullmatch
  ``drawer_<customer_code>_<room>_<24 hex>``, the room one of the five lesson rooms or a name without
  ``_`` (``is_customer_drawer``), so ``drawer_acme_x_alerts_…`` asked as ``acme`` is refused ("x_alerts"
  is no room); on the chat routes it must be the chat-memory wing and the caller's own room
  (``is_own_chat_drawer``: ``user `` and the SHA-256 of their id). Refused before Talon is asked.
  Every answer must name its owner (``Owner``): a drawer, a list item and a forget (200 and 409) carry
  ``customer_code`` *and* the stored MemPalace ``wing``, both equal to the customer; a chat item
  ``user_id`` and the chat-memory ``wing``; a chat forget ``user_id``; stats ``customer_code``. talon-analyst
  echoes ``customer_code`` from the path, so the ``wing`` it read is what proves the drawer is this
  customer's. Missing or different: never shown (a list item is dropped, anything else is a 502) and
  a forget is unconfirmed.
- **Paths.** A drawer id or an asset name goes into talon-analyst's path, so it must be safe
  (``is_safe_drawer_id``: at most 255 characters, nothing unseen, no ``/``, ``\\``, ``%``, ``?``, ``#``
  or ``..``; ``ASSET``) and is percent-encoded by ``utils/memory_client``; a search goes in the
  query string only, and never with a cursor (a search doesn't page).
- **Answers.** Every field is copied one by one into ``schema/talon_memory.py``, bounded, with the
  connector's key and password and any URL user-info removed from every string, so an unknown field
  never reaches the browser and a malformed one is ``None``. Talon's own error text is never relayed
  except its one-line 400 reasons and a forget refusal's ``error``. Errors are ``{"detail", "code"}``:
  talon-analyst's 404 ``unknown customer`` is ``unknown_customer`` and ``drawer not found``
  ``not_found``; any other 404 is ``unsupported`` (a talon-analyst without the memory API, or its v2
  API off).

The request's database session is closed before Talon is asked.
"""
import hashlib
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Union

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.connectors.talon.schema.talon_memory import TalonChatMemory
from app.connectors.talon.schema.talon_memory import TalonChatMemoryItem
from app.connectors.talon.schema.talon_memory import TalonMemoryAsset
from app.connectors.talon.schema.talon_memory import TalonMemoryAssets
from app.connectors.talon.schema.talon_memory import TalonMemoryDrawer
from app.connectors.talon.schema.talon_memory import TalonMemoryFact
from app.connectors.talon.schema.talon_memory import TalonMemoryForgotten
from app.connectors.talon.schema.talon_memory import TalonMemoryGrowth
from app.connectors.talon.schema.talon_memory import TalonMemoryItem
from app.connectors.talon.schema.talon_memory import TalonMemoryPage
from app.connectors.talon.schema.talon_memory import TalonMemoryRooms
from app.connectors.talon.schema.talon_memory import TalonMemorySourceRef
from app.connectors.talon.schema.talon_memory import TalonMemorySources
from app.connectors.talon.schema.talon_memory import TalonMemoryStats
from app.connectors.talon.schema.talon_memory import TalonMemoryTimeline
from app.connectors.talon.services.identity import CHAT_MEMORY_WING
from app.connectors.talon.services.identity import is_talon_customer_code
from app.connectors.talon.services.talon_health import _SECRET_PARAM
from app.connectors.talon.services.talon_health import _URL_USERINFO
from app.connectors.talon.services.talon_health import _URL_USERPASS
from app.connectors.talon.services.talon_health import make_scrub
from app.connectors.talon.services.talon_health import strip_url
from app.connectors.talon.utils import memory_client
from app.connectors.talon.utils.memory_client import MemoryAnswer
from app.connectors.talon.utils.universal import refusal_reason
from app.connectors.talon.utils.v2_client import TALON_CONNECTOR
from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session
from app.db.universal_models import AiAnalystPalaceLesson
from app.db.universal_models import Customers
from app.middleware.customer_access import customer_access_handler

ROOMS = ("alerts", "false_positives", "threat_intel", "assets", "environment", "other")
#: The rooms the list can be filtered by (talon-analyst's ``browse.ROOMS``). A wing can hold other
#: rooms (counted under ``rooms.other``); they are listed, but not filterable.
ROOM_FILTERS = ROOMS[:-1]
SOURCES = ("investigation", "review_durable", "review_one_off", "chat_remember", "other")
#: What a user may forget from a customer's memory (decision 1): one-off review lessons and chat
#: ``remember`` lessons. Never an investigation's own record, never a durable lesson.
FORGETTABLE_SOURCES = frozenset({"review_one_off", "chat_remember"})

#: What a drawer id CoPilot puts in talon-analyst's path may never hold: a separator, an escape, a
#: query or fragment start. MemPalace's ids are ``drawer_<wing>_<room>_<24 hex>`` (a customer code,
#: or the chat wing, which holds spaces; a room is any MemPalace name).
_UNSAFE_ID = re.compile(r"[/\\%?#]")
#: An asset name (a host name, an IP address, a machine account) CoPilot will put in the path.
ASSET = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:$ -]{0,254}")
JOB_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")
#: An opaque page cursor (base64url, base64 or a plain token), sent in the query string.
CURSOR = re.compile(r"[A-Za-z0-9._~:=+/-]{1,8000}")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
MAX_ID = 255
MAX_QUERY = 200
DEFAULT_LIMIT = 50
MAX_LIMIT = 100
#: The chat-memory list's limits (talon-analyst ``browse.CHAT_DEFAULT_LIMIT``/``CHAT_MAX_LIMIT``).
CHAT_DEFAULT_LIMIT = 20
CHAT_MAX_LIMIT = 50
#: talon-analyst's customer routes reserve ``chat`` (its ``/v2/memory/chat/...`` routes are a user's
#: chat memory and are matched first), so CoPilot never asks for a customer called that.
RESERVED_CUSTOMER = "chat"
MAX_INSTANT = 40
MAX_GROWTH = 40
MAX_ASSETS = 500
MAX_FACTS = 1000
MAX_CHAT_ITEMS = CHAT_MAX_LIMIT
MAX_PREVIEW = 500
MAX_CONTENT = 100_000
MAX_REASON = 300
ALERT_ID_MAX = 2**63 - 1

# ── fixed texts (the frontend repeats OLD_TALON) ──────────────────────────────

OLD_TALON = "This Talon has no memory API: upgrade talon-analyst, and check that its v2 API (TALON_V2_API) is on"
INVALID_CUSTOMER = "customer_code is not a valid customer code"
NOT_ACCESSIBLE = "You don't have access to this customer"
UNKNOWN_CUSTOMER = "There is no such customer"
NO_MEMORY = "Talon has no memory for this customer yet"
RESERVED = "Talon keeps no memory under the customer code chat: it is reserved"
INVALID_REQUEST = "Talon refused the request as invalid"
PALACE_FAILED = "Talon's memory service (MemPalace) failed or timed out"
NO_PALACE = "Talon has no memory service (MemPalace) configured"
INVALID_DRAWER = "drawer_id is not a drawer id CoPilot can open"
NOT_THIS_CUSTOMERS = "drawer_id is not one of this customer's memories"
NOT_YOUR_CHAT = "drawer_id is not one of your chat memories"
INVALID_ASSET = "asset is not an asset name CoPilot can open"
UNKNOWN_DRAWER = "Talon has no such memory"
NO_CONNECTOR = "There is no Talon connector in CoPilot"
NOT_CONFIGURED = "The Talon connector has no URL in CoPilot"
KEY_REFUSED = "Talon refused CoPilot's API key"
UNAVAILABLE = "Talon's memory is unavailable right now; try again shortly"
NOT_JSON = "Talon's answer was not valid JSON"
WRONG_SHAPE = "Talon's answer was not in the expected shape"
FAILED = "Talon request failed"
NOT_FORGETTABLE = "This memory can't be forgotten: only one-off review lessons and chat remember lessons can"
FORGET_REFUSED = "Talon refused to forget this memory"
FORGET_UNCONFIRMED = "Talon did not confirm that the memory was forgotten"
FORGET_UNKNOWN = "Talon didn't answer in time, so the memory may or may not have been forgotten; refresh to check"

NO_STORE = {"Cache-Control": "no-store"}


def problem(status: int, detail: str, code: str) -> JSONResponse:
    """One of CoPilot's answers that isn't data: ``{"detail", "code"}``, never stored."""
    return JSONResponse({"detail": detail, "code": code}, status_code=status, headers=dict(NO_STORE))


# ── checks on what the browser sent ───────────────────────────────────────────


class BadQuery(ValueError):
    """A query parameter CoPilot refuses (400); the message is a fixed text."""


def _has_unseen(text: str) -> bool:
    """A control, format, surrogate or line/paragraph separator character."""
    return any(unicodedata.category(c) in ("Cc", "Cf", "Cs", "Zl", "Zp") for c in text)


def is_safe_drawer_id(value: Any) -> bool:
    """At most 255 characters, nothing unseen (control, format, separator), no leading or trailing
    space, and nothing that could leave the path segment: no ``/``, ``\\``, ``%``, ``?``, ``#`` or
    ``..``. Spaces inside are fine (chat-memory ids hold them); every segment is percent-encoded."""
    return (
        isinstance(value, str)
        and 0 < len(value) <= MAX_ID
        and value == value.strip()
        and not _has_unseen(value)
        and not _UNSAFE_ID.search(value)
        and ".." not in value
        and value != "."
    )


#: A user's chat-memory room: ``user `` and the SHA-256 hex of their user id (talon-analyst
#: ``chat_memory.room_for``), in the chat-memory wing.
CHAT_ROOM_PREFIX = "user "


#: The five lesson rooms (talon-analyst ``browse.ROOMS``); any other room in an id must have no ``_``.
_LESSON_ROOMS = "|".join(ROOM_FILTERS)
_OTHER_ROOM = "[A-Za-z0-9-]+"
_DRAWER_HASH = "[0-9a-f]{24}"


def is_customer_drawer(drawer_id: Any, customer_code: str) -> bool:
    """Whether ``drawer_id`` is ``drawer_<customer_code>_<room>_<24 hex>`` exactly (case-sensitive),
    the room one of the five lesson rooms or a name without ``_``. Defence in depth, before Talon is
    asked: ``drawer_acme_x_alerts_<hex>`` asked as ``acme`` would need the room ``x_alerts``, so it is
    refused. (A code that ends like a lesson room's start, ``acme_false`` vs ``acme`` +
    ``false_positives``, still reads both ways: the answer's ``wing`` settles it.)"""
    return is_safe_drawer_id(drawer_id) and bool(
        re.fullmatch(f"drawer_{re.escape(customer_code)}_(?:{_LESSON_ROOMS}|{_OTHER_ROOM})_{_DRAWER_HASH}", drawer_id),
    )


def is_chat_drawer(drawer_id: Any) -> bool:
    """Whether ``drawer_id`` is in the chat-memory wing (anyone's)."""
    return isinstance(drawer_id, str) and drawer_id.casefold().startswith(f"drawer_{CHAT_MEMORY_WING}_")


def chat_room(user_id: str) -> str:
    return CHAT_ROOM_PREFIX + hashlib.sha256(user_id.encode()).hexdigest()


def is_own_chat_drawer(drawer_id: Any, user_id: str) -> bool:
    """Whether ``drawer_id`` is ``drawer_<chat wing>_<user_id's own room>_<24 hex>`` exactly."""
    return is_safe_drawer_id(drawer_id) and bool(
        re.fullmatch(f"drawer_{re.escape(CHAT_MEMORY_WING)}_{re.escape(chat_room(user_id))}_{_DRAWER_HASH}", drawer_id),
    )


@dataclass(frozen=True)
class Owner:
    """Whose an answer must say it is: ``field`` (``customer_code`` or ``user_id``) equal to ``value``,
    and the stored MemPalace ``wing`` equal to ``wing`` (required unless ``wing_required`` is off, then
    checked only when present). Missing or different fails closed: never shown, never acted on."""

    field: str
    value: str
    wing: str
    wing_required: bool = True

    def owns(self, raw: Any) -> bool:
        if not isinstance(raw, Mapping) or raw.get(self.field) != self.value:
            return False
        if "wing" in raw:
            return raw["wing"] == self.wing
        return not self.wing_required


def customer_owner(customer_code: str) -> Owner:
    """A drawer, a list item, a forget's answer: ``customer_code`` and the wing it was read from."""
    return Owner("customer_code", customer_code, customer_code)


def chat_owner(user_id: str, *, wing_required: bool = True) -> Owner:
    """A chat item (``user_id`` and the chat-memory wing); a chat forget's answer carries no wing."""
    return Owner("user_id", user_id, CHAT_MEMORY_WING, wing_required)


def names_another(raw: Mapping[str, Any], owner: str) -> bool:
    """For answers without a required owner field (assets, a timeline): a ``customer_code`` or
    ``wing`` that is there and isn't ``owner`` (a null included)."""
    return any(key in raw and raw[key] != owner for key in ("customer_code", "wing"))


def is_safe_asset(value: Any) -> bool:
    return isinstance(value, str) and bool(ASSET.fullmatch(value)) and ".." not in value and not value.endswith(" ")


def _search(q: Optional[str]) -> Optional[str]:
    if q is None:
        return None
    text = q.strip()
    if not text:
        return None
    if len(text) > MAX_QUERY:
        raise BadQuery(f"q is too long (at most {MAX_QUERY} characters)")
    if _has_unseen(text):
        raise BadQuery("q holds a control character")
    return text


def _instant(name: str, value: Optional[str]) -> Optional[str]:
    """``since``/``before``: a UTC day or an ISO 8601 date-time, forwarded in a normal form."""
    if value is None or not value.strip():
        return None
    text = value.strip()
    problem_text = f"{name} must be a date (YYYY-MM-DD) or an ISO 8601 date-time"
    if len(text) > MAX_INSTANT:
        raise BadQuery(problem_text)
    try:
        if DAY.fullmatch(text):
            return date.fromisoformat(text).isoformat()
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text)
    except ValueError:
        raise BadQuery(problem_text) from None
    return parsed.isoformat()


def _limit(value: Optional[int]) -> int:
    if value is None:
        return DEFAULT_LIMIT
    if value < 1:
        raise BadQuery("limit must be at least 1")
    return min(value, MAX_LIMIT)


def _cursor(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    if not CURSOR.fullmatch(value):
        raise BadQuery("cursor is not a page cursor")
    return value


def _choice(name: str, value: Optional[str], allowed) -> Optional[str]:
    if value is None or value == "":
        return None
    if value not in allowed:
        raise BadQuery(f"{name} must be one of: {', '.join(allowed)}")
    return value


# ── the connector and the customer ────────────────────────────────────────────


@dataclass(frozen=True)
class Talon:
    """Where and how to ask talon-analyst, and the cleaners for what it answers."""

    url: str
    api_key: str
    scrub: Callable[[Any, int], Optional[str]]
    scrub_text: Callable[[Any, int], Optional[str]]


#: Every control character but tab and newline, and the C1 range.
_TEXT_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def make_text_scrub(secrets) -> Callable[[Any, int], Optional[str]]:
    """``make_scrub`` for multi-line text (a drawer's markdown): newlines and tabs are kept,
    every other control character dropped, the rest of the cleaning the same."""
    hidden = [s for s in secrets if isinstance(s, str) and len(s) >= 6]

    def scrub(value: Any, cap: int) -> Optional[str]:
        if not isinstance(value, str):
            return None
        text = value.replace("\r\n", "\n").replace("\r", "\n")
        text = _TEXT_CONTROL.sub("", text)
        text = _URL_USERPASS.sub(r"\1", text)
        text = _URL_USERINFO.sub(r"\1", text)
        text = _SECRET_PARAM.sub(r"\1=[redacted]", text)
        for secret in hidden:
            text = text.replace(secret, "[redacted]")
        if not text.strip():
            return None
        return text if len(text) <= cap else text[: cap - 1] + "…"

    return scrub


def _talon(attributes: Optional[Mapping[str, Any]]) -> Union[Talon, JSONResponse]:
    if attributes is None:
        return problem(502, NO_CONNECTOR, "unavailable")
    url = strip_url(attributes.get("connector_url"))
    if not url:
        return problem(502, NOT_CONFIGURED, "unavailable")
    api_key = str(attributes.get("connector_api_key") or "")
    secrets = [api_key, str(attributes.get("connector_password") or "")]
    return Talon(url=url, api_key=api_key, scrub=make_scrub(secrets), scrub_text=make_text_scrub(secrets))


async def _connector_then_release(session: AsyncSession) -> Union[Talon, JSONResponse]:
    """The connector, then the request's session closed: no pooled connection waits on Talon."""
    attributes = await get_connector_info_from_db(TALON_CONNECTOR, session)
    await session.close()
    return _talon(attributes)


async def customer_problem(user: User, session: AsyncSession, customer_code: str) -> Optional[JSONResponse]:
    """Grammar (400), then the caller's access (403), then an exact ``customers`` row (404)."""
    if not is_talon_customer_code(customer_code):
        return problem(400, INVALID_CUSTOMER, "invalid")
    if not await customer_access_handler.check_customer_access(user, customer_code, session):
        return problem(403, NOT_ACCESSIBLE, "forbidden")
    result = await session.execute(select(Customers.customer_code).where(Customers.customer_code == customer_code))
    if customer_code not in set(result.scalars().all()):
        return problem(404, UNKNOWN_CUSTOMER, "unknown_customer")
    if customer_code == RESERVED_CUSTOMER:
        # talon-analyst matches /v2/memory/chat/... as a user's chat memory first: never asked.
        return problem(404, RESERVED, "unknown_customer")
    return None


async def _for_customer(user: User, session: AsyncSession, customer_code: str) -> Union[Talon, JSONResponse]:
    refused = await customer_problem(user, session, customer_code)
    if refused is not None:
        await session.close()
        return refused
    return await _connector_then_release(session)


# ── talon-analyst's answers ───────────────────────────────────────────────────


def _detail(answer: MemoryAnswer) -> Optional[str]:
    """talon-analyst's one-line reason (``{"detail": …}``, any status), when it gave a short printable
    one. Used to tell its fixed texts apart, and relayed only for a 400 (cleaned)."""
    return refusal_reason(400, answer.body)


def _answer_problem(answer: MemoryAnswer, talon: Optional["Talon"] = None) -> Optional[JSONResponse]:
    """The answer as CoPilot's refusal, or None for a usable 2xx.

    talon-analyst's errors (``api/memory.py``): 400 a fixed reason (relayed, as ``invalid``), 404
    ``unknown customer`` or ``drawer not found`` (any other 404 is a Talon without the memory API, or
    with its v2 API off), 422 ``invalid request``, 502 ``MemPalace request failed``, 503 ``MemPalace is
    not configured``. A 401 is CoPilot's key, never the user's session, so it is a 502 (a 401 would
    log the user out)."""
    status = answer.status
    if status is None:
        return problem(504 if answer.timed_out else 502, answer.error or FAILED, "unavailable")
    if 200 <= status < 300:
        return problem(502, answer.error, "bad_answer") if answer.error else None
    detail = _detail(answer)
    if status == 404:
        if detail == "unknown customer":
            return problem(404, NO_MEMORY, "unknown_customer")
        if detail == "drawer not found":
            return problem(404, UNKNOWN_DRAWER, "not_found")
        return problem(404, OLD_TALON, "unsupported")
    if status == 400:
        reason = talon.scrub(detail, MAX_REASON) if talon is not None and detail else None
        return problem(400, f"Talon refused the request: {reason}" if reason else INVALID_REQUEST, "invalid")
    if status == 422:
        return problem(400, INVALID_REQUEST, "invalid")
    if status == 401:
        logger.error("Talon memory: talon-analyst refused CoPilot's API key (401)")
        return problem(502, KEY_REFUSED, "unavailable")
    if status == 503:
        return problem(503, NO_PALACE if detail == "MemPalace is not configured" else UNAVAILABLE, "unavailable")
    if status == 502 and detail == "MemPalace request failed":
        return problem(502, PALACE_FAILED, "unavailable")
    logger.error(f"Talon memory: talon-analyst answered {status}")
    return problem(502, FAILED, "unavailable")


def _json(answer: MemoryAnswer) -> Union[Any, JSONResponse]:
    try:
        return json.loads(answer.body)
    except (ValueError, RecursionError):  # ValueError includes UnicodeDecodeError
        return problem(502, NOT_JSON, "bad_answer")


def _parsed(answer: MemoryAnswer, parse: Callable[[Any], Any], talon: Optional["Talon"] = None):
    refused = _answer_problem(answer, talon)
    if refused is not None:
        return refused
    raw = _json(answer)
    if isinstance(raw, JSONResponse):
        return raw
    try:
        data = parse(raw)
    except Exception as e:  # noqa: BLE001 - a value no check foresaw: a wrong-shape answer, not a 500
        logger.warning(f"Talon memory: an answer could not be read ({type(e).__name__})")
        data = None
    if data is None:
        return problem(502, WRONG_SHAPE, "bad_answer")
    return data


def _count(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > ALERT_ID_MAX:
        return None
    return value


def _tally(value: Any) -> Optional[int]:
    """A count, or a list's length (the contract says counts; a list is read as one)."""
    if isinstance(value, list):
        return len(value)
    return _count(value)


def _bool(value: Any) -> Optional[bool]:
    return value if isinstance(value, bool) else None


def _enum(value: Any, allowed) -> str:
    return value if isinstance(value, str) and value in allowed else "other"


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _id(value: Any, scrub) -> Optional[str]:
    """An id as Talon sent it, or None: a string of at most ``MAX_ID`` characters with nothing
    unseen in it and nothing the scrubber would change (so never the key)."""
    if not isinstance(value, str) or not value or len(value) > MAX_ID or _has_unseen(value):
        return None
    return value if scrub(value, MAX_ID) == value else None


def _source_ref(raw: Any) -> Optional[TalonMemorySourceRef]:
    if not isinstance(raw, dict):
        return None
    job_id = raw.get("job_id")
    job_id = job_id if isinstance(job_id, str) and JOB_ID.fullmatch(job_id) else None
    alert_id = _count(raw.get("alert_id"))
    alert_id = alert_id if alert_id else None
    if job_id is None and alert_id is None:
        return None
    return TalonMemorySourceRef(job_id=job_id, alert_id=alert_id)


def _item_fields(raw: Any, talon: Talon, customer_code: str) -> Optional[Dict[str, Any]]:
    """A drawer's fields, or None: not a dict, no usable id, an id outside ``customer_code``'s wing,
    or an answer naming another customer or wing (fail closed)."""
    if not isinstance(raw, dict) or not customer_owner(customer_code).owns(raw):
        return None
    drawer_id = _id(raw.get("drawer_id"), talon.scrub)
    if drawer_id is None or not is_customer_drawer(drawer_id, customer_code):
        return None
    return {
        "drawer_id": drawer_id,
        "openable": True,
        "room": _enum(raw.get("room"), ROOMS),
        "room_name": talon.scrub(raw.get("room"), 128),
        "source": _enum(raw.get("source"), SOURCES),
        "source_ref": _source_ref(raw.get("source_ref")),
        "filed_at": talon.scrub(raw.get("filed_at"), 64),
        "durable": _bool(raw.get("durable")),
        "testing_hidden": _bool(raw.get("testing_hidden")),
        "visible_to_investigations": _bool(raw.get("visible_to_investigations")),
        "preview": talon.scrub(raw.get("preview"), MAX_PREVIEW),
    }


def parse_stats(raw: Any, talon: Talon, customer_code: str) -> Optional[TalonMemoryStats]:
    if not isinstance(raw, dict):
        return None
    if not Owner("customer_code", customer_code, customer_code, wing_required=False).owns(raw):
        return None  # another customer's answer, or one that doesn't say whose, is never shown
    rooms = _dict(raw.get("rooms"))
    sources = _dict(raw.get("sources"))
    growth: List[TalonMemoryGrowth] = []
    seen = set()
    for day in raw.get("growth")[:MAX_GROWTH] if isinstance(raw.get("growth"), list) else []:
        when = day.get("date") if isinstance(day, dict) else None
        if isinstance(when, str) and DAY.fullmatch(when) and when not in seen:
            seen.add(when)
            growth.append(TalonMemoryGrowth(date=when, filed=_count(day.get("filed"))))
    return TalonMemoryStats(
        customer_code=customer_code,
        total=_count(raw.get("total")),
        checked_at=talon.scrub(raw.get("checked_at"), 64),
        rooms=TalonMemoryRooms(**{name: _count(rooms.get(name)) for name in ROOMS}),
        sources=TalonMemorySources(**{name: _count(sources.get(name)) for name in SOURCES}),
        testing_hidden=_count(raw.get("testing_hidden")),
        growth=growth,
        complete=_bool(raw.get("complete")),
    )


def parse_page(raw: Any, talon: Talon, customer_code: str) -> Optional[TalonMemoryPage]:
    if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
        return None
    items: List[TalonMemoryItem] = []
    seen = set()
    dropped = 0
    for entry in raw["items"]:
        if len(items) >= MAX_LIMIT:
            break
        fields = _item_fields(entry, talon, customer_code)
        if fields is None:
            dropped += 1
        elif fields["drawer_id"] not in seen:
            seen.add(fields["drawer_id"])
            items.append(TalonMemoryItem(**fields))
    if dropped:
        logger.warning(f"Talon memory: {dropped} drawer(s) not shown (unusable, or not this customer's)")
    cursor = raw.get("next_cursor")
    return TalonMemoryPage(items=items, next_cursor=cursor if isinstance(cursor, str) and CURSOR.fullmatch(cursor) else None)


def parse_drawer(raw: Any, talon: Talon, customer_code: str, drawer_id: str) -> Optional[TalonMemoryDrawer]:
    fields = _item_fields(raw, talon, customer_code)
    if fields is None or fields["drawer_id"] != drawer_id:
        return None
    return TalonMemoryDrawer(
        **fields,
        content=talon.scrub_text(raw.get("content"), MAX_CONTENT),
        forgettable=raw.get("forgettable") is True,
        why_not_forgettable=talon.scrub(raw.get("why_not_forgettable"), MAX_REASON),
        why_hidden=talon.scrub(raw.get("why_hidden"), MAX_REASON),
    )


def parse_assets(raw: Any, talon: Talon, customer_code: str) -> Optional[TalonMemoryAssets]:
    if not isinstance(raw, dict) or not isinstance(raw.get("items"), list) or names_another(raw, customer_code):
        return None
    items: List[TalonMemoryAsset] = []
    seen = set()
    for entry in raw["items"]:
        if len(items) >= MAX_ASSETS:
            break
        if not isinstance(entry, dict) or names_another(entry, customer_code):
            continue
        name = _id(entry.get("asset"), talon.scrub)
        if name is None or name in seen:
            continue
        seen.add(name)
        items.append(
            TalonMemoryAsset(
                asset=name,
                openable=is_safe_asset(name),
                alerts=_tally(entry.get("alerts")),
                iocs=_tally(entry.get("iocs")),
                last_seen=talon.scrub(entry.get("last_seen"), 64),
            ),
        )
    return TalonMemoryAssets(items=items)


def parse_timeline(raw: Any, talon: Talon, customer_code: str, asset: str) -> Optional[TalonMemoryTimeline]:
    if not isinstance(raw, dict) or not isinstance(raw.get("facts"), list) or names_another(raw, customer_code):
        return None
    facts = []
    for fact in raw["facts"][:MAX_FACTS]:
        if not isinstance(fact, dict):
            continue
        row = TalonMemoryFact(
            subject=talon.scrub(fact.get("subject"), MAX_PREVIEW),
            predicate=talon.scrub(fact.get("predicate"), MAX_PREVIEW),
            object=talon.scrub(fact.get("object"), MAX_PREVIEW),
            valid_from=talon.scrub(fact.get("valid_from"), 64),
            valid_to=talon.scrub(fact.get("valid_to"), 64),
        )
        if row.subject or row.predicate or row.object:
            facts.append(row)
    # talon-analyst answers the asset as it shows it (a token asked for comes back restored).
    return TalonMemoryTimeline(asset=talon.scrub(raw.get("asset"), MAX_ID) or asset, facts=facts)


def _thread_id(value: Any) -> Optional[str]:
    if not isinstance(value, str) or len(value) != 36:
        return None
    try:
        return str(uuid.UUID(value))
    except ValueError:
        return None


def parse_chat(raw: Any, talon: Talon, user_id: str) -> Optional[TalonChatMemory]:
    """The caller's chat memory. An item outside the caller's own room of the chat-memory wing, or
    naming another wing, is never shown (fail closed: another user's memory must not reach them)."""
    if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
        return None
    items: List[TalonChatMemoryItem] = []
    seen = set()
    dropped = 0
    for entry in raw["items"]:
        if len(items) >= MAX_CHAT_ITEMS:
            break
        if not isinstance(entry, dict) or not chat_owner(user_id).owns(entry):
            dropped += 1
            continue
        drawer_id = _id(entry.get("drawer_id"), talon.scrub)
        if drawer_id is None or not is_own_chat_drawer(drawer_id, user_id):
            dropped += 1
            continue
        if drawer_id in seen:
            continue
        seen.add(drawer_id)
        items.append(
            TalonChatMemoryItem(
                drawer_id=drawer_id,
                openable=True,
                filed_at=talon.scrub(entry.get("filed_at"), 64),
                preview=talon.scrub(entry.get("preview"), MAX_PREVIEW),
                thread_id=_thread_id(entry.get("thread_id")),
            ),
        )
    if dropped:
        logger.warning(f"Talon memory: {dropped} chat memory item(s) not shown to user {user_id} (unusable, or not theirs)")
    return TalonChatMemory(items=items)


def _forgotten(raw: Any, drawer_id: str, owner: Owner) -> Optional[TalonMemoryForgotten]:
    """A 2xx forget that says so, for this drawer and naming its owner."""
    if not isinstance(raw, dict) or raw.get("success") is not True or not owner.owns(raw):
        return None
    if raw.get("drawer_id") != drawer_id:
        return None
    return TalonMemoryForgotten(drawer_id=drawer_id)


async def _ask(talon: Talon, method: str, segments: List[str], **kwargs) -> MemoryAnswer:
    return await memory_client.request(method, talon.url, segments, api_key=talon.api_key, **kwargs)


# ── the routes' work ──────────────────────────────────────────────────────────


def _customer_drawer_problem(customer_code: str, drawer_id: str) -> Optional[JSONResponse]:
    """A drawer id CoPilot won't send for ``customer_code``: unsafe for a path (400), or not in the
    customer's wing (a chat-memory id, another customer's, an unknown room; 400). Checked before
    Talon is asked, so talon-analyst isn't the only thing binding the id to the customer."""
    if not is_safe_drawer_id(drawer_id):
        return problem(400, INVALID_DRAWER, "invalid")
    if is_chat_drawer(drawer_id) or not is_customer_drawer(drawer_id, customer_code):
        return problem(400, NOT_THIS_CUSTOMERS, "invalid")
    return None


async def get_stats(user: User, session: AsyncSession, customer_code: str):
    talon = await _for_customer(user, session, customer_code)
    if isinstance(talon, JSONResponse):
        return talon
    answer = await _ask(talon, "GET", [customer_code, "stats"], timeout=memory_client.STATS_SECONDS)
    return _parsed(answer, lambda raw: parse_stats(raw, talon, customer_code), talon)


async def list_drawers(
    user: User,
    session: AsyncSession,
    customer_code: str,
    *,
    room: Optional[str] = None,
    source: Optional[str] = None,
    q: Optional[str] = None,
    since: Optional[str] = None,
    before: Optional[str] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
):
    try:
        params = {
            "room": _choice("room", room, ROOM_FILTERS),
            "source": _choice("source", source, SOURCES),
            "q": _search(q),
            "since": _instant("since", since),
            "before": _instant("before", before),
            "limit": _limit(limit),
            "cursor": _cursor(cursor),
        }
        if params["q"] and params["cursor"]:
            raise BadQuery("a search has no cursor: it shows its best matches only")
    except BadQuery as e:
        await session.close()
        return problem(400, str(e), "invalid")
    talon = await _for_customer(user, session, customer_code)
    if isinstance(talon, JSONResponse):
        return talon
    answer = await _ask(talon, "GET", [customer_code, "drawers"], params=params, timeout=memory_client.SLOW_SECONDS)
    return _parsed(answer, lambda raw: parse_page(raw, talon, customer_code), talon)


async def get_drawer(user: User, session: AsyncSession, customer_code: str, drawer_id: str):
    refused = _customer_drawer_problem(customer_code, drawer_id)
    if refused is not None:
        await session.close()
        return refused
    talon = await _for_customer(user, session, customer_code)
    if isinstance(talon, JSONResponse):
        return talon
    answer = await _ask(talon, "GET", [customer_code, "drawers", drawer_id], timeout=memory_client.SLOW_SECONDS)
    return _parsed(
        answer,
        lambda raw: parse_drawer(raw, talon, customer_code, drawer_id),
        talon,
    )


async def list_assets(user: User, session: AsyncSession, customer_code: str, *, q: Optional[str] = None, limit: Optional[int] = None):
    try:
        params = {"q": _search(q), "limit": _limit(limit)}
    except BadQuery as e:
        await session.close()
        return problem(400, str(e), "invalid")
    talon = await _for_customer(user, session, customer_code)
    if isinstance(talon, JSONResponse):
        return talon
    answer = await _ask(talon, "GET", [customer_code, "assets"], params=params)
    return _parsed(answer, lambda raw: parse_assets(raw, talon, customer_code), talon)


async def asset_timeline(user: User, session: AsyncSession, customer_code: str, asset: str):
    if not is_safe_asset(asset):
        await session.close()
        return problem(400, INVALID_ASSET, "invalid")
    talon = await _for_customer(user, session, customer_code)
    if isinstance(talon, JSONResponse):
        return talon
    answer = await _ask(talon, "GET", [customer_code, "assets", asset, "timeline"], timeout=memory_client.SLOW_SECONDS)
    return _parsed(answer, lambda raw: parse_timeline(raw, talon, customer_code, asset), talon)


async def list_chat_memory(user: User, session: AsyncSession, limit: Optional[int] = None):
    if limit is not None and limit < 1:
        await session.close()
        return problem(400, "limit must be at least 1", "invalid")
    talon = await _connector_then_release(session)
    if isinstance(talon, JSONResponse):
        return talon
    # Always the caller's own id (decision 2): the route takes none from the request.
    count = CHAT_DEFAULT_LIMIT if limit is None else min(limit, CHAT_MAX_LIMIT)
    answer = await _ask(talon, "GET", ["chat", str(user.id)], params={"limit": count})
    return _parsed(answer, lambda raw: parse_chat(raw, talon, str(user.id)), talon)


# ── forgetting ────────────────────────────────────────────────────────────────


#: ``audit_log.customer_code``'s length.
AUDIT_CUSTOMER_MAX = 50


async def _record(audit: Mapping[str, Any], *, result, details: str, old_value: Optional[dict] = None) -> None:
    """One ``talon_memory.forget`` row. A customer code too long for the column is named in the
    details instead (``long_customer_code``)."""
    fields = dict(audit)
    long_code = fields.pop("long_customer_code", None)
    if long_code:
        details = f"customer {long_code}: {details}"
    await record_audit_event(**fields, result=result, old_value=old_value, details=details)


async def expire_lesson_rows(customer_code: str, drawer_id: str) -> None:
    """After a confirmed forget of a one-off review lesson: CoPilot's ``ai_analyst_palace_lesson`` rows
    for it go ``expired`` with ``expired_at``, as the sweeper leaves the ones it forgets, so the palace
    digest no longer counts it live. Best effort, in a session of its own."""
    try:
        async with get_db_session() as session:
            await session.execute(
                update(AiAnalystPalaceLesson)
                .where(
                    AiAnalystPalaceLesson.drawer_id == drawer_id,
                    AiAnalystPalaceLesson.customer_code == customer_code,
                    AiAnalystPalaceLesson.durability == "one_off",
                    AiAnalystPalaceLesson.status == "ingested",
                )
                .values(status="expired", expired_at=datetime.utcnow()),
            )
            await session.commit()
    except Exception as e:  # noqa: BLE001 - the forget happened; the row is a mirror
        logger.error(f"Talon memory: could not mark the lesson rows of a forgotten drawer expired ({type(e).__name__})")


def _audit_id(drawer_id: Any) -> str:
    """The drawer id for the audit row: as sent when it is one CoPilot could use, else a marker
    (a refused id is never written as the caller typed it)."""
    return drawer_id if is_safe_drawer_id(drawer_id) else "<invalid drawer id>"


def _refusal_text(answer: MemoryAnswer, talon: Talon, owner: Owner) -> str:
    """A forget refusal's own short line from talon-analyst (its ``error``), cleaned, when the 409
    names the owner asked about; else ours."""
    try:
        body = json.loads(answer.body)
    except (ValueError, RecursionError):
        body = None
    if not owner.owns(body):
        return FORGET_REFUSED
    reason = refusal_reason(answer.status or 0, answer.body)
    return talon.scrub(reason, MAX_REASON) or FORGET_REFUSED


async def _delete(
    talon: Talon,
    segments: List[str],
    drawer_id: str,
    user: User,
    audit: Dict[str, Any],
    owner: Owner,
    old_value: Optional[dict] = None,
    on_forgotten: Optional[Callable[[], Awaitable[None]]] = None,
):
    """The DELETE itself, audited whatever happens. A DELETE Talon didn't answer in time may have
    happened: audited as ``unknown``, never as not forgotten."""

    async def failed(response: JSONResponse, details: str) -> JSONResponse:
        await _record(audit, result=AuditResult.FAILURE, old_value=old_value, details=details)
        return response

    answer = await _ask(talon, "DELETE", segments, json_body={"actor": user.username}, timeout=memory_client.SLOW_SECONDS)
    status = answer.status
    if answer.timed_out:
        await _record(
            audit,
            result=AuditResult.UNKNOWN,
            old_value=old_value,
            details=f"Talon memory forget: outcome unknown ({answer.error}); it may have been forgotten",
        )
        return problem(504, FORGET_UNKNOWN, "unavailable")
    if status is not None and 200 <= status < 300:
        raw = _json(answer) if not answer.error else None
        done = None if isinstance(raw, JSONResponse) else _forgotten(raw, drawer_id, owner)
        if done is None and isinstance(raw, dict) and raw.get("success") is False:
            return await failed(problem(502, FORGET_UNCONFIRMED, "bad_answer"), "Talon answered 2xx with success false")
        # talon-analyst's 2xx means it was forgotten, whatever its body: audited as done.
        await _record(
            audit,
            result=AuditResult.SUCCESS,
            old_value=old_value,
            details="Talon memory forgotten" + ("" if done else "; talon-analyst's answer was unreadable, so it is unconfirmed"),
        )
        if done is not None and on_forgotten is not None:
            await on_forgotten()
        return done if done is not None else problem(502, FORGET_UNCONFIRMED, "bad_answer")
    if status == 409:
        reason = _refusal_text(answer, talon, owner)
        return await failed(problem(409, reason, "refused"), f"Talon refused the forget (409): {reason}")
    response = _answer_problem(answer, talon) or problem(502, FAILED, "unavailable")
    return await failed(response, f"Talon memory not forgotten: talon-analyst answered {status if status is not None else 'nothing'}")


async def forget_drawer(user: User, session: AsyncSession, customer_code: str, drawer_id: str, request: Optional[Request] = None):
    """Forget one of a customer's memories, if it is one a user may forget (decision 1)."""
    audit: Dict[str, Any] = {
        "action": AuditAction.TALON_MEMORY_FORGET,
        "actor_user_id": user.id,
        "actor_username": user.username,
        # audit_log.customer_code holds 50 characters: a longer code goes in the details instead.
        "customer_code": customer_code if is_talon_customer_code(customer_code) and len(customer_code) <= AUDIT_CUSTOMER_MAX else None,
        "entity_type": "talon_memory",
        "entity_id": _audit_id(drawer_id),
        "request": request,
    }

    if audit["customer_code"] is None and is_talon_customer_code(customer_code):
        audit["long_customer_code"] = customer_code

    async def failed(response: JSONResponse, details: str, old_value: Optional[dict] = None) -> JSONResponse:
        await _record(audit, result=AuditResult.FAILURE, old_value=old_value, details=details)
        return response

    refused = _customer_drawer_problem(customer_code, drawer_id)
    if refused is not None:
        await session.close()
        reason = json.loads(refused.body)["detail"]
        return await failed(refused, f"Talon memory not forgotten: {reason}")
    talon = await _for_customer(user, session, customer_code)
    if isinstance(talon, JSONResponse):
        reason = json.loads(talon.body)["detail"]
        return await failed(talon, f"Talon memory not forgotten: {reason}")

    # Read it first: CoPilot applies decision 1 itself, and the audit row says what was forgotten.
    drawer = _parsed(
        await _ask(talon, "GET", [customer_code, "drawers", drawer_id], timeout=memory_client.SLOW_SECONDS),
        lambda raw: parse_drawer(raw, talon, customer_code, drawer_id),
        talon,
    )
    if isinstance(drawer, JSONResponse):
        reason = json.loads(drawer.body)["detail"]
        return await failed(drawer, f"Talon memory not forgotten: reading it failed ({reason})")
    old_value = {"room": drawer.room, "source": drawer.source, "durable": drawer.durable, "filed_at": drawer.filed_at}
    if not drawer.forgettable or drawer.source not in FORGETTABLE_SOURCES or drawer.durable is True:
        return await failed(
            problem(409, NOT_FORGETTABLE, "refused"),
            f"Talon memory not forgotten: CoPilot refused a {drawer.source} memory"
            + (" (durable)" if drawer.durable else "")
            + ("" if drawer.forgettable else " that Talon says isn't forgettable"),
            old_value,
        )
    return await _delete(
        talon,
        [customer_code, "drawers", drawer_id],
        drawer_id,
        user,
        audit,
        customer_owner(customer_code),
        old_value,
        on_forgotten=(lambda: expire_lesson_rows(customer_code, drawer_id)) if drawer.source == "review_one_off" else None,
    )


async def forget_chat_memory(user: User, session: AsyncSession, drawer_id: str, request: Optional[Request] = None):
    """Forget one of the caller's own chat memories (decision 2: only ever their own)."""
    audit: Dict[str, Any] = {
        "action": AuditAction.TALON_MEMORY_FORGET,
        "actor_user_id": user.id,
        "actor_username": user.username,
        "entity_type": "talon_chat_memory",
        "entity_id": _audit_id(drawer_id),
        "request": request,
    }
    if not is_safe_drawer_id(drawer_id) or not is_own_chat_drawer(drawer_id, str(user.id)):
        # A customer's drawer, another user's chat memory, or an unsafe id: never sent to Talon.
        await session.close()
        detail = NOT_YOUR_CHAT if is_safe_drawer_id(drawer_id) else INVALID_DRAWER
        await _record(audit, result=AuditResult.FAILURE, details=f"Chat memory not forgotten: {detail}")
        return problem(400, detail, "invalid")
    talon = await _connector_then_release(session)
    if isinstance(talon, JSONResponse):
        reason = json.loads(talon.body)["detail"]
        await _record(audit, result=AuditResult.FAILURE, details=f"Chat memory not forgotten: {reason}")
        return talon
    return await _delete(
        talon,
        ["chat", str(user.id), drawer_id],
        drawer_id,
        user,
        audit,
        chat_owner(str(user.id), wing_required=False),
    )
