"""Deterministic verdict mapping for Tier 1 findings.

Implements the fixed table in CLAUDE.md -> File Analysis
section 4. The point of a table (rather than scattered ``if`` statements in each
analyzer) is that the same findings always produce the same verdict across
analysts and builds. The highest matching row wins.

This is intentionally a pure function of the assembled result dict — no I/O, no
tooling — so it is trivially unit-testable against fixtures.
"""
from __future__ import annotations

from typing import Dict

from contract import FLAG_ANALYSIS_INCOMPLETE
from contract import FLAG_AUTO_EXECUTE_JAVASCRIPT
from contract import FLAG_AUTOOPEN_MACRO
from contract import FLAG_DDE_PRESENT
from contract import FLAG_DEOBFUSCATION_INCOMPLETE
from contract import FLAG_ENCODED_POWERSHELL
from contract import FLAG_HTML_SMUGGLING
from contract import FLAG_LAUNCH_ACTION
from contract import FLAG_LNK_SUSPICIOUS_ARGS
from contract import FLAG_MALICIOUS_BEHAVIOR
from contract import FLAG_SUSPICIOUS_BEHAVIOR
from contract import FLAG_SUSPICIOUS_ATTACHMENT
from contract import VERDICT_CLEAN
from contract import VERDICT_MALICIOUS
from contract import VERDICT_SUSPICIOUS


# Executable-ish true types where an extension mismatch is itself alarming.
_EXECUTABLE_TYPES = {"pe", "elf", "script", "lnk", "hta"}

# Flags that on their own justify at least "suspicious".
_SUSPICIOUS_FLAGS = {
    FLAG_AUTO_EXECUTE_JAVASCRIPT,
    FLAG_LAUNCH_ACTION,
    FLAG_AUTOOPEN_MACRO,
    FLAG_ENCODED_POWERSHELL,
    FLAG_LNK_SUSPICIOUS_ARGS,
    FLAG_DDE_PRESENT,
    FLAG_HTML_SMUGGLING,
    FLAG_SUSPICIOUS_ATTACHMENT,
    FLAG_DEOBFUSCATION_INCOMPLETE,
    FLAG_SUSPICIOUS_BEHAVIOR,
}


def _has_av_hit(result: Dict) -> bool:
    av = result.get("av") or {}
    return bool(av.get("signature"))


def _macro_is_malicious(result: Dict) -> bool:
    """AutoOpen macro combined with an execution/download primitive."""
    if FLAG_AUTOOPEN_MACRO not in result.get("flags", []):
        return False
    macros = (result.get("content") or {}).get("macros", "")
    text = macros.lower() if isinstance(macros, str) else str(macros).lower()
    return any(token in text for token in ("shell", "urldownloadtofile", "wscript", "createobject", "powershell"))


def _pdf_is_malicious(result: Dict) -> bool:
    flags = result.get("flags", [])
    if not (FLAG_AUTO_EXECUTE_JAVASCRIPT in flags or FLAG_LAUNCH_ACTION in flags):
        return False
    content = result.get("content") or {}
    payload = " ".join(
        str(content.get(key, "")) for key in ("javascript", "deobfuscated", "launch")
    ).lower()
    return any(token in payload for token in ("powershell", "cmd.exe", "http://", "https://", "downloadstring", "iex"))


def _lnk_is_malicious(result: Dict) -> bool:
    if FLAG_LNK_SUSPICIOUS_ARGS not in result.get("flags", []):
        return False
    args = (result.get("content") or {}).get("arguments", "")
    args_l = args.lower() if isinstance(args, str) else ""
    invokes_interpreter = any(t in args_l for t in ("powershell", "cmd", "wscript", "cscript", "mshta", "rundll32"))
    remote_or_encoded = any(t in args_l for t in ("-enc", "http://", "https://", "downloadstring", "frombase64"))
    return invokes_interpreter and remote_or_encoded


def compute_verdict(result: Dict) -> str:
    """Return the ``verdict_hint`` for an assembled inspector result dict."""
    flags = set(result.get("flags", []))

    # Row 1 — malicious.
    if (
        _has_av_hit(result)
        or FLAG_MALICIOUS_BEHAVIOR in flags
        or _macro_is_malicious(result)
        or _pdf_is_malicious(result)
        or _lnk_is_malicious(result)
    ):
        return VERDICT_MALICIOUS

    # Row 2 — suspicious on a single strong flag or masquerading executable.
    if flags & _SUSPICIOUS_FLAGS:
        return VERDICT_SUSPICIOUS
    if result.get("extension_mismatch") and result.get("filetype") in _EXECUTABLE_TYPES:
        return VERDICT_SUSPICIOUS
    if _pe_high_risk(result):
        return VERDICT_SUSPICIOUS

    # Row 3 — never clean on partial data.
    if result.get("analysis_incomplete") or FLAG_ANALYSIS_INCOMPLETE in flags:
        return VERDICT_SUSPICIOUS

    # Row 4 — nothing matched.
    return VERDICT_CLEAN


def _pe_high_risk(result: Dict) -> bool:
    """Unsigned + high entropy + an injection/persistence capability."""
    if result.get("filetype") not in ("pe", "elf"):
        return False
    content = result.get("content") or {}
    signed = bool(content.get("signature_present"))
    entropy = float(result.get("entropy") or 0.0)
    caps = " ".join(content.get("capabilities", []) or []).lower()
    risky_cap = any(t in caps for t in ("inject", "persist", "registry run", "process hollow"))
    return (not signed) and entropy >= 7.5 and risky_cap
