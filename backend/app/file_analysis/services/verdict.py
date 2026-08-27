"""Cross-tier verdict logic.

Pure functions — no DB, no network, no CoPilot imports — so they are trivially
unit-testable and carry zero side effects.

The job-level verdict is the **max severity across tiers**. A dynamic ``clean``
never downgrades a static finding (VM-aware malware goes dormant), and reputation
folds in as another raising-only tier.

**A high malscore alone is NOT malicious — and often not even suspicious.** CAPE
derives malscore by summing signature hits, but on a freshly-booted Windows guest a
large fraction of those hits are *environmental noise*: CAPE's own monitor injecting
its DLL into the sample (``creates_suspended_process`` / ``reads_memory_remote_process``
/ ``resumethread_remote_process``) and the Windows/PowerShell host doing normal startup
(``antivm_checks_available_memory``, ``queries_locale_api``, ``language_check_registry``,
…). A benign ``exit 0`` script reaches malscore 10 from ~16 such signatures. Measured
on the CAPE box: the Linux guest fires **zero** signatures on benign input; the noise
is Windows-guest specific (see CLAUDE.md -> "CAPE accuracy").

So the dynamic verdict is computed from **meaningful** (non-noise) signal only:

  * *malicious* — a decoded malware **family/config**, a **C2 endpoint from that
    config** (never merely-observed traffic), or a **meaningful** signature at
    ``severity >= HIGH_SEVERITY_SIGNATURE``.
  * *suspicious* — at least one meaningful (non-noise) signature, but nothing
    conclusive.
  * *clean* — only environmental noise (or nothing), even at malscore 10.

Nothing is hidden: the malscore and every signature still reach the UI; this logic
only decides the *verdict*, and ``explain_verdict`` states when a score is noise-only.

**Trade-off (documented on purpose):** the CAPE monitor's own process-injection is
indistinguishable *by signature name* from real malware injection, and it fires on
every sample — so those names sit in the noise set and no longer drive a verdict.
Real injector malware is still caught via config/C2 extraction, network C2, or a
higher-severity behavioural signature. The proper root-cause fix is on the CAPE box
(stop flagging the monitor's own injection); this is the safe client-side mitigation.
"""
from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

VERDICT_CLEAN = "clean"
VERDICT_SUSPICIOUS = "suspicious"
VERDICT_MALICIOUS = "malicious"
_SEVERITY = {VERDICT_CLEAN: 0, VERDICT_SUSPICIOUS: 1, VERDICT_MALICIOUS: 2}

# A single *meaningful* signature at/above this severity is corroborating evidence.
# CAPE's environmental noise tops out at severity 3, so this is the line between
# "the guest did normal Windows things" and "something notable happened".
HIGH_SEVERITY_SIGNATURE = 4

# Environmental-noise signatures: CAPE's own instrumentation + Windows/PowerShell
# host baseline that fire on a freshly-booted guest REGARDLESS of the sample. Derived
# from detonating benign and do-nothing samples on the live CAPE box (a benign
# `exit 0` PowerShell script triggers every one of these). They must not drive a
# verdict. Keep this list conservative — a name added here can no longer raise a
# verdict on its own. Reassess if the CAPE box's signature set / monitor changes.
ENVIRONMENTAL_NOISE_SIGNATURES = frozenset(
    {
        # CAPE monitor injecting its analysis DLL into the sample + child processes.
        # NOTE: these are also generic injection indicators — suppressed here only
        # because the monitor triggers them on 100% of runs; see module trade-off.
        "creates_suspended_process",
        "resumethread_remote_process",
        "reads_memory_remote_process",
        "terminates_remote_process",
        # Windows / PowerShell host startup + anti-analysis heuristics that the OS
        # itself trips (not the sample).
        "antivm_checks_available_memory",
        "antidebug_setunhandledexceptionfilter",
        "registers_vectored_exception_handler",
        "queries_locale_api",
        "queries_keyboard_layout",
        "language_check_registry",
        "stealth_network",
        # Token / ACL baseline queries by OS processes.
        "privilege_elevation_check",
        "per_file_acl_token_check",
        # Mount-point / drive / hardware discovery by explorer / services.
        "mountpoint_manager_access",
        "mountpoints_volume_discovery",
        "discover_registry_mount_points",
        "enumerates_physical_drives",
        "hardware_id_profiling",
        # Generic DLL-load location heuristic tripped by the loader.
        "dllload_suspicious_directory",
        # Over-firing on trivial benign scripts (measured: a `Write-Host "hello"`
        # PowerShell one-liner trips both — the interpreter itself is flagged).
        "uses_windows_utilities",
        "driver_filtermanager",
    },
)


def is_noise_signature(name: str) -> bool:
    return (name or "") in ENVIRONMENTAL_NOISE_SIGNATURES


# Low-confidence signatures: real, sample-specific observations (unlike pure noise)
# but ones that fire on a LARGE fraction of *benign* software, so on their own they
# don't justify a verdict. Two families dominate:
#   * static PE-structure heuristics — a self-signed cert, TLS callbacks, a packer-ish
#     section name, an overlay, a "timestomped" (reproducible-build) timestamp, an
#     internal PDB path, high entropy. These describe how a binary was BUILT/PACKED,
#     which countless legit installers and signed tools share (measured: powershell.exe
#     and a RealVNC viewer trip only these).
#   * .NET-JIT "unbacked memory" artifacts — the CLR JIT-compiles managed code into
#     dynamically-allocated (unbacked) memory and runs from it, which looks exactly
#     like shellcode/injection to CAPE's unbacked-* heuristics. Every managed .NET
#     executable trips a dozen of these (measured on a benign .NET app scoring 8/10).
# They stay VISIBLE and tagged, but are excluded from the "meaningful" signal that
# drives the verdict. A genuinely malicious sample is still caught by config/C2
# extraction, network C2, persistence/behavioural signatures, a YARA family match,
# or a meaningful signature at severity >= HIGH_SEVERITY_SIGNATURE.
LOW_CONFIDENCE_SIGNATURES = frozenset(
    {
        # --- static PE structure / packer heuristics ---
        "pe_cert_self_signed",
        "pe_tls_callbacks",
        "antianalysis_tls_section",
        "packer_unknown_pe_section_name",
        "contains_pe_overlay",
        "pe_compile_timestomping",
        "static_pe_pdbpath",
        "packer_entropy",
        "packer_entropy_section",
        # --- .NET-JIT unbacked-memory artifacts (fire on every managed binary) ---
        "unbacked_privilege_escalation",
        "unbacked_process_mitigation_alteration",
        "unbacked_api_resolution",
        "unbacked_library_load",
        "unbacked_memory_protection_alteration",
        "unbacked_process_creation",
        "unbacked_com_instantiation",
        "unbacked_file_dropping",
        "unbacked_process_enumeration",
        "unbacked_registry_modification",
        "unbacked_service_manipulation",
        "unbacked_token_manipulation",
        "unbacked_bind_shell",
        "injection_rwx",  # RWX memory — .NET JIT, browsers, many runtimes
        "network_bind",  # loopback 127.0.0.1:0 listener — benign IPC
        # --- weak anti-analysis / recon heuristics that trip on benign software ---
        "antidebug_guardpages",  # guard pages are normal .NET/CRT stack protection
        "query_fips_reconnaissance",  # sig text itself: "or by legitimate encryption software"
    },
)


def is_low_confidence_signature(name: str) -> bool:
    return (name or "") in LOW_CONFIDENCE_SIGNATURES


def _signatures(sandbox: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [s for s in (sandbox.get("signatures") or []) if isinstance(s, dict)]


def meaningful_signatures(sandbox: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Signatures that drive the verdict — i.e. neither environmental noise NOR a
    low-confidence static-PE/.NET-JIT heuristic (both fire on benign software)."""
    return [
        s for s in _signatures(sandbox) if not is_noise_signature(s.get("name", "")) and not is_low_confidence_signature(s.get("name", ""))
    ]


def noise_stats(sandbox: Dict[str, Any]) -> Dict[str, int]:
    """{total, noise, low_confidence, meaningful} signature counts — UI + explanation."""
    sigs = _signatures(sandbox)
    noise = sum(1 for s in sigs if is_noise_signature(s.get("name", "")))
    low = sum(1 for s in sigs if not is_noise_signature(s.get("name", "")) and is_low_confidence_signature(s.get("name", "")))
    return {"total": len(sigs), "noise": noise, "low_confidence": low, "meaningful": len(sigs) - noise - low}


def merge_verdict(static_verdict: str, dynamic_verdict: Optional[str]) -> str:
    """Return the max severity of the two verdicts (dynamic may be None)."""
    best = static_verdict if static_verdict in _SEVERITY else VERDICT_CLEAN
    if dynamic_verdict and _SEVERITY.get(dynamic_verdict, 0) > _SEVERITY[best]:
        best = dynamic_verdict
    return best


def _malscore(sandbox: Dict[str, Any]) -> float:
    try:
        return float(sandbox.get("malscore", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _max_meaningful_severity(sandbox: Dict[str, Any]) -> int:
    worst = 0
    for sig in meaningful_signatures(sandbox):
        try:
            worst = max(worst, int(sig.get("severity", 0) or 0))
        except (TypeError, ValueError):
            continue
    return worst


def dynamic_evidence(sandbox: Dict[str, Any]) -> List[str]:
    """Concrete, non-heuristic reasons a detonation looks malicious (may be empty)."""
    if not sandbox:
        return []
    reasons: List[str] = []
    family = sandbox.get("family") or sandbox.get("malfamily")
    if family:
        reasons.append(f"malware config extracted ({family})")
    c2 = list(sandbox.get("c2_ips") or []) + list(sandbox.get("c2_domains") or [])
    if c2:
        reasons.append(f"C2 endpoint in extracted config ({c2[0]})")
    worst = _max_meaningful_severity(sandbox)
    if worst >= HIGH_SEVERITY_SIGNATURE:
        reasons.append(f"signature at severity {worst}")
    return reasons


def dynamic_verdict_from_report(sandbox: Dict[str, Any]) -> str:
    """Derive a dynamic verdict from a sandbox summary.

    Malicious needs corroboration; suspicious needs at least one *meaningful*
    (non-noise) signature; a run with only environmental noise is clean even at a
    high malscore (see module docstring).
    """
    if not sandbox:
        return VERDICT_CLEAN
    if dynamic_evidence(sandbox):
        return VERDICT_MALICIOUS
    if meaningful_signatures(sandbox):
        return VERDICT_SUSPICIOUS
    return VERDICT_CLEAN


def explain_verdict(
    static_verdict: str,
    sandbox: Optional[Dict[str, Any]] = None,
    reputation: Optional[Dict[str, Any]] = None,
    inspector: Optional[Dict[str, Any]] = None,
) -> str:
    """One line an analyst can act on: what actually drove the verdict.

    Deliberately surfaces *disagreement* between tiers rather than hiding it — a
    high sandbox score next to a clean multi-engine result is exactly the case a
    human needs to see.
    """
    parts: List[str] = []
    # A file we could not inspect is failed CLOSED to a cautious verdict — but that
    # is an INFRASTRUCTURE outcome, not a content finding. Say so plainly so an
    # analyst never reads "suspicious" as "this file looks malicious" when the
    # inspector was merely unreachable or timed out (e.g. the Tier-1 service down).
    if inspector and inspector.get("analysis_incomplete"):
        why = (inspector.get("error") or "inspection did not complete").strip().rstrip(".")
        parts.append(f"Tier-1 static inspection incomplete ({why}) — provisional fail-closed verdict, " f"not a content-based finding")
    elif static_verdict and static_verdict != VERDICT_CLEAN:
        parts.append(f"static inspection: {static_verdict}")

    if sandbox:
        evidence = dynamic_evidence(sandbox)
        score = _malscore(sandbox)
        stats = noise_stats(sandbox)
        if evidence:
            parts.append("sandbox: " + ", ".join(evidence))
        elif stats["meaningful"] > 0:
            parts.append(
                f"sandbox: malscore {score:g} with {stats['meaningful']} sample-driven "
                f"signature(s) (no malware config, no C2, nothing above severity {HIGH_SEVERITY_SIGNATURE - 1})",
            )
        elif stats.get("low_confidence", 0) > 0:
            parts.append(
                f"sandbox: malscore {score:g} is static packer / .NET-JIT heuristics only "
                f"({stats['low_confidence']}/{stats['total']} signatures fire on benign software) — "
                f"no sample-specific malicious behaviour",
            )
        elif score > 0 and stats["total"] > 0:
            parts.append(
                f"sandbox: malscore {score:g} is entirely environmental noise "
                f"({stats['noise']}/{stats['total']} signatures are guest/monitor baseline) — "
                f"no sample-specific behaviour",
            )

    if reputation and reputation.get("found"):
        mal = reputation.get("malicious") or 0
        total = reputation.get("total") or 0
        parts.append(f"VirusTotal {mal}/{total}" + (" — no engine flagged it" if not mal else ""))
    elif reputation and reputation.get("submitted"):
        parts.append("VirusTotal scan pending")

    return "; ".join(parts)
