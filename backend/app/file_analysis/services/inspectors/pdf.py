"""PDF inspector.

Deliberately **not** built on a PDF library. Two reasons, both practical:

- Malicious PDFs are usually malformed. They rely on readers being lenient, and
  a strict parser rejects the whole document precisely when there is something
  to find. Token scanning degrades gracefully where a parse would abort.
- The dangerous constructs (``/OpenAction``, ``/Launch``, ``/JavaScript``,
  ``/EmbeddedFile``) are name objects. Finding them needs lexing, not a document
  model, so a library buys nothing here.

What a naive raw scan *does* miss is anything inside a compressed object stream,
which is where a competent author puts it. So streams are inflated with stdlib
``zlib`` and scanned as well -- inflating is decompression, not execution, and
adds no dependency.

Nothing referenced by the document is ever fetched.
"""

from __future__ import annotations

import re
import zlib
from typing import List

from app.file_analysis.services.inspectors import register
from app.file_analysis.services.inspectors.base import Inspector
from app.file_analysis.services.inspectors.base import InspectorContext
from app.file_analysis.services.inspectors.base import InspectorResult
from app.file_analysis.services.inspectors.base import truncate_evidence
from app.file_analysis.services.iocs import CONTEXT_TEXT
from app.file_analysis.services.iocs import extract_iocs
from app.file_analysis.utils.deobfuscate import deobfuscate

_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)

# Token -> flag. Checked against both the raw bytes and every inflated stream.
_TOKENS = (
    (rb"/JavaScript", "pdf.javascript"),
    (rb"/JS", "pdf.javascript"),
    (rb"/OpenAction", "pdf.open_action"),
    (rb"/AA", "pdf.additional_action"),
    (rb"/Launch", "pdf.launch_action"),
    (rb"/EmbeddedFile", "pdf.embedded_file"),
    (rb"/URI", "pdf.uri_action"),
    (rb"/Encrypt", "pdf.encrypted"),
)

# Cap on inflated streams examined. A PDF can declare thousands; past a point
# they stop adding signal and start costing wall clock.
MAX_STREAMS = 300


@register
class PdfInspector(Inspector):
    name = "pdf"
    mime_types = ("application/pdf", "application/x-pdf")
    extensions = ("pdf",)
    magic_prefixes = (b"%PDF-",)

    def inspect(self, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()
        data = ctx.data

        inflated = self._inflate_streams(data)
        # Raw bytes plus every inflated stream: a token hidden in an object
        # stream is exactly the case the raw scan alone would miss.
        haystacks: List[bytes] = [data] + inflated

        for token, flag in _TOKENS:
            for haystack in haystacks:
                position = haystack.find(token)
                if position == -1:
                    continue
                snippet = haystack[max(0, position - 60) : position + 200]
                result.add(flag, truncate_evidence(snippet.decode("latin-1", errors="replace"), ctx.limits))
                break

        # JavaScript recovered from the document is worth deobfuscating: PDF
        # droppers routinely build the payload URL from char codes.
        script_text = self._recover_javascript(inflated, ctx.limits.max_text_chars)
        if script_text:
            peeled = deobfuscate(script_text)
            if peeled.layers:
                result.add("script.obfuscated", truncate_evidence(", ".join(peeled.layers), ctx.limits))
            result.extracted_text = peeled.text[: ctx.limits.max_text_chars]
            result.iocs.extend(extract_iocs(peeled.text, context=CONTEXT_TEXT))

        # Indicators from the document body itself (annotations, URI actions).
        text_blob = b"\n".join(haystacks)[: ctx.limits.max_text_chars]
        result.iocs.extend(extract_iocs(text_blob.decode("latin-1", errors="replace"), context=CONTEXT_TEXT))

        return result

    @staticmethod
    def _inflate_streams(data: bytes) -> List[bytes]:
        """Inflate FlateDecode streams, skipping the ones that are not."""
        out: List[bytes] = []
        for match in _STREAM.finditer(data):
            if len(out) >= MAX_STREAMS:
                break
            raw = match.group(1)
            try:
                out.append(zlib.decompress(raw))
            except zlib.error:
                # Not Flate, or truncated. Common in hostile files; the raw
                # bytes were already scanned so nothing is lost by skipping.
                continue
        return out

    @staticmethod
    def _recover_javascript(streams: List[bytes], max_chars: int) -> str:
        """Collect stream contents that look like the document's script."""
        collected: List[str] = []
        budget = max_chars
        for stream in streams:
            if budget <= 0:
                break
            text = stream.decode("latin-1", errors="replace")
            if not any(marker in text for marker in ("app.", "this.", "function", "eval", "unescape", "String.fromCharCode")):
                continue
            chunk = text[:budget]
            collected.append(chunk)
            budget -= len(chunk)
        return "\n".join(collected)
