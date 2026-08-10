"""Ship completed analyses to Graylog over the existing Event Shipper.

The stated goal of the output half of #974 is that findings drive detection
rules "like any other data source". That constrains the shape more than it might
look: a single JSON blob in the message body would satisfy "reaches Graylog" and
none of the purpose, because you cannot write a rule against a blob.

So the payload is **flat and bounded**:

- one boolean field per raised behaviour flag (``flag_pdf_javascript: true``)
- one comma-joined field per indicator *type* (``ioc_url``, ``ioc_domain``)

Bounded is what makes this safe. Flag keys come from the closed
``scoring.FLAG_CATALOGUE`` and IOC types from a fixed list, so the field set
Graylog sees cannot grow without a code change -- which is the other half of why
the catalogue refuses unknown keys.

Shipping is best effort. CoPilot is the system of record; Graylog is a fan-out,
and a Graylog outage must never turn a completed analysis into a failed one.
"""

from __future__ import annotations

from typing import Iterable
from typing import List

from loguru import logger

from app.file_analysis.models.file_analysis import FileAnalysisIoC
from app.file_analysis.models.file_analysis import FileAnalysisJob
from app.file_analysis.services.scoring import summarise
from app.integrations.utils.event_shipper import event_shipper
from app.integrations.utils.schema import EventShipperPayload

INTEGRATION_NAME = "file_analysis"

# Per-field cap. A job can carry a hundred URLs; a GELF field holding all of
# them helps nobody and risks the message being dropped for size.
MAX_VALUES_PER_TYPE = 25


def _field_name(flag: str) -> str:
    """``pdf.javascript`` -> ``flag_pdf_javascript``."""
    return "flag_" + flag.replace(".", "_")


async def ship_job(job: FileAnalysisJob, flags: Iterable[str], iocs: Iterable[FileAnalysisIoC]) -> bool:
    """Emit one completed job to Graylog. Returns whether it was accepted."""
    # Ordered by descending weight, so the field reads as the reason for the
    # verdict rather than as an alphabetical list.
    flag_list = summarise(flags)

    fields = {
        "message": (
            f"File analysis {job.verdict or 'unknown'} for {job.file_name} "
            f"({job.mime_type or 'unknown type'}, score {job.score if job.score is not None else 0})"
        ),
        "integration": INTEGRATION_NAME,
        "customer_code": job.customer_code,
        "file_analysis_job_uuid": job.job_uuid,
        "file_analysis_status": job.status,
        "file_analysis_verdict": job.verdict,
        "file_analysis_score": job.score,
        "file_analysis_inspector": job.inspector,
        "file_analysis_source": job.source,
        "file_analysis_submitted_by": job.submitted_by,
        "file_analysis_duration_ms": job.duration_ms,
        "file_name": job.file_name,
        "file_size": job.file_size,
        "file_mime_type": job.mime_type,
        "file_magic_type": job.magic_type,
        "file_entropy": job.entropy,
        "file_md5": job.md5,
        "file_sha1": job.sha1,
        "file_sha256": job.file_hash,
        "file_analysis_flag_count": len(flag_list),
        # Kept alongside the per-flag booleans so a rule can match on the set
        # without knowing every key, and a human can read one field.
        "file_analysis_flags": ",".join(flag_list),
    }

    if job.truncated_reason:
        fields["file_analysis_truncated_reason"] = job.truncated_reason

    for flag in flag_list:
        fields[_field_name(flag)] = True

    by_type: dict = {}
    for ioc in iocs:
        by_type.setdefault(ioc.ioc_type, []).append(ioc.value)

    total = 0
    for ioc_type, values in by_type.items():
        unique: List[str] = list(dict.fromkeys(values))[:MAX_VALUES_PER_TYPE]
        fields[f"ioc_{ioc_type}"] = ",".join(unique)
        total += len(unique)
    fields["ioc_count"] = total

    payload = EventShipperPayload(**{k: v for k, v in fields.items() if v is not None})

    try:
        await event_shipper(payload)
        return True
    except Exception as exc:
        # Deliberately broad: event_shipper raises HTTPException on transport
        # failure, and nothing about a fan-out target being down should surface
        # as an analysis error.
        logger.warning(f"file_analysis: shipping job {job.job_uuid} to Graylog failed: {exc}")
        return False
