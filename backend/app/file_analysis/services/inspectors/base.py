"""Inspector contract for the Tier 1 static engine.

An inspector claims one or more content types and returns behaviour flags,
indicators and any human-readable text it recovered (macro source, deobfuscated
script, document metadata).

**The contract forbids execution.** An inspector parses bytes. It does not call
``eval``, does not spawn a subprocess, does not hand the sample to an
interpreter, and does not resolve any reference the sample contains -- a remote
template URL is reported, never fetched. This is the property that makes it safe
to run Tier 1 on the CoPilot host (#974 §B), and it is the first thing to check
when reviewing a new inspector.
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from typing import ClassVar
from typing import List
from typing import Optional
from typing import Sequence

from app.file_analysis.services.iocs import ExtractedIoC
from app.file_analysis.services.limits import AnalysisLimits


@dataclass
class InspectorContext:
    """Everything an inspector is allowed to know about the sample."""

    data: bytes
    file_name: str
    mime_type: str
    magic_type: str
    limits: AnalysisLimits
    # Archive members are inspected recursively; depth 0 is the submitted file.
    depth: int = 0


@dataclass
class InspectorResult:
    """What an inspector produces.

    ``flags`` holds catalogue keys only -- the human title, severity and weight
    come from ``scoring.FLAG_CATALOGUE`` so an inspector cannot invent its own
    severity or quietly outweigh another inspector.
    """

    flags: List[str] = field(default_factory=list)
    # Per-flag supporting detail, keyed by flag. Missing entries are fine; the
    # catalogue title carries the meaning on its own.
    evidence: dict = field(default_factory=dict)
    iocs: List[ExtractedIoC] = field(default_factory=list)
    # Recovered text worth showing an analyst: macro source, deobfuscated
    # script, extracted document strings.
    extracted_text: Optional[str] = None
    # Set when a limit stopped this inspector short.
    truncated_reason: Optional[str] = None

    def add(self, flag: str, evidence: str = "") -> None:
        if flag not in self.flags:
            self.flags.append(flag)
        if evidence and flag not in self.evidence:
            self.evidence[flag] = evidence

    def merge(self, other: "InspectorResult") -> None:
        for flag in other.flags:
            if flag not in self.flags:
                self.flags.append(flag)
        for flag, evidence in other.evidence.items():
            self.evidence.setdefault(flag, evidence)
        self.iocs.extend(other.iocs)
        if other.truncated_reason and not self.truncated_reason:
            self.truncated_reason = other.truncated_reason
        if other.extracted_text:
            self.extracted_text = "\n\n".join(filter(None, [self.extracted_text, other.extracted_text]))


class Inspector(ABC):
    """Base class for every format inspector."""

    #: Stable identifier, stored on the job and on each finding.
    name: ClassVar[str] = "base"

    #: MIME types this inspector claims, as reported by libmagic from content.
    mime_types: ClassVar[Sequence[str]] = ()

    #: Extensions this inspector claims **only when the content type is generic**
    #: (``text/plain``, ``application/octet-stream``). Content always decides the
    #: container; the extension only disambiguates between things that are all
    #: legitimately plain text -- a PowerShell script and a CSV are both
    #: ``text/plain`` and libmagic cannot tell them apart.
    extensions: ClassVar[Sequence[str]] = ()

    #: Leading bytes that identify the format regardless of what libmagic says.
    #: Checked before MIME so a mislabelled or unknown type still routes.
    magic_prefixes: ClassVar[Sequence[bytes]] = ()

    def claims(self, data: bytes, mime_type: str, file_name: str) -> bool:
        """Optional content probe, for formats no magic prefix can identify.

        Some containers are only distinguishable by looking *inside* them. An
        OOXML document is a zip, and libmagic reports ``application/zip`` for
        one often enough that MIME routing alone would hand every macro-enabled
        document to the archive inspector.

        Runs on every registered inspector for every sample, so an override must
        be cheap and must never raise.
        """
        return False

    @abstractmethod
    def inspect(self, ctx: InspectorContext) -> InspectorResult:
        """Parse the sample and report. Must never execute it."""
        raise NotImplementedError


def truncate_evidence(text: str, limits: AnalysisLimits) -> str:
    """Clip a snippet to the configured evidence ceiling."""
    if text is None:
        return ""
    collapsed = text.strip()
    if len(collapsed) <= limits.max_evidence_chars:
        return collapsed
    return collapsed[: limits.max_evidence_chars] + " […truncated]"
