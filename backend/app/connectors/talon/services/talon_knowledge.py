"""The customer page's "What Talon sees" panel (``/api/talon/knowledge/{customer_code}``, talon-analyst
D98, K1-2): what talon-analyst has measured of a customer's log sources, relayed from its
``/v2/knowledge`` API. Read-only, and all of it comes from a daily job, so nothing here is a person's.

The Memory tab's rulebook (``services/talon_memory.py``) applies, because talon-analyst trusts CoPilot
here too: it is asked with the connector's API key alone, no identity headers.

- **Tenancy, before Talon is asked** (``customer_problem``, shared with Memory): the code matches
  talon-analyst's grammar, the caller may see it, and it is a real ``customers`` row exactly as
  written, in that order, so a scoped analyst learns nothing about whether a customer they lack
  exists. Memory's reserved ``chat`` isn't reserved here: ``/v2/knowledge/`` has no chat routes.
- **The request's database session is closed before Talon is asked.**
- **The answer must name its owner:** a ``customer_code`` that isn't the one asked for, a missing one
  included, is a 502 and never shown. So is an unknown ``status``.
- **Answers** are copied field by field into ``schema/talon_knowledge.py``. Statuses, categories and
  roles are allowlisted. A pattern or a field name is taken whole or dropped (``_id``: bounded, nothing
  unseen, nothing the scrubber would change, so never the connector's key or password or URL
  user-info), never cut or shown redacted, because a part of a name would read as another name. A
  status other than ``ok`` carries nothing else, whatever Talon sent with it.
- **Errors** are ``{"detail", "code"}`` with fixed texts, and Talon's own text is never relayed (unlike
  Memory, there is no reason of Talon's worth showing). Any 404 from Talon is ``unsupported``: a
  talon-analyst without this route, or its ``TALON_V2_API`` off. A customer talon-analyst has never
  heard of is a 200 ``no_sources``. A 401 is CoPilot's key, never the user's session, so it is a 502
  (a 401 would log the user out).

The deadline is the client's default of 8 s: talon-analyst gives this read 6 s (``api/knowledge.py``),
so a slow read is its fixed 502, not our timeout.
"""
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence

from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.connectors.talon.schema.talon_knowledge import TalonKnowledge
from app.connectors.talon.schema.talon_knowledge import TalonKnowledgeCoverage
from app.connectors.talon.schema.talon_knowledge import TalonKnowledgeSource
from app.connectors.talon.services.talon_memory import FAILED
from app.connectors.talon.services.talon_memory import KEY_REFUSED
from app.connectors.talon.services.talon_memory import MAX_ID
from app.connectors.talon.services.talon_memory import WRONG_SHAPE
from app.connectors.talon.services.talon_memory import BadQuery
from app.connectors.talon.services.talon_memory import Talon
from app.connectors.talon.services.talon_memory import _bool
from app.connectors.talon.services.talon_memory import _connector_then_release
from app.connectors.talon.services.talon_memory import _count
from app.connectors.talon.services.talon_memory import _id
from app.connectors.talon.services.talon_memory import _instant
from app.connectors.talon.services.talon_memory import _parsed
from app.connectors.talon.services.talon_memory import customer_problem
from app.connectors.talon.services.talon_memory import problem
from app.connectors.talon.utils import memory_client
from app.connectors.talon.utils.memory_client import MemoryAnswer

PREFIX = "/v2/knowledge"
STATUSES = ("ok", "no_sources", "no_profile", "no_tenant_map")
CATEGORIES = ("endpoint", "identity", "email", "network", "cloud", "waf")
ROLES = (
    "src_ip",
    "dst_ip",
    "user",
    "host",
    "process",
    "command_line",
    "file_hash",
    "file_path",
    "url",
    "domain",
    "email",
    "action",
)
COVERAGE_STATES = ("available", "degraded", "unavailable")
MAX_SOURCES = 200
MAX_NOT_MEASURED = 200
MAX_FIELD = 128
MAX_FIELDS_PER_ROLE = 3

# ── fixed texts ───────────────────────────────────────────────────────────────

OLD_TALON = "This Talon has no knowledge API: upgrade talon-analyst, and check that its v2 API (TALON_V2_API) is on"
REFUSED_CODE = "Talon refused this customer code"
READ_FAILED = "Talon couldn't read what it has measured; try again shortly"
NO_ANSWER = "Talon didn't answer in time; try again shortly"
UNREACHABLE = "Talon could not be reached"


def _refusal(answer: MemoryAnswer, talon: Optional[Talon] = None) -> Optional[JSONResponse]:
    """The answer as CoPilot's refusal, or None for a usable 2xx. Nothing of Talon's is relayed."""
    status = answer.status
    if status is None:
        return problem(504, NO_ANSWER, "unavailable") if answer.timed_out else problem(502, UNREACHABLE, "unavailable")
    if 200 <= status < 300:
        return problem(502, WRONG_SHAPE, "bad_answer") if answer.error else None
    if status == 404:
        return problem(404, OLD_TALON, "unsupported")
    if status in (400, 422):
        return problem(400, REFUSED_CODE, "invalid")
    if status == 401:
        logger.error("Talon knowledge: talon-analyst refused CoPilot's API key (401)")
        return problem(502, KEY_REFUSED, "unavailable")
    if status == 502:
        return problem(502, READ_FAILED, "unavailable")
    logger.error(f"Talon knowledge: talon-analyst answered {status}")
    return problem(502, FAILED, "unavailable")


def _moment(value: Any) -> Optional[str]:
    """An ISO 8601 date-time in a normal form, or None: the panel formats it, so it must parse."""
    if not isinstance(value, str):
        return None
    try:
        return _instant("measured_at", value)
    except BadQuery:
        return None


def _allowed(value: Any, allowed: Sequence[str]) -> List[str]:
    """The entries of a list that are in ``allowed``, once each, in Talon's order."""
    kept: List[str] = []
    for entry in value if isinstance(value, list) else []:
        if isinstance(entry, str) and entry in allowed and entry not in kept:
            kept.append(entry)
    return kept


def _names(value: Any, scrub, cap: int, limit: int) -> List[str]:
    """At most ``limit`` different names of a list, each taken whole or dropped (``_id``)."""
    kept: List[str] = []
    for entry in value if isinstance(value, list) else []:
        if len(kept) >= limit:
            break
        name = _id(entry, scrub, cap)
        if name is not None and name not in kept:
            kept.append(name)
    return kept


def _coverage(raw: Any) -> Optional[TalonKnowledgeCoverage]:
    if not isinstance(raw, dict):
        return None
    return TalonKnowledgeCoverage(**{state: _allowed(raw.get(state), CATEGORIES) for state in COVERAGE_STATES})


def _fields(raw: Any, scrub) -> Dict[str, List[str]]:
    if not isinstance(raw, dict):
        return {}
    names = {role: _names(raw.get(role), scrub, MAX_FIELD, MAX_FIELDS_PER_ROLE) for role in ROLES}
    return {role: fields for role, fields in names.items() if fields}


def _source(raw: Any, scrub) -> Optional[TalonKnowledgeSource]:
    pattern = _id(raw.get("pattern"), scrub) if isinstance(raw, dict) else None
    if pattern is None:
        return None
    return TalonKnowledgeSource(
        pattern=pattern,
        categories=_allowed(raw.get("categories"), CATEGORIES),
        events=_count(raw.get("events")),
        degraded=_bool(raw.get("degraded")),
        measured_at=_moment(raw.get("measured_at")),
        fields=_fields(raw.get("fields"), scrub),
    )


def _sources(raw: Any, scrub) -> List[TalonKnowledgeSource]:
    sources: List[TalonKnowledgeSource] = []
    seen = set()
    dropped = 0
    for entry in raw if isinstance(raw, list) else []:
        if len(sources) >= MAX_SOURCES:
            break
        source = _source(entry, scrub)
        if source is None:
            dropped += 1
        elif source.pattern not in seen:
            seen.add(source.pattern)
            sources.append(source)
    if dropped:
        logger.warning(f"Talon knowledge: {dropped} log source(s) not shown (unusable)")
    return sources


def parse_knowledge(raw: Any, talon: Talon, customer_code: str) -> Optional[TalonKnowledge]:
    """The answer, or None: not an object, a status CoPilot doesn't know, or not this customer's."""
    if not isinstance(raw, dict) or raw.get("status") not in STATUSES:
        return None
    if raw.get("customer_code") != customer_code:
        logger.warning("Talon knowledge: an answer that isn't the customer's asked for was not shown")
        return None
    if raw["status"] != "ok":
        return TalonKnowledge(customer_code=customer_code, status=raw["status"])
    return TalonKnowledge(
        customer_code=customer_code,
        status="ok",
        measured_at=_moment(raw.get("measured_at")),
        field_days=_count(raw.get("field_days")),
        event_days=_count(raw.get("event_days")),
        coverage=_coverage(raw.get("coverage")),
        sources=_sources(raw.get("sources"), talon.scrub),
        not_measured=_names(raw.get("not_measured"), talon.scrub, MAX_ID, MAX_NOT_MEASURED),
    )


async def what_talon_sees(user: User, session: AsyncSession, customer_code: str):
    refused = await customer_problem(user, session, customer_code)
    if refused is not None:
        await session.close()
        return refused
    talon = await _connector_then_release(session)
    if isinstance(talon, JSONResponse):
        return talon
    answer = await memory_client.request("GET", talon.url, [customer_code], api_key=talon.api_key, prefix=PREFIX)
    return _parsed(answer, lambda raw: parse_knowledge(raw, talon, customer_code), talon, refusal=_refusal)
