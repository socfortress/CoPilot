"""PE and ELF inspector.

Header and section parsing only -- the binary is never loaded, mapped or run.

The flags here are individually weak on purpose. A high-entropy section, an
empty import table and a trailing overlay are each ordinary in isolation
(installers, .NET assemblies and self-extracting archives all show them). They
carry weight in combination, which is exactly what an additive score expresses.
"""

from __future__ import annotations

import io
from typing import List

import pefile
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from loguru import logger

from app.file_analysis.services.inspectors import register
from app.file_analysis.services.inspectors.base import Inspector
from app.file_analysis.services.inspectors.base import InspectorContext
from app.file_analysis.services.inspectors.base import InspectorResult
from app.file_analysis.services.inspectors.base import truncate_evidence
from app.file_analysis.services.iocs import CONTEXT_RAW
from app.file_analysis.services.iocs import extract_iocs
from app.file_analysis.utils.entropy import HIGH_ENTROPY_THRESHOLD
from app.file_analysis.utils.entropy import shannon_entropy

PE_MAGIC = b"MZ"
ELF_MAGIC = b"\x7fELF"

# Imports that are unremarkable alone but characteristic of injection, hollowing
# and anti-analysis when they cluster.
SUSPICIOUS_IMPORTS = frozenset(
    {
        "createremotethread",
        "writeprocessmemory",
        "virtualallocex",
        "ntunmapviewofsection",
        "queueuserapc",
        "setwindowshookex",
        "isdebuggerpresent",
        "checkremotedebuggerpresent",
        "ntqueryinformationprocess",
        "getprocaddress",
        "loadlibrarya",
        "loadlibraryw",
        "winexec",
        "shellexecutea",
        "shellexecutew",
        "urldownloadtofilea",
        "urldownloadtofilew",
        "internetopenurla",
        "cryptencrypt",
        "ptrace",
        "mprotect",
    },
)

# Minimum printable run treated as a string worth extracting indicators from.
MIN_STRING_LENGTH = 6


@register
class BinaryInspector(Inspector):
    name = "binary"
    mime_types = (
        "application/x-dosexec",
        "application/x-msdownload",
        "application/vnd.microsoft.portable-executable",
        "application/x-executable",
        "application/x-sharedlib",
        "application/x-pie-executable",
        "application/x-elf",
    )
    extensions = ("exe", "dll", "sys", "scr", "so", "o", "elf")
    magic_prefixes = (ELF_MAGIC,)

    def inspect(self, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()
        data = ctx.data

        if data.startswith(ELF_MAGIC):
            result.merge(self._inspect_elf(data, ctx))
        elif data.startswith(PE_MAGIC):
            result.merge(self._inspect_pe(data, ctx))

        # Printable strings feed indicator extraction. This is a read of the
        # bytes, nothing more.
        result.iocs.extend(extract_iocs(self._strings(data, ctx.limits.max_text_chars), context=CONTEXT_RAW))
        return result

    # ------------------------------------------------------------------
    def _inspect_pe(self, data: bytes, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()

        try:
            pe = pefile.PE(data=data, fast_load=True)
            pe.parse_data_directories(
                directories=[
                    pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                    pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"],
                ],
            )
        except Exception as exc:
            logger.warning(f"file_analysis: PE parsing failed for {ctx.file_name}: {exc}")
            return result

        try:
            for section in pe.sections:
                section_data = section.get_data()
                if not section_data:
                    continue
                entropy = shannon_entropy(section_data)
                if entropy >= HIGH_ENTROPY_THRESHOLD:
                    name = section.Name.rstrip(b"\x00").decode("latin-1", errors="replace")
                    result.add("binary.packed_section", truncate_evidence(f"{name}: entropy {entropy:.2f}", ctx.limits))
                    break

            imports = self._pe_imports(pe)
            if not imports:
                result.add("binary.no_imports", "PE has no readable import table")
            else:
                hits = sorted(imports & SUSPICIOUS_IMPORTS)
                if hits:
                    result.add("binary.suspicious_import", truncate_evidence(", ".join(hits[:20]), ctx.limits))

            security = getattr(pe, "OPTIONAL_HEADER", None)
            directory = getattr(security, "DATA_DIRECTORY", []) if security else []
            signed = any(entry.name == "IMAGE_DIRECTORY_ENTRY_SECURITY" and entry.VirtualAddress and entry.Size for entry in directory)
            if not signed:
                result.add("binary.unsigned", "no authenticode signature directory")

            end_of_sections = max((s.PointerToRawData + s.SizeOfRawData for s in pe.sections), default=0)
            if end_of_sections and len(data) > end_of_sections:
                result.add(
                    "binary.overlay_present",
                    truncate_evidence(f"{len(data) - end_of_sections} bytes past the last section", ctx.limits),
                )
        finally:
            try:
                pe.close()
            except Exception:  # pragma: no cover - close is best effort
                pass

        return result

    @staticmethod
    def _pe_imports(pe) -> set:
        names = set()
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) or []:
            for imp in entry.imports or []:
                if imp.name:
                    names.add(imp.name.decode("latin-1", errors="replace").lower())
        return names

    # ------------------------------------------------------------------
    def _inspect_elf(self, data: bytes, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()

        try:
            elf = ELFFile(io.BytesIO(data))

            for section in elf.iter_sections():
                section_data = section.data()
                if not section_data or len(section_data) < 1024:
                    continue
                entropy = shannon_entropy(section_data)
                if entropy >= HIGH_ENTROPY_THRESHOLD:
                    result.add("binary.packed_section", truncate_evidence(f"{section.name}: entropy {entropy:.2f}", ctx.limits))
                    break

            symbols = self._elf_dynamic_symbols(elf)
            if not symbols:
                result.add("binary.no_imports", "ELF has no dynamic symbol table")
            else:
                hits = sorted(symbols & SUSPICIOUS_IMPORTS)
                if hits:
                    result.add("binary.suspicious_import", truncate_evidence(", ".join(hits[:20]), ctx.limits))
        except Exception as exc:
            logger.warning(f"file_analysis: ELF parsing failed for {ctx.file_name}: {exc}")

        return result

    @staticmethod
    def _elf_dynamic_symbols(elf) -> set:
        names = set()
        for section in elf.iter_sections():
            if not isinstance(section, SymbolTableSection):
                continue
            for symbol in section.iter_symbols():
                if symbol.name:
                    names.add(symbol.name.lower())
        return names

    # ------------------------------------------------------------------
    @staticmethod
    def _strings(data: bytes, max_chars: int) -> str:
        """Extract printable ASCII runs, the classic `strings` behaviour."""
        out: List[str] = []
        current: List[int] = []
        budget = max_chars

        for byte in data:
            if 0x20 <= byte < 0x7F:
                current.append(byte)
                continue
            if len(current) >= MIN_STRING_LENGTH:
                text = bytes(current).decode("ascii", errors="ignore")
                out.append(text)
                budget -= len(text)
                if budget <= 0:
                    break
            current = []

        if budget > 0 and len(current) >= MIN_STRING_LENGTH:
            out.append(bytes(current).decode("ascii", errors="ignore"))

        return "\n".join(out)[:max_chars]
