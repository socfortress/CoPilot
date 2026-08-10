"""SQLModel tables for the Tier 1 static file analysis engine (#1067).

Three tables, one parent and two children:

    file_analysis_job -> file_analysis_finding
                      -> file_analysis_ioc

``customer_code`` is a **hard FK** to ``customers.customer_code``, unlike the
string-only convention used by ``incident_management_*``. Every row here is
created by an authenticated submission against a customer that already exists,
so there is no ingest path that could land an orphan and nothing to tolerate.

No ``Relationship`` / ``back_populates`` on any of these models. Analysis runs
in a background task that writes findings and IOCs after several awaits, and a
bidirectional relationship fires an implicit synchronous load on ``flush()``
that raises ``MissingGreenlet`` under ``AsyncSession``. Children carry a plain
``job_id`` FK and are loaded with explicit selects.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import Text
from sqlmodel import Field
from sqlmodel import SQLModel


class FileAnalysisJob(SQLModel, table=True):
    """One submitted file and the verdict the static engine reached on it."""

    __tablename__ = "file_analysis_job"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Stable public identifier. The integer PK never leaves the backend: the API
    # addresses jobs by UUID so an id cannot be walked to enumerate other
    # tenants' submissions.
    job_uuid: str = Field(max_length=36, index=True, unique=True, nullable=False)

    customer_code: str = Field(
        foreign_key="customers.customer_code",
        max_length=50,
        index=True,
        nullable=False,
    )

    # ---- submission ------------------------------------------------------
    # ``file_name`` is what the submitter called it and is never trusted for
    # anything but display -- the type always comes from content (see identify).
    file_name: str = Field(max_length=512, nullable=False)
    submitted_by: Optional[str] = Field(default=None, max_length=256)
    submitted_at: datetime = Field(default_factory=datetime.utcnow, index=True, nullable=False)
    # Phase 1 only ever writes "upload". Velociraptor and alert origins arrive
    # with the Phase 2 entry points (#974 §F) and reuse this column.
    source: str = Field(default="upload", max_length=32, nullable=False)

    # ---- MinIO blob pointer ---------------------------------------------
    # Same six-field convention as agent_datastore / vulnerability_reports:
    # the row is the manifest, the bytes live in MinIO. ``file_hash`` is the
    # SHA-256 the convention expects; md5/sha1 below are additional.
    bucket_name: str = Field(default="copilot-file-analysis", max_length=255, nullable=False)
    object_key: str = Field(max_length=1024, nullable=False)
    file_size: int = Field(nullable=False)
    file_hash: str = Field(max_length=128, index=True, nullable=False)
    content_type: str = Field(default="application/octet-stream", max_length=128, nullable=False)

    # ---- identification --------------------------------------------------
    magic_type: Optional[str] = Field(default=None, max_length=512)
    mime_type: Optional[str] = Field(default=None, max_length=255, index=True)
    md5: Optional[str] = Field(default=None, max_length=32, index=True)
    sha1: Optional[str] = Field(default=None, max_length=40, index=True)
    # Shannon entropy over the whole file, 0.0-8.0. High entropy on a format
    # that is not natively compressed is itself a weak signal of packing.
    entropy: Optional[float] = Field(default=None)

    # ---- lifecycle -------------------------------------------------------
    # pending -> running -> completed | failed
    status: str = Field(default="pending", max_length=32, index=True, nullable=False)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    duration_ms: Optional[int] = Field(default=None)
    # A failed job stays queryable on purpose: "this file could not be parsed"
    # is a triage signal, not something to drop.
    error_message: Optional[str] = Field(sa_column=Column(Text, nullable=True), default=None)

    # ---- result ----------------------------------------------------------
    # clean | suspicious | malicious | unknown
    verdict: Optional[str] = Field(default=None, max_length=32, index=True)
    score: Optional[int] = Field(default=None)
    # Which inspector claimed the file. Null when identification succeeded but
    # no inspector handles that type -- that is a completed job with a
    # hash/type-only result, not a failure.
    inspector: Optional[str] = Field(default=None, max_length=64)
    # Set when a limit stopped the analysis short (archive depth, expanded
    # size, extracted-object cap). The job still completes with whatever was
    # produced before the limit; this records that the view is partial.
    truncated_reason: Optional[str] = Field(default=None, max_length=255)

    # Whether the completed result was accepted by the Graylog shipper. A
    # shipping failure never fails the job -- CoPilot is the system of record
    # and Graylog is a fan-out -- but an operator needs to see it happened.
    shipped_to_graylog: bool = Field(default=False, nullable=False)


class FileAnalysisFinding(SQLModel, table=True):
    """A behaviour flag raised by an inspector.

    Findings are what an analyst actually reads, and what the score is derived
    from -- the score is the sum of the ``weight`` column across a job's
    findings, so a verdict can always be explained by pointing at these rows.
    """

    __tablename__ = "file_analysis_finding"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="file_analysis_job.id", index=True, nullable=False)

    # Stable machine key, e.g. "pdf.open_action", "office.auto_exec_macro".
    # This is what becomes a Graylog field and what a detection rule matches
    # on, so it must not be reworded once released.
    flag: str = Field(max_length=128, index=True, nullable=False)
    category: str = Field(max_length=64, nullable=False)
    title: str = Field(max_length=255, nullable=False)
    description: Optional[str] = Field(sa_column=Column(Text, nullable=True), default=None)
    # info | low | medium | high
    severity: str = Field(default="info", max_length=16, index=True, nullable=False)
    # Contribution to the job score. Kept on the row rather than looked up at
    # read time so a historical verdict stays reproducible after the weights
    # table changes.
    weight: int = Field(default=0, nullable=False)
    # The snippet that justifies the finding, already truncated by the
    # inspector. Never the whole file.
    evidence: Optional[str] = Field(sa_column=Column(Text, nullable=True), default=None)
    inspector: Optional[str] = Field(default=None, max_length=64)


class FileAnalysisIoC(SQLModel, table=True):
    """An indicator extracted from a sample.

    ``value`` is stored **defanged** (``hxxp://``, ``1.2.3[.]4``). Storing the
    live form would mean the raw indicator reaches the UI, an export, and every
    Graylog message -- one accidental click away from being a live link. Any
    consumer that needs the original refangs it explicitly.
    """

    __tablename__ = "file_analysis_ioc"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="file_analysis_job.id", index=True, nullable=False)

    # url | domain | ipv4 | ipv6 | email | md5 | sha1 | sha256 | path | registry_key
    ioc_type: str = Field(max_length=32, index=True, nullable=False)
    value: str = Field(max_length=2048, nullable=False)
    # Where it surfaced: raw | text | deobfuscated | macro | metadata.
    # "deobfuscated" is the interesting one -- an indicator that only appears
    # after decoding is a stronger signal than one sitting in plain text.
    context: str = Field(default="raw", max_length=32, nullable=False)
    inspector: Optional[str] = Field(default=None, max_length=64)
