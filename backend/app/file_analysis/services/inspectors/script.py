"""Script inspector: PowerShell, VBScript, JScript, batch, HTA, shell.

The script is decoded, never run. Deobfuscation is pure string rewriting (see
``utils/deobfuscate``), and detection is substring matching over the original
*and* the peeled text.

Matching both matters: an author who base64-encodes the payload defeats a scan
of the original, while an author who leaves it in plain sight is missed by a
scan of the peeled text only when deobfuscation rewrote the region. Scanning
both costs one extra pass and closes both gaps.
"""

from __future__ import annotations

from typing import Sequence
from typing import Tuple

from app.file_analysis.services.inspectors import register
from app.file_analysis.services.inspectors.base import Inspector
from app.file_analysis.services.inspectors.base import InspectorContext
from app.file_analysis.services.inspectors.base import InspectorResult
from app.file_analysis.services.inspectors.base import truncate_evidence
from app.file_analysis.services.iocs import CONTEXT_DEOBFUSCATED
from app.file_analysis.services.iocs import CONTEXT_TEXT
from app.file_analysis.services.iocs import extract_iocs
from app.file_analysis.utils.deobfuscate import deobfuscate

# (flag, markers) — matched case-insensitively.
SCRIPT_INDICATORS: Sequence[Tuple[str, Tuple[str, ...]]] = (
    (
        "script.encoded_command",
        ("-encodedcommand", "-enc ", "-ec ", "frombase64string", "::frombase64", "certutil -decode", "certutil.exe -decode"),
    ),
    (
        "script.download_invocation",
        (
            "downloadstring",
            "downloadfile",
            "downloaddata",
            "invoke-webrequest",
            "invoke-restmethod",
            "start-bitstransfer",
            "urldownloadtofile",
            "msxml2.xmlhttp",
            "winhttp.winhttprequest",
            "bitsadmin",
            "wget ",
            "curl ",
        ),
    ),
    (
        "script.hidden_window",
        ("-windowstyle hidden", "-w hidden", "-windowstyle 1", "vbhide", "createnowindow", "0,true)", "0, true)"),
    ),
    (
        "script.suspicious_api",
        (
            "invoke-expression",
            "iex(",
            "iex (",
            "add-type",
            "virtualalloc",
            "createremotethread",
            "reflection.assembly",
            "wscript.shell",
            "shell.application",
            "rundll32",
            "regsvr32",
            "mshta",
            "schtasks",
            "vssadmin delete",
            "wmic process call create",
            "set-mppreference",
            "new-object net.webclient",
        ),
    ),
)

# Extensions treated as script when libmagic reports something generic.
SCRIPT_EXTENSIONS = ("ps1", "psm1", "psd1", "vbs", "vbe", "js", "jse", "wsf", "wsh", "bat", "cmd", "hta", "sh", "py", "pl")


@register
class ScriptInspector(Inspector):
    name = "script"
    mime_types = (
        "text/x-shellscript",
        "text/x-msdos-batch",
        "application/javascript",
        "text/javascript",
        "application/x-powershell",
        "text/x-python",
        "text/x-perl",
    )
    extensions = SCRIPT_EXTENSIONS
    magic_prefixes = ()

    def inspect(self, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()

        text = self._decode(ctx.data)[: ctx.limits.max_text_chars]
        if not text.strip():
            return result

        peeled = deobfuscate(text)
        if peeled.layers:
            result.add("script.obfuscated", truncate_evidence(" -> ".join(peeled.layers), ctx.limits))
        if peeled.hit_pass_limit:
            # Still changing when the pass ceiling was reached. Either the
            # obfuscation is deeper than anything legitimate needs, or it is
            # self-referential; both are worth surfacing rather than silently
            # returning a half-peeled result.
            result.add(
                "script.deep_obfuscation",
                truncate_evidence(f"still rewriting after {peeled.passes} passes", ctx.limits),
            )

        result.merge(self.scan_text(original=text, peeled=peeled.text, ctx=ctx))
        result.extracted_text = peeled.text[: ctx.limits.max_text_chars]
        return result

    @staticmethod
    def scan_text(original: str, peeled: str, ctx: InspectorContext) -> InspectorResult:
        """Flag and IOC extraction shared with the Office macro inspector.

        Office VBA and a standalone .ps1 raise the same ``script.*`` flags for
        the same constructs, so the logic lives here once rather than being
        duplicated per container.
        """
        result = InspectorResult()

        lowered_original = original.lower()
        lowered_peeled = peeled.lower()

        for flag, markers in SCRIPT_INDICATORS:
            for marker in markers:
                where = None
                if marker in lowered_peeled:
                    where = (peeled, lowered_peeled)
                elif marker in lowered_original:
                    where = (original, lowered_original)
                if where is None:
                    continue
                haystack, lowered = where
                position = lowered.find(marker)
                snippet = haystack[max(0, position - 80) : position + 160]
                result.add(flag, truncate_evidence(snippet, ctx.limits))
                break

        result.iocs.extend(extract_iocs(original, context=CONTEXT_TEXT))
        if peeled != original:
            # Indicators that only surface after peeling are the stronger
            # signal, and merge_iocs keeps that attribution.
            result.iocs.extend(extract_iocs(peeled, context=CONTEXT_DEOBFUSCATED))

        return result

    @staticmethod
    def _decode(data: bytes) -> str:
        """Decode script bytes, tolerating BOMs and UTF-16 (common on Windows)."""
        for encoding in ("utf-8-sig", "utf-16", "utf-8", "latin-1"):
            try:
                return data.decode(encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return data.decode("latin-1", errors="replace")
