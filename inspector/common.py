"""Common analysis applied to every sample regardless of type.

Hashes, magic-vs-extension mismatch, Shannon entropy, IOC regex extraction, and
merging the MOTW/parent-process context that the Velociraptor collection
artifact gathered (the container cannot see the original ADS, so it arrives in
``job.context``).

Everything here is pure Python + hashlib; no external tooling required, so this
layer never degrades.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Dict
from typing import List

# IOC regexes — deliberately conservative to limit false positives on binary noise.
_URL_RE = re.compile(r"\b(?:https?|ftp)://[^\s\"'<>)\]}]+", re.IGNORECASE)
_IP_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_DOMAIN_RE = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"(?:com|net|org|io|co|ru|cn|info|biz|xyz|top|club|online|site|tk|ml|ga|cf|gq|su|us|uk|de|fr|nl|br|in|ir|pw)\b",
    re.IGNORECASE,
)
# Defanged variants seen in analyst notes / emails (hxxp, evil[.]com).
_DEFANG = (("hxxp", "http"), ("[.]", "."), ("(.)", "."), ("[:]", ":"))

# Map common extensions to the true-type family we expect, for mismatch detection.
_EXT_TO_FAMILY = {
    ".pdf": "pdf",
    ".doc": "office", ".docx": "office", ".docm": "office",
    ".xls": "office", ".xlsx": "office", ".xlsm": "office",
    ".ppt": "office", ".pptx": "office", ".pptm": "office",
    ".rtf": "office",
    ".ps1": "script", ".vbs": "script", ".js": "script", ".jse": "script",
    ".bat": "script", ".cmd": "script", ".hta": "script", ".wsf": "script", ".sh": "script",
    ".lnk": "lnk",
    ".exe": "pe", ".dll": "pe", ".sys": "pe", ".scr": "pe",
    ".zip": "archive", ".rar": "archive", ".7z": "archive", ".iso": "archive", ".img": "archive",
    ".eml": "email", ".msg": "email",
    ".html": "html", ".htm": "html", ".svg": "html",
}


def compute_hashes(path: str) -> Dict[str, str]:
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
    return {"md5": md5.hexdigest(), "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest(), "imphash": None}


def shannon_entropy(path: str, cap_bytes: int = 8 * 1024 * 1024) -> float:
    """Shannon entropy over up to ``cap_bytes`` (bounded so a huge sample can't stall)."""
    counts = [0] * 256
    total = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            for byte in chunk:
                counts[byte] += 1
            total += len(chunk)
            if total >= cap_bytes:
                break
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts:
        if count:
            p = count / total
            entropy -= p * math.log2(p)
    return round(entropy, 3)


def extension_mismatch(filename: str, filetype: str) -> bool:
    """True if the declared extension implies a different family than detected."""
    _, ext = os.path.splitext(filename.lower())
    expected = _EXT_TO_FAMILY.get(ext)
    if expected is None or filetype in ("unknown", ""):
        return False
    return expected != filetype


def _refang(text: str) -> str:
    for bad, good in _DEFANG:
        text = text.replace(bad, good)
    return text


def extract_iocs(*texts: str) -> Dict[str, List[str]]:
    """Pull urls/ips/domains out of one or more text blobs."""
    urls: List[str] = []
    ips: List[str] = []
    domains: List[str] = []
    for raw in texts:
        if not raw:
            continue
        text = _refang(raw)
        for match in _URL_RE.findall(text):
            if match not in urls:
                urls.append(match.rstrip(".,);"))
        for match in _IP_RE.findall(text):
            if match not in ips:
                ips.append(match)
        for match in _DOMAIN_RE.findall(text):
            m = match.lower()
            if m not in domains:
                domains.append(m)
    return {"urls": urls, "ips": ips, "domains": domains}


def apply_context(result_iocs: Dict[str, List[str]], context: Dict) -> Dict[str, List[str]]:
    """Fold MOTW url (if any) from the collection context into IOC domains/urls."""
    motw = (context or {}).get("motw")
    if motw:
        found = extract_iocs(motw)
        for kind, values in found.items():
            for value in values:
                if value not in result_iocs.setdefault(kind, []):
                    result_iocs[kind].append(value)
    return result_iocs
