"""Cross-tier verdict logic.

Pure functions — no DB, no network, no CoPilot imports — so they are trivially
unit-testable and carry zero side effects.

The job-level verdict is the **max severity across tiers**. A dynamic ``clean``
never downgrades a static finding (VM-aware malware goes dormant), and reputation
folds in as another raising-only tier.

**A high malscore alone is NOT malicious.** CAPE derives malscore by summing
signature hits, and a freshly-booted Windows guest fires a dozen environmental
signatures (mount-point enumeration, keyboard-layout queries, drive discovery)
before the sample does anything — a benign script routinely reaches 10/10. So a
sandbox verdict of *malicious* requires concrete corroboration:

  * a decoded malware **family/config**, or
  * a **C2 endpoint recovered from that config** (never merely-observed traffic —
    see ``CapeSummary.c2_ips``), or
  * a signature at **severity >= HIGH_SEVERITY_SIGNATURE**.

An uncorroborated high score still raises the verdict to *suspicious*, so nothing
is hidden — the analyst sees the score and every signature in the UI.
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

# Score at/above which the run is at least suspicious (CAPE's own "bad" threshold).
MALSCORE_SUSPICIOUS = 7.0
# A single signature at/above this severity is treated as corroborating evidence.
# CAPE's environmental noise tops out at 3, so this is the line between
# "the guest did normal Windows things" and "something notable happened".
HIGH_SEVERITY_SIGNATURE = 4


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


def _max_signature_severity(sandbox: Dict[str, Any]) -> int:
    worst = 0
    for sig in sandbox.get("signatures", []) or []:
        if not isinstance(sig, dict):
            continue
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
    worst = _max_signature_severity(sandbox)
    if worst >= HIGH_SEVERITY_SIGNATURE:
        reasons.append(f"signature at severity {worst}")
    return reasons


def dynamic_verdict_from_report(sandbox: Dict[str, Any]) -> str:
    """Derive a dynamic verdict from a sandbox summary.

    Malicious requires corroboration (see module docstring); a bare high malscore
    caps at suspicious.
    """
    if not sandbox:
        return VERDICT_CLEAN
    if dynamic_evidence(sandbox):
        return VERDICT_MALICIOUS
    if _malscore(sandbox) > 0:
        return VERDICT_SUSPICIOUS
    return VERDICT_CLEAN


def explain_verdict(
    static_verdict: str,
    sandbox: Optional[Dict[str, Any]] = None,
    reputation: Optional[Dict[str, Any]] = None,
) -> str:
    """One line an analyst can act on: what actually drove the verdict.

    Deliberately surfaces *disagreement* between tiers rather than hiding it — a
    high sandbox score next to a clean multi-engine result is exactly the case a
    human needs to see.
    """
    parts: List[str] = []
    if static_verdict and static_verdict != VERDICT_CLEAN:
        parts.append(f"static inspection: {static_verdict}")

    if sandbox:
        evidence = dynamic_evidence(sandbox)
        score = _malscore(sandbox)
        if evidence:
            parts.append("sandbox: " + ", ".join(evidence))
        elif score > 0:
            parts.append(
                f"sandbox: malscore {score:g} from signature hits only "
                f"(no malware config, no C2, nothing above severity {HIGH_SEVERITY_SIGNATURE - 1})"
            )

    if reputation and reputation.get("found"):
        mal = reputation.get("malicious") or 0
        total = reputation.get("total") or 0
        parts.append(f"VirusTotal {mal}/{total}" + (" — no engine flagged it" if not mal else ""))
    elif reputation and reputation.get("submitted"):
        parts.append("VirusTotal scan pending")

    return "; ".join(parts)
