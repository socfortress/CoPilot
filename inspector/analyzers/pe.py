"""PE analyzer — imports, sections, signature, imphash, capabilities, strings.

pefile for structure/imphash; capa for capabilities; FLOSS for strings. capa and
FLOSS are the slowest tools in the image, so each runs under its own sub-timeout
and a failure degrades to "pefile-only + analysis_incomplete" rather than eating
the whole job budget (see CLAUDE.md -> File Analysis). No preview — a binary is not a document.

FLOSS is honest emulation (vivisect), not native execution; that distinction is
documented but it is still contained by the no-network no-caps container.
"""
from __future__ import annotations

import json
import subprocess
from typing import List

from common import extract_iocs
from contract import InspectorResult

_CAPA_TIMEOUT = 120
_FLOSS_TIMEOUT = 120


def _pefile(sample_path: str, result: InspectorResult) -> bool:
    try:
        import pefile
    except ImportError:
        return False
    try:
        pe = pefile.PE(sample_path, fast_load=True)
        pe.parse_data_directories()
    except Exception:
        return False

    imports: List[str] = []
    try:
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) or []:
            dll = entry.dll.decode("utf-8", errors="replace") if entry.dll else ""
            for imp in entry.imports:
                name = imp.name.decode("utf-8", errors="replace") if imp.name else f"ord{imp.ordinal}"
                imports.append(f"{dll}!{name}")
    except Exception:
        pass

    result.content["imports"] = imports[:2000]
    result.content["import_count"] = len(imports)
    result.content["sections"] = [
        {
            "name": s.Name.decode("utf-8", errors="replace").rstrip("\x00"),
            "vsize": int(s.Misc_VirtualSize),
            "rawsize": int(s.SizeOfRawData),
            "entropy": round(s.get_entropy(), 3),
        }
        for s in pe.sections
    ]
    try:
        result.hashes["imphash"] = pe.get_imphash() or None
    except Exception:
        pass
    result.content["timestamp"] = int(getattr(pe.FILE_HEADER, "TimeDateStamp", 0))
    # Signature presence: a Security directory entry with non-zero size.
    result.content["signature_present"] = _has_signature(pe)
    pe.close()
    return True


def _has_signature(pe) -> bool:
    try:
        directory = pe.OPTIONAL_HEADER.DATA_DIRECTORY[4]  # IMAGE_DIRECTORY_ENTRY_SECURITY
        return bool(directory.VirtualAddress and directory.Size)
    except Exception:
        return False


def _capa(sample_path: str, result: InspectorResult) -> None:
    # capa is OPTIONAL capability enrichment. Its absence/timeout must degrade
    # gracefully — the core PE parse already succeeded, so a missing FLARE tool
    # must NOT mark the whole analysis incomplete (that would fail-close EVERY
    # .exe to "suspicious" on any inspector without capa installed).
    try:
        proc = subprocess.run(["capa", "-j", sample_path], capture_output=True, timeout=_CAPA_TIMEOUT, check=False)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        result.content.setdefault("enrichment_skipped", []).append("capa")
        return
    if proc.returncode != 0 or not proc.stdout:
        return
    try:
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        rules = data.get("rules", {})
        caps = sorted({meta.get("meta", {}).get("name", "") for meta in rules.values() if meta})
        result.content["capabilities"] = [c for c in caps if c]
    except (json.JSONDecodeError, AttributeError):
        pass


def _floss(sample_path: str, result: InspectorResult) -> None:
    # FLOSS is OPTIONAL deobfuscated-string enrichment — same rule as capa: a
    # missing/slow tool degrades gracefully and never marks the analysis incomplete.
    try:
        proc = subprocess.run(["floss", "-j", "-q", sample_path], capture_output=True, timeout=_FLOSS_TIMEOUT, check=False)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        result.content.setdefault("enrichment_skipped", []).append("floss")
        return
    if not proc.stdout:
        return
    try:
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        strings_block = data.get("strings", data)
        collected: List[str] = []
        for key in ("static_strings", "stack_strings", "decoded_strings", "tight_strings"):
            for item in strings_block.get(key, []) or []:
                s = item.get("string") if isinstance(item, dict) else str(item)
                if s:
                    collected.append(s)
        result.content["strings"] = collected[:5000]
        for kind, values in extract_iocs("\n".join(collected)).items():
            for value in values:
                result.add_ioc(kind, value)
    except (json.JSONDecodeError, AttributeError):
        pass


def analyze(sample_path: str, result: InspectorResult) -> None:
    result.filetype = "pe"
    if not _pefile(sample_path, result):
        result.mark_incomplete()
        return
    _capa(sample_path, result)
    _floss(sample_path, result)
