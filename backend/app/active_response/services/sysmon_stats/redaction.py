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
R4. Everything else, structurally: the install folder, user SIDs (also glued to a word: GoogleUpdateTaskUser<SID>Core),
    profile folders (also through an admin share and on a non-default profile root; what may follow them, below), UNC
    hosts and what a share may hold (the first segment below a share that is not a well-known one may be a user's:
    home, roaming-profile and redirected-folder shares; it is <redacted> also as the last segment, unless it is a
    program, script or installer file below a share not named for per-user folders), e-mail addresses, OneDrive
    for Business folders, the domain folder of SYSVOL, host names in registry keys (printer connections, print
    servers, Remote Desktop servers), private-domain and own-domain path segments, IPv4 and IPv6 addresses (not a
    version in the places Windows writes one: GAC, AppX, WinSxS), document file names.
R5. The customer's own names (code, name, its distinctive words, its name written as one word, install folders, agent
    host names, the accounts and domains seen in its events, admin hints), matched as whole words, become
    ``<redacted>``; its name written as one word (``acmewidgets``) also inside a longer word.

Before any value of a report is redacted, ``learn_from_patterns`` reads every value of the customer's patterns for its
own domains (dns_policy.owner_domain, a SYSVOL folder, the host of a SYSVOL or NETLOGON share): what one value reveals
redacts every other, whatever the order of the patterns.
R7. sysmon-sync's checks: at most 1024 characters, the value rules (``value_reasons``), and no identity leak. Any
    failure drops the pattern.

Values are never case-folded or normalised: they stay as logged, so a suggestion built from them matches real events.
"""
import ipaddress
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
from app.active_response.services.sysmon_stats.contract_v1_rules import _VOLUME_ROOT
from app.active_response.services.sysmon_stats.contract_v1_rules import (
    REGISTRY_SERVICE_HIVES,
)
from app.active_response.services.sysmon_stats.contract_v1_rules import SID_PATTERN
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
from app.active_response.services.sysmon_stats.dns_policy import owner_domain
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
# A user's SID wherever it is, also glued to a word (Tasks\GoogleUpdateTaskUserS-1-5-21-...-1001Core becomes
# Tasks\GoogleUpdateTaskUser<SID>Core): the contract's own SID_PATTERN, no leading word boundary. A Classes hive keeps
# its suffix (HKU\<SID>_Classes\).
SID_RE = re.compile(r"(?i)" + SID_PATTERN)
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
_SPLIT_KEEP_RE = re.compile(r"([\\/])")
# Profile roots other than \Users: roaming-profile, home-folder and Remote Desktop profile folders on a volume's root
# (also through an admin share: \\fs01\D$\Home\jsmith)
_OTHER_PROFILE_ROOTS = (
    "Profiles",
    "UserProfiles",
    "User Profiles",
    "RoamingProfiles",
    "Roaming Profiles",
    "TSProfiles",
    "Home",
    "Homes",
    "HomeDirs",
    "UserHome",
    "UserHomes",
    "UserData",
    "RedirectedFolders",
    "FolderRedirection",
)
OTHER_PROFILE_ROOT_RE = re.compile(
    r"(?i)(" + _VOLUME_ROOT + r"[\\/]+(?:" + "|".join(re.escape(root) for root in _OTHER_PROFILE_ROOTS) + r")[\\/]+)"
    r"(?!(?:Public|Default|All Users|Default User)(?:[\\/\"]|$))([^\\/\"]+)",
)
_PROFILE_ROOTS = frozenset({"users", "documents and settings"} | {root.lower() for root in _OTHER_PROFILE_ROOTS})
_DOCUME_RE = re.compile(r"(?i)docume~\d")
_SHARED_PROFILES = frozenset({"public", "default", "all users", "default user"})
# Shares whose first folder is never a user's: Active Directory's, the admin shares, the printer drivers'
_WELL_KNOWN_SHARES = frozenset({"sysvol", "netlogon", "ipc$", "admin$", "print$"})
# A volume's root: a drive's admin share (C$) on any host, a bare drive letter (C) only on tsclient (a drive Remote
# Desktop redirects). On any other host a one-letter share is an ordinary one (a file server's H for home folders).
_ADMIN_DRIVE_SHARE_RE = re.compile(r"(?i)[a-z]\$")
_REDIRECTED_DRIVE_RE = re.compile(r"(?i)[a-z]")
_RDP_REDIRECTOR_HOST = "tsclient"
# A share named for per-user folders (home, roaming-profile, redirected-folder and user shares: home$, Homes,
# HomeDirs, Profiles$, TSProfiles, Redirect$, RedirectedFolders, Folders$, Users, UserData): what is directly below it
# is a user's, a file too
_PER_USER_SHARE_RE = re.compile(r"(?i)home|profile|redirect|folder|^user")
# The only thing kept directly below any other share, and only as the path's last segment: a program, script or
# installer file (a deployment share's agent.msi, setup.exe, logon.ps1). Never a folder, never another kind of file.
_PROGRAM_EXTS = frozenset(
    {
        "exe",
        "dll",
        "sys",
        "ocx",
        "cpl",
        "scr",
        "msi",
        "msp",
        "msu",
        "mst",
        "msix",
        "msixbundle",
        "appx",
        "appxbundle",
        "cab",
        "inf",
        "ps1",
        "psm1",
        "psd1",
        "bat",
        "cmd",
        "vbs",
        "vbe",
        "js",
        "jse",
        "wsf",
        "wsh",
        "hta",
    },
)
_PROGRAM_FILE_RE = re.compile(r"(?i)[^\s<>][^<>]*\.([a-z0-9]{2,10})")
# What may follow a SYSVOL folder without being the domain's name
_SYSVOL_KEEP = frozenset({"sysvol", "domain", "staging", "staging areas", "sysvol_dfsr", "policies", "scripts"})
_GUID_RE = re.compile(r"\{[0-9A-Fa-f-]{1,64}\}")
# IP addresses (owner decision D1: never sent). A dotted quad not inside a longer run of numbers and dots (a version)
_IP_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
IPV4_RE = re.compile(rf"(?<![\d.]){_IP_OCTET}\.{_IP_OCTET}\.{_IP_OCTET}\.{_IP_OCTET}(?!\d|\.\d)")
IPV6_RE = re.compile(r"(?i)(?<![0-9a-z:])((?:[0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4}(?:%[0-9a-z_.-]{1,32})?)(?![0-9a-z:])")
# Where Windows writes a version, never an address: _<v>__<public key token> (GAC), _<v>_<architecture>_ (AppX,
# WinSxS), _<v>_<language>_ (WinSxS)
_VERSION_TAIL_RE = re.compile(r"(?i)__[0-9a-f]{16}(?![0-9a-z])|_(?:x86|x64|arm|arm64|amd64|neutral|none|msil|wow64|[a-z]{2}-[a-z]{2,4})_")

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
    # The first label of each of its host names (what dns_policy.owner_domain learns <host>.<domain> from)
    hosts: Set[str] = field(default_factory=set)
    # Its name written as one word (acmewidgets): redacted inside longer words too, in paths and DNS labels
    compounds: Set[str] = field(default_factory=set)
    # Also dropped inside a longer DNS label (contosoinc.com): its code and a one-word name
    dns_fragments: Set[str] = field(default_factory=set)
    _index: Optional[Dict[str, List[str]]] = None

    @staticmethod
    def clean(value: Optional[str], min_len: int = 3) -> Optional[str]:
        """``value`` as an identity name (lowercase, stripped of leading and trailing non-alphanumerics), or None when
        it is too short or a stopword."""
        if not value:
            return None
        name = " ".join(value.split()).strip().lower()
        start, end = 0, len(name)
        while start < end and name[start] not in _ALNUM:
            start += 1
        while end > start and name[end - 1] not in _ALNUM:
            end -= 1
        name = name[start:end]
        if len(name) < min_len or name in STOPLIST:
            return None
        return name

    def add_name(self, value: Optional[str], min_len: int = 3) -> None:
        """Add one identity name (stripped of leading and trailing non-alphanumerics), unless it is a stopword."""
        if len(self.names) >= MAX_NAMES:
            return
        name = self.clean(value, min_len)
        if name is None or name in self.names:
            return
        self.names.add(name)
        self._index = None

    def add_host(self, hostname: Optional[str]) -> None:
        """One of its host names: a short name (WS-0142) or a fully qualified one (WS-0142.corp.contoso.com, whose
        domain is learned; a single-label AD domain becomes a name)."""
        host = (hostname or "").strip().rstrip(".")
        if not host:
            return
        self.add_name(host)
        first, dot, rest = host.partition(".")
        label = self.clean(first)
        if label is not None and len(self.hosts) < MAX_NAMES:
            self.hosts.add(label)
        if dot:
            self.add_name(first)
            if "." in rest:
                self.add_domain(rest)
            else:
                self.add_name(rest)

    def add_compound(self, words: Iterable[str]) -> None:
        """A name of several words, written as one (acmewidgets) and hyphenated (acme-widgets), with and without its
        stopwords (Ltd, Inc, ...)."""
        tokens = [w.lower() for w in words if w]
        kept = [t for t in tokens if t not in STOPLIST]
        for group in (tokens, kept):
            if len(group) < 2:
                continue
            joined = self.clean("".join(group), min_len=6)
            if joined is not None:
                self.add_name(joined, min_len=6)
                self.compounds.add(joined)
                self.dns_fragments.add(joined)
            self.add_name("-".join(group), min_len=6)

    def add_dns_fragment(self, value: Optional[str]) -> None:
        fragment = self.clean(value, min_len=6)
        if fragment is not None and _NAME_TOKEN_RE.fullmatch(fragment):
            self.dns_fragments.add(fragment)

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
    ctx.add_compound(_NAME_TOKEN_RE.findall(customer_code or ""))
    ctx.add_dns_fragment(customer_code)
    if customer_name:
        ctx.add_name(customer_name)
        tokens = _NAME_TOKEN_RE.findall(customer_name)
        for token in tokens:
            ctx.add_name(token, min_len=4)
        ctx.add_compound(tokens)
        if len(tokens) == 1:
            ctx.add_dns_fragment(tokens[0])
    from app.active_response.services.sysmon_config import usable_as_install_dir

    if usable_as_install_dir(customer_code):
        ctx.add_install_dir(customer_code)
    for name in install_dirs:
        ctx.add_install_dir(name)
    for domain in own_domains:
        ctx.add_domain(domain)
    for hostname in hostnames:
        if isinstance(hostname, str):
            ctx.add_host(hostname)
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


def _learn_domain(ctx: RedactionContext, domain: Optional[str]) -> None:
    if not domain:
        return
    if "." in domain:
        ctx.add_domain(domain)
    else:
        ctx.add_name(domain)


def _learn_path(ctx: RedactionContext, value: str) -> None:
    r"""The domain a path reveals: the folder below SYSVOL (\\<domain>\SYSVOL\<domain>\, ...\GroupPolicy\DataStore\0
    \sysvol\<domain>\), and the host of a SYSVOL or NETLOGON share."""
    lowered = value.lower()
    if "sysvol" not in lowered and "netlogon" not in lowered:
        return
    parts = _SPLIT_KEEP_RE.split(value)[0::2]
    for i in range(1, len(parts)):
        if parts[i - 1].lower() == "sysvol" and parts[i] and parts[i].lower() not in _SYSVOL_KEEP and "." in parts[i]:
            if _DNS_SEGMENT_RE.fullmatch(parts[i]):
                _learn_domain(ctx, parts[i].lower().rstrip("."))
    for m in UNC_ANY_RE.finditer(value):
        share = _SPLIT_KEEP_RE.split(value[m.end() :], maxsplit=1)[0].lower()
        host = m.group("host").lower().rstrip(".")
        if share in ("sysvol", "netlogon") and _DNS_SEGMENT_RE.fullmatch(host):
            _learn_domain(ctx, host)


def learn_from_patterns(ctx: RedactionContext, patterns: Iterable[RawPattern]) -> None:
    """Learn the customer's own domains from every value of its patterns, before any is redacted (so the order of the
    patterns does not matter): the DNS names (dns_policy.owner_domain) and the SYSVOL and NETLOGON paths."""
    for p in patterns:
        values: List[Tuple[str, object]] = list(p.key.items())
        for name, detail in p.details.items():
            values.extend((name, v) for v in (detail or []))
        for name, raw in values:
            if not isinstance(raw, str) or len(raw) > settings.MAX_RAW_VALUE_LEN or name in USER_FIELDS:
                continue
            value = unescape_value(raw)
            if name in DNS_FIELDS:
                _learn_domain(ctx, owner_domain(value, ctx.hosts))
            else:
                _learn_path(ctx, value)


# ---- per value ------------------------------------------------------------------------------------------------------


def _replace_names(piece: str, ctx: RedactionContext) -> str:
    """Every whole-word occurrence of a name (case-insensitive) in a piece without placeholders becomes <redacted>."""
    index = ctx.name_index()
    if not index and not ctx.compounds:
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
            if any(c in lowered[i:j] for c in ctx.compounds):
                # Its name written as one word, inside a longer one (AcmeWidgetsIT): the whole word
                out.append(REDACTED)
                i = j
                continue
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
    for regex in (USER_DIR_RE, OTHER_PROFILE_ROOT_RE):
        pos = 0
        for _ in range(32):
            m = regex.search(value, pos)
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


def _program_file(segment: str) -> bool:
    """A program, script or installer file name (agent.msi, Setup 2.1.exe, logon.ps1)."""
    m = _PROGRAM_FILE_RE.fullmatch(segment)
    return bool(m) and m.group(1).lower() in _PROGRAM_EXTS


def _share_tail(tail: str, host: str) -> str:
    r"""What follows \\<host>\ in a UNC path: the share, then its folders. Empty segments (a doubled separator) are
    skipped, never taken for the segment that decides.

    - SYSVOL, NETLOGON, ADMIN$, IPC$, print$: kept (the folder below SYSVOL is ``_redact_sysvol``'s).
    - A volume's root (a drive's admin share C$, or \\tsclient\C, a drive Remote Desktop redirects): its first folder is
      the volume's (Windows, Program Files) and kept; a profile folder below \Users or another profile root (\Home,
      \Profiles, ...) becomes <user>, and what follows it is cut down as in a profile (D9).
    - Any other share: its first segment may be a user's (a home, roaming-profile or redirected-folder share:
      \\fs01\home$\jsmith, \\fs01\Profiles$\jsmith.V6, \\fs01\Users\jsmith), also when it is the path's last segment:
      it becomes <redacted>, and what follows it is cut down as in a profile (D9). The one exception is a program,
      script or installer file as the last segment, directly below a share not named for per-user folders
      (\\fs01\deploy$\agent.msi is kept, \\fs01\home$\x.exe is not). A folder is never kept, whatever the share's name:
      a deployment share cannot be told from a home share by its name, so \\fs01\deploy$\Contoso\setup.exe becomes
      \\<host>\deploy$\<redacted>\<redacted>.
    """
    parts = _SPLIT_KEEP_RE.split(tail)
    share = parts[0].lower()
    if share in _WELL_KNOWN_SHARES:
        return tail
    segments = [i for i in range(2, len(parts), 2) if parts[i]]
    if not segments:
        return tail
    if _ADMIN_DRIVE_SHARE_RE.fullmatch(share) or (host.lower() == _RDP_REDIRECTOR_HOST and _REDIRECTED_DRIVE_RE.fullmatch(share)):
        if len(segments) < 2:
            return tail
        folder, i = parts[segments[0]], segments[1]
        user = parts[i]
        if (folder.lower() in _PROFILE_ROOTS or _DOCUME_RE.fullmatch(folder)) and user.lower() not in _SHARED_PROFILES:
            if user in PLACEHOLDERS:
                return tail
            return "".join(parts[:i]) + "<user>" + _profile_rest("".join(parts[i + 1 :]))
        return tail
    i = segments[0]
    first = parts[i]
    if i == len(parts) - 1 and not _PER_USER_SHARE_RE.search(share) and _program_file(first):
        return tail
    return "".join(parts[:i]) + (first if first in PLACEHOLDERS else REDACTED) + _profile_rest("".join(parts[i + 1 :]))


def _redact_unc(value: str) -> str:
    """Every UNC host becomes <host>, and what its share may hold is cut down (``_share_tail``)."""
    matches = list(UNC_ANY_RE.finditer(value))
    if not matches:
        return value
    out: List[str] = []
    pos = 0
    for k, m in enumerate(matches):
        out.append(value[pos : m.start()])
        out.append(m.group("prefix") + "<host>" + (m.group("sep") or ""))
        end = matches[k + 1].start() if k + 1 < len(matches) else len(value)
        tail = value[m.end() : end]
        out.append(_share_tail(tail, m.group("host")) if m.group("sep") in ("\\", "/") else tail)
        pos = end
    out.append(value[pos:])
    return "".join(out)


def _redact_sysvol(value: str) -> str:
    r"""The folder below a SYSVOL folder is the AD domain's DNS name (\\<host>\SYSVOL\<domain>\, C:\Windows\SYSVOL\sysvol
    \<domain>\, ...\GroupPolicy\DataStore\0\sysvol\<domain>\): <redacted>, learned or not."""
    if "sysvol" not in value.lower():
        return value
    parts = _SPLIT_KEEP_RE.split(value)
    for i in range(2, len(parts), 2):
        if parts[i - 2].lower() == "sysvol" and parts[i] and parts[i].lower() not in _SYSVOL_KEEP and parts[i] not in PLACEHOLDERS:
            parts[i] = REDACTED
    return "".join(parts)


def _host_list(parent: str) -> bool:
    """A registry key whose subkeys are server names: Remote Desktop's servers, a print provider's print servers."""
    return parent == "terminal server client" or parent.endswith("print provider") or parent.endswith("print services")


def _redact_registry_hosts(value: str) -> str:
    r"""Host names in registry key paths: a printer connection ``,,<server>,<share>`` becomes ``,,<host>,<redacted>``;
    below ...\Terminal Server Client\Servers\ and a print provider's ...\Servers\, the server becomes <host> (and a
    printer below it that is not a GUID, <redacted>)."""
    if "\\" not in value:
        return value
    segments = value.split("\\")
    lowered = [s.lower() for s in segments]
    for i, segment in enumerate(segments):
        if segment.startswith(",,") and not segment.startswith(",,<host>"):
            _, comma, _ = segment[2:].partition(",")
            segments[i] = ",,<host>" + (",<redacted>" if comma else "")
        elif i >= 2 and lowered[i - 1] == "servers" and _host_list(lowered[i - 2]) and segment and segment not in PLACEHOLDERS:
            segments[i] = "<host>"
            if i + 2 < len(segments) and lowered[i + 1] == "printers":
                printer = segments[i + 2]
                if printer and printer not in PLACEHOLDERS and not _GUID_RE.fullmatch(printer):
                    segments[i + 2] = REDACTED
    return "\\".join(segments)


def _redact_addresses(value: str) -> str:
    """Every IPv6 and IPv4 address becomes <redacted> (a dotted quad in a place where Windows writes a version is
    kept)."""
    if value.count(":") >= 2:

        def v6(m: "re.Match[str]") -> str:
            try:
                ipaddress.IPv6Address(m.group(1).split("%", 1)[0])
            except ValueError:
                return m.group(0)
            return REDACTED

        value = IPV6_RE.sub(v6, value)

    def v4(m: "re.Match[str]") -> str:
        start, end = m.span()
        if start > 0 and m.string[start - 1] == "_" and _VERSION_TAIL_RE.match(m.string, end):
            return m.group(0)
        return REDACTED

    return IPV4_RE.sub(v4, value)


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
    value = _redact_sysvol(value)
    value = _redact_registry_hosts(value)
    value = _redact_private_segments(value, ctx)
    value = _redact_addresses(value)
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
        verdict = classify_dns(value, ctx.names, ctx.own_domains, ctx.dns_fragments)
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
