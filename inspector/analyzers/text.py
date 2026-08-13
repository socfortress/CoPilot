"""Plain-text analyzer.

For files that aren't a recognized document/executable but are textual (configs,
logs, .txt, JSON/XML/CSV, unknown scripts), surface the decoded text so an analyst
can actually read the file, and pull IOCs out of it. Non-executing: it only decodes
bytes — nothing is run.
"""
from __future__ import annotations

from common import extract_iocs

_MAX_TEXT = 200_000  # cap the displayed text at ~200 KB


def looks_textual(magic_str: str, path: str) -> bool:
    """True if the file is plain text (by magic, or a printable-byte heuristic)."""
    m = (magic_str or "").lower()
    if any(k in m for k in ("text", "ascii", "utf-8", "json", "xml", "csv")):
        return True
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(4096)
    except OSError:
        return False
    if not chunk or b"\x00" in chunk:  # NUL byte ⇒ binary
        return False
    printable = sum(1 for b in chunk if b in (9, 10, 13) or 32 <= b <= 126 or b >= 128)
    return printable / len(chunk) > 0.85


def analyze(path, result) -> None:
    try:
        with open(path, "rb") as fh:
            raw = fh.read(_MAX_TEXT + 1)
    except OSError:
        return
    truncated = len(raw) > _MAX_TEXT
    text = raw[:_MAX_TEXT].decode("utf-8", errors="replace")
    if truncated:
        text += "\n… (truncated)"

    result.filetype = "text"
    result.content["text"] = text

    found = extract_iocs(text)
    for kind in ("urls", "ips", "domains"):
        bucket = result.iocs.setdefault(kind, [])
        for value in found.get(kind, []):
            if value not in bucket:
                bucket.append(value)
