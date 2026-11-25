r"""Redaction of the values in a Sysmon noise report. Pure, allow-list, fail-closed.

A value leaves this CoPilot only in one of these forms: a value nothing identifying was found in, a value whose
identifying parts were replaced with the contract's placeholders (``<user>`` a profile folder, ``<SID>`` a user SID,
``<host>`` a UNC host, ``<redacted>`` anything else, ``__INSTALLDIRNAME__`` the EDR install folder), or nothing: a
pattern whose key value cannot be made safe is dropped, never sent half-redacted. Every result then goes through
sysmon-sync's own value and identity checks (the vendored contract), so what the service would refuse is never sent.

Per value, in order (``redact_value``):

R0. Not a string, or longer than 4096 characters: dropped before any regex runs on it.
R1. Wazuh's doubling undone: the eventchannel decoder JSON-escapes each eventdata value once more than Sysmon logged it
    (``C:\\Windows`` for ``C:\Windows``). The installer repo's conservative per-field rule decides: decoded only when
    the value is a valid JSON string body holding an escaped backslash and no escape other than ``\\``, ``\"``, ``\/``.
R2. Empty: dropped (Sysmon logs ``-`` for an empty field).
R3. Account fields (User, SourceUser, TargetUser) keep only well-known service principals (``NT AUTHORITY\SYSTEM``,
    ``NT SERVICE\x``, ``BUILTIN\x``, ``-``); anything else is ``<redacted>``. DNS fields go through dns_policy.
R4. Everything else, structurally: the install folder, user SIDs, profile folders (what may follow them, below), UNC
    hosts, e-mail addresses, OneDrive for Business folders, private-domain path segments, document file names.
R5. The customer's own names (code, name, its distinctive words, install folders, agent host names, the accounts and
    domains seen in its events, admin hints), matched as whole words, become ``<redacted>``.
R7. sysmon-sync's checks: at most 1024 characters, the value rules (``value_reasons``), and no identity leak. Any
    failure drops the pattern.

Values are never case-folded or normalised: they stay as logged, so a suggestion built from them matches real events.
"""
import json
import re
import unicodedata
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import FrozenSet
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Union

from app.active_response.services.sysmon_stats import settings
from app.active_response.services.sysmon_stats.contract_v1 import EVENTS
from app.active_response.services.sysmon_stats.contract_v1 import VALUE_REASON_ORDER
from app.active_response.services.sysmon_stats.contract_v1 import pattern_key
from app.active_response.services.sysmon_stats.contract_v1 import rule_name_leak
from app.active_response.services.sysmon_stats.contract_v1 import service_leak
from app.active_response.services.sysmon_stats.contract_v1_rules import (
    REGISTRY_SERVICE_HIVES,
)
from app.active_response.services.sysmon_stats.contract_v1_rules import UNC_ANY_RE
from app.active_response.services.sysmon_stats.contract_v1_rules import USER_DIR_RE
from app.active_response.services.sysmon_stats.contract_v1_rules import bad_characters
from app.active_response.services.sysmon_stats.contract_v1_rules import identity_leak
from app.active_response.services.sysmon_stats.contract_v1_rules import value_reasons
from app.active_response.services.sysmon_stats.contract_v1_rules import (
    well_known_principal,
)
from app.active_response.services.sysmon_stats.dns_policy import PRIVATE_SUFFIXES
from app.active_response.services.sysmon_stats.dns_policy import Drop
from app.active_response.services.sysmon_stats.dns_policy import classify_dns
from app.active_response.services.sysmon_stats.dns_policy import under
from app.active_response.services.sysmon_stats.fields import EVENT_PLAN
from app.active_response.services.sysmon_stats.queries import RawPattern

TOKEN = "__INSTALLDIRNAME__"
PLACEHOLDERS = ("<user>", "<SID>", "<host>", "<redacted>")
REDACTED = "<redacted>"
USER_FIELDS = frozenset({"User", "SourceUser", "TargetUser"})
DNS_FIELDS = frozenset({"QueryName", "DestinationHostname"})
MAX_NAMES = 20_000

# ---- R1: Wazuh's doubling -------------------------------------------------------------------------------------------
# One JSON string escape (the installer repo's tools/sysmonctl/alert.py)
_ESCAPE = re.compile(r'\\(["\\/bfnrt]|u[0-9a-fA-F]{4})')


def _escapes(value: str) -> Optional[Set[str]]:
    """The escape letters in value if it is a valid JSON string body (every backslash starts an escape, no bare quote),
    else None."""
    used: Set[str] = set()
    i = 0
    while True:
        j = min((k for k in (value.find("\\", i), value.find('"', i)) if k >= 0), default=-1)
        if j < 0:
            return used
        m = _ESCAPE.match(value, j)
        if not m:
            return None
        used.add(m.group(1)[0])
        i = m.end()


def unescape_value(value: str) -> str:
    """Undo Wazuh's JSON escaping of one eventdata value, conservatively (the installer repo's per-field rule)."""
    used = _escapes(value)
    if used is not None and "\\" in used and used <= {"\\", '"', "/"}:
        try:
            return json.loads('"' + value + '"', strict=False)
        except ValueError:
            return value
    return value


def _doubled_backslash(value: str) -> bool:
    rest = value[2:] if value.startswith("\\\\") else value
    return "\\\\" in rest


# ---- R4: structure --------------------------------------------------------------------------------------------------
SID_RE = re.compile(r"(?i)\bS-1-(?:5-21|12-1)(?:-\d+)+")
# Under a profile, the first folder decides what of the rest is kept (owner decision D9)
_USER_CONTENT = frozenset(
    {
        "desktop",
        "documents",
        "downloads",
        "pictures",
        "music",
        "videos",
        "favorites",
        "contacts",
        "links",
        "searches",
        "saved games",
        "3d objects",
    },
)
_NTUSER = frozenset({"ntuser.dat", "ntuser.dat.log1", "ntuser.dat.log2", "ntuser.ini", "ntuser.pol"})
# AppData subtrees that hold document and attachment names
_APPDATA_SENSITIVE = (
    ("appdata", "roaming", "microsoft", "windows", "recent"),
    ("appdata", "roaming", "microsoft", "office", "recent"),
    ("appdata", "local", "microsoft", "windows", "inetcache", "content.outlook"),
    ("appdata", "local", "microsoft", "olk", "attachments"),
)
_SEP_RE = re.compile(r"[\\/]")
_PLACEHOLDER_ALT = "|".join(re.escape(p) for p in PLACEHOLDERS)
# An e-mail address, the whole of it (a redacted local part too: the domain names the organisation). Not "icon@2x.png"
# (image scale suffixes) and not "lodash@4.17.21" (no alphabetic last label).
EMAIL_RE = re.compile(
    r"(?i)(?:[a-z0-9._%+'-]|" + _PLACEHOLDER_ALT + r")+@(?![0-9]++(?:\.[0-9]++)?x\.)(?:[a-z0-9-]++\.)+[a-z]{2,63}(?![a-z0-9-])",
)
# A file extension Outlook and others put right after an address (john.doe@contoso.com.ost): kept after <redacted>
_EMAIL_FILE_EXTS = frozenset({"ost", "pst", "nst", "oab", "dat", "xml", "json", "log", "txt", "tmp", "db", "lock", "bak", "ini"})
ONEDRIVE_BUSINESS_RE = re.compile(r"(?i)((?:^|[\\/])OneDrive - )(?!Personal(?:[\\/]|$))[^\\/]+")
_DNS_SEGMENT_RE = re.compile(r"(?i)[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+")
_DOCUMENT_EXTS = frozenset(
    {
        "doc",
        "docx",
        "docm",
        "xls",
        "xlsx",
        "xlsm",
        "ppt",
        "pptx",
        "pdf",
        "msg",
        "eml",
        "rtf",
        "odt",
        "ods",
        "odp",
        "vsd",
        "vsdx",
        "one",
        "pub",
        "jpg",
        "jpeg",
        "heic",
        "mov",
        "mp4",
    },
)
_SYSTEM_ROOT_RE = re.compile(
    r"(?i)^(?:[a-z]:|\\Device\\[^\\/]+|\\\\[?.]\\[a-z]:|\\\?\?\\[a-z]:)?[\\/](?:Windows|Program Files|Program Files \(x86\)|ProgramData)[\\/]",
)
_DOCUMENT_RE = re.compile(r"(?i)^(.+)\.([a-z0-9]{2,5})$")

# ---- R5: names ------------------------------------------------------------------------------------------------------
# Never a customer name on their own: the placeholders, and words every Windows path is made of
STOPLIST = frozenset(
    {
        "user",
        "users",
        "sid",
        "host",
        "redacted",
        "installdirname",
        "windows",
        "microsoft",
        "program",
        "programs",
        "files",
        "file",
        "system",
        "system32",
        "syswow64",
        "public",
        "default",
        "local",
        "localhost",
        "service",
        "services",
        "network",
        "admin",
        "administrator",
        "administrators",
        "guest",
        "data",
        "appdata",
        "roaming",
        "temp",
        "common",
        "shared",
        "software",
        "classes",
        "config",
        "client",
        "server",
        "office",
        "domain",
        "group",
        "global",
        "security",
        "update",
        "support",
        "desktop",
        "documents",
        "downloads",
        "onedrive",
        "personal",
        "corp",
        "corporation",
        "inc",
        "ltd",
        "llc",
        "gmbh",
        "services",
        "solutions",
        "systems",
        "technologies",
        "technology",
        "holdings",
        "company",
        "international",
        "the",
        "and",
        "com",
        "net",
        "org",
        "www",
        "nt authority",
        "nt service",
        "builtin",
        "authority",
        "azuread",
        "workgroup",
    },
)
_NAME_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_ALNUM = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
_GENERIC_ACCOUNTS = frozenset({"administrator", "admin", "guest", "defaultaccount", "wdagutilityaccount", "defaultuser0", "user"})
_SKIPPED_DOMAINS = frozenset({"nt authority", "nt service", "builtin", "window manager", "font driver host", "azuread", "iis apppool"})
_UPN_RE = re.compile(r"(?i)^([^@\\/\s]+)@([a-z0-9-]+(?:\.[a-z0-9-]+)+)$")


@dataclass
class RedactionContext:
    """What one customer's values are redacted with. Built per customer, after its stage-2 answers."""

    names: Set[str] = field(default_factory=set)
    install_dirs: List[str] = field(default_factory=list)
    own_domains: Set[str] = field(default_factory=set)
    _index: Optional[Dict[str, List[str]]] = None

    def add_name(self, value: Optional[str], min_len: int = 3) -> None:
        """Add one identity name (stripped of leading and trailing non-alphanumerics), unless it is a stopword."""
        if not value or len(self.names) >= MAX_NAMES:
            return
        name = " ".join(value.split()).strip().lower()
        start, end = 0, len(name)
        while start < end and name[start] not in _ALNUM:
            start += 1
        while end > start and name[end - 1] not in _ALNUM:
            end -= 1
        name = name[start:end]
        if len(name) < min_len or name in STOPLIST:
            return
        self.names.add(name)
        self._index = None

    def add_domain(self, domain: Optional[str]) -> None:
        if not domain:
            return
        d = domain.strip().lower().rstrip(".")
        if "." not in d or len(d) > 253 or len(self.own_domains) >= 200:
            return
        self.own_domains.add(d)
        # The organisation's label: contoso in contoso.com. Under a two-part public suffix (contoso.co.uk) it is "co",
        # shorter than a name may be, so nothing is added: the whole domain still counts
        labels = d.split(".")
        if len(labels) >= 2:
            self.add_name(labels[-2], min_len=4)

    def add_install_dir(self, name: Optional[str]) -> None:
        if name and re.fullmatch(r"[A-Za-z0-9._-]{1,64}", name) and name != TOKEN and name not in self.install_dirs:
            self.install_dirs.append(name)
            self.add_name(name)

    def name_index(self) -> Dict[str, List[str]]:
        """Names by their first alphanumeric run, longest first (built once)."""
        if self._index is None:
            index: Dict[str, List[str]] = {}
            for name in self.names:
                m = _NAME_TOKEN_RE.match(name)
                if m:
                    index.setdefault(m.group(0), []).append(name)
            for names in index.values():
                names.sort(key=len, reverse=True)
            self._index = index
        return self._index


def build_context(
    *,
    customer_code: str,
    customer_name: Optional[str],
    install_dirs: Iterable[str] = (),
    own_domains: Iterable[str] = (),
    hostnames: Iterable[str] = (),
    accounts: Iterable[str] = (),
) -> RedactionContext:
    """The customer's redaction context. ``accounts`` are the raw (unescaped) values of its User, SourceUser and
    TargetUser buckets: the domains, accounts and UPN domains in them are learned."""
    ctx = RedactionContext()
    ctx.add_name(customer_code)
    if customer_name:
        ctx.add_name(customer_name)
        for token in _NAME_TOKEN_RE.findall(customer_name):
            ctx.add_name(token, min_len=4)
    from app.active_response.services.sysmon_config import usable_as_install_dir

    if usable_as_install_dir(customer_code):
        ctx.add_install_dir(customer_code)
    for name in install_dirs:
        ctx.add_install_dir(name)
    for domain in own_domains:
        ctx.add_domain(domain)
    for hostname in hostnames:
        if not hostname:
            continue
        host = hostname.strip()
        ctx.add_name(host)
        if "." in host:
            first, _, rest = host.partition(".")
            ctx.add_name(first)
            if rest.count(".") >= 1:
                ctx.add_domain(rest)
    for account in accounts:
        learn_account(ctx, account)
    return ctx


def learn_account(ctx: RedactionContext, raw: str) -> None:
    """The names in one account value: DOMAIN\\account, account@domain.tld, HOST$."""
    value = unescape_value(raw).strip() if isinstance(raw, str) else ""
    if not value or well_known_principal(value):
        return
    upn = _UPN_RE.match(value)
    if upn:
        account, domain = upn.group(1), upn.group(2)
        if account.lower() not in _GENERIC_ACCOUNTS:
            ctx.add_name(account)
        ctx.add_domain(domain)
        return
    domain, sep, account = value.rpartition("\\")
    if sep:
        if domain.lower() not in _SKIPPED_DOMAINS:
            ctx.add_name(domain)
    else:
        account = value
    account = account.strip()
    if account.endswith("$"):
        ctx.add_name(account[:-1])
    elif account.lower() not in _GENERIC_ACCOUNTS:
        ctx.add_name(account)


# ---- per value ------------------------------------------------------------------------------------------------------


def _replace_names(piece: str, ctx: RedactionContext) -> str:
    """Every whole-word occurrence of a name (case-insensitive) in a piece without placeholders becomes <redacted>."""
    index = ctx.name_index()
    if not index:
        return piece
    out: List[str] = []
    i, n = 0, len(piece)
    lowered = piece.lower()
    if len(lowered) != n:  # a character whose lower case is longer: match on the original's ASCII lower case
        lowered = "".join(ch.lower() if ch.isascii() else ch for ch in piece)
    while i < n:
        if piece[i] in _ALNUM and (i == 0 or piece[i - 1] not in _ALNUM):
            j = i
            while j < n and piece[j] in _ALNUM:
                j += 1
            hit = None
            for name in index.get(lowered[i:j], ()):
                end = i + len(name)
                if lowered[i:end] == name and (end == n or piece[end] not in _ALNUM):
                    hit = end
                    break
            if hit is not None:
                out.append(REDACTED)
                i = hit
                continue
            out.append(piece[i:j])
            i = j
            continue
        out.append(piece[i])
        i += 1
    return "".join(out)


_PROTECTED_RE = re.compile("(" + _PLACEHOLDER_ALT + "|" + re.escape(TOKEN) + ")")


def redact_names(value: str, ctx: RedactionContext) -> str:
    """R5 over the parts of ``value`` that are not a placeholder or the install-folder token."""
    parts = _PROTECTED_RE.split(value)
    return "".join(part if i % 2 else _replace_names(part, ctx) for i, part in enumerate(parts))


def _profile_rest(rest: str) -> str:
    """What may follow C:\\Users\\<user> (owner decision D9)."""
    if not rest or rest[0] not in "\\/":
        return rest
    sep = rest[0]
    segments = [s for s in _SEP_RE.split(rest[1:])]
    if not segments or segments == [""]:
        return rest
    first = segments[0].lower()
    if first == "appdata":
        lowered = tuple(s.lower() for s in segments)
        for subtree in _APPDATA_SENSITIVE:
            if lowered[: len(subtree)] == subtree and len(segments) > len(subtree):
                kept = sep.join(segments[: len(subtree)])
                return sep + kept + sep + REDACTED
        return rest
    if first.startswith(".") or first in _NTUSER:
        return rest
    if first in _USER_CONTENT or first.startswith("onedrive"):
        if len(segments) == 1 or (len(segments) == 2 and segments[1] == ""):
            return rest
        return sep + segments[0] + sep + REDACTED
    return sep + REDACTED


def _redact_profiles(value: str) -> str:
    """Every profile folder (C:\\Users\\<name>, in every spelling the contract knows) becomes <user>, the whole folder
    name, and what follows it is cut down (D9). A path through ``.`` or ``..`` is not rewritten: the identity check
    refuses it afterwards."""
    pos = 0
    for _ in range(32):
        m = USER_DIR_RE.search(value, pos)
        if not m:
            break
        if m.group(2) == "<user>":
            pos = m.end(2)
            continue
        tail = value[m.end(2) :]
        # The rest of this path: up to a quote or whitespace-separated next token is unusual in these fields; the
        # whole remainder is treated as the path
        value = value[: m.start(2)] + "<user>" + _profile_rest(tail)
        pos = m.start(2) + len("<user>")
    return value


def _redact_unc(value: str) -> str:
    def sub(m: "re.Match[str]") -> str:
        return m.group("prefix") + "<host>" + (m.group("sep") or "")

    return UNC_ANY_RE.sub(sub, value)


def _redact_emails(value: str) -> str:
    if "@" not in value:
        return value

    def sub(m: "re.Match[str]") -> str:
        text = m.group(0)
        domain = text[text.rindex("@") + 1 :]
        labels = domain.split(".")
        if len(labels) >= 3 and labels[-1].lower() in _EMAIL_FILE_EXTS:
            return REDACTED + "." + labels[-1]
        return REDACTED

    return EMAIL_RE.sub(sub, value)


def _private_segment(segment: str, own_domains: Iterable[str]) -> bool:
    if not _DNS_SEGMENT_RE.fullmatch(segment):
        return False
    name = segment.lower().rstrip(".")
    if name.split(".")[-1].isdigit():
        return False
    return any(under(name, s) for s in PRIVATE_SUFFIXES) or any(under(name, d) for d in own_domains)


def _redact_private_segments(value: str, ctx: RedactionContext) -> str:
    parts = re.split(r"([\\/])", value)
    for i in range(0, len(parts), 2):
        if parts[i] and _private_segment(parts[i], ctx.own_domains):
            parts[i] = REDACTED
    return "".join(parts)


def _redact_document_name(value: str) -> str:
    if _SYSTEM_ROOT_RE.match(value):
        return value
    head, sep, last = max(value.rpartition("\\"), value.rpartition("/"), key=lambda t: len(t[0]))
    if not sep:
        return value
    m = _DOCUMENT_RE.match(last)
    if not m or m.group(2).lower() not in _DOCUMENT_EXTS or m.group(1) == REDACTED:
        return value
    return head + sep + REDACTED + "." + m.group(2)


def _redact_structure(value: str, ctx: RedactionContext) -> str:
    """R4, in order."""
    for install_dir in sorted(ctx.install_dirs, key=len, reverse=True):
        value = re.sub(r"(?i)(\\Program Files\\)" + re.escape(install_dir) + r"(?=[\\/]|$)", lambda m: m.group(1) + TOKEN, value)
    value = SID_RE.sub("<SID>", value)
    value = _redact_profiles(value)
    value = _redact_unc(value)
    value = _redact_emails(value)
    value = ONEDRIVE_BUSINESS_RE.sub(lambda m: m.group(1) + REDACTED, value)
    value = _redact_private_segments(value, ctx)
    value = _redact_document_name(value)
    return value


def _reason_rank(reason: str) -> int:
    return VALUE_REASON_ORDER.index(reason) if reason in VALUE_REASON_ORDER else len(VALUE_REASON_ORDER)


def _post_checks(field_name: str, value: str) -> Optional[Drop]:
    """R7: sysmon-sync's own checks on the redacted value."""
    if len(value) > settings.MAX_VALUE_LEN:
        return Drop("value-too-long")
    reasons = value_reasons(field_name, value)
    if reasons:
        # The service's choice when several apply: the most specific (a Kelvin sign is "look-alike", not "not-nfc")
        return Drop(f"value-rule-{min(reasons, key=_reason_rank)}")
    if identity_leak(field_name, value, REGISTRY_SERVICE_HIVES) is not None or service_leak(value) is not None:
        return Drop("identity-unredacted")
    return None


def redact_value(field_name: str, raw: object, ctx: RedactionContext) -> Union[str, Drop]:
    """The value to send for one field, or why it cannot be sent."""
    if not isinstance(raw, str):
        return Drop("value-invalid")
    if len(raw) > settings.MAX_RAW_VALUE_LEN:
        return Drop("value-too-long")
    value = unescape_value(raw)
    if _doubled_backslash(value):
        return Drop("value-rule-doubled-backslash")
    if value == "":
        return Drop("value-empty")
    if field_name in USER_FIELDS:
        # A service's virtual account (NT SERVICE\<name>) may still carry the customer's name
        value = redact_names(value, ctx) if well_known_principal(value) else REDACTED
        if not well_known_principal(value):
            value = REDACTED
    elif field_name in DNS_FIELDS:
        verdict = classify_dns(value, ctx.names, ctx.own_domains)
        if isinstance(verdict, Drop):
            return verdict
        value = verdict
    else:
        value = redact_names(_redact_structure(value, ctx), ctx)
    return _post_checks(field_name, value) or value


def redact_rule_name(raw: object, ctx: RedactionContext) -> Optional[str]:
    """The rule name to send, or None (the key is left out: leaving it out only removes information)."""
    if not isinstance(raw, str) or len(raw) > settings.MAX_RAW_VALUE_LEN:
        return None
    value = unescape_value(raw)
    if not value or _doubled_backslash(value):
        return None
    value = redact_names(_redact_structure(value, ctx), ctx)
    if not value or len(value) > settings.MAX_RULENAME_LEN or bad_characters(value):
        return None
    if not unicodedata.is_normalized("NFC", value) or rule_name_leak(value):
        return None
    return value


# ---- per pattern ----------------------------------------------------------------------------------------------------


@dataclass
class RedactedPattern:
    eid: int
    fields: Dict[str, str]
    key_fields: Dict[str, str]
    events: int
    endpoints: int
    days: int
    rule_name: Optional[str]
    pattern_key: bytes
    members: int = 1


def _canonical_key(eid: int, fields: Dict[str, str]) -> Tuple[Dict[str, str], bytes]:
    """The contract's key fields (with the derived EventType) and pattern key."""
    spec = EVENTS[eid]
    key: Dict[str, str] = {}
    if spec.event_types:
        key["EventType"] = fields.get("EventType") or spec.derive or ""
    for name in spec.key:
        if name != "EventType":
            key[name] = fields[name]
    if spec.destination:
        key["DestinationHostname"] = fields["DestinationHostname"]
    return key, pattern_key(eid, key)


def _same(values: Optional[List[str]], redact) -> Optional[str]:
    """The one redacted value all of ``values`` share, or None."""
    if not values:
        return None
    out: Set[str] = set()
    for raw in values:
        result = redact(raw)
        if result is None or isinstance(result, Drop):
            return None
        out.add(result)
        if len(out) > 1:
            return None
    return out.pop()


def redact_pattern(raw: RawPattern, ctx: RedactionContext) -> Union[RedactedPattern, Drop]:
    """P1-P4: the key fields (each must survive), the details all events share once redacted, the rule name, the cap of
    5 fields in the plan's order, and the pattern key."""
    plan = EVENT_PLAN[raw.eid]
    values: Dict[str, str] = {}
    for name in plan.key_fields:
        if name not in raw.key:
            return Drop("key-field-missing")
        if raw.eid == 3 and name == "DestinationHostname" and unescape_value(raw.key[name]).strip() in ("", "-"):
            return Drop("ip-destination")
        result = redact_value(name, raw.key[name], ctx)
        if isinstance(result, Drop):
            return result
        values[name] = result
    for name, _ in plan.details:
        same = _same(raw.details.get(name), lambda v, n=name: redact_value(n, v, ctx))
        if same is not None:
            values[name] = same
    fields = {name: values[name] for name in plan.order if name in values}
    # Never more than 5: the key fields come first in every plan's order
    fields = dict(list(fields.items())[: settings.MAX_FIELDS])
    rule_name = _same(raw.rule_names, lambda v: redact_rule_name(v, ctx))
    try:
        key_fields, pkey = _canonical_key(raw.eid, fields)
    except KeyError:
        return Drop("key-field-missing")
    return RedactedPattern(
        eid=raw.eid,
        fields=fields,
        key_fields=key_fields,
        events=raw.events,
        endpoints=raw.endpoints,
        days=raw.days,
        rule_name=rule_name,
        pattern_key=pkey,
    )


def merge_collisions(patterns: List[RedactedPattern]) -> Tuple[List[RedactedPattern], int]:
    """Patterns that redact to the same key become one (owner decision D12): events summed, endpoints the maximum (a
    merge never inflates prevalence), days ORed, a detail or the rule name kept only if every member had the same.
    Returns the merged patterns and how many were merged away."""
    by_key: Dict[bytes, RedactedPattern] = {}
    merged = 0
    for p in patterns:
        existing = by_key.get(p.pattern_key)
        if existing is None:
            by_key[p.pattern_key] = RedactedPattern(
                p.eid,
                dict(p.fields),
                dict(p.key_fields),
                p.events,
                p.endpoints,
                p.days,
                p.rule_name,
                p.pattern_key,
            )
            continue
        merged += 1
        existing.members += 1
        existing.events = min(settings.MAX_PATTERN_EVENTS, existing.events + p.events)
        existing.endpoints = max(existing.endpoints, p.endpoints)
        existing.days |= p.days
        key_names = set(existing.key_fields) | {"EventType"}
        for name in list(existing.fields):
            if name in key_names or name in EVENT_PLAN[p.eid].key_fields:
                continue
            if p.fields.get(name) != existing.fields[name]:
                del existing.fields[name]
        if existing.rule_name != p.rule_name:
            existing.rule_name = None
    return list(by_key.values()), merged


def user_values(raw_patterns: Iterable[RawPattern]) -> FrozenSet[str]:
    """The account values of every user detail in the customer's leaves (what build_context learns names from)."""
    out: Set[str] = set()
    for p in raw_patterns:
        out.update(p.accounts)
    return frozenset(out)
