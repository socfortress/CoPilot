"""This CoPilot's default Sysmon config, pulled from SOCFortress.

Client CoPilots run inside client networks, where SOCFortress cannot reach them, so each CoPilot pulls the approved
default from a small SOCFortress service (``SOCFORTRESS_SYSMON_SYNC_URL``, by default https://sysmon-sync.socfortress.co;
the production host is still to be decided) over the outbound HTTPS it already uses. The default is the installer
repository's template ``sysmon_config.xml`` (``__INSTALLDIRNAME__`` placeholders in), which "Add new Configuration"
renders for each new customer. Its content is confidential (it shows what is not logged): it is never part of this
public repository, never logged, and never written to the audit log.

Trust comes from a signature, not from the channel. SOCFortress's release workflow signs a manifest (Ed25519) that
names the content's SHA-256; this module verifies it against the public keys shipped in this repository
(``assets/sysmon_default/release_keys.json``), so neither the service nor anything between it and this CoPilot can plant
a config. An empty key list means "not configured": nothing is fetched.

A check, every 6 hours (the ``sync_sysmon_default`` job) or on an admin's "Sync now":

1. ``SYSMON_DEFAULT_SYNC``: ``on`` (default), ``force`` or ``off`` (no request at all).
2. GET {url}/v1/sysmon/default with this CoPilot's license key (``x-api-key``; only its fingerprint is ever logged),
   the release it has (``x-sysmon-default-sequence``) and, while the stored default is that release, its ETag (a 304
   means nothing new). TLS verified, 30 s, at most 12 MiB, no redirect to another host.
3. Verify the bundle: the signature over the exact manifest bytes first, with a key in the trust list that has not
   expired, and only then the manifest (format, key, channel, hashes, size, placeholders, schemaversion), then the
   config itself (``validate_sysmon_config``, the default's checks).
4. Anti-rollback: the release's sequence must be above the one applied (sync.json); the same sequence is accepted only
   with the same content.
5. The local-modification guard ("on"): a stored default that is neither the release applied last nor the one offered
   was changed on this CoPilot (an admin's "Save as default"), and is not overwritten. "force" (the env, or Sync now
   confirmed by an admin) overwrites it. A stored default equal to the offered release is adopted: only sync.json is
   written. Line endings do not count as a change (the editor turns CRLF into LF).
6. Store the content as the default (the existing MinIO helper), then sync.json; record the check in sync-status.json;
   audit ``response.sysmon_default_sync`` when a release is applied.

A check never raises: every failure is an outcome with a message (``SyncOutcome``).
"""
import asyncio
import base64
import binascii
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import AsyncIterator
from typing import List
from typing import Optional
from typing import Tuple

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.schema.sysmon_default_sync import OK_OUTCOMES
from app.active_response.schema.sysmon_default_sync import SyncMode
from app.active_response.schema.sysmon_default_sync import SyncOutcome
from app.active_response.schema.sysmon_default_sync import SysmonDefaultSyncApplied
from app.active_response.schema.sysmon_default_sync import SysmonDefaultSyncRunResult
from app.active_response.schema.sysmon_default_sync import SysmonDefaultSyncStatus
from app.active_response.services.sysmon_config import INSTALL_DIR_PLACEHOLDER
from app.active_response.services.sysmon_config import MAX_SYSMON_CONFIG_BYTES
from app.active_response.services.sysmon_config import validate_sysmon_config
from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.data_store.data_store_operations import SYSMON_CONFIG_DEFAULT_OBJECT
from app.data_store.data_store_operations import SYSMON_CONFIG_DEFAULTS_BUCKET
from app.data_store.data_store_operations import SYSMON_DEFAULT_SYNC_OBJECT
from app.data_store.data_store_operations import SYSMON_DEFAULT_SYNC_STATUS_OBJECT
from app.data_store.data_store_operations import read_default_sysmon_config
from app.data_store.data_store_operations import read_sysmon_defaults_object
from app.data_store.data_store_operations import write_default_sysmon_config
from app.data_store.data_store_operations import write_sysmon_defaults_object
from app.middleware.license import get_license
from app.version.services.version import CURRENT_VERSION

JOB_ID = "sync_sysmon_default"
# Still to be decided: the production host of the SOCFortress sync service
DEFAULT_SERVICE_URL = "https://sysmon-sync.socfortress.co"
BUNDLE_PATH = "/v1/sysmon/default"
BUNDLE_FORMAT = "socfortress-sysmon-default-bundle/1"
MANIFEST_FORMAT = "socfortress-sysmon-default/1"
CHANNEL = "stable"
MODULE_VERSION = "1.0"
SOURCE = "socfortress-sync"
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
FETCH_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
MAX_REDIRECTS = 3
TRUSTED_KEYS_FILE = Path(__file__).resolve().parents[1] / "assets" / "sysmon_default" / "release_keys.json"
# The audit actor of the scheduled check (no user): audit rows take a null actor_user_id
SYSTEM_ACTOR = "system"

KEY_ID_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")
_HEX40_RE = re.compile(r"[0-9a-f]{40}")
_HEX64_RE = re.compile(r"[0-9a-f]{64}")
_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_LINE_END_RE = re.compile(rb"\r\n|\r|\n")
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
_OFF_VALUES = frozenset({"off", "false", "0", "no", "disabled"})
_ON_VALUES = frozenset({"", "on", "true", "1", "yes", "enabled"})

# One check at a time (the job and an admin's Sync now)
_RUN_LOCK = asyncio.Lock()
# Held while the stored default is read, compared and written, by a check and by "Save as default", so a check can
# never overwrite a default an admin saved after the check read it
DEFAULT_CONFIG_LOCK = asyncio.Lock()


# --------------------------------------------------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------------------------------------------------


def sync_mode() -> Tuple[SyncMode, Optional[str]]:
    """SYSMON_DEFAULT_SYNC, read at call time, and the raw value when it is not one CoPilot knows (it then runs as "on")."""
    raw = (os.getenv("SYSMON_DEFAULT_SYNC") or "").strip()
    value = raw.lower()
    if value in _ON_VALUES:
        return SyncMode.ON, None
    if value in _OFF_VALUES:
        return SyncMode.OFF, None
    if value == SyncMode.FORCE.value:
        return SyncMode.FORCE, None
    return SyncMode.ON, raw


def service_url() -> str:
    """SOCFORTRESS_SYSMON_SYNC_URL, read at call time, without a trailing slash."""
    return (os.getenv("SOCFORTRESS_SYSMON_SYNC_URL") or "").strip().rstrip("/") or DEFAULT_SERVICE_URL


def _bundle_url(base: str) -> Tuple[Optional[str], Optional[str]]:
    """The bundle's URL, or why the service URL cannot be used. https only; plain http only to this host (testing)."""
    try:
        url = httpx.URL(base)
    except (httpx.InvalidURL, TypeError, ValueError) as e:
        return None, f"SOCFORTRESS_SYSMON_SYNC_URL is not a URL ({e})."
    if not url.host:
        return None, "SOCFORTRESS_SYSMON_SYNC_URL has no host."
    if url.scheme != "https" and not (url.scheme == "http" and url.host in _LOOPBACK_HOSTS):
        return None, "SOCFORTRESS_SYSMON_SYNC_URL must be an https URL: this CoPilot's license key is sent with each check."
    if url.userinfo or url.query or url.fragment:
        return None, "SOCFORTRESS_SYSMON_SYNC_URL must have no user name, query or fragment."
    return base + BUNDLE_PATH, None


def key_fingerprint(license_key: str) -> str:
    """What the logs say about a license key: the first 12 hex digits of its SHA-256, never the key."""
    return hashlib.sha256(license_key.encode("utf-8")).hexdigest()[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_text(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime(_UTC_FORMAT)


def _parse_utc(value: object) -> Optional[datetime]:
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, _UTC_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# --------------------------------------------------------------------------------------------------------------------
# Trusted release keys
# --------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TrustedKey:
    key_id: str
    public_key: Ed25519PublicKey
    not_after: Optional[datetime] = None

    def trusted_at(self, moment: datetime) -> bool:
        return self.not_after is None or moment <= self.not_after


def _parse_trusted_key(entry: object) -> TrustedKey:
    if not isinstance(entry, dict):
        raise ValueError("an entry is not an object")
    key_id = entry.get("key_id")
    if not isinstance(key_id, str) or not KEY_ID_RE.fullmatch(key_id):
        raise ValueError(f"key_id {key_id!r} is not 1-64 of A-Z, a-z, 0-9, '.', '_', '-'")
    try:
        raw = base64.b64decode(str(entry.get("public_key", "")).encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        raise ValueError(f"{key_id}: public_key is not base64")
    if len(raw) != 32:
        raise ValueError(f"{key_id}: public_key is not a raw 32-byte Ed25519 public key")
    not_after = None
    if entry.get("not_after") is not None:
        not_after = _parse_utc(entry["not_after"])
        if not_after is None:
            raise ValueError(f"{key_id}: not_after is not YYYY-MM-DDTHH:MM:SSZ")
    return TrustedKey(key_id=key_id, public_key=Ed25519PublicKey.from_public_bytes(raw), not_after=not_after)


def load_trusted_keys(path: Optional[Path] = None) -> List[TrustedKey]:
    """
    The release keys this CoPilot trusts ({"keys": [{"key_id", "public_key", "not_after"?}]}). An entry that cannot be
    read is left out, and logged: a broken entry never widens trust. An empty list means sync is not configured.
    """
    path = path or TRUSTED_KEYS_FILE
    try:
        document = json.loads(path.read_bytes())
    except (OSError, ValueError) as e:
        logger.error(f"Sysmon default sync: could not read the trusted release keys ({path.name}): {e}")
        return []
    entries = document.get("keys") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        logger.error(f"Sysmon default sync: {path.name} has no 'keys' list")
        return []
    keys: List[TrustedKey] = []
    for entry in entries:
        try:
            key = _parse_trusted_key(entry)
        except ValueError as e:
            logger.error(f"Sysmon default sync: a trusted release key was left out: {e}")
            continue
        if any(existing.key_id == key.key_id for existing in keys):
            logger.error(f"Sysmon default sync: trusted release key {key.key_id!r} is listed twice; the first one is used")
            continue
        keys.append(key)
    return keys


# --------------------------------------------------------------------------------------------------------------------
# Bundle verification
# --------------------------------------------------------------------------------------------------------------------


class SyncError(Exception):
    """A check that cannot go on: its outcome and the message the admin sees."""

    def __init__(self, outcome: SyncOutcome, message: str):
        super().__init__(message)
        self.outcome = outcome
        self.message = message


def _refuse(message: str, outcome: SyncOutcome = SyncOutcome.VERIFICATION_FAILED) -> SyncError:
    return SyncError(outcome, f"The SOCFortress release was refused: {message}. Nothing was changed.")


@dataclass(frozen=True)
class Release:
    """A bundle whose signature, manifest and content all checked out."""

    content: bytes
    key_id: str
    sequence: int
    commit: str
    created_at: str
    content_sha256: str
    content_sha256_crlf: str
    content_size: int
    placeholders: int
    schemaversion: str

    @property
    def label(self) -> str:
        return f"SOCFortress release #{self.sequence} ({self.commit[:7]})"


def crlf(data: bytes) -> bytes:
    """The content with every line ending normalised to CRLF (what the manifest's content_sha256_crlf is of)."""
    return _LINE_END_RE.sub(b"\r\n", data)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def same_config(stored: bytes, content_sha256: str, content_sha256_crlf: Optional[str]) -> bool:
    """Whether stored bytes are the given release's content, line endings aside (the editor saves LF)."""
    if _sha256(stored) == content_sha256:
        return True
    return bool(content_sha256_crlf) and _sha256(crlf(stored)) == content_sha256_crlf


def _b64(bundle: dict, field: str) -> bytes:
    value = bundle.get(field)
    if not isinstance(value, str):
        raise _refuse(f"the bundle has no base64 {field!r}")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        raise _refuse(f"the bundle's {field!r} is not valid base64")


def _verifies(key: TrustedKey, signature: bytes, manifest: bytes) -> bool:
    try:
        key.public_key.verify(signature, manifest)
    except InvalidSignature:
        return False
    return True


def _signer(keys: List[TrustedKey], signature: bytes, manifest: bytes, moment: datetime) -> TrustedKey:
    """The trusted, unexpired key the signature verifies with. Nothing of the manifest is read before this."""
    if not keys:
        raise SyncError(SyncOutcome.NOT_CONFIGURED, "No SOCFortress release key is configured in this CoPilot version.")
    for key in keys:
        if key.trusted_at(moment) and _verifies(key, signature, manifest):
            return key
    expired = next((key for key in keys if not key.trusted_at(moment) and _verifies(key, signature, manifest)), None)
    if expired is not None:
        raise _refuse(
            f"it is signed with release key {expired.key_id!r}, which expired on {_utc_text(expired.not_after)} and is no longer trusted",
        )
    trusted = ", ".join(key.key_id for key in keys if key.trusted_at(moment)) or "none unexpired"
    raise _refuse(
        f"its signature does not verify with any trusted release key ({trusted}): it was not signed by SOCFortress, or it was altered",
    )


def _int_field(manifest: dict, field: str) -> int:
    value = manifest.get(field)
    if type(value) is not int:  # bool is an int subclass: never a count
        raise _refuse(f"the manifest's {field!r} is not an integer")
    return value


def _text_field(manifest: dict, field: str, pattern: Optional[re.Pattern] = None) -> str:
    value = manifest.get(field)
    if not isinstance(value, str) or (pattern is not None and not pattern.fullmatch(value)):
        raise _refuse(f"the manifest's {field!r} is missing or malformed")
    return value


async def verify_bundle(raw: bytes, keys: List[TrustedKey], moment: Optional[datetime] = None) -> Release:
    """Verify a release bundle (contract sections 1-4) and the config it carries. Raises SyncError on any failure."""
    moment = moment or _now()
    try:
        bundle = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise _refuse("the service's answer is not JSON")
    if not isinstance(bundle, dict):
        raise _refuse("the service's answer is not a release bundle")
    if bundle.get("bundle_format") != BUNDLE_FORMAT:
        raise _refuse(f"unknown bundle format {str(bundle.get('bundle_format'))[:64]!r}")
    manifest_bytes = _b64(bundle, "manifest")
    signature = _b64(bundle, "signature")
    content = _b64(bundle, "content")
    if len(signature) != 64:
        raise _refuse("the signature is not a 64-byte Ed25519 signature")

    signer = _signer(keys, signature, manifest_bytes, moment)

    # Only now that the signature checks out is the manifest read
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise _refuse("the signed manifest is not JSON")
    if not isinstance(manifest, dict):
        raise _refuse("the signed manifest is not an object")
    if manifest.get("format") != MANIFEST_FORMAT:
        raise _refuse(f"unknown manifest format {str(manifest.get('format'))[:64]!r}")
    key_id = _text_field(manifest, "key_id", KEY_ID_RE)
    if key_id != signer.key_id:
        raise _refuse(f"the manifest names release key {key_id!r}, but it is signed with {signer.key_id!r}")
    if manifest.get("channel") != CHANNEL:
        raise _refuse(f"it is for channel {str(manifest.get('channel'))[:64]!r}, not {CHANNEL!r}")
    sequence = _int_field(manifest, "sequence")
    if sequence < 1:
        raise _refuse("its sequence is not a positive integer")
    commit = _text_field(manifest, "commit", _HEX40_RE)
    created_at = _text_field(manifest, "created_at", _UTC_RE)
    if _parse_utc(created_at) is None:
        raise _refuse("the manifest's 'created_at' is not a UTC time")
    content_sha256 = _text_field(manifest, "content_sha256", _HEX64_RE)
    content_sha256_crlf = _text_field(manifest, "content_sha256_crlf", _HEX64_RE)
    content_size = _int_field(manifest, "content_size")
    placeholders = _int_field(manifest, "placeholders")
    schemaversion = _text_field(manifest, "schemaversion")

    if len(content) != content_size:
        raise _refuse(f"the content is {len(content)} bytes, the signed manifest says {content_size}")
    if _sha256(content) != content_sha256:
        raise _refuse("the content's SHA-256 is not the one in the signed manifest")
    if _sha256(crlf(content)) != content_sha256_crlf:
        raise _refuse("the content's CRLF SHA-256 is not the one in the signed manifest")
    if placeholders < 1:
        raise _refuse(f"it has no {INSTALL_DIR_PLACEHOLDER} placeholder, so it is not the installer's template")
    found = content.count(INSTALL_DIR_PLACEHOLDER.encode("ascii"))
    if found != placeholders:
        raise _refuse(f"the content has {found} {INSTALL_DIR_PLACEHOLDER} placeholder(s), the signed manifest says {placeholders}")

    # The config itself: the checks of "Save as default"
    invalid = SyncOutcome.INVALID_CONFIG
    if content_size > MAX_SYSMON_CONFIG_BYTES:
        raise _refuse(f"the config is {content_size} bytes, over the {MAX_SYSMON_CONFIG_BYTES} bytes (5 MiB) a deploy accepts", invalid)
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise _refuse("the config is not UTF-8 text", invalid)
    try:
        # The only parse of the content, once its signature checked out
        root = await validate_sysmon_config(text, allow_installer_tokens=True)
    except HTTPException as e:
        raise _refuse(f"it is not a valid Sysmon config: {e.detail}", invalid)
    root_schema = root.get("schemaversion")
    if root_schema != schemaversion:
        raise _refuse(f"the manifest's schemaversion {schemaversion[:32]!r} is not the config's ({str(root_schema)[:32]!r})")

    return Release(
        content=content,
        key_id=key_id,
        sequence=sequence,
        commit=commit,
        created_at=created_at,
        content_sha256=content_sha256,
        content_sha256_crlf=content_sha256_crlf,
        content_size=content_size,
        placeholders=placeholders,
        schemaversion=schemaversion,
    )


# --------------------------------------------------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------------------------------------------------

_STATUS_OUTCOMES = {
    401: (
        SyncOutcome.UNAUTHORIZED,
        "The SOCFortress sync service refused the request as unauthenticated (HTTP 401): it got no license key.",
    ),
    403: (
        SyncOutcome.LICENSE_REJECTED,
        "The SOCFortress sync service rejected this CoPilot's license (HTTP 403): it is invalid or expired.",
    ),
    404: (SyncOutcome.NOT_PUBLISHED, "SOCFortress has not published a default Sysmon config yet (HTTP 404)."),
    429: (SyncOutcome.RATE_LIMITED, "The SOCFortress sync service is rate-limiting this CoPilot (HTTP 429)."),
    503: (
        SyncOutcome.SERVICE_UNAVAILABLE,
        "The SOCFortress sync service is unavailable, or could not check this CoPilot's license right now (HTTP 503).",
    ),
}


def _origin(url: httpx.URL) -> Tuple[str, str, int]:
    return url.scheme, url.host, url.port or (443 if url.scheme == "https" else 80)


async def _raw(response: httpx.Response) -> AsyncIterator[bytes]:
    """The raw bytes. A response already read into memory (an in-process transport's) is its content."""
    if response.is_stream_consumed:
        yield response.content
        return
    async for chunk in response.aiter_raw():
        yield chunk


async def _read_capped(response: httpx.Response) -> bytes:
    encodings = [t.strip().lower() for v in response.headers.get_list("content-encoding") for t in v.split(",")]
    if any(e not in ("", "identity") for e in encodings):
        raise SyncError(
            SyncOutcome.HTTP_ERROR,
            "The SOCFortress sync service answered with a compressed body, which this CoPilot does not accept.",
        )
    too_large = SyncError(
        SyncOutcome.TOO_LARGE,
        f"The SOCFortress sync service's answer is larger than {MAX_RESPONSE_BYTES // (1024 * 1024)} MiB: refused.",
    )
    declared = response.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
        raise too_large
    body = bytearray()
    async for chunk in _raw(response):
        body.extend(chunk)
        if len(body) > MAX_RESPONSE_BYTES:
            raise too_large
    return bytes(body)


async def _fetch(url: str, headers: dict, transport: Optional[httpx.AsyncBaseTransport] = None) -> Tuple[int, bytes, httpx.Headers]:
    """
    GET the bundle: (status, body, headers), the body read only for a 200. Redirects are followed only within the
    service's own scheme, host and port, so the license key never goes anywhere else.
    """
    target = httpx.URL(url)
    origin = _origin(target)
    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT, follow_redirects=False, transport=transport) as client:
        for _ in range(MAX_REDIRECTS + 1):
            async with client.stream("GET", target, headers=headers) as response:
                if response.status_code in _REDIRECT_CODES:
                    location = response.headers.get("location")
                    if not location:
                        raise SyncError(
                            SyncOutcome.HTTP_ERROR,
                            f"The SOCFortress sync service answered HTTP {response.status_code} without a location.",
                        )
                    following = response.url.join(location)
                    if _origin(following) != origin:
                        raise SyncError(
                            SyncOutcome.REDIRECT_REFUSED,
                            f"The SOCFortress sync service redirected to {following.scheme}://{following.host}, another host or scheme: not "
                            f"followed, so this CoPilot's license key is only sent to {target.host}.",
                        )
                    target = following
                    continue
                if response.status_code != 200:
                    return response.status_code, b"", response.headers
                return 200, await _read_capped(response), response.headers
    raise SyncError(SyncOutcome.HTTP_ERROR, f"The SOCFortress sync service redirected more than {MAX_REDIRECTS} times.")


def etag(sequence: int, content_sha256: str) -> str:
    """The service's ETag for a release."""
    return f'"{sequence}-{content_sha256}"'


# --------------------------------------------------------------------------------------------------------------------
# Records in MinIO (sync.json, sync-status.json)
# --------------------------------------------------------------------------------------------------------------------


async def read_applied() -> Optional[SysmonDefaultSyncApplied]:
    """
    sync.json, or None when there is none. One that cannot be read as a sync record counts as none (logged): the guard
    then protects whatever default is stored, and anyone able to write it could write the default itself. A MinIO
    failure raises.
    """
    raw = await read_sysmon_defaults_object(SYSMON_DEFAULT_SYNC_OBJECT)
    if raw is None:
        return None
    try:
        return SysmonDefaultSyncApplied.model_validate(json.loads(raw))
    except (ValueError, UnicodeDecodeError, ValidationError):
        logger.warning(f"Sysmon default sync: {SYSMON_DEFAULT_SYNC_OBJECT} is not a sync record; it is ignored")
        return None


async def read_last_check() -> Optional[SysmonDefaultSyncRunResult]:
    raw = await read_sysmon_defaults_object(SYSMON_DEFAULT_SYNC_STATUS_OBJECT)
    if raw is None:
        return None
    try:
        return SysmonDefaultSyncRunResult.model_validate(json.loads(raw))
    except (ValueError, UnicodeDecodeError, ValidationError):
        logger.warning(f"Sysmon default sync: {SYSMON_DEFAULT_SYNC_STATUS_OBJECT} is not a check record; it is ignored")
        return None


def _json_bytes(model) -> bytes:
    return json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True).encode("utf-8")


async def _record_check(result: SysmonDefaultSyncRunResult) -> None:
    try:
        await write_sysmon_defaults_object(SYSMON_DEFAULT_SYNC_STATUS_OBJECT, _json_bytes(result), "application/json")
    except Exception as e:  # noqa: BLE001 - the check's outcome is still returned and logged
        logger.error(f"Sysmon default sync: could not record the check in {SYSMON_DEFAULT_SYNC_STATUS_OBJECT}: {e}")


# --------------------------------------------------------------------------------------------------------------------
# A check
# --------------------------------------------------------------------------------------------------------------------


@dataclass
class _Apply:
    """An apply to audit: what was there and what is now."""

    release: Release
    outcome: SyncOutcome
    forced: bool
    previous: Optional[SysmonDefaultSyncApplied]
    replaced_sha256: Optional[str]
    service: str
    error: Optional[str] = None


def _done(
    outcome: SyncOutcome,
    message: str,
    mode: SyncMode,
    forced: bool,
    checked_at: str,
    release: Optional[Release] = None,
) -> SysmonDefaultSyncRunResult:
    return SysmonDefaultSyncRunResult(
        outcome=outcome,
        ok=outcome in OK_OUTCOMES,
        message=message,
        mode=mode,
        forced=forced,
        checked_at=checked_at,
        sequence=release.sequence if release else None,
        commit=release.commit if release else None,
    )


def _applied_record(release: Release, service: str, applied_at: str) -> SysmonDefaultSyncApplied:
    return SysmonDefaultSyncApplied(
        sequence=release.sequence,
        commit=release.commit,
        content_sha256=release.content_sha256,
        content_sha256_crlf=release.content_sha256_crlf,
        key_id=release.key_id,
        applied_at=applied_at,
        created_at=release.created_at,
        schemaversion=release.schemaversion,
        source=SOURCE,
        service_url=service,
    )


def _changed_here_message(release: Release, applied: Optional[SysmonDefaultSyncApplied]) -> str:
    since = f" since SOCFortress release #{applied.sequence} was synced" if applied else ""
    return (
        f"This CoPilot's default Sysmon config was changed here{since}, so {release.label} was not applied: sync never "
        "overwrites a default an admin saved. To replace it with SOCFortress's, run Sync now and confirm the replacement."
    )


async def _check(
    session: AsyncSession,
    mode: SyncMode,
    forced: bool,
    checked_at: str,
    transport: Optional[httpx.AsyncBaseTransport],
) -> Tuple[SysmonDefaultSyncRunResult, Optional[_Apply], Optional[str]]:
    """One check: its result, the apply to audit (if any), and the license fingerprint for the log."""

    def done(outcome: SyncOutcome, message: str, release: Optional[Release] = None) -> SysmonDefaultSyncRunResult:
        return _done(outcome, message, mode, forced, checked_at, release)

    keys = load_trusted_keys()
    if not keys:
        return (
            done(
                SyncOutcome.NOT_CONFIGURED,
                "No SOCFortress release key is configured in this CoPilot version, so the default Sysmon config is not synced. Nothing was fetched.",
            ),
            None,
            None,
        )
    service = service_url()
    url, url_error = _bundle_url(service)
    if url is None:
        return done(SyncOutcome.INVALID_URL, f"{url_error} Nothing was fetched."), None, None

    license_row = await get_license(session, raise_on_missing=False)
    license_key = (getattr(license_row, "license_key", None) or "").strip()
    if not license_key:
        return (
            done(SyncOutcome.NO_LICENSE, "This CoPilot has no license, which the SOCFortress sync service requires. Nothing was fetched."),
            None,
            None,
        )
    fingerprint = key_fingerprint(license_key)

    try:
        result, apply, _ = await _fetch_and_apply(done, keys, service, url, license_key, fingerprint, forced, checked_at, transport)
    except Exception as e:  # noqa: BLE001 - reported as the check's outcome
        result, apply = done(SyncOutcome.ERROR, f"The check failed: {type(e).__name__}: {e}"), None
    # Whatever an error message quoted (a header value in a protocol error), the key never leaves this function
    if license_key in result.message:
        result.message = result.message.replace(license_key, f"[license key {fingerprint}]")
    return result, apply, fingerprint


async def _fetch_and_apply(
    done,
    keys: List[TrustedKey],
    service: str,
    url: str,
    license_key: str,
    fingerprint: str,
    forced: bool,
    checked_at: str,
    transport: Optional[httpx.AsyncBaseTransport],
) -> Tuple[SysmonDefaultSyncRunResult, Optional[_Apply], Optional[str]]:
    """The check once a license key is known: fetch, verify, anti-rollback, the guard, apply."""

    try:
        applied = await read_applied()
        stored = await read_default_sysmon_config()
    except Exception as e:  # noqa: BLE001 - reported as the check's outcome
        return (
            done(
                SyncOutcome.STORE_ERROR,
                f"Could not read this CoPilot's default Sysmon config from its data store (MinIO): {e}. Nothing was fetched.",
            ),
            None,
            fingerprint,
        )

    headers = {
        "x-api-key": license_key,
        "module-version": MODULE_VERSION,
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": f"SOCFortress-CoPilot/{CURRENT_VERSION}",
    }
    if applied is not None:
        headers["x-sysmon-default-sequence"] = str(applied.sequence)
    # Only while the stored default is that release: otherwise this check needs the bundle (to restore a missing
    # default, to replace a changed one when forced, or to say which release a changed one differs from)
    conditional = (
        applied is not None
        and not forced
        and stored is not None
        and same_config(stored, applied.content_sha256, applied.content_sha256_crlf)
    )
    if conditional:
        headers["If-None-Match"] = etag(applied.sequence, applied.content_sha256)

    try:
        status, body, response_headers = await _fetch(url, headers, transport)
    except SyncError as e:
        return done(e.outcome, e.message), None, fingerprint
    except httpx.HTTPError as e:
        detail = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
        return done(SyncOutcome.NETWORK_ERROR, f"Could not reach the SOCFortress sync service at {service}: {detail}."), None, fingerprint

    if status == 304:
        if not conditional:
            return (
                done(SyncOutcome.HTTP_ERROR, "The SOCFortress sync service answered 304 to a request that had no ETag."),
                None,
                fingerprint,
            )
        return (
            done(
                SyncOutcome.UP_TO_DATE,
                f"This CoPilot's default is SOCFortress release #{applied.sequence} ({applied.commit[:7]}), the latest.",
            ),
            None,
            fingerprint,
        )
    if status in _STATUS_OUTCOMES:
        outcome, message = _STATUS_OUTCOMES[status]
        retry_after = response_headers.get("retry-after")
        if status == 429 and retry_after and retry_after.strip().isdigit():
            message = f"{message[:-1]}: retry after {retry_after.strip()} seconds."
        return done(outcome, f"{message} The next scheduled check tries again."), None, fingerprint
    if status != 200:
        return done(SyncOutcome.HTTP_ERROR, f"The SOCFortress sync service answered HTTP {status}."), None, fingerprint

    try:
        release = await verify_bundle(body, keys)
    except SyncError as e:
        return done(e.outcome, e.message), None, fingerprint

    async with DEFAULT_CONFIG_LOCK:
        # Read again under the lock: an admin may have saved a default while the bundle was on its way
        try:
            applied = await read_applied()
            stored = await read_default_sysmon_config()
        except Exception as e:  # noqa: BLE001 - reported as the check's outcome
            return (
                done(
                    SyncOutcome.STORE_ERROR,
                    f"Could not read this CoPilot's default Sysmon config from its data store (MinIO): {e}.",
                    release,
                ),
                None,
                fingerprint,
            )

        # Anti-rollback
        if applied is not None:
            if release.sequence < applied.sequence:
                return (
                    done(
                        SyncOutcome.ROLLBACK_REFUSED,
                        f"The service offered {release.label}, older than SOCFortress release #{applied.sequence} already synced here: refused. Nothing was changed.",
                        release,
                    ),
                    None,
                    fingerprint,
                )
            if release.sequence == applied.sequence and release.content_sha256 != applied.content_sha256:
                return (
                    done(
                        SyncOutcome.ROLLBACK_REFUSED,
                        f"The service offered SOCFortress release #{release.sequence} with a different content than the release #{applied.sequence} synced here: refused. Nothing was changed.",
                        release,
                    ),
                    None,
                    fingerprint,
                )
        same_release = applied is not None and release.sequence == applied.sequence

        # The local-modification guard
        if stored is not None and same_config(stored, release.content_sha256, release.content_sha256_crlf):
            if same_release:
                return done(SyncOutcome.UP_TO_DATE, f"This CoPilot's default is {release.label}, the latest.", release), None, fingerprint
            action = SyncOutcome.ADOPTED
        elif stored is None or (applied is not None and same_config(stored, applied.content_sha256, applied.content_sha256_crlf)):
            action = SyncOutcome.APPLIED
        elif forced:
            action = SyncOutcome.APPLIED
        else:
            return done(SyncOutcome.LOCAL_DEFAULT_DIFFERS, _changed_here_message(release, applied), release), None, fingerprint

        guard_bypassed = (
            action is SyncOutcome.APPLIED
            and stored is not None
            and not (applied is not None and same_config(stored, applied.content_sha256, applied.content_sha256_crlf))
        )
        apply = _Apply(
            release=release,
            outcome=action,
            forced=guard_bypassed,
            previous=applied,
            replaced_sha256=_sha256(stored) if stored is not None else None,
            service=service,
        )
        if action is SyncOutcome.APPLIED:
            try:
                await write_default_sysmon_config(release.content)
            except Exception as e:  # noqa: BLE001 - audited as a failure, reported as the outcome
                apply.error = f"Could not store it: {e}"[:1000]
                return (
                    done(
                        SyncOutcome.STORE_ERROR,
                        f"Could not store {release.label} as this CoPilot's default in its data store (MinIO): {e}.",
                        release,
                    ),
                    apply,
                    fingerprint,
                )
        # The record goes after the content: a record without the content would make the next check take the stored
        # (old) default for a local change, while content without the record is adopted by the next check.
        try:
            await write_sysmon_defaults_object(
                SYSMON_DEFAULT_SYNC_OBJECT,
                _json_bytes(_applied_record(release, service, checked_at)),
                "application/json",
            )
        except Exception as e:  # noqa: BLE001 - reported as the outcome; the next check adopts the stored release
            stored_note = (
                f"{release.label} was stored as this CoPilot's default, but" if action is SyncOutcome.APPLIED else "The default is"
            )
            return (
                done(
                    SyncOutcome.STORE_ERROR,
                    f"{stored_note} the sync record ({SYSMON_DEFAULT_SYNC_OBJECT}) could not be written: {e}. The next check records it.",
                    release,
                ),
                apply if action is SyncOutcome.APPLIED else None,
                fingerprint,
            )

    if action is SyncOutcome.ADOPTED:
        message = f"This CoPilot's default already was {release.label}: it is now recorded as synced."
    elif guard_bypassed:
        message = f"Replaced this CoPilot's default, which had been changed here, with {release.label}."
    elif stored is None:
        message = f"Stored {release.label} as this CoPilot's default Sysmon config."
    else:
        message = f"Updated this CoPilot's default Sysmon config to {release.label}."
    return done(action, message, release), apply, fingerprint


async def _audit(apply: _Apply, actor, request: Optional[Request]) -> None:
    release = apply.release
    await record_audit_event(
        action=AuditAction.SYSMON_DEFAULT_SYNC,
        actor_user_id=getattr(actor, "id", None),
        actor_username=getattr(actor, "username", None) or SYSTEM_ACTOR,
        entity_type="sysmon_config_default",
        entity_id=f"{SYSMON_CONFIG_DEFAULTS_BUCKET}/{SYSMON_CONFIG_DEFAULT_OBJECT}",
        result=AuditResult.FAILURE if apply.error else AuditResult.SUCCESS,
        # The release identified by its hashes; the config itself is never stored here
        old_value={
            "sequence": apply.previous.sequence if apply.previous else None,
            "commit": apply.previous.commit if apply.previous else None,
            "content_sha256": apply.replaced_sha256,
        },
        new_value={
            "outcome": apply.outcome.value,
            "sequence": release.sequence,
            "commit": release.commit,
            "key_id": release.key_id,
            "created_at": release.created_at,
            "content_sha256": release.content_sha256,
            "content_size": release.content_size,
            "placeholders": release.placeholders,
            "schemaversion": release.schemaversion,
            "forced": apply.forced,
            "service_url": apply.service,
        },
        details=apply.error or ("Sync now" if actor is not None else f"Scheduled check ({JOB_ID})"),
        request=request,
    )


async def run_sysmon_default_sync(
    session: AsyncSession,
    *,
    force: bool = False,
    actor=None,
    request: Optional[Request] = None,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> SysmonDefaultSyncRunResult:
    """
    One check. ``force`` (an admin's confirmed Sync now) overwrites a default changed on this CoPilot, as
    SYSMON_DEFAULT_SYNC=force does on every check. ``actor`` is the admin (None: the scheduled job). Never raises.
    """
    mode, _ = sync_mode()
    forced = force or mode is SyncMode.FORCE
    if mode is SyncMode.OFF:
        return _done(
            SyncOutcome.OFF,
            "Sync from SOCFortress is off on this CoPilot (SYSMON_DEFAULT_SYNC=off). Nothing was fetched.",
            mode,
            False,
            _utc_text(_now()),
        )

    async with _RUN_LOCK:
        checked_at = _utc_text(_now())
        fingerprint = None
        apply = None
        try:
            result, apply, fingerprint = await _check(session, mode, forced, checked_at, transport)
        except Exception as e:  # noqa: BLE001 - a check never raises into the scheduler or the route
            result = _done(SyncOutcome.ERROR, f"The check failed: {type(e).__name__}: {e}", mode, forced, checked_at)
        await _record_check(result)
        if apply is not None:
            await _audit(apply, actor, request)

    who = f"license {fingerprint}" if fingerprint else "no license key sent"
    line = f"Sysmon default sync ({who}): {result.outcome.value}: {result.message}"
    if result.ok or result.outcome in (SyncOutcome.NOT_CONFIGURED, SyncOutcome.LOCAL_DEFAULT_DIFFERS):
        logger.info(line)
    else:
        logger.warning(line)
    return result


async def get_sync_status() -> SysmonDefaultSyncStatus:
    """What the Sysmon Config page shows: the mode, the last check, the release applied, and whether the default was changed here."""
    mode, raw_mode = sync_mode()
    keys = load_trusted_keys()
    status = SysmonDefaultSyncStatus(
        mode=mode,
        mode_setting=raw_mode,
        service_url=service_url(),
        configured=bool(keys),
        trusted_key_ids=[key.key_id for key in keys],
    )
    errors = []
    try:
        status.last_check = await read_last_check()
    except Exception as e:  # noqa: BLE001 - shown as a read error
        errors.append(f"the last check ({e})")
    try:
        status.applied = await read_applied()
    except Exception as e:  # noqa: BLE001 - shown as a read error
        errors.append(f"the sync record ({e})")
    try:
        stored = await read_default_sysmon_config()
        status.default_present = stored is not None
        if status.applied is not None and stored is not None:
            status.local_default_differs = not same_config(stored, status.applied.content_sha256, status.applied.content_sha256_crlf)
    except Exception as e:  # noqa: BLE001 - shown as a read error
        errors.append(f"the default ({e})")
    if errors:
        status.read_error = f"Could not read {', '.join(errors)} from this CoPilot's data store (MinIO)."
    return status
