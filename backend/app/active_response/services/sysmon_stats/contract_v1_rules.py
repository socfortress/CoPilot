"""Vendored from sysmon-sync (socfortress/sysmon-sync, commit 034dcbd, app/reports/cka_rules.py), which vendors them
from the installer repo, Client-Kickstart-Automated, at commit 0d86099.

These are the value and identity rules sysmon-sync applies to every value of a fleet noise report (contract v1). CoPilot
runs the same rules on its own report before it sends it, so the service should only ever see accepted patterns: a
report the service would refuse wastes a week. The rules are copied, not re-invented; only the loader functions the
service uses for its candidates (self_check) are left out. Nothing here rewrites a value.

When sysmon-sync changes these rules, copy the new version here and name its commit above.
tests/test_sysmon_stats_contract.py compares the constants and runs the service's own validator on CoPilot's reports
when SYSMON_SYNC_DIR names a sysmon-sync checkout. The regexes use possessive quantifiers (fold_dots): Python 3.11 or
later.
"""

from __future__ import annotations

import re
import unicodedata

CKA_COMMIT = "0d86099"

# ---- context.py --------------------------------------------------------------------------
TOKEN = "__INSTALLDIRNAME__"
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")

# ---- policy.toml -------------------------------------------------------------------------
PATH_FIELDS = [
    "Image",
    "ParentImage",
    "SourceImage",
    "TargetImage",
    "ImageLoaded",
    "TargetFilename",
    "CurrentDirectory",
    "StartModule",
    "CommandLine",
    "ParentCommandLine",
]
DNS_FIELDS = ["QueryName", "DestinationHostname"]
UNSTABLE_FIELDS = [
    "RuleName",
    "UtcTime",
    "ProcessGuid",
    "ProcessId",
    "ParentProcessGuid",
    "ParentProcessId",
    "SourceProcessGuid",
    "SourceProcessId",
    "SourceProcessGUID",
    "SourceThreadId",
    "TargetProcessGuid",
    "TargetProcessId",
    "TargetProcessGUID",
    "NewThreadId",
    "LogonGuid",
    "LogonId",
    "CreationUtcTime",
    "PreviousCreationUtcTime",
    "StartAddress",
    "SourcePort",
]
REGISTRY_SERVICE_HIVES = [".DEFAULT", "S-1-5-18", "S-1-5-19", "S-1-5-20"]
POLICY = {
    "path_fields": PATH_FIELDS,
    "dns_fields": DNS_FIELDS,
    "unstable_fields": UNSTABLE_FIELDS,
    "registry_service_hives": REGISTRY_SERVICE_HIVES,
}

# ---- sysmon/schema/sysmon-4.60-fields.json (the accepted event types only) ----------------
SCHEMA: dict[str, list[str]] = {
    "ProcessCreate": [
        "RuleName",
        "UtcTime",
        "ProcessGuid",
        "ProcessId",
        "Image",
        "FileVersion",
        "Description",
        "Product",
        "Company",
        "OriginalFileName",
        "CommandLine",
        "CurrentDirectory",
        "User",
        "LogonGuid",
        "LogonId",
        "TerminalSessionId",
        "IntegrityLevel",
        "Hashes",
        "ParentProcessGuid",
        "ParentProcessId",
        "ParentImage",
        "ParentCommandLine",
        "ParentUser",
    ],
    "FileCreateTime": [
        "RuleName",
        "UtcTime",
        "ProcessGuid",
        "ProcessId",
        "Image",
        "TargetFilename",
        "CreationUtcTime",
        "PreviousCreationUtcTime",
        "User",
    ],
    "NetworkConnect": [
        "RuleName",
        "UtcTime",
        "ProcessGuid",
        "ProcessId",
        "Image",
        "User",
        "Protocol",
        "Initiated",
        "SourceIsIpv6",
        "SourceIp",
        "SourceHostname",
        "SourcePort",
        "SourcePortName",
        "DestinationIsIpv6",
        "DestinationIp",
        "DestinationHostname",
        "DestinationPort",
        "DestinationPortName",
    ],
    "DriverLoad": ["RuleName", "UtcTime", "ImageLoaded", "Hashes", "Signed", "Signature", "SignatureStatus"],
    "ImageLoad": [
        "RuleName",
        "UtcTime",
        "ProcessGuid",
        "ProcessId",
        "Image",
        "ImageLoaded",
        "FileVersion",
        "Description",
        "Product",
        "Company",
        "OriginalFileName",
        "Hashes",
        "Signed",
        "Signature",
        "SignatureStatus",
        "User",
    ],
    "CreateRemoteThread": [
        "RuleName",
        "UtcTime",
        "SourceProcessGuid",
        "SourceProcessId",
        "SourceImage",
        "TargetProcessGuid",
        "TargetProcessId",
        "TargetImage",
        "NewThreadId",
        "StartAddress",
        "StartModule",
        "StartFunction",
        "SourceUser",
        "TargetUser",
    ],
    "ProcessAccess": [
        "RuleName",
        "UtcTime",
        "SourceProcessGUID",
        "SourceProcessId",
        "SourceThreadId",
        "SourceImage",
        "TargetProcessGUID",
        "TargetProcessId",
        "TargetImage",
        "GrantedAccess",
        "CallTrace",
        "SourceUser",
        "TargetUser",
    ],
    "FileCreate": ["RuleName", "UtcTime", "ProcessGuid", "ProcessId", "Image", "TargetFilename", "CreationUtcTime", "User"],
    "RegistryEvent": [
        "RuleName",
        "EventType",
        "UtcTime",
        "ProcessGuid",
        "ProcessId",
        "Image",
        "TargetObject",
        "Details",
        "NewName",
        "User",
    ],
    "FileCreateStreamHash": [
        "RuleName",
        "UtcTime",
        "ProcessGuid",
        "ProcessId",
        "Image",
        "TargetFilename",
        "CreationUtcTime",
        "Hash",
        "Contents",
        "User",
    ],
    "PipeEvent": ["RuleName", "EventType", "UtcTime", "ProcessGuid", "ProcessId", "PipeName", "Image", "User"],
    "DnsQuery": ["RuleName", "UtcTime", "ProcessGuid", "ProcessId", "QueryName", "QueryStatus", "QueryResults", "Image", "User"],
    "FileDelete": [
        "RuleName",
        "UtcTime",
        "ProcessGuid",
        "ProcessId",
        "User",
        "Image",
        "TargetFilename",
        "Hashes",
        "IsExecutable",
        "Archived",
    ],
    "ProcessTampering": ["RuleName", "UtcTime", "ProcessGuid", "ProcessId", "Image", "Type", "User"],
    "FileDeleteDetected": ["RuleName", "UtcTime", "ProcessGuid", "ProcessId", "User", "Image", "TargetFilename", "Hashes", "IsExecutable"],
}
EVENT_IDS: dict[int, str] = {
    1: "ProcessCreate",
    2: "FileCreateTime",
    3: "NetworkConnect",
    6: "DriverLoad",
    7: "ImageLoad",
    8: "CreateRemoteThread",
    10: "ProcessAccess",
    11: "FileCreate",
    12: "RegistryEvent",
    13: "RegistryEvent",
    14: "RegistryEvent",
    15: "FileCreateStreamHash",
    17: "PipeEvent",
    18: "PipeEvent",
    22: "DnsQuery",
    23: "FileDelete",
    25: "ProcessTampering",
    26: "FileDeleteDetected",
}

# ---- candidates.py: format, limits, regexes ------------------------------------------------
FORMAT = "socfortress-sysmon-candidates/1"
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_CANDIDATES = 500
MAX_FIELDS = 16  # observed fields per candidate
MAX_PREVALENCE = 2000  # environments per candidate
MAX_TAGS = 8
MAX_WEEKS = 106
MAX_VALUE_LEN = 1024
MAX_COMMAND_LINE_LEN = 2048  # CommandLine, ParentCommandLine
MAX_RULENAME_LEN = 256
MAX_COUNT = 10**12
MAX_REASONS = 20  # problems recorded per invalid candidate
COMMAND_LINE_FIELDS = ("CommandLine", "ParentCommandLine")
REGISTRY_KEY_FIELDS = ("TargetObject", "NewName")

TOP_KEYS = {"format", "generated_at", "window", "candidates"}
WINDOW_KEYS = {"from", "to"}
CANDIDATE_KEYS = {"candidate_id", "event", "fields", "absent", "hashed", "rule_name", "totals", "first_seen", "last_seen", "prevalence"}
TOTALS_KEYS = {"events", "endpoints", "environments"}
PREVALENCE_REQUIRED = {"env_id", "owner_id", "trial", "env_first_seen", "tags", "endpoints", "events", "days", "weeks", "config"}
PREVALENCE_KEYS = PREVALENCE_REQUIRED | {"customer_ref"}
CONFIG_WORDS = ("customized", "unknown")

CANDIDATE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}")
ENV_ID_RE = re.compile(r"env_[A-Za-z0-9_-]{8,64}")
OWNER_ID_RE = re.compile(r"own_[A-Za-z0-9_-]{8,64}")
TAG_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DATETIME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})Z")
WEEK_RE = re.compile(r"(\d{4})-W(\d{2})")

PLACEHOLDERS = ("<user>", "<SID>", "<host>", "<redacted>")
PLACEHOLDER_LIKE = re.compile(r"<[A-Za-z][A-Za-z0-9_-]{0,31}>")
TEMPLATE_TOKEN_LIKE = re.compile(r"__[A-Z0-9_]+__")
ENV_VAR_RE = re.compile(r"%[A-Za-z_][A-Za-z0-9_()]*%")
BAD_CATEGORIES = {"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"}

EVENT_IDS_BY_TYPE = {
    "RegistryEvent": {"CreateKey": 12, "DeleteKey": 12, "CreateValue": 12, "DeleteValue": 12, "SetValue": 13, "RenameKey": 14},
    "PipeEvent": {"CreatePipe": 17, "ConnectPipe": 18},
    "WmiEvent": {"WmiFilterEvent": 19, "WmiConsumerEvent": 20, "WmiBindingEvent": 21},
}

# ---- names.py ----------------------------------------------------------------------------
CONFUSABLES = frozenset(
    "\u017f\u0131\u0130\u212a\u212b" + "".join(chr(c) for c in range(0xFB00, 0xFB07)) + "".join(chr(c) for c in range(0xFF01, 0xFF5F)),
)


def confusable(s: str) -> str | None:
    """The first character of S in CONFUSABLES, as 'U+XXXX', or None."""
    for ch in s:
        if ch in CONFUSABLES:
            return f"U+{ord(ch):04X}"
    return None


def program_head(cmd: str) -> str:
    """The program a command line starts with, as written: its first token (a quoted string's content)."""
    m = re.match(r'\s*(?:"([^"]*)"?|(\S+))', cmd)
    if not m:
        return ""
    return m.group(1) if m.group(1) is not None else m.group(2) or ""


# ---- candidates.py: value checks ---------------------------------------------------------
def bad_characters(s: str) -> str | None:
    """The first forbidden character as 'U+XXXX (category)', or None."""
    for ch in s:
        cat = unicodedata.category(ch)
        if cat in BAD_CATEGORIES:
            return f"U+{ord(ch):04X} ({cat})"
    return None


def value_problems(field_name: str, value) -> list[str]:
    """Why VALUE can't be a Sysmon field value in a candidate (or a drafted condition). Never echoes it."""
    if not isinstance(value, str):
        return [f"{field_name}: must be a string"]
    if value == "":
        return [f"{field_name}: empty (Sysmon logs '-' for an empty field)"]
    out = []
    cap = MAX_COMMAND_LINE_LEN if field_name in COMMAND_LINE_FIELDS else MAX_VALUE_LEN
    if len(value) > cap:
        out.append(f"{field_name}: longer than {cap} characters")
    bad = bad_characters(value)
    if bad:
        out.append(f"{field_name}: a control, format (bidi, zero-width), unassigned or separator character {bad}")
    elif not unicodedata.is_normalized("NFC", value):
        out.append(f"{field_name}: not Unicode NFC")
    if "*" in value:
        out.append(f"{field_name}: '*' (Sysmon has no wildcards; a pattern must carry the value as logged)")
    if ENV_VAR_RE.search(value):
        out.append(f"{field_name}: a %VARIABLE% (Sysmon logs expanded values)")
    rest = value[2:] if value.startswith("\\\\") else value
    if "\\\\" in rest:
        out.append(f"{field_name}: a doubled backslash (JSON-escaped twice?) other than a leading UNC \\\\")
    for m in PLACEHOLDER_LIKE.finditer(value):
        if m.group(0) not in PLACEHOLDERS:
            out.append(f"{field_name}: an unknown placeholder (allowed: {', '.join(PLACEHOLDERS)}, {TOKEN})")
            break
    for m in TEMPLATE_TOKEN_LIKE.finditer(value):
        if m.group(0) != TOKEN:
            out.append(f"{field_name}: an unknown template token (only {TOKEN})")
            break
    return out


def confusable_problems(field_name: str, value, policy: dict) -> list[str]:
    """A look-alike character (CONFUSABLES) in a path field, a command line's program name or a registry key."""
    if not isinstance(value, str):
        return []
    if field_name in COMMAND_LINE_FIELDS:
        where, text = "the program name it starts with", program_head(value)
    elif field_name in REGISTRY_KEY_FIELDS:
        where, text = "the key", value
    elif field_name in policy["path_fields"]:
        where, text = "the path", value
    else:
        return []
    bad = confusable(text)
    if not bad:
        return []
    return [
        f"{field_name}: a look-alike character {bad} in {where} (long s, dotless i, Kelvin or Angstrom sign, a "
        "Latin ligature or a full-width form): Windows' case-insensitive compare may or may not read it as an "
        "ASCII letter, so the name it spells can't be judged",
    ]


def dns_name_problems(field_name: str, value, policy: dict) -> list[str]:
    """A non-ASCII character in a DNS name (QueryName, DestinationHostname). Never echoes the value."""
    if not isinstance(value, str) or field_name not in policy["dns_fields"]:
        return []
    ch = next((ch for ch in value if not ch.isascii()), None)
    if ch is None:
        return []
    return [
        f"{field_name}: a non-ASCII character U+{ord(ch):04X} in a DNS name (IDNA reads an ideographic or "
        "full-width full stop as a dot and a full-width letter as an ASCII one, so the name it resolves as can't "
        "be judged against the deny lists; names on the wire are ASCII, an internationalised one as xn--)",
    ]


# ---- alert.py: identities ----------------------------------------------------------------
HKU_HIVE_RE = re.compile(r"(?i)\bHKU\\([^\\;]+)(?:\\|$|;)")
SERVICE_HIVES = (".DEFAULT", "S-1-5-18", "S-1-5-19", "S-1-5-20")
SID_RE = re.compile(r"(?i)\bS-1-(?:5-21|12-1)(?:-\d+)+(?:_Classes)?")
_VOLUME_ROOT = r"(?:[A-Z]:|\\Device\\[^\\/\s\"]+(?:\\Partition\d+)?|\\(?:\\[?.]|\?\?)\\Volume\{[^}\\/\s\"]*\}" r"|(?<![^\s\"'=,(;]))"
USER_DIR_RE = re.compile(
    r"(?i)(" + _VOLUME_ROOT + r"[\\/]+(?:Users|Documents and Settings|DOCUME~\d)[\\/]+)"
    r"(?!(?:Public|Default|All Users|Default User)(?:[\\/\"]|$))([^\\/\"]+)",
)
UNC_ANY_RE = re.compile(
    r"(?i)(?P<prefix>(?P<bs>(?:^|(?<=[\s\"'=,(;:]))(?:\\\\(?:[?.]\\UNC\\)?|\\\?\?\\UNC\\)"
    r"|\\Device\\(?:Mup|LanmanRedirector|WebDavRedirector|RdpDr)\\(?:;[^\\/]*\\)*)"
    r"|(?:^|(?<=[\s\"'=,(;]))//(?:[?.]/UNC/)?)"
    r"(?![?.][\\/])(?P<host>[^\\/\s\"';]+)(?P<sep>[\\/]|(?(bs)(?=[\s\"',;)&|<>]|$)|(?!)))",
)
USER_FIELDS = ("User", "ParentUser", "SourceUser", "TargetUser")
WELL_KNOWN_DOMAINS = ("nt authority", "nt service", "window manager", "font driver host", "builtin")
WELL_KNOWN_ACCOUNTS = ("system", "local service", "network service", "localsystem", "-")
REDACTION = ("<user>", "<SID>", "<host>", "<redacted>")


def well_known_principal(value: str) -> bool:
    """True for a built-in or virtual service account (NT AUTHORITY\\SYSTEM, NT SERVICE\\<service>, ...)."""
    v = value.strip().lower()
    if v in WELL_KNOWN_ACCOUNTS:
        return True
    dom, sep, name = v.partition("\\")
    return bool(sep) and dom in WELL_KNOWN_DOMAINS and bool(name.strip()) and "\\" not in name


def fold_dots(value: str) -> str:
    """VALUE with its . and .. path components resolved (C:\\Windows\\..\\Users\\x is C:\\Users\\x), so a
    profile folder spelled through them is still seen."""
    v = re.sub(r"(?<=[\\/])\.(?:[\\/]+|$)", "", value)
    while True:
        w = re.sub(r"(?<![\\/])[\\/]++(?!\.\.(?:[\\/]|$))[^\\/\"]++[\\/]++\.\.(?=[\\/]|$|[\s\"])", "", v, count=1)
        if w == v:
            return re.sub(r"(?i)([A-Z]:)(?:[\\/]+\.\.(?=[\\/]|$))+", r"\1", v)  # C:\..\ is C:\
        v = w


def _redacted(s: str) -> bool:
    return any(p in s for p in REDACTION)


def identity_leak(field: str, value: str, service_hives=SERVICE_HIVES) -> str | None:
    """What in VALUE identifies a person, a host or an organisation and is NOT redacted, or None (never the
    literal itself): an account in a user field other than a well-known principal, a user's profile folder,
    a user's registry hive, a user SID, or a UNC host. The redacted forms (<user>, <SID>, <host>,
    <redacted>) are fine."""
    if field in USER_FIELDS:
        parts = value.split("\\")
        if not (well_known_principal(value) or all(p.strip() in REDACTION for p in parts)):
            return "an account name (only a well-known service principal, e.g. NT AUTHORITY\\SYSTEM, or <redacted>)"
    for m in (*USER_DIR_RE.finditer(value), *USER_DIR_RE.finditer(fold_dots(value))):
        if not _redacted(m.group(2)):
            return "a user's profile folder (C:\\Users\\<name>\\, in any spelling)"
    service = {h.lower() for h in service_hives}
    for m in HKU_HIVE_RE.finditer(value):
        if m.group(1).lower() not in service and not _redacted(m.group(1)):
            return "a user's registry hive (HKU\\<SID>\\)"
    if SID_RE.search(value):
        return "a user's SID"
    for m in UNC_ANY_RE.finditer(value):
        if not _redacted(m.group("host")):
            return "a host name (UNC path, in any spelling)"
    return None


# ---- reason codes (this service) ---------------------------------------------------------
# CKA problem text (after the "<field>: " prefix) -> the reason code this service returns. Matched by prefix, in
# order; a problem no prefix matches maps to "value-invalid" (the tests assert that none does).
_PROBLEM_REASONS = (
    ("empty", "value-empty"),
    ("longer than", "value-too-long"),
    ("a control, format", "bad-character"),
    ("not Unicode NFC", "not-nfc"),
    ("'*'", "wildcard"),
    ("a %VARIABLE%", "env-var"),
    ("a doubled backslash", "doubled-backslash"),
    ("an unknown placeholder", "unknown-placeholder"),
    ("an unknown template token", "unknown-token"),
    ("a look-alike character", "look-alike"),
    ("a non-ASCII character", "non-ascii-dns"),
    ("must be a string", "value-invalid"),
)


def problem_reason(field_name: str, problem: str) -> str:
    """The reason code of one CKA problem string about FIELD_NAME."""
    text = problem[len(field_name) + 2 :] if problem.startswith(field_name + ": ") else problem
    for prefix, reason in _PROBLEM_REASONS:
        if text.startswith(prefix):
            return reason
    return "value-invalid"


def value_reasons(field_name: str, value: str) -> list[str]:
    """Every reason code CKA's loader would give VALUE in FIELD_NAME (value rules, look-alikes, DNS names), in
    CKA's order. Identity leaks are separate (identity_leak): they refuse a whole report."""
    problems = (
        value_problems(field_name, value) + confusable_problems(field_name, value, POLICY) + dns_name_problems(field_name, value, POLICY)
    )
    return [problem_reason(field_name, p) for p in problems]
