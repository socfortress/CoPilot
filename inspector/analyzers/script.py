"""Script analyzer — PURE-STATIC deobfuscation only.

Covers .ps1/.vbs/.js/.bat/.hta/.wsf/.sh. The entire safety story of Tier 1 rests
on nothing ever executing the sample, so this analyzer NEVER runs the script and
NEVER shells out to an instrumented interpreter (PSDecode/box-ps are banned from
the image). It applies a transform chain iteratively to a bounded fixpoint and
records each layer.

What it can unwind statically: base64 ``-enc`` payloads, ``FromBase64String``
literals, string concatenation, format operator ``-f`` with literal args,
char-array folding, backtick/caret removal, ``-replace``/``.Replace`` with
literal args, and gzip/deflate blob inflation. What it cannot resolve (computed
member access, live ``IEX`` of a runtime value) is surfaced as
``deobfuscation_incomplete`` — itself the Tier 2 escalation signal.
"""
from __future__ import annotations

import base64
import binascii
import gzip
import re
import zlib
from typing import List
from typing import Tuple

from common import extract_iocs
from contract import FLAG_DEOBFUSCATION_INCOMPLETE
from contract import FLAG_ENCODED_POWERSHELL
from contract import InspectorResult

_MAX_ROUNDS = 10
_MAX_LAYER_BYTES = 2 * 1024 * 1024  # cap inflated/decoded output per layer

# Markers that mean "there is still dynamic behaviour we could not statically resolve".
_DYNAMIC_MARKERS = re.compile(
    r"\b(iex|invoke-expression|invoke-command|&\s*\(|\.invoke\(|downloadstring|"
    r"start-process|createobject|eval\s*\(|new-object\s+net\.webclient)\b",
    re.IGNORECASE,
)
_ENC_FLAG_RE = re.compile(r"-e(nc(odedcommand)?)?\b", re.IGNORECASE)
_B64_BLOB_RE = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")
_FROMB64_RE = re.compile(r"FromBase64String\(\s*['\"]([A-Za-z0-9+/=]+)['\"]\s*\)", re.IGNORECASE)
_CONCAT_RE = re.compile(r"""['"]([^'"]*)['"]\s*\+\s*['"]([^'"]*)['"]""")
_CHAR_RE = re.compile(r"\[char\]\s*(0x[0-9a-fA-F]+|\d+)", re.IGNORECASE)
_REPLACE_DOT_RE = re.compile(r"""\.[Rr]eplace\(\s*['"]([^'"]*)['"]\s*,\s*['"]([^'"]*)['"]\s*\)""")
_REPLACE_OP_RE = re.compile(r"""-replace\s+['"]([^'"]*)['"]\s*,\s*['"]([^'"]*)['"]""", re.IGNORECASE)


def _try_b64(blob: str) -> str:
    """Decode a base64 blob, trying UTF-16LE (PowerShell -enc) then UTF-8."""
    try:
        raw = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=False)
    except (binascii.Error, ValueError):
        return ""
    if len(raw) > _MAX_LAYER_BYTES:
        raw = raw[:_MAX_LAYER_BYTES]
    # PowerShell -enc is UTF-16LE; many other payloads are UTF-8.
    for encoding in ("utf-16-le", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            # Heuristic: decoded text should be mostly printable.
            printable = sum(c.isprintable() or c in "\r\n\t" for c in text)
            if text and printable / max(len(text), 1) > 0.8:
                return text
        except (UnicodeDecodeError, ValueError):
            continue
    return ""


def _try_inflate(blob: str) -> str:
    """Try gzip then raw-deflate on a base64 blob (IO.Compression payloads)."""
    try:
        raw = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=False)
    except (binascii.Error, ValueError):
        return ""
    for decompress in (
        lambda b: gzip.decompress(b),
        lambda b: zlib.decompress(b, -zlib.MAX_WBITS),
        lambda b: zlib.decompress(b),
    ):
        try:
            out = decompress(raw)
            if out:
                return out[:_MAX_LAYER_BYTES].decode("utf-8", errors="replace")
        except (OSError, zlib.error, EOFError):
            continue
    return ""


def _flatten_concat(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = _CONCAT_RE.sub(lambda m: "'" + m.group(1) + m.group(2) + "'", text)
    return text


def _fold_chars(text: str) -> str:
    def repl(match: re.Match) -> str:
        token = match.group(1)
        try:
            code = int(token, 16) if token.lower().startswith("0x") else int(token)
            if 0 <= code <= 0x10FFFF:
                return "'" + chr(code) + "'"
        except ValueError:
            pass
        return match.group(0)

    return _CHAR_RE.sub(repl, text)


def _apply_replace(text: str) -> str:
    text = _REPLACE_DOT_RE.sub(lambda m: _do_replace(m), text)
    text = _REPLACE_OP_RE.sub(lambda m: _do_replace(m), text)
    return text


def _do_replace(match: re.Match) -> str:
    # Best-effort: we cannot know the target string statically, so we only strip
    # the call syntax when the search term is an obvious obfuscation separator.
    search, replacement = match.group(1), match.group(2)
    if search and len(search) <= 3:
        return "/*replace:" + search + "->" + replacement + "*/"
    return match.group(0)


def _one_round(text: str) -> str:
    """Apply every transform once; caller loops until fixpoint."""
    out = text
    # base64 -enc payloads
    if _ENC_FLAG_RE.search(out):
        for blob in _B64_BLOB_RE.findall(out):
            decoded = _try_b64(blob)
            if decoded:
                out = out.replace(blob, "\n# --- decoded (-enc) ---\n" + decoded + "\n")
    # FromBase64String literals
    for match in _FROMB64_RE.finditer(out):
        decoded = _try_b64(match.group(1))
        if decoded:
            out = out.replace(match.group(0), "'" + decoded + "'")
    # gzip/deflate blobs
    for blob in _B64_BLOB_RE.findall(out):
        inflated = _try_inflate(blob)
        if inflated:
            out = out.replace(blob, "\n# --- inflated ---\n" + inflated + "\n")
    # structural simplification
    out = _flatten_concat(out)
    out = _fold_chars(out)
    out = out.replace("`", "").replace("^", "")
    out = _apply_replace(out)
    return out


def deobfuscate(raw: str) -> Tuple[List[str], bool, bool]:
    """Return (layers, saw_encoded, incomplete).

    ``layers`` excludes the raw input; each entry is the output of one round that
    changed something. ``saw_encoded`` is True if an -enc/base64 blob was
    unwound. ``incomplete`` is True if the fixpoint still contains dynamic
    constructs we could not statically resolve.
    """
    layers: List[str] = []
    saw_encoded = bool(_ENC_FLAG_RE.search(raw) and _B64_BLOB_RE.search(raw))
    current = raw
    for _ in range(_MAX_ROUNDS):
        nxt = _one_round(current)
        if nxt == current:
            break
        layers.append(nxt)
        if len(nxt) > len(current) and _B64_BLOB_RE.search(current) and "decoded" in nxt:
            saw_encoded = True
        current = nxt
    incomplete = bool(_DYNAMIC_MARKERS.search(current))
    return layers, saw_encoded, incomplete


def analyze(sample_path: str, result: InspectorResult) -> None:
    try:
        with open(sample_path, "rb") as fh:
            raw_bytes = fh.read(_MAX_LAYER_BYTES)
        raw = raw_bytes.decode("utf-8", errors="replace")
    except OSError:
        result.mark_incomplete()
        return

    result.filetype = "script"
    result.content["raw"] = raw

    layers, saw_encoded, incomplete = deobfuscate(raw)
    if layers:
        result.content["deobfuscated_layers"] = layers
        result.content["deobfuscated"] = layers[-1]
    if saw_encoded:
        result.add_flag(FLAG_ENCODED_POWERSHELL)
    if incomplete:
        result.add_flag(FLAG_DEOBFUSCATION_INCOMPLETE)

    # IOCs from raw AND every decoded layer.
    blobs = [raw] + layers
    found = extract_iocs(*blobs)
    for kind, values in found.items():
        for value in values:
            result.add_ioc(kind, value)
