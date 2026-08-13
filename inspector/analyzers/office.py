"""Office document analyzer — macro source, autoexec flags, DDE, page preview.

olevba/mraptor (oletools, pure-python) dump and score macros; LibreOffice
headless renders a page preview. The LibreOffice conversion runs under a locked
profile (macro security highest, no link/DDE auto-update) and its own sub-timeout
(see CLAUDE.md -> File Analysis). Everything degrades gracefully when a tool is missing.
"""
from __future__ import annotations

import os
import subprocess
from typing import List

from common import extract_iocs
from contract import FLAG_AUTOOPEN_MACRO
from contract import FLAG_DDE_PRESENT
from contract import InspectorResult

_LIBREOFFICE_TIMEOUT = 120
_RENDER_TIMEOUT = 60

_AUTOEXEC_KEYWORDS = (
    "AutoOpen", "AutoClose", "AutoExec", "Document_Open", "Workbook_Open",
    "Auto_Open", "DocumentOpen",
)
_SUSPICIOUS_KEYWORDS = ("Shell", "WScript", "URLDownloadToFile", "powershell", "CreateObject", "Run")


def _olevba(sample_path: str, result: InspectorResult) -> bool:
    try:
        from oletools.olevba import VBA_Parser
    except ImportError:
        return False
    try:
        parser = VBA_Parser(sample_path)
    except Exception:
        return False
    macro_sources: List[str] = []
    try:
        if parser.detect_vba_macros():
            for _, _, _, vba_code in parser.extract_macros():
                if vba_code:
                    macro_sources.append(vba_code)
    except Exception:
        result.mark_incomplete()
    finally:
        try:
            parser.close()
        except Exception:
            pass

    if macro_sources:
        joined = "\n\n".join(macro_sources)
        result.content["macros"] = joined[:500000]
        lowered = joined.lower()
        if any(k.lower() in lowered for k in _AUTOEXEC_KEYWORDS):
            result.add_flag(FLAG_AUTOOPEN_MACRO)
        result.content["autoexec_keywords"] = [k for k in _AUTOEXEC_KEYWORDS if k.lower() in lowered]
        result.content["suspicious_keywords"] = [k for k in _SUSPICIOUS_KEYWORDS if k.lower() in lowered]
        for kind, values in extract_iocs(joined).items():
            for value in values:
                result.add_ioc(kind, value)
    return True


def _dde(sample_path: str, result: InspectorResult) -> None:
    try:
        from oletools.msodde import process_file
    except ImportError:
        return
    try:
        dde_result = process_file(sample_path)
        if dde_result and dde_result.strip():
            result.content["dde"] = dde_result[:20000]
            result.add_flag(FLAG_DDE_PRESENT)
    except Exception:
        pass


def _preview(sample_path: str, result: InspectorResult, results_dir: str) -> None:
    if not results_dir:
        return
    binary = _find_libreoffice()
    if not binary:
        return
    # Locked profile: macros off, no link update. -env:UserInstallation isolates the profile.
    profile = os.path.join(results_dir, ".lo_profile")
    try:
        subprocess.run(
            [
                binary, "--headless", "--nologo", "--nofirststartwizard",
                "-env:UserInstallation=file://" + profile,
                "--convert-to", "pdf", "--outdir", results_dir, sample_path,
            ],
            capture_output=True, timeout=_LIBREOFFICE_TIMEOUT, check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        result.mark_incomplete()
        return
    pdfs = [f for f in os.listdir(results_dir) if f.endswith(".pdf")]
    if not pdfs:
        return
    pdf_path = os.path.join(results_dir, pdfs[0])
    prefix = os.path.join(results_dir, "page")
    try:
        subprocess.run(["pdftoppm", "-png", "-r", "100", "-l", "25", pdf_path, prefix],
                       capture_output=True, timeout=_RENDER_TIMEOUT, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return
    result.previews.extend(sorted(f for f in os.listdir(results_dir) if f.startswith("page") and f.endswith(".png")))


def _find_libreoffice() -> str:
    for name in ("soffice", "libreoffice"):
        for base in ("/usr/bin/", "/usr/local/bin/", ""):
            candidate = base + name
            if os.path.exists(candidate) or base == "":
                return candidate
    return ""


def analyze(sample_path: str, result: InspectorResult, results_dir: str = "") -> None:
    result.filetype = "office"
    had_tool = _olevba(sample_path, result)
    _dde(sample_path, result)
    _preview(sample_path, result, results_dir)
    if not had_tool:
        result.mark_incomplete()
