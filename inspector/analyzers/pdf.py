"""PDF analyzer — structural flags, embedded JS, page-image render.

Primary engine is PyMuPDF (``fitz``): one pip package, no external binaries,
works on every OS — it renders page previews AND lets us read structure. Falls
back to poppler's ``pdftoppm`` / Didier Stevens ``pdfid`` if PyMuPDF is absent.
Structural keyword flagging is a pure-Python raw-byte scan (pdfid-equivalent) so
it works even with no tooling at all. Nothing renders the live PDF — the analyst
only ever sees PNGs produced here.
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import List

from common import extract_iocs
from contract import FLAG_AUTO_EXECUTE_JAVASCRIPT
from contract import FLAG_EMBEDDED_FILE
from contract import FLAG_LAUNCH_ACTION
from contract import InspectorResult

_RENDER_TIMEOUT = 90
_PARSER_TIMEOUT = 45
_MAX_PAGES = 25
_MAX_SCAN_BYTES = 16 * 1024 * 1024

_STRUCT_KEYWORDS = ("/OpenAction", "/AA", "/JavaScript", "/JS", "/Launch", "/EmbeddedFile", "/URI")


def analyze(sample_path: str, result: InspectorResult, results_dir: str = "") -> None:
    result.filetype = "pdf"
    try:
        _keyword_flags(sample_path, result)
        rendered = _render_pymupdf(sample_path, result, results_dir)
        if not rendered:
            rendered = _render_pdftoppm(sample_path, result, results_dir)
        _extract_js(sample_path, result)
    except Exception:
        # Any parser blow-up on a malformed PDF is a partial result, not a crash.
        result.mark_incomplete()
        return
    # We always get structural flags from the raw scan, so a missing renderer is a
    # preview gap, not an analysis gap — only flag incomplete if the file was
    # unreadable (handled above) — otherwise leave the verdict to the flags.


def _keyword_flags(sample_path: str, result: InspectorResult) -> None:
    """Count dangerous structural keywords by scanning raw bytes (like pdfid).

    We do NOT extract IOCs here: the raw bytes include compressed streams and XMP
    metadata, which produce garbage "domains" and boilerplate namespace URLs
    (w3.org, ns.adobe.com, …). IOCs come only from clean sources — the visible
    page text and embedded JavaScript.
    """
    try:
        with open(sample_path, "rb") as fh:
            data = fh.read(_MAX_SCAN_BYTES)
    except OSError:
        result.mark_incomplete()
        return
    text = data.decode("latin-1", errors="replace")
    counts = {kw: len(re.findall(re.escape(kw), text)) for kw in _STRUCT_KEYWORDS}
    result.content["structure"] = counts
    # Only an actual embedded script auto-executing is suspicious. A bare
    # /OpenAction or /AA is common in benign PDFs (it just sets the initial view),
    # so it does NOT raise the flag on its own.
    if counts["/JavaScript"] or counts["/JS"]:
        result.add_flag(FLAG_AUTO_EXECUTE_JAVASCRIPT)
    if counts["/Launch"]:
        result.add_flag(FLAG_LAUNCH_ACTION)
    if counts["/EmbeddedFile"]:
        result.add_flag(FLAG_EMBEDDED_FILE)


def _render_pymupdf(sample_path: str, result: InspectorResult, results_dir: str) -> bool:
    if not results_dir:
        return False
    try:
        import fitz  # PyMuPDF
    except ImportError:
        try:
            import pymupdf as fitz  # newer import name
        except ImportError:
            return False
    try:
        doc = fitz.open(sample_path)
    except Exception:
        return False
    try:
        page_count = min(doc.page_count, _MAX_PAGES)
        text_parts: List[str] = []
        for i in range(page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=100)
            name = f"page-{i + 1}.png"
            pix.save(os.path.join(results_dir, name))
            if name not in result.previews:
                result.previews.append(name)
            try:
                text_parts.append(page.get_text())
            except Exception:
                pass
        # PyMuPDF also exposes document metadata cheaply.
        meta = doc.metadata or {}
        if meta:
            result.content["pdf_metadata"] = {k: v for k, v in meta.items() if v}
        # IOCs come from the VISIBLE text only (clean, decoded) — not raw bytes.
        text = "\n".join(text_parts)
        if text.strip():
            result.content["text"] = text[:200000]
            for kind, values in extract_iocs(text).items():
                for value in values:
                    result.add_ioc(kind, value)
        return page_count > 0
    finally:
        doc.close()


def _render_pdftoppm(sample_path: str, result: InspectorResult, results_dir: str) -> bool:
    if not results_dir:
        return False
    prefix = os.path.join(results_dir, "page")
    try:
        subprocess.run(
            ["pdftoppm", "-png", "-r", "100", "-l", str(_MAX_PAGES), sample_path, prefix],
            capture_output=True,
            timeout=_RENDER_TIMEOUT,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    pages = sorted(f for f in os.listdir(results_dir) if f.startswith("page") and f.endswith(".png"))
    for name in pages:
        if name not in result.previews:
            result.previews.append(name)
    return bool(pages)


def _extract_js(sample_path: str, result: InspectorResult) -> None:
    """Best-effort embedded-JS extraction via pdf-parser, if available."""
    out = _run(["pdf-parser.py", "--search", "javascript", "--raw", sample_path], _PARSER_TIMEOUT)
    if not out:
        out = _run(["pdf-parser", "--search", "javascript", "--raw", sample_path], _PARSER_TIMEOUT)
    if out:
        result.content["javascript"] = out[:200000]
        for kind, values in extract_iocs(out).items():
            for value in values:
                result.add_ioc(kind, value)


def _run(cmd: List[str], timeout: int) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        return proc.stdout.decode("utf-8", errors="replace")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
