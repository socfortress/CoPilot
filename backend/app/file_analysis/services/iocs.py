"""Indicator extraction and defanging.

Indicators are pulled from three places, and the *context* they came from is
kept because it carries signal: an indicator sitting in plain text is weaker
than the same indicator that only appeared after deobfuscation.

Everything leaves this module **defanged** (``hxxp://``, ``1.2.3[.]4``,
``user[@]host``). Storing the live form would put a clickable indicator into the
UI, into every export and into every Graylog message; defanging at the point of
extraction means no downstream consumer has to remember to do it. Anything that
genuinely needs the original calls :func:`refang` explicitly (#974 §C).

Pure stdlib on purpose -- this module is unit-testable without libmagic, MinIO
or a database.
"""

from __future__ import annotations

import re
from typing import Iterable
from typing import List
from typing import NamedTuple
from typing import Set
from typing import Tuple

# Per-type and overall caps. A packed binary can yield tens of thousands of
# path-like runs; past a point they stop being triage material and start being
# a denial of service against the UI and the Graylog message size.
MAX_PER_TYPE = 100
MAX_TOTAL = 500

VALUE_MAX_LENGTH = 2048

_URL = re.compile(r"\b(?:https?|ftp|ftps|smb|ldap)://[^\s\"'<>()\[\]{}\\^`]{3,2000}", re.IGNORECASE)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,255}\.[A-Za-z]{2,24}\b")
_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b")
_IPV6 = re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}\b")
_DOMAIN = re.compile(r"\b(?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.){1,8}(?:[A-Za-z]{2,24})\b")
_MD5 = re.compile(r"\b[A-Fa-f0-9]{32}\b")
_SHA1 = re.compile(r"\b[A-Fa-f0-9]{40}\b")
_SHA256 = re.compile(r"\b[A-Fa-f0-9]{64}\b")
# Registry paths legitimately contain spaces ("Windows NT\CurrentVersion"), but a
# component class that allows spaces *and* dots together will bridge straight past
# the end of the key to the next backslash anywhere later in the text -- turning
# "HKLM\Software\Run payload.dll <hash> HKLM\SOFTWARE\..." into one indicator that
# spans two keys and a hash.
#
# So a spaced component is restricted to a single space between dot-free runs:
# "Windows NT" still matches, "Run payload.dll" cannot, and the match stops where
# the key does. The final component takes no space at all.
_REG_COMPONENT = r"[A-Za-z0-9_\-.]{1,48}(?: [A-Za-z0-9_\-]{1,48})?"
_REGISTRY_KEY = re.compile(
    r"\b(?:HKEY_(?:LOCAL_MACHINE|CURRENT_USER|CLASSES_ROOT|USERS|CURRENT_CONFIG)|HKLM|HKCU|HKCR|HKU)"
    r"(?:[\\/]" + _REG_COMPONENT + r"(?=[\\/]))*"
    r"[\\/][A-Za-z0-9_\-.]{1,64}",
    re.IGNORECASE,
)
_WINDOWS_PATH = re.compile(r"\b[A-Za-z]:\\[^\s\"'<>|*?\r\n]{2,400}")
_UNC_PATH = re.compile(r"\\\\[A-Za-z0-9._\-]{1,64}\\[^\s\"'<>|*?\r\n]{1,400}")
_ENV_PATH = re.compile(r"%[A-Za-z_][A-Za-z0-9_]{2,32}%\\[^\s\"'<>|*?\r\n]{2,400}")
# POSIX paths are restricted to directories that mean something in an incident.
# Matching bare "/" prefixes would tag every URL fragment and every code comment.
_POSIX_PATH = re.compile(r"(?:/etc|/tmp|/var|/root|/home|/usr/bin|/usr/sbin|/dev/shm|/opt)/[^\s\"'<>|*?\r\n:]{1,400}")

# Suffixes that match the domain grammar but are, in a malware-analysis context,
# overwhelmingly filenames. Several are also real ccTLDs (.sh, .pl, .py, .md);
# the trade is deliberate -- "dropper.py" is a script far more often than it is
# a Paraguayan host, and a missed domain is recoverable from the raw strings
# while thousands of phantom domains make the IOC list useless.
_FILENAME_SUFFIXES: Set[str] = {
    "asp",
    "aspx",
    "avi",
    "bak",
    "bat",
    "bin",
    "bmp",
    "cab",
    "cfg",
    "class",
    "cmd",
    "conf",
    "cpl",
    "cs",
    "css",
    "csv",
    "dat",
    "db",
    "dll",
    "doc",
    "docm",
    "docx",
    "dylib",
    "eml",
    "exe",
    "gif",
    "gz",
    "hta",
    "htm",
    "html",
    "ico",
    "img",
    "ini",
    "iso",
    "jar",
    "java",
    "jpeg",
    "jpg",
    "js",
    "jse",
    "json",
    "lnk",
    "log",
    "md",
    "mp3",
    "mp4",
    "msg",
    "msi",
    "old",
    "otf",
    "pdf",
    "php",
    "pl",
    "png",
    "ppt",
    "pptm",
    "pptx",
    "ps1",
    "psd1",
    "psm1",
    "py",
    "rar",
    "rb",
    "rtf",
    "scr",
    "sh",
    "so",
    "sqlite",
    "swp",
    "sys",
    "tar",
    "tmp",
    "ttf",
    "txt",
    "url",
    "vbe",
    "vbs",
    "wav",
    "woff",
    "woff2",
    "xls",
    "xlsm",
    "xlsx",
    "xml",
    "zip",
}

# Context labels, ordered weakest to strongest as triage signal.
CONTEXT_RAW = "raw"
CONTEXT_TEXT = "text"
CONTEXT_METADATA = "metadata"
CONTEXT_MACRO = "macro"
CONTEXT_DEOBFUSCATED = "deobfuscated"


class ExtractedIoC(NamedTuple):
    ioc_type: str
    value: str  # already defanged
    context: str


# Only network indicators are defanged. A file path, a registry key and a hash
# are not clickable and never resolve to anything, so neutering their dots buys
# no safety and costs real usability: "C:\Users\a\drop[.]exe" no longer greps,
# copies or reads like the thing it names.
DEFANGED_TYPES = frozenset({"url", "domain", "ipv4", "ipv6", "email"})


def defang(value: str) -> str:
    """Render a network indicator inert for display, storage and transport."""
    out = re.sub(r"^http(s?)://", r"hxxp\1://", value, flags=re.IGNORECASE)
    out = re.sub(r"^ftp(s?)://", r"fxp\1://", out, flags=re.IGNORECASE)
    out = out.replace("@", "[@]")
    # Every dot, not just the host's: it keeps the rule trivially reversible and
    # avoids having to parse the URL to find where the authority ends.
    out = out.replace(".", "[.]")
    return out


def defang_for_type(ioc_type: str, value: str) -> str:
    """Defang only the types where a live indicator is a hazard."""
    return defang(value) if ioc_type in DEFANGED_TYPES else value


def refang(value: str) -> str:
    """Inverse of :func:`defang`, for callers that need the live indicator."""
    out = value.replace("[.]", ".").replace("[@]", "@")
    out = re.sub(r"^hxxp(s?)://", r"http\1://", out, flags=re.IGNORECASE)
    out = re.sub(r"^fxp(s?)://", r"ftp\1://", out, flags=re.IGNORECASE)
    return out


def _is_plausible_domain(candidate: str) -> bool:
    suffix = candidate.rsplit(".", 1)[-1].lower()
    if suffix in _FILENAME_SUFFIXES:
        return False
    # A bare version string ("1.2.3.4" already handled as IPv4) or an all-digit
    # label sequence is never a domain.
    return not all(part.isdigit() for part in candidate.split(".")[:-1])


def _ordered_unique(values: Iterable[str]) -> List[str]:
    """Deduplicate case-insensitively, preserving first-seen order and casing."""
    seen: Set[str] = set()
    out: List[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _match_all(text: str) -> List[Tuple[str, List[str]]]:
    """Run every pattern, in the order indicators should be reported."""
    urls = _URL.findall(text)
    # A domain or IP that is only present because it is inside a URL we already
    # captured adds nothing; drop it so the list stays readable.
    url_blob = " ".join(urls).lower()

    domains: List[str] = []
    for match in _DOMAIN.finditer(text):
        candidate = match.group(0)
        if not _is_plausible_domain(candidate):
            continue
        if candidate.lower() in url_blob:
            continue
        domains.append(candidate)

    ipv4 = [ip for ip in _IPV4.findall(text) if ip.lower() not in url_blob]

    return [
        ("url", urls),
        ("domain", domains),
        ("ipv4", ipv4),
        ("ipv6", _IPV6.findall(text)),
        ("email", _EMAIL.findall(text)),
        ("sha256", _SHA256.findall(text)),
        ("sha1", _SHA1.findall(text)),
        ("md5", _MD5.findall(text)),
        ("registry_key", _REGISTRY_KEY.findall(text)),
        ("path", _WINDOWS_PATH.findall(text) + _UNC_PATH.findall(text) + _ENV_PATH.findall(text) + _POSIX_PATH.findall(text)),
    ]


def extract_iocs(text: str, context: str = CONTEXT_TEXT) -> List[ExtractedIoC]:
    """Extract typed, defanged indicators from one blob of text.

    Hash types are mutually exclusive by length, so a SHA-256 is never also
    reported as three MD5s -- the patterns are anchored on word boundaries and
    the longer forms are matched first.
    """
    if not text:
        return []

    found: List[ExtractedIoC] = []
    for ioc_type, raw_values in _match_all(text):
        for value in _ordered_unique(raw_values)[:MAX_PER_TYPE]:
            trimmed = value[:VALUE_MAX_LENGTH]
            found.append(ExtractedIoC(ioc_type=ioc_type, value=defang_for_type(ioc_type, trimmed), context=context))

    return found


def merge_iocs(batches: Iterable[Iterable[ExtractedIoC]]) -> List[ExtractedIoC]:
    """Combine per-source extractions, keeping the strongest context per value.

    When the same URL appears both in plain text and in a deobfuscated payload,
    the deobfuscated attribution is the one worth keeping -- it is the one that
    says the author tried to hide it.
    """
    strength = {
        CONTEXT_RAW: 0,
        CONTEXT_TEXT: 1,
        CONTEXT_METADATA: 2,
        CONTEXT_MACRO: 3,
        CONTEXT_DEOBFUSCATED: 4,
    }

    best: dict = {}
    order: List[Tuple[str, str]] = []
    for batch in batches:
        for ioc in batch:
            key = (ioc.ioc_type, ioc.value.lower())
            if key not in best:
                best[key] = ioc
                order.append(key)
            elif strength.get(ioc.context, 0) > strength.get(best[key].context, 0):
                best[key] = ioc

    return [best[key] for key in order][:MAX_TOTAL]
