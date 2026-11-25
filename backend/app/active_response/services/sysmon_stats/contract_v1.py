"""Vendored from sysmon-sync (socfortress/sysmon-sync, commit 034dcbd, app/reports/contract.py): the report contract v1
("socfortress-sysmon-report/1", CoPilot to sysmon-sync), strict parsing and validation.

CoPilot runs the service's own validator on each report before sending it (app/active_response/services/sysmon_stats/
report.py), so a report the service would refuse is never sent. Changes against the original: the relative imports
(contract_v1_rules is sysmon-sync's cka_rules) and the caps of sysmon-sync's app/reports/__init__.py defined here.
The rules themselves are not edited. tests/test_sysmon_stats_contract.py checks this copy against a sysmon-sync
checkout (SYSMON_SYNC_DIR).

The original module docstring follows.

The report contract v1 ("socfortress-sysmon-report/1", CoPilot to this service): strict parsing and validation.

Nothing here rewrites a value: a report is either refused as a whole (ReportRefused, a 422: a broken or leaking
sender, nothing is stored) or each pattern is accepted as sent or dropped with a reason code (a value the
installer repo's loader would refuse, which real endpoints can produce). No message, reason or log line built
from this module ever carries a value: only reason codes, indexes and allow-listed field names.

Order (README, "Fleet noise reports"):
  1. structure and caps (malformed, format, too-many-patterns, too-many-fields);
  2. over every pattern, an unaccepted event_id included: identity leaks, command lines and field names
     outside the allow-list;
  3. the pattern key of every pattern that has one, and duplicate-pattern;
  4. per-pattern drops (event-not-accepted, event-type-mismatch, key-field-missing, rule-name, the value rules).
The week, environment and customer checks need the clock and the database; the route does them afterwards.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from .contract_v1_rules import MAX_RULENAME_LEN
from .contract_v1_rules import MAX_VALUE_LEN
from .contract_v1_rules import REDACTION
from .contract_v1_rules import REGISTRY_SERVICE_HIVES
from .contract_v1_rules import UNSTABLE_FIELDS
from .contract_v1_rules import USER_DIR_RE
from .contract_v1_rules import bad_characters
from .contract_v1_rules import fold_dots
from .contract_v1_rules import identity_leak
from .contract_v1_rules import value_reasons

# From sysmon-sync's app/reports/__init__.py (the report caps)
MAX_REPORT_BYTES = 1536 * 1024
MAX_WITHDRAW_BYTES = 4 * 1024  # withdraw body cap (4 KiB)
MAX_PATTERNS = 70  # per report; with MAX_FIELDS_PER_PATTERN this keeps a report under the WAF's 1000 ARGS
MAX_FIELDS_PER_PATTERN = 5
MAX_REFUSAL_LISTED = 20  # patterns entries in a 422

REPORT_FORMAT = "socfortress-sysmon-report/1"
WITHDRAW_FORMAT = "socfortress-sysmon-withdraw/1"
PATTERN_KEY_LABEL = "socfortress-sysmon-pattern/1"

MAX_CONFIG = 10**12
MAX_REPORT_ENDPOINTS = 1_000_000
MAX_PATTERN_EVENTS = 10**9

CUSTOMER_RE = re.compile(r"cust_[0-9a-f]{32}")
WEEK_RE = re.compile(r"([0-9]{4})-W([0-9]{2})")  # [0-9], not \d: no other script's digits
CONFIG_WORDS = ("customized", "unknown")

TOP_KEYS = frozenset({"format", "customer", "week", "config", "endpoints", "truncated", "patterns"})
PATTERN_REQUIRED = frozenset({"event_id", "fields", "events", "endpoints", "days"})
PATTERN_KEYS = PATTERN_REQUIRED | {"rule_name"}
COMMAND_LINE_FIELDS = frozenset({"CommandLine", "ParentCommandLine"})
# Never accepted as a field name, whatever the event (a whole-report 422): command lines (reason command-line),
# free text and hashes, the source of a connection, WMI text, the per-event (unstable) fields and RuleName.
NEVER_FIELDS = frozenset(
    {
        "Details",
        "Hashes",
        "Hash",
        "Contents",
        "CallTrace",
        "QueryResults",
        "SourceIp",
        "SourceHostname",
        "Query",
        "Consumer",
        "Destination",
        *UNSTABLE_FIELDS,
        "RuleName",
    },
)

# Whole-report reasons, most important first (the 422's top-level reason when several apply).
REFUSAL_ORDER = (
    "malformed",
    "format",
    "too-many-patterns",
    "too-many-fields",
    "identity-leak",
    "command-line",
    "field-not-allowed",
    "duplicate-pattern",
)
# Per-pattern drop reasons. A value with several problems gets the first of VALUE_REASON_ORDER (the most specific:
# a KELVIN SIGN is both "not NFC" and a look-alike, and look-alike says more).
DROP_REASONS = (
    "event-not-accepted",
    "event-type-mismatch",
    "key-field-missing",
    "rule-name",
    "value-empty",
    "value-too-long",
    "bad-character",
    "not-nfc",
    "wildcard",
    "env-var",
    "doubled-backslash",
    "unknown-placeholder",
    "unknown-token",
    "look-alike",
    "non-ascii-dns",
    "value-invalid",
)
VALUE_REASON_ORDER = (
    "value-empty",
    "value-too-long",
    "bad-character",
    "look-alike",
    "non-ascii-dns",
    "not-nfc",
    "wildcard",
    "env-var",
    "doubled-backslash",
    "unknown-placeholder",
    "unknown-token",
    "value-invalid",
)


@dataclass(frozen=True)
class EventSpec:
    name: str
    key: tuple[str, ...]  # required key fields (NetworkConnect's destination aside)
    detail: tuple[str, ...]  # optional detail fields
    event_types: tuple[str, ...] = ()  # allowed EventType values (RegistryEvent, PipeEvent)
    derive: str | None = None  # the EventType derived when missing (None: it must be sent)
    destination: bool = False  # NetworkConnect: DestinationHostname, else DestinationIp, is a key field

    @property
    def allowed(self) -> frozenset[str]:
        names = set(self.key) | set(self.detail)
        if self.event_types:
            names.add("EventType")
        if self.destination:
            names |= {"DestinationHostname", "DestinationIp"}
        return frozenset(names)


_REGISTRY_KEY = ("Image", "TargetObject", "EventType")
_PIPE_KEY = ("Image", "PipeName", "EventType")
EVENTS: dict[int, EventSpec] = {
    1: EventSpec("ProcessCreate", ("Image", "ParentImage"), ("OriginalFileName", "User", "IntegrityLevel")),
    2: EventSpec("FileCreateTime", ("Image", "TargetFilename"), ("User",)),
    3: EventSpec("NetworkConnect", ("Image", "DestinationPort"), ("Protocol", "Initiated", "User"), destination=True),
    6: EventSpec("DriverLoad", ("ImageLoaded", "Signature", "SignatureStatus"), ("Signed",)),
    7: EventSpec("ImageLoad", ("Image", "ImageLoaded", "Signature"), ("SignatureStatus", "Signed", "OriginalFileName", "User")),
    8: EventSpec("CreateRemoteThread", ("SourceImage", "TargetImage", "StartModule"), ("StartFunction", "SourceUser", "TargetUser")),
    10: EventSpec("ProcessAccess", ("SourceImage", "TargetImage", "GrantedAccess"), ("SourceUser", "TargetUser")),
    11: EventSpec("FileCreate", ("Image", "TargetFilename"), ("User",)),
    12: EventSpec("RegistryEvent", _REGISTRY_KEY, ("User",), event_types=("CreateKey", "DeleteKey", "CreateValue", "DeleteValue")),
    13: EventSpec("RegistryEvent", _REGISTRY_KEY, ("User",), event_types=("SetValue",), derive="SetValue"),
    14: EventSpec("RegistryEvent", _REGISTRY_KEY, ("NewName", "User"), event_types=("RenameKey",), derive="RenameKey"),
    15: EventSpec("FileCreateStreamHash", ("Image", "TargetFilename"), ("User",)),
    17: EventSpec("PipeEvent", _PIPE_KEY, ("User",), event_types=("CreatePipe",), derive="CreatePipe"),
    18: EventSpec("PipeEvent", _PIPE_KEY, ("User",), event_types=("ConnectPipe",), derive="ConnectPipe"),
    22: EventSpec("DnsQuery", ("Image", "QueryName"), ("QueryStatus", "User")),
    23: EventSpec("FileDelete", ("Image", "TargetFilename"), ("IsExecutable", "User")),
    25: EventSpec("ProcessTampering", ("Image", "Type"), ("User",)),
    26: EventSpec("FileDeleteDetected", ("Image", "TargetFilename"), ("IsExecutable", "User")),
}
# Every name any accepted event allows: the only field names a log line or a response may carry.
ALLOW_LISTED = frozenset().union(*(spec.allowed for spec in EVENTS.values()))


# ---- identity checks stricter than the installer repo's (this service only) ------------------------
# CKA's identity_leak (vendored) knows profile folders, user hives, SIDs, UNC hosts and accounts. These add what
# real redacted paths still leak, and refuse the whole report the same way (identity-leak). Being stricter than
# CKA only removes values, so the candidates still load there. Documented for CoPilot's redaction in the README.
_PLACEHOLDER_RE = re.compile("|".join(re.escape(p) for p in REDACTION))
_LETTER_RE = re.compile(r"[^\W\d_]")  # a letter of any script
# An e-mail address, also with a redacted local part (the domain names the organisation): a local-part character
# (or the ">" of <user>) right before "@", then a DNS name with an alphabetic top-level label. Not "@2x." /
# "@1.5x." (image scale suffixes, icon@2x.png) and not "name@1.2.3" (package versions: no alphabetic last label).
# Linear per "@": the labels are possessive, only the last one is given back.
EMAIL_RE = re.compile(r"(?i)(?<=[a-z0-9._%+'>-])@(?![0-9]++(?:\.[0-9]++)?x\.)" r"(?:[a-z0-9-]++\.)+[a-z]{2,63}(?![a-z0-9-])")
# OneDrive for Business syncs to "OneDrive - <organisation name>" (OneDrive personal: "OneDrive", or "OneDrive -
# Personal" next to a business account).
ONEDRIVE_RE = re.compile(r"(?i)(?:^|[\\/])OneDrive - ([^\\/]+)")
_DOT_COMPONENT_RE = re.compile(r"[\\/]\.")


def _unredacted_letters(text: str) -> bool:
    """TEXT still has a letter once every placeholder is taken out (john.doe<user>, <user>.ACME)."""
    return bool(_LETTER_RE.search(_PLACEHOLDER_RE.sub("", text)))


def service_leak(value: str) -> str | None:
    """What in VALUE identifies a person or an organisation that CKA's identity_leak lets through, or None (never
    the literal): an e-mail address, a partly redacted profile folder, a OneDrive for Business folder. Callers
    keep VALUE at most MAX_VALUE_LEN characters (fold_dots is quadratic)."""
    if "@" in value and EMAIL_RE.search(value):
        return "an e-mail address (also with a redacted local part: the domain names the organisation)"
    if any(p in value for p in REDACTION):
        spellings = [value] + ([fold_dots(value)] if _DOT_COMPONENT_RE.search(value) else [])
        for v in spellings:
            for m in USER_DIR_RE.finditer(v):
                folder = m.group(2)
                if any(p in folder for p in REDACTION) and _unredacted_letters(folder):
                    return "a partly redacted profile folder (the whole folder name must be a placeholder)"
    for m in ONEDRIVE_RE.finditer(value):
        org = m.group(1).strip()
        if org.lower() != "personal" and _unredacted_letters(org):
            return "a OneDrive for Business folder (OneDrive - <organisation>)"
    return None


def any_leak(name: str, value: str) -> bool:
    """CKA's identity_leak or the stricter service_leak, for a value of at most MAX_VALUE_LEN characters (a longer
    one is dropped as value-too-long and never stored)."""
    return len(value) <= MAX_VALUE_LEN and bool(identity_leak(name, value, REGISTRY_SERVICE_HIVES) or service_leak(value))


def rule_name_leak(rule_name: str) -> bool:
    """The rule name is the one free-text value: the field-independent identity checks apply to it too (profile
    folder, user hive, SID, UNC host, e-mail, ...). One longer than MAX_RULENAME_LEN is dropped (rule-name)."""
    return len(rule_name) <= MAX_RULENAME_LEN and any_leak("RuleName", rule_name)


def absent_fields(event_id: int, fields: dict[str, str]) -> list[str]:
    """The candidate's "absent": the event's allow-list (plus the command lines for a ProcessCreate) minus FIELDS."""
    names = set(EVENTS[event_id].allowed)
    if event_id == 1:
        names |= COMMAND_LINE_FIELDS
    return sorted(names - set(fields))


# ---- results -------------------------------------------------------------------------------
@dataclass(frozen=True)
class Problem:
    index: int
    reason: str
    field: str | None = None  # only an allow-listed name, or "rule_name" (the contract's key, a constant)
    unlisted: bool = False  # about a field whose name is not allow-listed (never shown, only counted)

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"index": self.index, "reason": self.reason}
        if self.field is not None:
            out["field"] = self.field
        return out


class BadJSON(Exception):
    """400: the body is not strict UTF-8 JSON (BOM, duplicate key, NaN, invalid UTF-8, too deep, ...)."""


class ReportRefused(Exception):
    """422: the whole report is refused; nothing is stored."""

    def __init__(self, reason: str, problems: list[Problem] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.problems = list(problems or [])

    def patterns_json(self) -> list[dict[str, Any]]:
        return [p.to_json() for p in self.problems[:MAX_REFUSAL_LISTED]]

    def field_names(self) -> list[str]:
        return sorted({p.field for p in self.problems if p.field is not None})

    def unlisted_fields(self) -> int:
        return sum(1 for p in self.problems if p.unlisted)


@dataclass(frozen=True)
class AcceptedPattern:
    index: int
    event_id: int
    key_fields: dict[str, str]  # with the derived EventType
    detail: dict[str, str]
    rule_name: str | None
    events: int
    endpoints: int
    days: int
    pattern_key: bytes  # 32 bytes


@dataclass(frozen=True)
class ParsedReport:
    customer: str
    week: str
    week_monday: _dt.date | None  # None: not a real ISO week (refused as week-not-accepted by the route)
    config: str  # decimal | "customized" | "unknown"
    endpoints: int
    truncated: bool
    received: int
    accepted: list[AcceptedPattern] = field(default_factory=list)
    rejected: list[Problem] = field(default_factory=list)

    @property
    def week_sunday(self) -> _dt.date | None:
        return None if self.week_monday is None else self.week_monday + _dt.timedelta(days=6)

    def rejected_by_reason(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for p in self.rejected:
            out[p.reason] = out.get(p.reason, 0) + 1
        return dict(sorted(out.items()))


# ---- strict JSON -----------------------------------------------------------------------------
class _Duplicate(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise _Duplicate("duplicate key")  # never the key itself
        out[k] = v
    return out


def _constant(_name: str) -> Any:
    raise ValueError("NaN or Infinity")


def strict_loads(raw: bytes | bytearray) -> Any:
    """Parse UTF-8 JSON with no BOM, no duplicate keys and no NaN/Infinity. BadJSON carries no input text."""
    if raw.startswith(b"\xef\xbb\xbf"):
        raise BadJSON("starts with a byte order mark")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise BadJSON("not UTF-8") from None
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except _Duplicate:
        raise BadJSON("a JSON object has a duplicate key") from None
    except RecursionError:
        raise BadJSON("nested too deeply") from None
    except ValueError:
        raise BadJSON("not valid JSON") from None


def canonical(obj: Any) -> str:
    """ASCII JSON: the input of the pattern key (stable, never stored as such)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stored_json(obj: Any) -> str:
    """What the database keeps: the same JSON as canonical(), in UTF-8 (a non-ASCII character costs its UTF-8
    bytes, not a 6-byte \\uXXXX escape)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def pattern_key(event_id: int, key_fields: dict[str, str]) -> bytes:
    return hashlib.sha256(canonical([PATTERN_KEY_LABEL, event_id, key_fields]).encode("ascii")).digest()


def iso_week(week: str) -> _dt.date | None:
    """The Monday of a real ISO week "YYYY-Www", or None."""
    m = WEEK_RE.fullmatch(week)
    if not m:
        return None
    try:
        return _dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
    except (ValueError, OverflowError):
        return None


def last_completed_sunday(today: _dt.date) -> _dt.date:
    """The last Sunday whose UTC day has ended: yesterday on a Monday, a week ago on a Sunday."""
    return today - _dt.timedelta(days=today.isoweekday())


def week_accepted(week_monday: _dt.date, today: _dt.date, max_age_weeks: int) -> bool:
    """Only completed weeks, at most max_age_weeks back (the last two by default)."""
    sunday = week_monday + _dt.timedelta(days=6)
    last = last_completed_sunday(today)
    return last - _dt.timedelta(days=7 * max_age_weeks) < sunday <= last


def _int(v: Any, lo: int, hi: int) -> bool:
    return type(v) is int and lo <= v <= hi


def _first_refusal(problems: list[Problem]) -> ReportRefused:
    reason = min((p.reason for p in problems), key=REFUSAL_ORDER.index)
    return ReportRefused(reason, sorted(problems, key=lambda p: (REFUSAL_ORDER.index(p.reason), p.index)))


def _listed(name: str, spec: EventSpec | None = None) -> str | None:
    """NAME when it may appear in a response or a log line, else None: a name on some accepted event's allow-list
    (a constant of this module, so never attacker text), even when it is not allowed for this event."""
    return name if name in ALLOW_LISTED else None


def _problem(i: int, reason: str, name: str, spec: EventSpec | None) -> Problem:
    listed = _listed(name, spec)
    return Problem(i, reason, listed, unlisted=listed is None)


# ---- validation ------------------------------------------------------------------------------
def validate_report(doc: Any) -> ParsedReport:
    """Validate a parsed report body. Raises ReportRefused (422) or returns the accepted and dropped patterns."""
    if not isinstance(doc, dict):
        raise ReportRefused("malformed")
    if doc.get("format") != REPORT_FORMAT:
        raise ReportRefused("format")
    if set(doc) != TOP_KEYS:
        raise ReportRefused("malformed")
    customer, week, config = doc["customer"], doc["week"], doc["config"]
    endpoints, truncated, patterns = doc["endpoints"], doc["truncated"], doc["patterns"]
    if not isinstance(customer, str) or not CUSTOMER_RE.fullmatch(customer):
        raise ReportRefused("malformed")
    if not isinstance(week, str) or not WEEK_RE.fullmatch(week):
        raise ReportRefused("malformed")
    if not (_int(config, 0, MAX_CONFIG) or config in CONFIG_WORDS):
        raise ReportRefused("malformed")
    if not _int(endpoints, 0, MAX_REPORT_ENDPOINTS) or not isinstance(truncated, bool):
        raise ReportRefused("malformed")
    if not isinstance(patterns, list):
        raise ReportRefused("malformed")
    if len(patterns) > MAX_PATTERNS:
        raise ReportRefused("too-many-patterns")
    monday = iso_week(week)  # None: not a real ISO week; the route refuses it as week-not-accepted

    # 1. structure and caps, per pattern
    problems: list[Problem] = []
    for i, p in enumerate(patterns):
        problems.extend(_structure(i, p, endpoints))
    if problems:
        raise _first_refusal(problems)

    # 2. identity leaks, command lines and field names, over every pattern. A value longer than MAX_VALUE_LEN is
    # dropped as value-too-long (never stored) and skips the leak check: CKA's fold_dots is quadratic in the value's
    # length, and Python's re holds the GIL, so one 1.5 MiB value would stall the service for hours. Up to 1024
    # characters it costs at most a few milliseconds per value. The rule name gets the same checks (any_leak).
    for i, p in enumerate(patterns):
        spec = EVENTS.get(p["event_id"])
        rule_name = p.get("rule_name")
        if rule_name is not None and rule_name_leak(rule_name):
            problems.append(Problem(i, "identity-leak", "rule_name"))
        for name, value in p["fields"].items():
            if any_leak(name, value):
                problems.append(_problem(i, "identity-leak", name, spec))
            if name in COMMAND_LINE_FIELDS:
                problems.append(Problem(i, "command-line"))  # the reason names it; not an allow-listed name
            elif name in NEVER_FIELDS or (spec is not None and name not in spec.allowed):
                problems.append(_problem(i, "field-not-allowed", name, spec))
    if problems:
        raise _first_refusal(problems)

    # 3. pattern keys and duplicates; 4. per-pattern drops
    accepted: list[AcceptedPattern] = []
    rejected: list[Problem] = []
    seen: dict[bytes, int] = {}
    for i, p in enumerate(patterns):
        keyed = _key_fields(i, p)
        if isinstance(keyed, Problem):
            rejected.append(keyed)
            continue
        key_fields, pkey = keyed
        if pkey in seen:
            problems.append(Problem(i, "duplicate-pattern"))
            continue
        seen[pkey] = i
        drop = _drop_reason(i, p, key_fields)
        if drop is not None:
            rejected.append(drop)
            continue
        detail = {k: v for k, v in p["fields"].items() if k not in key_fields}
        accepted.append(
            AcceptedPattern(
                index=i,
                event_id=p["event_id"],
                key_fields=key_fields,
                detail=detail,
                rule_name=p.get("rule_name"),
                events=p["events"],
                endpoints=p["endpoints"],
                days=p["days"],
                pattern_key=pkey,
            ),
        )
    if problems:
        raise _first_refusal(problems)
    return ParsedReport(
        customer=customer,
        week=week,
        week_monday=monday,
        config=str(config),
        endpoints=endpoints,
        truncated=truncated,
        received=len(patterns),
        accepted=accepted,
        rejected=rejected,
    )


def _structure(i: int, p: Any, report_endpoints: int) -> list[Problem]:
    if not isinstance(p, dict):
        return [Problem(i, "malformed")]
    unknown = set(p) - PATTERN_KEYS
    if unknown & COMMAND_LINE_FIELDS:
        return [Problem(i, "command-line")]
    if unknown or not PATTERN_REQUIRED <= set(p):
        return [Problem(i, "malformed")]
    fields = p["fields"]
    if type(p["event_id"]) is not int or not isinstance(fields, dict) or not fields:
        return [Problem(i, "malformed")]
    if not all(isinstance(v, str) for v in fields.values()):
        return [Problem(i, "malformed")]
    if not (_int(p["events"], 1, MAX_PATTERN_EVENTS) and _int(p["endpoints"], 1, report_endpoints) and _int(p["days"], 1, 127)):
        return [Problem(i, "malformed")]
    rule_name = p.get("rule_name")
    if rule_name is not None and not isinstance(rule_name, str):
        return [Problem(i, "malformed")]
    if len(fields) > MAX_FIELDS_PER_PATTERN:
        return [Problem(i, "too-many-fields")]
    return []


def _key_fields(i: int, p: dict[str, Any]) -> tuple[dict[str, str], bytes] | Problem:
    """(key fields with the derived EventType, pattern key), or the drop that prevents a key."""
    spec = EVENTS.get(p["event_id"])
    if spec is None:
        return Problem(i, "event-not-accepted")
    fields: dict[str, str] = p["fields"]
    key: dict[str, str] = {}
    if spec.event_types:
        et = fields.get("EventType")
        if et is None:
            if spec.derive is None:
                return Problem(i, "key-field-missing", "EventType")
            et = spec.derive
        elif et not in spec.event_types:
            return Problem(i, "event-type-mismatch", "EventType")
        key["EventType"] = et
    for name in spec.key:
        if name == "EventType":
            continue
        if name not in fields:
            return Problem(i, "key-field-missing", name)
        key[name] = fields[name]
    if spec.destination:
        host = fields.get("DestinationHostname")
        if host is not None and host != "-":
            key["DestinationHostname"] = host
        elif "DestinationIp" in fields:
            key["DestinationIp"] = fields["DestinationIp"]
        else:
            return Problem(i, "key-field-missing", "DestinationIp")
    return key, pattern_key(p["event_id"], key)


def _drop_reason(i: int, p: dict[str, Any], key_fields: dict[str, str]) -> Problem | None:
    rule_name = p.get("rule_name")
    if rule_name is not None and (
        rule_name == "" or len(rule_name) > MAX_RULENAME_LEN or bad_characters(rule_name) or not unicodedata.is_normalized("NFC", rule_name)
    ):
        return Problem(i, "rule-name")
    spec = EVENTS[p["event_id"]]
    values = dict(p["fields"])
    values.update({k: v for k, v in key_fields.items() if k not in values})  # a derived EventType
    for name, value in values.items():
        if len(value) > MAX_VALUE_LEN:  # CKA would say so too; the other rules are not worth running on it
            return Problem(i, "value-too-long", _listed(name, spec))
        reasons = value_reasons(name, value)
        if reasons:
            return Problem(i, min(reasons, key=VALUE_REASON_ORDER.index), _listed(name, spec))
    return None


# ---- withdraw --------------------------------------------------------------------------------
def validate_withdraw(doc: Any) -> str | None:
    """The customer pseudonym to withdraw, or None for all of the license's reports. ReportRefused("malformed")."""
    if not isinstance(doc, dict) or doc.get("format") != WITHDRAW_FORMAT:
        raise ReportRefused("malformed")
    if set(doc) == {"format", "customer"}:
        customer = doc["customer"]
        if isinstance(customer, str) and CUSTOMER_RE.fullmatch(customer):
            return customer
    elif set(doc) == {"format", "all"} and doc["all"] is True:
        return None
    raise ReportRefused("malformed")
