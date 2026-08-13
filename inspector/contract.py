"""Shared types, flag constants, and result scaffolding for the Tier 1 inspector.

This module has ZERO third-party dependencies so it can be imported by the
analyzers, the entrypoint, and the test suite without pulling in parser tooling.

The JSON contract emitted on stdout is specified in
CLAUDE.md -> File Analysis
"""
from __future__ import annotations

import dataclasses
from typing import Any
from typing import Dict
from typing import List
from typing import Optional


# --- Verdicts (see CLAUDE.md -> File Analysis) ---------------------
VERDICT_CLEAN = "clean"
VERDICT_SUSPICIOUS = "suspicious"
VERDICT_MALICIOUS = "malicious"

# Severity ordering so max(static, dynamic) is a simple comparison.
VERDICT_SEVERITY: Dict[str, int] = {
    VERDICT_CLEAN: 0,
    VERDICT_SUSPICIOUS: 1,
    VERDICT_MALICIOUS: 2,
}


# --- Flags -----------------------------------------------------------------
# One canonical constant per flag string so analyzers never hand-type them and
# the verdict table can match on identity. These strings are part of the result
# contract the CoPilot UI renders — renaming one is a breaking change.
FLAG_AUTO_EXECUTE_JAVASCRIPT = "auto_execute_javascript"
FLAG_LAUNCH_ACTION = "launch_action"
FLAG_AUTOOPEN_MACRO = "autoopen_macro"
FLAG_ENCODED_POWERSHELL = "encoded_powershell"
FLAG_LNK_SUSPICIOUS_ARGS = "lnk_suspicious_args"
FLAG_DDE_PRESENT = "dde_present"
FLAG_HTML_SMUGGLING = "html_smuggling"
FLAG_ENCRYPTED_ARCHIVE = "encrypted_archive"
FLAG_ENCRYPTED_ARCHIVE_OPENED = "encrypted_archive_opened"
FLAG_REPLY_TO_MISMATCH = "reply_to_mismatch"
FLAG_SUSPICIOUS_ATTACHMENT = "suspicious_attachment"
FLAG_DEOBFUSCATION_INCOMPLETE = "deobfuscation_incomplete"
FLAG_ANALYSIS_INCOMPLETE = "analysis_incomplete"
FLAG_EMBEDDED_FILE = "embedded_file"
FLAG_ELF_STATIC_STRIPPED = "elf_static_stripped"
FLAG_ELF_SUSPICIOUS_INTERP = "elf_suspicious_interp"


@dataclasses.dataclass
class InspectorResult:
    """In-memory builder for the stdout JSON contract.

    Analyzers mutate an instance of this via the ``add_*`` helpers; the
    entrypoint serialises it with :meth:`to_dict` after computing the verdict.
    """

    sha256: str
    filename: str
    customer_code: str
    filetype: str = "unknown"
    magic: str = ""
    extension_mismatch: bool = False
    entropy: float = 0.0
    hashes: Dict[str, Optional[str]] = dataclasses.field(default_factory=dict)
    iocs: Dict[str, List[str]] = dataclasses.field(
        default_factory=lambda: {"urls": [], "ips": [], "domains": []},
    )
    av: Optional[Dict[str, Any]] = None
    previews: List[str] = dataclasses.field(default_factory=list)
    content: Dict[str, Any] = dataclasses.field(default_factory=dict)
    flags: List[str] = dataclasses.field(default_factory=list)
    analysis_incomplete: bool = False
    verdict_hint: str = VERDICT_CLEAN
    engine_version: int = 1

    def add_flag(self, flag: str) -> None:
        if flag not in self.flags:
            self.flags.append(flag)

    def add_ioc(self, kind: str, value: str) -> None:
        bucket = self.iocs.setdefault(kind, [])
        if value and value not in bucket:
            bucket.append(value)

    def mark_incomplete(self) -> None:
        self.analysis_incomplete = True
        self.add_flag(FLAG_ANALYSIS_INCOMPLETE)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


# The single integer bumped whenever analyzers change meaningfully; the CoPilot
# cache is keyed by (sha256, engine_version) so improvements re-apply to files
# already seen (see CLAUDE.md -> File Analysis).
ENGINE_VERSION = 1
