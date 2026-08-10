"""Resource limits for static analysis.

Tier 1 runs on the CoPilot host itself, so every limit here is protecting the
host that also serves the API. All of them are enforced server-side and all are
overridable per deployment through the environment (#974 §E).

A limit being hit is never silent: the job records a ``truncated_reason`` and
raises the matching ``limit.*`` informational flag, so a partial result reads as
partial. A limit is never a *failure* either -- whatever was produced before the
ceiling is still the best available triage material.
"""

from __future__ import annotations

import os
from typing import NamedTuple

MB = 1024 * 1024


def _env_int(name: str, default: int) -> int:
    """Read a positive integer from the environment, falling back on nonsense.

    A malformed or non-positive override is ignored rather than raising: a typo
    in one limit must not stop the backend from booting.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class AnalysisLimits(NamedTuple):
    # Largest sample accepted at upload. Rejected with a 413 before a single
    # byte reaches MinIO.
    max_file_size: int = 100 * MB
    # Wall clock per inspector. A parser fed a hostile file can loop; this is
    # what stops one submission from occupying a worker indefinitely.
    inspector_timeout_seconds: int = 60
    # Archive recursion. Depth 3 covers zip-in-zip-in-zip, which is as deep as
    # real deliveries go; beyond that it is a zip bomb, not a delivery.
    max_archive_depth: int = 3
    # Total decompressed bytes across an entire archive tree. The primary zip
    # bomb defence -- a 42 KB archive can expand to petabytes.
    max_expanded_size: int = 250 * MB
    # Members expanded from an archive tree.
    max_extracted_objects: int = 200
    # Per-finding evidence snippet. Findings are triage material, not a place
    # to store the file.
    max_evidence_chars: int = 2000
    # Text handed to deobfuscation and IOC extraction from any single object.
    max_text_chars: int = 500_000
    # Analyses allowed to run at once. Every upload queues a background task, so
    # without a ceiling a burst of N uploads becomes N concurrent analyses, all
    # competing for the *shared* SQLAlchemy pool (5 + 10 overflow). Saturate it
    # and unrelated requests start failing to check out a connection -- during
    # testing a burst of a dozen submissions made login itself return 401.
    # Four keeps the feature responsive while leaving the pool to the rest of
    # the app; excess submissions wait their turn instead of stampeding.
    max_concurrent_analyses: int = 4


def load_limits() -> AnalysisLimits:
    """Build the limit set from the environment, defaults where unset."""
    return AnalysisLimits(
        max_file_size=_env_int("FILE_ANALYSIS_MAX_FILE_SIZE", AnalysisLimits().max_file_size),
        inspector_timeout_seconds=_env_int("FILE_ANALYSIS_INSPECTOR_TIMEOUT", AnalysisLimits().inspector_timeout_seconds),
        max_archive_depth=_env_int("FILE_ANALYSIS_MAX_ARCHIVE_DEPTH", AnalysisLimits().max_archive_depth),
        max_expanded_size=_env_int("FILE_ANALYSIS_MAX_EXPANDED_SIZE", AnalysisLimits().max_expanded_size),
        max_extracted_objects=_env_int("FILE_ANALYSIS_MAX_EXTRACTED_OBJECTS", AnalysisLimits().max_extracted_objects),
        max_evidence_chars=_env_int("FILE_ANALYSIS_MAX_EVIDENCE_CHARS", AnalysisLimits().max_evidence_chars),
        max_text_chars=_env_int("FILE_ANALYSIS_MAX_TEXT_CHARS", AnalysisLimits().max_text_chars),
        max_concurrent_analyses=_env_int("FILE_ANALYSIS_MAX_CONCURRENT", AnalysisLimits().max_concurrent_analyses),
    )
