"""Behaviour flags, their weights, and the verdict derived from them.

The score is a **plain sum of the weights of the flags a sample raised**. It is
not a model and not a tuned heuristic: an analyst must always be able to explain
a verdict by pointing at the findings that produced it, and a reviewer must be
able to predict the effect of adding a flag by reading one table (#974 §C).

Two consequences that are load-bearing:

- ``FLAG_CATALOGUE`` is the single source of truth. An inspector cannot invent a
  flag key; :func:`flag_spec` raises on an unknown one, and a test asserts every
  key an inspector emits exists here. This is what stops the Graylog field set
  from drifting silently, since each flag key becomes a queryable field.
- The weight is copied onto the finding row at write time rather than looked up
  at read time, so re-tuning this table never rewrites history. Yesterday's
  verdict stays reproducible.

Flag keys are a public interface once released: detection rules in Graylog match
on them. Rename one and you break every rule that used it.
"""

from __future__ import annotations

from typing import Dict
from typing import Iterable
from typing import List
from typing import NamedTuple

SEVERITY_INFO = "info"
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"

VERDICT_CLEAN = "clean"
VERDICT_SUSPICIOUS = "suspicious"
VERDICT_MALICIOUS = "malicious"
VERDICT_UNKNOWN = "unknown"

# Calibrated so that a single structural oddity stays "clean", a recognised
# malicious *technique* reaches "suspicious", and a combination that has no
# benign explanation reaches "malicious". A PDF that merely carries JavaScript
# is suspicious; one that carries JavaScript *and* auto-executes it *and* has a
# /Launch action is not a document anyone sends by accident.
SUSPICIOUS_THRESHOLD = 10
MALICIOUS_THRESHOLD = 40


class FlagSpec(NamedTuple):
    category: str
    title: str
    severity: str
    weight: int


FLAG_CATALOGUE: Dict[str, FlagSpec] = {
    # ---- generic, raised by identification rather than by a format inspector
    "generic.eicar": FlagSpec("generic", "EICAR test signature present", SEVERITY_HIGH, 100),
    "generic.high_entropy": FlagSpec("generic", "High entropy for this file type", SEVERITY_LOW, 5),
    "generic.extension_mismatch": FlagSpec("generic", "Content does not match the declared extension", SEVERITY_MEDIUM, 10),
    # ---- PDF
    "pdf.javascript": FlagSpec("pdf", "Embedded JavaScript", SEVERITY_HIGH, 15),
    "pdf.open_action": FlagSpec("pdf", "/OpenAction runs on open", SEVERITY_HIGH, 12),
    "pdf.additional_action": FlagSpec("pdf", "/AA additional action defined", SEVERITY_MEDIUM, 8),
    "pdf.launch_action": FlagSpec("pdf", "/Launch action starts an external program", SEVERITY_HIGH, 25),
    "pdf.embedded_file": FlagSpec("pdf", "Embedded file attachment", SEVERITY_MEDIUM, 10),
    "pdf.uri_action": FlagSpec("pdf", "/URI action present", SEVERITY_LOW, 3),
    "pdf.encrypted": FlagSpec("pdf", "Document is encrypted", SEVERITY_LOW, 3),
    # ---- Office (OOXML and OLE legacy share the flag namespace: the technique
    # is the same, only the container differs)
    "office.macro_present": FlagSpec("office", "VBA macro project present", SEVERITY_MEDIUM, 8),
    "office.auto_exec_macro": FlagSpec("office", "Macro runs automatically on open", SEVERITY_HIGH, 15),
    "office.suspicious_macro_keyword": FlagSpec("office", "Macro uses a suspicious API", SEVERITY_MEDIUM, 10),
    "office.dde_field": FlagSpec("office", "DDE field executes an external command", SEVERITY_HIGH, 25),
    "office.external_relationship": FlagSpec("office", "External relationship reference", SEVERITY_MEDIUM, 8),
    "office.remote_template": FlagSpec("office", "Remote template injection", SEVERITY_HIGH, 20),
    "office.encrypted": FlagSpec("office", "Document is encrypted", SEVERITY_LOW, 5),
    # ---- scripts
    "script.obfuscated": FlagSpec("script", "Obfuscation layers detected", SEVERITY_MEDIUM, 12),
    "script.deep_obfuscation": FlagSpec("script", "Obfuscation still unresolved at the pass limit", SEVERITY_HIGH, 15),
    "script.encoded_command": FlagSpec("script", "Encoded command invocation", SEVERITY_HIGH, 20),
    "script.download_invocation": FlagSpec("script", "Downloads and runs remote content", SEVERITY_HIGH, 20),
    "script.suspicious_api": FlagSpec("script", "Suspicious API usage", SEVERITY_MEDIUM, 8),
    "script.hidden_window": FlagSpec("script", "Runs with a hidden window", SEVERITY_MEDIUM, 8),
    # ---- PE / ELF
    "binary.packed_section": FlagSpec("binary", "High-entropy section suggests packing", SEVERITY_MEDIUM, 10),
    "binary.suspicious_import": FlagSpec("binary", "Imports associated with injection or evasion", SEVERITY_MEDIUM, 8),
    "binary.no_imports": FlagSpec("binary", "No import table (imports likely resolved at runtime)", SEVERITY_LOW, 5),
    "binary.overlay_present": FlagSpec("binary", "Data appended past the last section", SEVERITY_LOW, 3),
    "binary.unsigned": FlagSpec("binary", "No embedded authenticode signature", SEVERITY_INFO, 0),
    # ---- archives
    "archive.encrypted": FlagSpec("archive", "Archive is password protected", SEVERITY_MEDIUM, 10),
    "archive.executable_content": FlagSpec("archive", "Archive contains an executable", SEVERITY_MEDIUM, 10),
    "archive.double_extension": FlagSpec("archive", "Entry uses a deceptive double extension", SEVERITY_HIGH, 20),
    "archive.nested_archive": FlagSpec("archive", "Archive nested inside archive", SEVERITY_LOW, 3),
    # ---- informational: recorded so a partial result is visibly partial,
    # never scored (weight 0) because a limit says nothing about the sample
    "limit.depth_reached": FlagSpec("limit", "Archive recursion depth limit reached", SEVERITY_INFO, 0),
    "limit.size_reached": FlagSpec("limit", "Expanded size limit reached", SEVERITY_INFO, 0),
    "limit.object_cap_reached": FlagSpec("limit", "Extracted object cap reached", SEVERITY_INFO, 0),
    "limit.inspector_timeout": FlagSpec("limit", "Inspector timed out", SEVERITY_INFO, 0),
}


class Flag(NamedTuple):
    """A raised flag, ready to become a ``file_analysis_finding`` row."""

    flag: str
    description: str
    evidence: str


def flag_spec(flag: str) -> FlagSpec:
    """Look up a flag, refusing anything not in the catalogue.

    Raising here rather than defaulting is intentional: a typo'd flag key would
    otherwise reach Graylog as a brand-new field and quietly split every rule
    that matched the correct spelling.
    """
    try:
        return FLAG_CATALOGUE[flag]
    except KeyError:
        raise KeyError(f"Unknown file analysis flag '{flag}'. Add it to FLAG_CATALOGUE before emitting it.")


def score_flags(flags: Iterable[str]) -> int:
    """Sum the weights of a set of raised flags.

    Each distinct flag counts once no matter how many times it was raised: a
    macro with forty suspicious keywords is not forty times more malicious than
    one with a single keyword, and letting repeats accumulate would let a noisy
    sample outrank a genuinely dangerous one.
    """
    return sum(flag_spec(flag).weight for flag in set(flags))


def verdict_for(score: int, inspected: bool) -> str:
    """Map a score to a verdict.

    **The score is consulted first, and outranks ``inspected``.** Some flags are
    raised by identification rather than by a format inspector -- EICAR and the
    extension mismatch among them -- so a file no inspector claims can still
    score. Checking ``inspected`` first reported an EICAR sample as *unknown*
    while it sat at score 100: the single worst failure mode this function has,
    because it buries a malicious result under a label that reads as "nothing to
    see".

    ``inspected=False`` only decides the *zero-score* case. There, "clean" would
    assert something the engine never checked, so it stays *unknown*.
    """
    if score >= MALICIOUS_THRESHOLD:
        return VERDICT_MALICIOUS
    if score >= SUSPICIOUS_THRESHOLD:
        return VERDICT_SUSPICIOUS
    if not inspected:
        return VERDICT_UNKNOWN
    return VERDICT_CLEAN


def summarise(flags: Iterable[str]) -> List[str]:
    """Flag keys ordered by descending weight -- the "why" behind a verdict."""
    return sorted(set(flags), key=lambda f: (-flag_spec(f).weight, f))
