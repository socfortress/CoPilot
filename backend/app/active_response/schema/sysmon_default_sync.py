"""Shapes of the SOCFortress default Sysmon config sync (app/active_response/services/sysmon_default_sync.py)."""
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class SyncMode(str, Enum):
    """SYSMON_DEFAULT_SYNC: "on" applies a release unless the default was changed here, "force" always applies, "off" never fetches."""

    ON = "on"
    FORCE = "force"
    OFF = "off"


class SyncOutcome(str, Enum):
    """What one check ended with. Recorded in sync-status.json and shown on the Sysmon Config page."""

    # A release was stored as this CoPilot's default
    APPLIED = "applied"
    # The stored default already was the release: only the sync record was written
    ADOPTED = "adopted"
    # No newer release (HTTP 304, or the release already applied)
    UP_TO_DATE = "up_to_date"
    # The local-modification guard: the default was changed on this CoPilot, so it was not overwritten
    LOCAL_DEFAULT_DIFFERS = "local_default_differs"
    # SYSMON_DEFAULT_SYNC=off: nothing fetched
    OFF = "off"
    # No trusted release key in this CoPilot version: nothing fetched
    NOT_CONFIGURED = "not_configured"
    # SOCFORTRESS_SYSMON_SYNC_URL is not usable (not https, or no host)
    INVALID_URL = "invalid_url"
    # This CoPilot has no license
    NO_LICENSE = "no_license"
    # HTTP 401 / 403 / 404 / 429 / 503 from the service
    UNAUTHORIZED = "unauthorized"
    LICENSE_REJECTED = "license_rejected"
    NOT_PUBLISHED = "not_published"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    # Any other HTTP answer, a redirect to another host, a body over the size cap, or no answer at all
    HTTP_ERROR = "http_error"
    REDIRECT_REFUSED = "redirect_refused"
    TOO_LARGE = "too_large"
    NETWORK_ERROR = "network_error"
    # The bundle failed verification (signature, key, format, hashes, placeholders)
    VERIFICATION_FAILED = "verification_failed"
    # The signed content is no valid Sysmon config
    INVALID_CONFIG = "invalid_config"
    # Anti-rollback: older than (or a different content for) the release already applied
    ROLLBACK_REFUSED = "rollback_refused"
    # MinIO could not be read or written
    STORE_ERROR = "store_error"
    # Anything else (a database error reading the license, a bug)
    ERROR = "error"


# The outcomes after which this CoPilot's default is SOCFortress's latest release, as far as it knows
OK_OUTCOMES = frozenset({SyncOutcome.APPLIED, SyncOutcome.ADOPTED, SyncOutcome.UP_TO_DATE})


class SysmonDefaultSyncRunResult(BaseModel):
    outcome: SyncOutcome
    ok: bool = Field(
        ...,
        description="Whether the default is SOCFortress's latest release after this check (applied, adopted or up to date).",
    )
    message: str
    mode: SyncMode
    forced: bool = Field(False, description="Whether the local-modification guard was bypassed (force=true, or SYSMON_DEFAULT_SYNC=force).")
    checked_at: str = Field(..., description="UTC, YYYY-MM-DDTHH:MM:SSZ.")
    sequence: Optional[int] = Field(None, description="The release this check got from the service, when it got one.")
    commit: Optional[str] = None


class SysmonDefaultSyncApplied(BaseModel):
    """sync.json: the SOCFortress release this CoPilot's default was last synced to."""

    sequence: int
    commit: str
    content_sha256: str
    content_sha256_crlf: Optional[str] = None
    key_id: Optional[str] = None
    applied_at: Optional[str] = None
    created_at: Optional[str] = Field(None, description="When SOCFortress published the release.")
    schemaversion: Optional[str] = None
    source: Optional[str] = None
    service_url: Optional[str] = None


class SysmonDefaultSyncStatus(BaseModel):
    mode: SyncMode
    mode_setting: Optional[str] = Field(
        None,
        description="SYSMON_DEFAULT_SYNC as set, when it is not one of on / force / off (then sync runs as on).",
    )
    service_url: str
    configured: bool = Field(..., description="Whether this CoPilot version ships a trusted SOCFortress release key.")
    trusted_key_ids: List[str] = Field(default_factory=list)
    last_check: Optional[SysmonDefaultSyncRunResult] = None
    applied: Optional[SysmonDefaultSyncApplied] = None
    default_present: Optional[bool] = Field(None, description="Whether a default is stored. None when it could not be read.")
    local_default_differs: Optional[bool] = Field(
        None,
        description=(
            "Whether the stored default differs from the release in sync.json (it was changed on this CoPilot), so sync "
            "will not overwrite it. None when there is no sync record, or the default could not be read."
        ),
    )
    read_error: Optional[str] = Field(None, description="Why the stored default or the sync records could not be read.")


class SysmonDefaultSyncStatusResponse(BaseModel):
    success: bool
    message: str
    status: SysmonDefaultSyncStatus


class SysmonDefaultSyncRunResponse(BaseModel):
    success: bool
    message: str
    result: SysmonDefaultSyncRunResult
    status: SysmonDefaultSyncStatus
