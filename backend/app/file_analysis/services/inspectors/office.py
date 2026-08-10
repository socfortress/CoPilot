"""Office inspector: OOXML (.docx/.xlsm/.pptm) and OLE legacy (.doc/.xls/.ppt).

Both containers share the ``office.*`` flag namespace because the *techniques*
are identical -- an auto-executing macro is the same tradecraft whether it sits
in a 2003 compound file or a 2007 zip. Only the parsing differs.

VBA extraction goes through ``oletools``, which is the reference implementation
for this and is parse-only: it walks the compound-file structure and decompresses
VBA source. It never runs the project. The remaining checks (DDE fields, external
relationships, remote template injection) are direct reads of the container.

A remote template URL is reported as an indicator. It is never fetched -- doing so
would turn a static inspection into a callback that tells the author their sample
was analysed, and hands the CoPilot host's egress to the sample.
"""

from __future__ import annotations

import io
import re
import zipfile
from typing import List
from typing import Tuple

from loguru import logger

# Imported at module scope, not lazily inside inspect(). oletools builds its
# pyparsing grammars at import time (~0.25s); paying that inside a worker
# thread makes the first Office document of every process pause the request
# that triggered it. It is a declared dependency, so a missing one should
# fail loudly at boot rather than turn into a per-job RuntimeError.
from oletools.olevba import VBA_Parser

from app.file_analysis.services.inspectors import register
from app.file_analysis.services.inspectors.base import Inspector
from app.file_analysis.services.inspectors.base import InspectorContext
from app.file_analysis.services.inspectors.base import InspectorResult
from app.file_analysis.services.inspectors.base import truncate_evidence
from app.file_analysis.services.inspectors.script import ScriptInspector
from app.file_analysis.services.iocs import CONTEXT_MACRO
from app.file_analysis.services.iocs import CONTEXT_METADATA
from app.file_analysis.services.iocs import extract_iocs
from app.file_analysis.utils.deobfuscate import deobfuscate

# OLE compound file header. Shared by legacy Office and by encrypted OOXML,
# which wraps the real package in a compound file.
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

_DDE_FIELD = re.compile(rb"DDEAUTO|\bDDE\b\s+[\"']?[a-z]:", re.IGNORECASE)
_EXTERNAL_REL = re.compile(rb'TargetMode\s*=\s*"External"', re.IGNORECASE)
_ATTACHED_TEMPLATE = re.compile(rb'Type\s*=\s*"[^"]*attachedTemplate"[^>]*Target\s*=\s*"([^"]+)"', re.IGNORECASE)
_REL_TARGET = re.compile(rb'Target\s*=\s*"([^"]+)"[^>]*TargetMode\s*=\s*"External"', re.IGNORECASE)

# Members of an OOXML package worth reading as text for DDE and indicators.
_TEXT_PARTS = (".xml", ".rels", ".bin")

MAX_MEMBERS_READ = 200


@register
class OfficeInspector(Inspector):
    name = "office"
    mime_types = (
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "application/vnd.ms-office",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-word.document.macroenabled.12",
        "application/vnd.ms-excel.sheet.macroenabled.12",
        "application/vnd.ms-powerpoint.presentation.macroenabled.12",
        "application/x-ole-storage",
        "application/CDFV2",
    )
    extensions = ("doc", "docx", "docm", "dot", "dotm", "xls", "xlsx", "xlsm", "xlsb", "ppt", "pptx", "pptm", "rtf")
    # Not registered as a magic prefix: the OLE header is shared with several
    # non-Office formats (MSI, some installers), and the zip header is shared
    # with every zip. Content probing below handles the OOXML case; MIME and
    # extension routing handle the rest.
    magic_prefixes = ()

    def claims(self, data: bytes, mime_type: str, file_name: str) -> bool:
        """Recognise an OOXML package by its own manifest part.

        libmagic reports ``application/zip`` for OOXML often enough that MIME
        routing alone would hand a macro-enabled document to the archive
        inspector, which would happily list ``word/vbaProject.bin`` as a member
        and never raise a single ``office.*`` flag.

        ``[Content_Types].xml`` is required at the package root by the OPC
        specification, so its presence is a definition rather than a heuristic --
        and a plain zip that merely happens to contain a ``word/`` folder does
        not match.
        """
        if not data.startswith(b"PK\x03\x04"):
            return False
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                return "[Content_Types].xml" in archive.namelist()
        except (zipfile.BadZipFile, OSError, ValueError):
            return False

    def inspect(self, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()
        data = ctx.data

        if data.startswith(OLE_MAGIC) and b"EncryptedPackage" in data[:16384]:
            # An encrypted package cannot be parsed further without the
            # password. Reported rather than failed: "this document is
            # encrypted" is itself triage material.
            result.add("office.encrypted", "OLE container holds an EncryptedPackage stream")
            return result

        if zipfile.is_zipfile(io.BytesIO(data)):
            result.merge(self._inspect_ooxml(data, ctx))
        else:
            result.merge(self._inspect_ole(data, ctx))

        result.merge(self._inspect_macros(data, ctx))
        return result

    # ------------------------------------------------------------------
    # OOXML
    # ------------------------------------------------------------------
    def _inspect_ooxml(self, data: bytes, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            logger.warning(f"file_analysis: OOXML container unreadable: {exc}")
            return result

        text_blobs: List[bytes] = []
        for info in archive.infolist()[:MAX_MEMBERS_READ]:
            if not info.filename.lower().endswith(_TEXT_PARTS):
                continue
            try:
                blob = archive.read(info)
            except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
                logger.debug(f"file_analysis: OOXML member {info.filename} unreadable: {exc}")
                continue
            text_blobs.append(blob)

            if info.filename.lower().endswith("vbaproject.bin"):
                result.add("office.macro_present", f"VBA project at {info.filename}")

            if info.filename.lower().endswith(".rels"):
                result.merge(self._inspect_relationships(blob, info.filename, ctx))

        combined = b"\n".join(text_blobs)
        if _DDE_FIELD.search(combined):
            match = _DDE_FIELD.search(combined)
            snippet = combined[max(0, match.start() - 60) : match.start() + 200]
            result.add("office.dde_field", truncate_evidence(snippet.decode("latin-1", errors="replace"), ctx.limits))

        result.iocs.extend(
            extract_iocs(combined[: ctx.limits.max_text_chars].decode("latin-1", errors="replace"), context=CONTEXT_METADATA),
        )
        return result

    @staticmethod
    def _inspect_relationships(blob: bytes, part_name: str, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()

        template = _ATTACHED_TEMPLATE.search(blob)
        if template:
            target = template.group(1).decode("latin-1", errors="replace")
            result.add("office.remote_template", truncate_evidence(f"{part_name}: {target}", ctx.limits))
            result.iocs.extend(extract_iocs(target, context=CONTEXT_METADATA))
        elif _EXTERNAL_REL.search(blob):
            targets = [t.decode("latin-1", errors="replace") for t in _REL_TARGET.findall(blob)]
            result.add("office.external_relationship", truncate_evidence(f"{part_name}: {', '.join(targets[:5])}", ctx.limits))
            for target in targets[:20]:
                result.iocs.extend(extract_iocs(target, context=CONTEXT_METADATA))

        return result

    # ------------------------------------------------------------------
    # OLE legacy
    # ------------------------------------------------------------------
    @staticmethod
    def _inspect_ole(data: bytes, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()

        match = _DDE_FIELD.search(data)
        if match:
            snippet = data[max(0, match.start() - 60) : match.start() + 200]
            result.add("office.dde_field", truncate_evidence(snippet.decode("latin-1", errors="replace"), ctx.limits))

        return result

    # ------------------------------------------------------------------
    # VBA, shared by both containers
    # ------------------------------------------------------------------
    def _inspect_macros(self, data: bytes, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()

        parser = None
        try:
            parser = VBA_Parser(ctx.file_name or "sample", data=data)
            if not parser.detect_vba_macros():
                return result

            result.add("office.macro_present", "VBA macro project detected")

            sources: List[str] = []
            for _, _, vba_filename, vba_code in parser.extract_macros():
                if not vba_code:
                    continue
                sources.append(f"' ---- {vba_filename} ----\n{vba_code}")

            for kind, keyword, description in parser.analyze_macros():
                label = (kind or "").lower()
                if label == "autoexec":
                    result.add("office.auto_exec_macro", truncate_evidence(f"{keyword}: {description}", ctx.limits))
                elif label == "suspicious":
                    result.add("office.suspicious_macro_keyword", truncate_evidence(f"{keyword}: {description}", ctx.limits))

            if sources:
                result.merge(self._analyse_macro_source("\n\n".join(sources), ctx))

        except RuntimeError:
            raise
        except Exception as exc:
            # oletools raises a wide range of parser errors on malformed input.
            # A document it cannot parse is not a failed job: the container
            # checks above already ran and their findings stand.
            logger.warning(f"file_analysis: VBA parsing failed for {ctx.file_name}: {exc}")
        finally:
            if parser is not None:
                try:
                    parser.close()
                except Exception:  # pragma: no cover - close is best effort
                    pass

        return result

    @staticmethod
    def _analyse_macro_source(source: str, ctx: InspectorContext) -> InspectorResult:
        """Run recovered VBA through the same analysis a standalone script gets."""
        result = InspectorResult()
        trimmed = source[: ctx.limits.max_text_chars]

        peeled = deobfuscate(trimmed)
        if peeled.layers:
            result.add("script.obfuscated", truncate_evidence(" -> ".join(peeled.layers), ctx.limits))

        scanned = ScriptInspector.scan_text(original=trimmed, peeled=peeled.text, ctx=ctx)
        result.merge(scanned)

        # Re-attribute to the macro context: an indicator inside a macro is a
        # stronger statement than the same string in document metadata.
        result.iocs = [ioc._replace(context=CONTEXT_MACRO) for ioc in result.iocs]
        result.extracted_text = peeled.text[: ctx.limits.max_text_chars]
        return result


def ole_header() -> Tuple[bytes, ...]:
    """Exposed for tests that build synthetic OLE fixtures."""
    return (OLE_MAGIC,)
