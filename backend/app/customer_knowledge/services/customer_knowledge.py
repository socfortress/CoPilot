"""What SOC analysts record about a customer (talon-analyst SPEC D98, plan K1).

Facts that help an investigation read an alert: which range is a server zone, which public space is
the customer's, what a host is for, what activity to expect. talon-analyst reads ``approved`` rows
over its read-only MySQL user and matches them to each alert in code. A fact never decides a verdict,
so the risk here is a wrong fact, and these rules keep the entries narrow:

- **Ranges parse, and aren't absurdly wide.** A public range wider than /16 (IPv4) or /48 (IPv6) is
  refused, the numbers the WAF blocks at, and a private one wider than /8 or /16. An address is
  stored in its canonical form, an IPv4-mapped one as IPv4.
- **A public range holds public addresses.** Private ones belong in a zone, and space no host of a
  customer sits on (multicast, loopback, NAT64, 6to4) is in neither.
- **Expected activity is bounded:** it names a host or a source range, and its window is at most
  ``EXPECTED_MAX_DAYS`` long, starts no earlier than that before now and ends no later than that
  after. talon-analyst shows it only when all of it matches.
- **Text is clean.** No control or invisible characters and no angle brackets, so a fact can't break
  out of the block it is rendered in, and hosts and accounts hold no wildcards: they match exactly.
- **A fact is recorded once.** The same range, or the same role on a host, is refused within a
  customer, and a customer holds at most ``MAX_FACTS``.
- **Public space another customer also records is a warning, never a refusal.** It doesn't say who.
  The warning counts only customers the caller can read, as saving a range to see whether it warns
  would otherwise map other tenants' space. Every overlap is in the audit row, which only admins read.
- **Domains, tenants and accounts (plan K1-7)** are checked in ``domains.py``: a domain isn't a shared
  suffix or a public mail provider's, a tenant id has its provider's form, and an account is an
  identifier, never a display name. A domain or a tenant another customer also records is the same
  kind of warning as overlapping public space.
- **A business profile (plan K1-8)** is checked in ``business.py``: an IANA time zone, a working week
  with an SLA calendar's shape and rules or round-the-clock operation, and ISO country codes. A
  customer has one: a second is refused as a duplicate, so the SOC edits the one it has.

Every write is audited with the old and new values, straight after its commit. A save that changes
nothing writes nothing. ``status`` and ``source`` are set here: every fact is ``approved`` and ``soc``
until customer editing brings its approval queue.
"""

import ipaddress
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Set
from typing import Union

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.customer_knowledge.schema.customer_knowledge import KINDS
from app.customer_knowledge.schema.customer_knowledge import NAME_MAX
from app.customer_knowledge.schema.customer_knowledge import KnowledgeItem
from app.customer_knowledge.schema.customer_knowledge import KnowledgeItemBody
from app.customer_knowledge.schema.customer_knowledge import KnowledgeItemUpdate
from app.customer_knowledge.services.business import BusinessProblem
from app.customer_knowledge.services.business import checked_countries
from app.customer_knowledge.services.business import checked_time_zone
from app.customer_knowledge.services.business import checked_week
from app.customer_knowledge.services.domains import BAD_DOMAIN
from app.customer_knowledge.services.domains import DomainProblem
from app.customer_knowledge.services.domains import checked_domain
from app.customer_knowledge.services.domains import checked_identifier
from app.customer_knowledge.services.domains import checked_tenant
from app.customer_knowledge.services.domains import related
from app.db.universal_models import CustomerKnowledgeItem
from app.db.universal_models import Customers
from app.middleware.customer_access import customer_access_handler
from app.time_utils import now_utc
from app.time_utils import to_naive_utc

Network = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]

APPROVED = "approved"
SOC = "soc"
EXPECTED_MAX_DAYS = 90
MAX_FACTS = 1000
#: The widest range accepted. Public: the WAF's block limits. Private: a whole RFC 1918 block.
PUBLIC_MIN_PREFIX = {4: 16, 6: 48}
PRIVATE_MIN_PREFIX = {4: 8, 6: 16}

_MAPPED = ipaddress.ip_network("::ffff:0:0/96")
#: No host of a customer sits here, in a zone or a public range.
_UNUSABLE = tuple(ipaddress.ip_network(n) for n in ("0.0.0.0/8", "127.0.0.0/8", "224.0.0.0/4", "::/128", "::1/128", "ff00::/8"))
#: ``is_global`` calls some of this public, or does on some Python versions. An address here stands
#: for another one (NAT64, 6to4, Teredo, IPv4-compatible), or is a whole class of hosts (multicast).
_NEVER_PUBLIC = tuple(
    ipaddress.ip_network(n) for n in ("224.0.0.0/4", "64:ff9b::/96", "64:ff9b:1::/48", "2001::/32", "2002::/16", "::/8", "ff00::/8")
)
#: Control and invisible characters: format (zero-width, bidi), surrogates, private use, separators.
_UNSAFE_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Zl", "Zp"})
#: Kinds whose value can hold public space, and where.
_CIDR_FIELDS = {"network_zone": "cidr", "public_range": "cidr", "expected_activity": "source_cidrs"}

#: Refusal texts (422). Fixed: they never echo input.
BAD_CIDR = "enter an IP address or a CIDR range"
TOO_WIDE = "this range is too wide: narrow it, or record the part that is really in use"
NOT_PUBLIC = "this range isn't public address space: record it as a network zone"
UNUSABLE = "loopback, multicast and unspecified addresses can't be recorded"
NEEDS_TARGET = "expected activity needs at least one host or source range"
NEEDS_EXPIRY = "expected activity needs an expiry"
BAD_TIME = "enter a real date and time"
EXPIRY_PAST = "the expiry is in the past"
EXPIRY_TOO_FAR = f"expected activity can't run for more than {EXPECTED_MAX_DAYS} days from now"
EXPIRY_BEFORE_START = "the expiry is before the start"
START_TOO_OLD = f"the start can't be more than {EXPECTED_MAX_DAYS} days ago"
WINDOW_TOO_LONG = f"expected activity can't run for more than {EXPECTED_MAX_DAYS} days"
BAD_HOST = "host names can't hold spaces, wildcards, angle brackets or control characters"
BAD_ACCOUNT = "account names can't hold wildcards, angle brackets or control characters"
BAD_TEXT = "notes, owners and names can't hold angle brackets or control characters"
DUPLICATE = "this is already recorded for this customer: change that fact instead"
TOO_MANY = f"this customer has reached the limit of {MAX_FACTS} facts: remove some first"
#: Not a refusal: the caller's copy is out of date (409).
VERSION_CHANGED = "this fact changed after you opened it: open it again to edit the latest version"

OVERLAP = "Another customer records public space that overlaps this. Check it before relying on it."
DOMAIN_OVERLAP = "Another customer records this domain, or one above or under it. Check it before relying on it."
TENANT_OVERLAP = "Another customer records this tenant. Check it before relying on it."
#: In the audit row, which names no other customer: a customer-scoped view of it could show its row.
OVERLAP_AUDIT = "public space overlaps another customer's"
DOMAIN_OVERLAP_AUDIT = "domain overlaps another customer's"
TENANT_OVERLAP_AUDIT = "tenant is another customer's too"
#: kind -> (the warning, the audit row's line) when another customer records the same thing.
_OVERLAP_TEXTS = {
    "network_zone": (OVERLAP, OVERLAP_AUDIT),
    "public_range": (OVERLAP, OVERLAP_AUDIT),
    "expected_activity": (OVERLAP, OVERLAP_AUDIT),
    "own_domain": (DOMAIN_OVERLAP, DOMAIN_OVERLAP_AUDIT),
    "identity_tenant": (TENANT_OVERLAP, TENANT_OVERLAP_AUDIT),
}


class KnowledgeProblem(ValueError):
    """A fact that can't be saved. Its text is one of the fixed texts above."""


def normalize_cidr(value: str) -> Network:
    """``value`` as a network, a single address included, an IPv4-mapped one as IPv4. Raises
    ``KnowledgeProblem``."""
    text = str(value).strip()
    if "%" in text:  # an IPv6 scope id: free text that `ipaddress` keeps
        raise KnowledgeProblem(BAD_CIDR)
    try:
        network = ipaddress.ip_network(text, strict=False)
    except ValueError:
        raise KnowledgeProblem(BAD_CIDR) from None
    if network.version == 6 and network.subnet_of(_MAPPED):
        return ipaddress.IPv4Network((int(network.network_address) & 0xFFFFFFFF, network.prefixlen - _MAPPED.prefixlen))
    return network


def _overlaps_any(network: Network, others: "tuple[Network, ...]") -> bool:
    return any(network.version == other.version and network.overlaps(other) for other in others)


def _is_public(network: Network) -> bool:
    return network.is_global and not _overlaps_any(network, _NEVER_PUBLIC)


def _checked_cidr(value: str, *, public: bool) -> str:
    """The canonical range. ``public``: True for a public range, False for a zone, where either kind
    of space may be recorded (a customer can use public space internally)."""
    network = normalize_cidr(value)
    is_public = _is_public(network)
    if network.prefixlen < (PUBLIC_MIN_PREFIX if is_public else PRIVATE_MIN_PREFIX)[network.version]:
        raise KnowledgeProblem(TOO_WIDE)
    if _overlaps_any(network, _UNUSABLE):
        raise KnowledgeProblem(UNUSABLE)
    if public and not is_public:
        raise KnowledgeProblem(NOT_PUBLIC)
    return str(network)


def _unsafe(text: str) -> bool:
    return any(ch in "<>" or unicodedata.category(ch) in _UNSAFE_CATEGORIES for ch in text)


def _bad_name(text: str) -> bool:
    return not text or len(text) > NAME_MAX or _unsafe(text) or "*" in text or "%" in text


def _host(value: str) -> str:
    text = str(value).strip()
    if _bad_name(text) or any(ch.isspace() for ch in text):
        raise KnowledgeProblem(BAD_HOST)
    return text


def _account(value: str) -> str:
    """Spaces are allowed, as in ``NT AUTHORITY\\SYSTEM``. Other whitespace isn't."""
    text = str(value).strip()
    if _bad_name(text) or any(ch.isspace() and ch != " " for ch in text):
        raise KnowledgeProblem(BAD_ACCOUNT)
    return text


def _domain(value: str) -> str:
    if _unsafe(str(value)):  # an invisible character IDNA would drop: refused, as in a host name
        raise KnowledgeProblem(BAD_DOMAIN)
    try:
        return checked_domain(value)
    except DomainProblem as exc:
        raise KnowledgeProblem(str(exc)) from None


def _tenant(provider: str, value: str) -> str:
    try:
        return checked_tenant(provider, value)
    except DomainProblem as exc:
        raise KnowledgeProblem(str(exc)) from None


def _identifier(value: str) -> str:
    """An account identifier: an account name (``_account``) that isn't a display name."""
    text = _account(value)
    try:
        return checked_identifier(text)
    except DomainProblem as exc:
        raise KnowledgeProblem(str(exc)) from None


def _business(value: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return {
            "time_zone": checked_time_zone(value["time_zone"]),
            "week": checked_week(value["week"], value["always_open"]),
            "always_open": value["always_open"],
            "countries": checked_countries(value["countries"]),
        }
    except BusinessProblem as exc:
        raise KnowledgeProblem(str(exc)) from None


def _line(value: Optional[str]) -> Optional[str]:
    """Free text as one clean line, or None when there's nothing in it."""
    text = " ".join(str(value or "").split())
    if _unsafe(text):
        raise KnowledgeProblem(BAD_TEXT)
    return text or None


def _utc(moment: datetime) -> datetime:
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)


def _moment(value: datetime) -> datetime:
    """``value`` in UTC. A date at the very edge of the calendar can't be moved there."""
    try:
        return _utc(value)
    except OverflowError:
        raise KnowledgeProblem(BAD_TIME) from None


def _iso(moment: Optional[datetime]) -> Optional[str]:
    return _utc(moment).isoformat() if moment is not None else None


def _natural_key(kind: str, value: Mapping[str, Any]) -> Optional[str]:
    """What makes two facts of a customer the same fact. A host or an account can hold several roles,
    and expected activity can repeat, so it has no key. A domain is recorded once, with all its uses,
    and a customer has one business profile."""
    if kind in ("network_zone", "public_range"):
        return f"{kind}:{value['cidr']}"
    if kind == "asset_role":
        return f"{kind}:{value['host'].lower()}:{value['role']}"
    if kind == "own_domain":
        return f"{kind}:{value['domain']}"
    if kind == "identity_tenant":
        return f"{kind}:{value['provider']}:{value['tenant_id'].lower()}"
    if kind == "account_role":
        return f"{kind}:{value['account'].lower()}:{value['role']}"
    if kind == "business_profile":
        return kind
    return None


@dataclass(frozen=True)
class CheckedItem:
    kind: str
    branch: str
    value: Dict[str, Any]
    note: Optional[str]
    expires_at: Optional[datetime]  # naive UTC, as the column holds it
    natural_key: Optional[str]


def check_item(body: KnowledgeItemBody, now: datetime, kept: Optional[CustomerKnowledgeItem] = None) -> CheckedItem:
    """A fact as it will be stored, or ``KnowledgeProblem``. Pure, so the rules test without a
    database. A ``value`` that doesn't fit its kind raises ``pydantic.ValidationError``.

    ``kept`` is the row an edit changes. The rules that read the clock apply to a time the edit moves:
    a note on an expired fact can change, and a fact doesn't go invalid for having aged."""
    branch, model = KINDS[body.kind]
    typed = model.model_validate(body.value)
    parsed = typed.model_dump(mode="json")
    moment = _utc(now)
    expires = _moment(body.expires_at).replace(microsecond=0) if body.expires_at is not None else None
    new_expiry = kept is None or to_naive_utc(expires) != kept.expires_at
    if expires is not None and new_expiry and expires <= moment:
        raise KnowledgeProblem(EXPIRY_PAST)
    if body.kind == "network_zone":
        parsed["cidr"] = _checked_cidr(parsed["cidr"], public=False)
    elif body.kind == "public_range":
        parsed["cidr"] = _checked_cidr(parsed["cidr"], public=True)
    elif body.kind == "asset_role":
        parsed["host"] = _host(parsed["host"])
        parsed["owner"] = _line(parsed["owner"])
    elif body.kind == "own_domain":
        parsed["domain"] = _domain(parsed["domain"])
        parsed["uses"] = sorted(set(parsed["uses"]))
    elif body.kind == "identity_tenant":
        parsed["tenant_id"] = _tenant(parsed["provider"], parsed["tenant_id"])
        parsed["name"] = _line(parsed["name"])
    elif body.kind == "account_role":
        parsed["account"] = _identifier(parsed["account"])
        seen = {parsed["account"].lower()}
        aliases = []
        for alias in parsed["aliases"]:
            checked = _identifier(alias)
            if checked.lower() not in seen:
                seen.add(checked.lower())
                aliases.append(checked)
        parsed["aliases"] = sorted(aliases, key=str.lower)
    elif body.kind == "business_profile":
        parsed = _business(parsed)
    elif body.kind == "expected_activity":
        parsed["hosts"] = sorted({_host(h) for h in parsed["hosts"]})
        parsed["accounts"] = sorted({_account(a) for a in parsed["accounts"]})
        parsed["source_cidrs"] = sorted({_checked_cidr(c, public=False) for c in parsed["source_cidrs"]})
        if not parsed["hosts"] and not parsed["source_cidrs"]:
            raise KnowledgeProblem(NEEDS_TARGET)
        if expires is None:
            raise KnowledgeProblem(NEEDS_EXPIRY)
        limit = timedelta(days=EXPECTED_MAX_DAYS)
        if new_expiry and expires > moment + limit:
            raise KnowledgeProblem(EXPIRY_TOO_FAR)
        starts = _moment(typed.starts_at)
        parsed["starts_at"] = starts.isoformat()
        if expires <= starts:
            raise KnowledgeProblem(EXPIRY_BEFORE_START)
        if expires - starts > limit:
            raise KnowledgeProblem(WINDOW_TOO_LONG)
        new_start = kept is None or parsed["starts_at"] != kept.value.get("starts_at")
        if new_start and starts < moment - limit:
            raise KnowledgeProblem(START_TOO_OLD)
    return CheckedItem(body.kind, branch, parsed, _line(body.note), to_naive_utc(expires), _natural_key(body.kind, parsed))


def to_schema(row: CustomerKnowledgeItem, now: Optional[datetime] = None) -> KnowledgeItem:
    moment = _utc(now or now_utc())
    return KnowledgeItem(
        id=row.id,
        customer_code=row.customer_code,
        branch=row.branch,
        kind=row.kind,
        value=row.value,
        note=row.note,
        status=row.status,
        source=row.source,
        version=row.version,
        expires_at=_iso(row.expires_at),
        expired=row.expires_at is not None and _utc(row.expires_at) <= moment,
        created_at=_iso(row.created_at),
        updated_at=_iso(row.updated_at),
        updated_by_username=row.updated_by_username,
    )


def _audited(row: CustomerKnowledgeItem) -> Dict[str, Any]:
    return {"kind": row.kind, "value": row.value, "note": row.note, "expires_at": _iso(row.expires_at)}


async def _audit(
    action: AuditAction,
    user: User,
    customer_code: str,
    item_id: int,
    old: Optional[Mapping[str, Any]],
    new: Optional[Mapping[str, Any]],
    request: Optional[Request],
    overlap: Optional[str] = None,
) -> None:
    await record_audit_event(
        action=action,
        actor_user_id=user.id,
        actor_username=user.username,
        customer_code=customer_code,
        entity_type="customer_knowledge_item",
        entity_id=str(item_id),
        old_value=dict(old) if old is not None else None,
        new_value=dict(new) if new is not None else None,
        details=overlap,
        request=request,
    )


async def _customer_code(customer_code: str, session: AsyncSession) -> str:
    """The customer's code as stored (MySQL compares codes case-insensitively, talon-analyst's tenant
    keys don't), or a 404."""
    found = (await session.execute(select(Customers.customer_code).where(Customers.customer_code == customer_code))).scalars().first()
    if found is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return found


async def list_items(customer_code: str, session: AsyncSession) -> "tuple[str, List[CustomerKnowledgeItem]]":
    """The customer's code as stored, and its facts. ``MAX_FACTS`` bounds them."""
    code = await _customer_code(customer_code, session)
    query = (
        select(CustomerKnowledgeItem)
        .where(CustomerKnowledgeItem.customer_code == code)
        .order_by(CustomerKnowledgeItem.kind, CustomerKnowledgeItem.id)
    )
    return code, list((await session.execute(query)).scalars().all())


async def _get_item(item_id: int, customer_code: str, session: AsyncSession, *, lock: bool = False) -> CustomerKnowledgeItem:
    """By id and customer, so another customer's id is the same 404 as an unknown one."""
    query = select(CustomerKnowledgeItem).where(
        CustomerKnowledgeItem.id == item_id,
        CustomerKnowledgeItem.customer_code == customer_code,
    )
    row = (await session.execute(query.with_for_update() if lock else query)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Fact not found")
    return row


def _public_networks(kind: str, value: Any) -> "tuple[Network, ...]":
    """The public space a fact names, in any kind that can hold a range."""
    field = _CIDR_FIELDS.get(kind)
    cidrs = value.get(field) if field and isinstance(value, dict) else None
    found: List[Network] = []
    for cidr in cidrs if isinstance(cidrs, list) else [cidrs] if cidrs else []:
        try:
            network = normalize_cidr(cidr)
        except KnowledgeProblem:
            continue
        if _is_public(network):
            found.append(network)
    return tuple(found)


def _same_claim(kind: str, mine: Mapping[str, Any], theirs: Any) -> bool:
    """Whether another customer's fact of the same kind claims what ``mine`` does: a domain equal to,
    above or under it, or the same provider's tenant."""
    if not isinstance(theirs, dict):
        return False
    if kind == "own_domain":
        other = theirs.get("domain")
        return isinstance(other, str) and related(mine["domain"], other.lower())
    other = theirs.get("tenant_id")
    return theirs.get("provider") == mine["provider"] and isinstance(other, str) and other.lower() == mine["tenant_id"].lower()


async def _overlapping_customers(checked: CheckedItem, customer_code: str, session: AsyncSession) -> Set[str]:
    """The other customers whose live facts name public space this fact also names, or, for a domain or
    a tenant, claim the same one."""
    live = (
        CustomerKnowledgeItem.customer_code != customer_code,
        CustomerKnowledgeItem.status == APPROVED,
        or_(CustomerKnowledgeItem.expires_at.is_(None), CustomerKnowledgeItem.expires_at > to_naive_utc(now_utc())),
    )
    if checked.kind in ("own_domain", "identity_tenant"):
        query = select(CustomerKnowledgeItem.customer_code, CustomerKnowledgeItem.value).where(
            CustomerKnowledgeItem.kind == checked.kind,
            *live,
        )
        rows = (await session.execute(query)).all()
        return {code for code, value in rows if _same_claim(checked.kind, checked.value, value)}
    mine = _public_networks(checked.kind, checked.value)
    if not mine:
        return set()
    query = select(CustomerKnowledgeItem.customer_code, CustomerKnowledgeItem.kind, CustomerKnowledgeItem.value).where(
        CustomerKnowledgeItem.kind.in_(_CIDR_FIELDS),
        *live,
    )
    rows = (await session.execute(query)).all()
    return {code for code, kind, value in rows if any(_overlaps_any(n, _public_networks(kind, value)) for n in mine)}


async def _warnings(kind: str, overlapping: Set[str], user: User, session: AsyncSession) -> List[str]:
    """Never says whose, and counts only customers ``user`` can read: for an analyst scoped to one
    customer, a warning from the rest would be a way to find out what space, domains or tenants they
    record."""
    if not overlapping:
        return []
    readable = await customer_access_handler.get_user_accessible_customers(user, session)
    return [_OVERLAP_TEXTS[kind][0]] if "*" in readable or overlapping & set(readable) else []


def _overlap_line(kind: str, overlapping: Set[str]) -> Optional[str]:
    """The audit row's line for an overlap, which names no other customer."""
    return _OVERLAP_TEXTS[kind][1] if overlapping else None


def _checked(body: KnowledgeItemBody, kept: Optional[CustomerKnowledgeItem] = None) -> CheckedItem:
    """``check_item`` with its refusals as 422s."""
    try:
        return check_item(body, now_utc(), kept)
    except KnowledgeProblem as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except ValidationError:
        raise HTTPException(status_code=422, detail=f"this value doesn't fit a {body.kind}") from None


async def _commit(session: AsyncSession) -> None:
    """Commit, a fact already recorded as a 422. The customer's row is known to exist, so the unique
    key is what can fail here, also between two saves at once."""
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=422, detail=DUPLICATE) from None


async def create_item(
    customer_code: str,
    body: KnowledgeItemBody,
    user: User,
    session: AsyncSession,
    request: Optional[Request] = None,
) -> "tuple[CustomerKnowledgeItem, List[str]]":
    code = await _customer_code(customer_code, session)
    checked = _checked(body)
    count = select(func.count()).select_from(CustomerKnowledgeItem).where(CustomerKnowledgeItem.customer_code == code)
    if (await session.execute(count)).scalar_one() >= MAX_FACTS:
        raise HTTPException(status_code=422, detail=TOO_MANY)
    overlapping = await _overlapping_customers(checked, code, session)
    warnings = await _warnings(checked.kind, overlapping, user, session)
    now = now_utc()
    row = CustomerKnowledgeItem(
        customer_code=code,
        branch=checked.branch,
        kind=checked.kind,
        value=checked.value,
        note=checked.note,
        status=APPROVED,
        source=SOC,
        natural_key=checked.natural_key,
        expires_at=checked.expires_at,
        created_at=now,
        updated_at=now,
        updated_by_user_id=user.id,
        updated_by_username=user.username,
    )
    session.add(row)
    await _commit(session)
    await _audit(
        AuditAction.CUSTOMER_KNOWLEDGE_CREATE,
        user,
        code,
        row.id,
        None,
        _audited(row),
        request,
        _overlap_line(checked.kind, overlapping),
    )
    await session.refresh(row)
    logger.info(f"Knowledge item {row.id} ({row.kind}) added for {code}")
    return row, warnings


async def update_item(
    customer_code: str,
    item_id: int,
    body: KnowledgeItemUpdate,
    user: User,
    session: AsyncSession,
    request: Optional[Request] = None,
) -> "tuple[CustomerKnowledgeItem, List[str]]":
    code = await _customer_code(customer_code, session)
    row = await _get_item(item_id, code, session, lock=True)
    if body.kind != row.kind:
        raise HTTPException(status_code=422, detail="a fact keeps its kind: delete it and add a new one")
    if body.expected_version != row.version:
        raise HTTPException(status_code=409, detail=VERSION_CHANGED)
    checked = _checked(body, row)
    overlapping = await _overlapping_customers(checked, code, session)
    warnings = await _warnings(checked.kind, overlapping, user, session)
    if (row.value, row.note, row.expires_at) == (checked.value, checked.note, checked.expires_at):
        return row, warnings
    old = _audited(row)
    row.value = checked.value
    row.note = checked.note
    row.expires_at = checked.expires_at
    row.natural_key = checked.natural_key
    row.version += 1
    row.updated_at = now_utc()
    row.updated_by_user_id = user.id
    row.updated_by_username = user.username
    await _commit(session)
    await _audit(
        AuditAction.CUSTOMER_KNOWLEDGE_UPDATE,
        user,
        code,
        row.id,
        old,
        _audited(row),
        request,
        _overlap_line(checked.kind, overlapping),
    )
    await session.refresh(row)
    logger.info(f"Knowledge item {row.id} ({row.kind}) updated for {code}")
    return row, warnings


async def delete_item(customer_code: str, item_id: int, user: User, session: AsyncSession, request: Optional[Request] = None) -> None:
    code = await _customer_code(customer_code, session)
    row = await _get_item(item_id, code, session)
    old = _audited(row)
    await session.delete(row)
    await session.commit()
    await _audit(AuditAction.CUSTOMER_KNOWLEDGE_DELETE, user, code, item_id, old, None, request)
    logger.info(f"Knowledge item {item_id} deleted for {code}")
