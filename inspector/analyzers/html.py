"""HTML / SVG analyzer — HTML smuggling detection.

HTML smuggling delivers a payload as a script-assembled blob; the file itself is
the dropper. We extract <script> bodies, run them through the same pure-static JS
deobfuscation as the script analyzer, and hunt for the smuggling signature
(large base64 + Blob/atob/msSaveOrOpenBlob/createObjectURL). When a blob can be
statically reassembled it is decoded and recursed through the router.

We NEVER render HTML/SVG for preview — a browser-grade renderer is not worth its
attack surface in the inspector. Text extraction only.
"""
from __future__ import annotations

import base64
import binascii
import os
import re
import tempfile
from typing import List

from common import extract_iocs
from contract import FLAG_HTML_SMUGGLING
from contract import FLAG_SUSPICIOUS_ATTACHMENT
from contract import InspectorResult
from analyzers.script import deobfuscate

_SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
_SMUGGLING_MARKERS = ("atob", "blob", "mssaveoropenblob", "createobjecturl", "msSaveBlob".lower(), "data:application/octet-stream")
_B64_LITERAL_RE = re.compile(r"['\"]([A-Za-z0-9+/]{200,}={0,2})['\"]")


def analyze(sample_path: str, result: InspectorResult, results_dir: str = "", depth: int = 0) -> None:
    result.filetype = "html"
    try:
        with open(sample_path, "rb") as fh:
            raw = fh.read(5 * 1024 * 1024).decode("utf-8", errors="replace")
    except OSError:
        result.mark_incomplete()
        return

    scripts = _SCRIPT_RE.findall(raw)
    result.content["script_count"] = len(scripts)

    joined = "\n".join(scripts)
    lowered = joined.lower()
    smuggling = any(marker in lowered for marker in _SMUGGLING_MARKERS) and bool(_B64_LITERAL_RE.search(joined))

    # Deobfuscate scripts statically and pull IOCs.
    deob_layers: List[str] = []
    for script in scripts[:20]:
        layers, _, _ = deobfuscate(script)
        deob_layers.extend(layers)
    if deob_layers:
        result.content["deobfuscated_scripts"] = deob_layers[:50]

    if smuggling:
        result.add_flag(FLAG_HTML_SMUGGLING)
        _try_reassemble(joined, result, depth)

    for kind, values in extract_iocs(raw, *deob_layers).items():
        for value in values:
            result.add_ioc(kind, value)


def _try_reassemble(script_text: str, result: InspectorResult, depth: int) -> None:
    """Statically decode the largest base64 literal and recurse the payload."""
    if depth >= 3:
        return
    candidates = _B64_LITERAL_RE.findall(script_text)
    if not candidates:
        return
    blob = max(candidates, key=len)
    try:
        data = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=False)
    except (binascii.Error, ValueError):
        return
    if len(data) < 16:
        return
    import router

    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix="smuggled_")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        child = router.inspect_path(tmp, filename="smuggled_payload", customer_code=result.customer_code, results_dir="", depth=depth + 1)
        result.content["smuggled_payload"] = {
            "filetype": child.filetype,
            "flags": child.flags,
            "verdict_hint": child.verdict_hint,
        }
        if child.verdict_hint in ("suspicious", "malicious"):
            result.add_flag(FLAG_SUSPICIOUS_ATTACHMENT)
    except Exception:
        pass
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
