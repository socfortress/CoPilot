"""Type detection + dispatch for the Tier 1 inspector.

True type comes from libmagic (python-magic) when available, with a pure-python
magic-byte + extension fallback so the router still works in a dev checkout
without the native library. ``inspect_path`` is the single recursion entry point
that archive/email/html analyzers call for nested members.
"""
from __future__ import annotations

import os
from typing import Callable
from typing import Dict

from analyzers import archive as archive_analyzer
from analyzers import email as email_analyzer
from analyzers import html as html_analyzer
from analyzers import lnk as lnk_analyzer
from analyzers import office as office_analyzer
from analyzers import pdf as pdf_analyzer
from analyzers import pe as pe_analyzer
from analyzers import script as script_analyzer
from analyzers import text as text_analyzer
from analyzers.verdict import compute_verdict
from common import apply_context
from common import compute_hashes
from common import extension_mismatch
from common import shannon_entropy
from contract import ENGINE_VERSION
from contract import InspectorResult

_MAX_DEPTH = 4


def detect_type(path: str, filename: str) -> str:
    """Return a coarse family: pdf/office/script/lnk/pe/archive/email/html/unknown."""
    magic_str = _libmagic(path)
    family = _family_from_magic(magic_str)
    if family != "unknown":
        return family
    # Fallback: magic bytes, then extension.
    family = _family_from_bytes(path)
    if family != "unknown":
        return family
    return _family_from_ext(filename)


def _libmagic(path: str) -> str:
    try:
        import magic
    except ImportError:
        return ""
    try:
        return magic.from_file(path)
    except Exception:
        return ""


def _family_from_magic(magic_str: str) -> str:
    m = (magic_str or "").lower()
    if not m:
        return "unknown"
    if "pdf" in m:
        return "pdf"
    if (
        "composite document" in m
        or "opendocument" in m
        or "microsoft word" in m
        or "microsoft excel" in m
        or "microsoft office" in m
        or "zip archive" in m
        and "opendocument" in m
    ):
        return "office"
    if "ms windows shortcut" in m or "shortcut" in m:
        return "lnk"
    if "pe32" in m or "ms-dos executable" in m or "executable (console)" in m:
        return "pe"
    if "elf " in m:
        return "elf"
    # Interpreted scripts by content (shebang/type) — catches e.g. a Python or shell
    # script with no extension or a misleading one.
    if (
        "python script" in m
        or "python source" in m
        or "shell script" in m
        or "perl script" in m
        or "ruby script" in m
        or "php script" in m
        or "batch file" in m
        or "powershell" in m
    ):
        return "script"
    if "rfc 822" in m or "smtp mail" in m or "news or mail" in m or "microsoft outlook" in m:
        return "email"
    if "html" in m or "svg" in m or "xml" in m and "svg" in m:
        return "html"
    if "zip archive" in m or "rar archive" in m or "7-zip" in m or "iso 9660" in m:
        return "archive"
    return "unknown"


def _family_from_bytes(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            head = fh.read(8)
    except OSError:
        return "unknown"
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"MZ"):
        return "pe"
    if head.startswith(b"\x7fELF"):
        return "elf"
    if head.startswith(b"PK\x03\x04"):
        return "office_or_zip"  # resolved by extension below
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return "office"  # OLE compound
    if head[:4] == b"L\x00\x00\x00":
        return "lnk"
    return "unknown"


def _family_from_ext(filename: str) -> str:
    _, ext = os.path.splitext(filename.lower())
    from common import _EXT_TO_FAMILY

    return _EXT_TO_FAMILY.get(ext, "unknown")


# Dispatch table: family -> analyzer callable(sample_path, result, results_dir?, depth?)
def _dispatch(family: str) -> Callable:
    table: Dict[str, Callable] = {
        "pdf": lambda p, r, rd, d: pdf_analyzer.analyze(p, r, rd),
        "office": lambda p, r, rd, d: office_analyzer.analyze(p, r, rd),
        "script": lambda p, r, rd, d: script_analyzer.analyze(p, r),
        "lnk": lambda p, r, rd, d: lnk_analyzer.analyze(p, r),
        "pe": lambda p, r, rd, d: pe_analyzer.analyze(p, r),
        "elf": lambda p, r, rd, d: pe_analyzer.analyze(p, r),  # ELF via P7; PE analyzer degrades cleanly for now
        "archive": lambda p, r, rd, d: archive_analyzer.analyze(p, r, rd, d),
        "email": lambda p, r, rd, d: email_analyzer.analyze(p, r, rd, d),
        "html": lambda p, r, rd, d: html_analyzer.analyze(p, r, rd, d),
    }
    return table.get(family, _unknown)


def _unknown(path, result, results_dir, depth):
    result.filetype = "unknown"
    # Not a recognized document/executable — if it's textual, show the text + IOCs
    # instead of leaving the analyst with an empty result.
    if text_analyzer.looks_textual(result.magic, path):
        text_analyzer.analyze(path, result)


def inspect_path(
    path: str,
    filename: str,
    customer_code: str,
    results_dir: str = "",
    depth: int = 0,
    context: dict = None,
) -> InspectorResult:
    """Analyze a single file and return an assembled :class:`InspectorResult`."""
    hashes = compute_hashes(path)
    result = InspectorResult(
        sha256=hashes["sha256"],
        filename=filename,
        customer_code=customer_code,
        hashes=hashes,
        engine_version=ENGINE_VERSION,
    )
    result.magic = _libmagic(path)
    result.entropy = shannon_entropy(path)

    if depth > _MAX_DEPTH:
        result.filetype = "unknown"
        result.mark_incomplete()
        return result

    family = detect_type(path, filename)
    if family == "office_or_zip":
        family = _family_from_ext(filename) or "archive"
    result.extension_mismatch = extension_mismatch(filename, family)

    try:
        _dispatch(family)(path, result, results_dir, depth)
    except Exception:
        result.mark_incomplete()

    if context:
        apply_context(result.iocs, context)

    result.verdict_hint = compute_verdict(result.to_dict())
    return result
