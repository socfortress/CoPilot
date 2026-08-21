"""MinIO-backed state + cache for File Analysis — NO new database schema.

Everything the module needs to persist is a key lookup, so we store it as objects
in MinIO (which CoPilot already runs) instead of new MySQL tables. This is durable
across backend restarts and image pulls — the data lives on MinIO's own volume, a
separate service, not in the app container's filesystem.

Layout (all under one bucket, tenant-isolated by key prefix):
    jobs/{job_id}.json                          -> AnalysisJob state (polled)
    {customer_code}/{sha256}/result.json        -> merged AnalysisResult (cache)
    {customer_code}/{sha256}/previews/{name}    -> PNG preview bytes

Hot paths (cache check, job status) are single-key stat/get — fast at any volume.
Object storage is deliberately not a query engine: this module does key lookups
and a bounded per-tenant listing, nothing that needs scanning at scale.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import aiohttp
from loguru import logger

from app.data_store.data_store_session import create_session

BUCKET = os.getenv("FILE_ANALYSIS_MINIO_BUCKET", "file-analysis")

# Bump whenever the analysis pipeline changes meaningfully — a cached result from
# an older engine is treated as a miss and re-analyzed, so improvements re-apply
# to files already seen (see CLAUDE.md -> File Analysis).
#   1: initial   2: + VirusTotal reputation + PDF/PyMuPDF + IOC cleanup
#   3: reputation tracing / re-run to surface VT logs
#   4: non-blocking VT (detached upload+scan), VT-ratio header, preview-flicker fix
#   5: plain-text analyzer — text/config/log files now show their contents + IOCs
#   6: enriched CAPE detonation summary (processes, dns/http/connections, MITRE, payloads)
#   7: process pid read from CAPE's process_id (was always null -> broken process tree)
#   8: VirusTotal deep intel (per-engine detections, crowdsourced YARA/Sigma/IDS, VT sandbox behaviour)
#   9: noise-aware sandbox verdict — environmental/monitor signatures no longer drive the verdict
#  10: Tier-1 ATT&CK static behaviour rules (T1490/T1562/T1059/T1003/… script detection) +
#      honest "inspection incomplete" reason (infra failure no longer reads as a content finding)
#  11: behaviour rules expanded to 31 techniques + applied across office-macro/LNK/HTML analyzers
#  12: PE optional-enrichment (capa/FLOSS) degrades gracefully — a MISSING tool no longer
#      marks the analysis incomplete, so .exe files stop falsely reading "suspicious"
#  13: full detonation behaviour surfaced (files/registry/mutexes/services/commands/APIs/timeline)
#  14: broadened detonation coverage — .py/scripts, MSI, Office, PDF, archives, HTA now escalate
#  15: low-confidence static-PE/.NET-JIT signatures no longer drive the verdict (benign packed = clean)
ENGINE_VERSION = 15

_bucket_ready = False

# MinIO I/O crosses the network (a VPN in this dev setup), so a single connection
# timeout — Windows surfaces it as "The semaphore timeout period has expired" — used
# to abort the whole analysis mid-write (orchestrator crashed in save_result). Retry
# transient connection/timeout errors with exponential backoff so a blip is ridden out.
# Logical S3 errors (NoSuchKey/NoSuchBucket) are NOT transient: _retry re-raises them
# immediately (no wasted retries) and the read helpers treat them as "not found".
_MINIO_RETRIES = int(os.getenv("FILE_ANALYSIS_MINIO_RETRIES", "4"))
_MINIO_BACKOFF = float(os.getenv("FILE_ANALYSIS_MINIO_BACKOFF", "0.5"))
_TRANSIENT_ERRORS = (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError, OSError)


async def _client():
    return await create_session()


async def _retry(what: str, op):
    """Run an async MinIO op, retrying only transient connection/timeout errors.

    Re-raises the last transient error once retries are exhausted, and re-raises
    non-transient errors (e.g. S3 ``NoSuchKey``) immediately so callers can act on them.
    """
    for attempt in range(_MINIO_RETRIES):
        try:
            return await op()
        except _TRANSIENT_ERRORS as exc:
            if attempt + 1 >= _MINIO_RETRIES:
                logger.error(f"MinIO {what} failed after {_MINIO_RETRIES} attempts: {exc}")
                raise
            delay = _MINIO_BACKOFF * (2 ** attempt)
            logger.warning(
                f"MinIO {what} transient error (attempt {attempt + 1}/{_MINIO_RETRIES}): {exc}; retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)


async def ensure_bucket() -> None:
    """Create the bucket on first use (idempotent) — avoids editing CoPilot startup."""
    global _bucket_ready
    if _bucket_ready:
        return

    async def _op():
        client = await _client()
        if not await client.bucket_exists(BUCKET):
            await client.make_bucket(BUCKET)
            logger.info(f"Created MinIO bucket {BUCKET}")

    await _retry("ensure_bucket", _op)
    _bucket_ready = True


# --- low-level object ops --------------------------------------------------
async def put_json(key: str, obj: Dict[str, Any]) -> None:
    await ensure_bucket()
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")

    async def _op():
        client = await _client()
        await client.put_object(BUCKET, key, io.BytesIO(body), length=len(body), content_type="application/json")

    await _retry(f"put_json {key}", _op)


async def get_json(key: str) -> Optional[Dict[str, Any]]:
    await ensure_bucket()

    async def _op():
        client = await _client()
        await client.stat_object(BUCKET, key)  # NoSuchKey (non-transient) -> re-raised -> None below
        async with aiohttp.ClientSession() as session:
            response = await client.get_object(BUCKET, key, session)
            try:
                return await response.read()
            finally:
                response.close()

    try:
        data = await _retry(f"get_json {key}", _op)
    except Exception:
        # Missing object, or a sustained outage after all retries -> treat as a miss.
        return None
    return json.loads(data.decode("utf-8"))


async def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    await ensure_bucket()

    async def _op():
        client = await _client()
        await client.put_object(BUCKET, key, io.BytesIO(data), length=len(data), content_type=content_type)

    await _retry(f"put_bytes {key}", _op)


async def get_bytes(key: str) -> Optional[bytes]:
    await ensure_bucket()

    async def _op():
        client = await _client()
        await client.stat_object(BUCKET, key)
        async with aiohttp.ClientSession() as session:
            response = await client.get_object(BUCKET, key, session)
            try:
                return await response.read()
            finally:
                response.close()

    try:
        return await _retry(f"get_bytes {key}", _op)
    except Exception:
        return None


async def list_prefix(prefix: str) -> List[str]:
    await ensure_bucket()

    async def _op():
        client = await _client()
        names: List[str] = []
        objects = client.list_objects(BUCKET, prefix=prefix, recursive=True)
        # miniopy_async yields a lone ``None`` for an empty listing (prefix with no
        # objects, e.g. a customer that has never been analyzed) — guard against it.
        async for obj in objects:
            name = getattr(obj, "object_name", None) if obj is not None else None
            if name:
                names.append(name)
        return names

    try:
        return await _retry(f"list_prefix {prefix}", _op)
    except Exception:
        return []


# --- domain helpers --------------------------------------------------------
def _job_key(job_id: str) -> str:
    return f"jobs/{job_id}.json"


def _result_key(customer_code: str, sha256: str) -> str:
    return f"{customer_code}/{sha256}/result.json"


def _preview_key(customer_code: str, sha256: str, name: str) -> str:
    return f"{customer_code}/{sha256}/previews/{name}"


def _summary_key(customer_code: str, sha256: str) -> str:
    # A tiny per-analysis index row so the history list never has to fetch (and
    # deserialize) the full result.json — detonation results are large.
    return f"{customer_code}/{sha256}/summary.json"


def _history_item(result: Dict[str, Any]) -> Dict[str, Any]:
    """Project a full result down to the lightweight fields the history table shows."""
    job = result.get("job") or {}
    insp = result.get("inspector") or {}
    rep = result.get("reputation") or {}
    found = bool(rep.get("found"))
    return {
        "job_id": job.get("job_id", ""),
        "filename": job.get("filename") or insp.get("filename") or "",
        "sha256": job.get("sha256") or insp.get("sha256") or "",
        "verdict": job.get("verdict"),
        "source": job.get("source", ""),
        "status": job.get("status", ""),
        "hardened": bool(job.get("hardened", True)),
        "created_at": job.get("created_at", ""),
        "updated_at": job.get("updated_at", ""),
        "vt_malicious": rep.get("malicious") if found else None,
        "vt_total": rep.get("total") if found else None,
    }


async def save_job(job: Dict[str, Any]) -> None:
    await put_json(_job_key(job["job_id"]), job)


async def load_job(job_id: str) -> Optional[Dict[str, Any]]:
    return await get_json(_job_key(job_id))


async def save_result(customer_code: str, sha256: str, result: Dict[str, Any]) -> None:
    await put_json(_result_key(customer_code, sha256), result)
    # Also write the lightweight index row so list_history reads small objects, not
    # the full result. Best-effort: a summary write failure must not fail the save.
    try:
        await put_json(_summary_key(customer_code, sha256), _history_item(result))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"summary write failed for {sha256[:12]}: {exc}")


async def delete_analysis(customer_code: str, sha256: str, job_id: Optional[str] = None) -> int:
    """Remove one analysis: its result, summary, previews, and (optional) job object.

    Scoped strictly to ``{customer_code}/{sha256}/`` plus the given job — nothing
    else is touched. Returns the number of objects removed.
    """
    keys = [_result_key(customer_code, sha256), _summary_key(customer_code, sha256)]
    keys.extend(await list_prefix(f"{customer_code}/{sha256}/previews/"))
    if job_id:
        keys.append(_job_key(job_id))

    async def _op():
        client = await _client()
        removed = 0
        for key in keys:
            try:
                await client.remove_object(BUCKET, key)
                removed += 1
            except Exception:  # object may not exist (e.g. no previews) — ignore
                pass
        return removed

    return await _retry(f"delete_analysis {sha256[:12]}", _op)


async def load_result(customer_code: str, sha256: str) -> Optional[Dict[str, Any]]:
    return await get_json(_result_key(customer_code, sha256))


async def find_cached_job_id(customer_code: str, sha256: str) -> Optional[str]:
    """Cache-by-SHA256: return the job id ONLY if a COMPLETE result exists.

    An incomplete/failed result (e.g. the runner was unreachable when it was
    first analyzed) must NOT be treated as a cache hit — otherwise re-uploads
    keep serving the stale failure and never re-run.
    """
    result = await load_result(customer_code, sha256)
    if not result or result.get("inspector", {}).get("analysis_incomplete"):
        return None
    # Stale engine → re-analyze so new features (e.g. reputation) get applied.
    if result.get("engine_version") != ENGINE_VERSION:
        return None
    if result.get("job", {}).get("job_id"):
        return result["job"]["job_id"]
    return None


_HISTORY_SCAN_CAP = 250      # most analyses considered before sort+limit
_HISTORY_CONCURRENCY = 24    # parallel reads (MinIO is over a VPN here)


async def _read_json_batch(keys: List[str]) -> List[Optional[Dict[str, Any]]]:
    """Read many JSON objects KNOWN to exist (from a listing) as fast as possible.

    One shared client + one pooled aiohttp session (connection reuse across the
    batch), and NO per-key ``stat_object`` round-trip — halving the trips that made
    the history list crawl over the VPN. Missing/garbled objects come back as None.
    Order matches ``keys``.
    """
    if not keys:
        return []
    await ensure_bucket()
    client = await _client()
    sem = asyncio.Semaphore(_HISTORY_CONCURRENCY)

    async def _one(session, key):
        async with sem:
            try:
                resp = await client.get_object(BUCKET, key, session)
                try:
                    data = await resp.read()
                finally:
                    resp.close()
                return json.loads(data.decode("utf-8"))
            except Exception:
                return None

    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(*[_one(session, k) for k in keys])


async def list_history(customer_code: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Recent analyses for a customer, newest first.

    Fast path: batch-read the tiny per-analysis ``summary.json`` rows (pooled, no
    stat, parallel) instead of fetching every large ``result.json`` one at a time —
    that sequential full-result fetch was what made the list crawl. Analyses saved
    before summaries existed fall back to the full result and are backfilled so the
    next listing is fast. Tenant-isolated by the ``{cc}/`` prefix.
    """
    names = await list_prefix(f"{customer_code}/")
    have_summary: set = set()
    result_shas: Dict[str, str] = {}
    for name in names:
        parts = name.split("/")
        if len(parts) < 3:
            continue
        sha = parts[1]
        if name.endswith("/summary.json"):
            have_summary.add(sha)
        elif name.endswith("/result.json"):
            result_shas[sha] = name

    # One key per sha: prefer the small summary, else the full result (legacy).
    fast = [(sha, _summary_key(customer_code, sha), True) for sha in have_summary]
    fast.extend((sha, key, False) for sha, key in result_shas.items() if sha not in have_summary)
    fast = fast[:_HISTORY_SCAN_CAP]

    blobs = await _read_json_batch([key for _, key, _ in fast])

    items: List[Dict[str, Any]] = []
    backfill: List[tuple] = []
    for (sha, _key, is_summary), blob in zip(fast, blobs):
        if not blob:
            continue
        if is_summary:
            items.append(blob)
        else:
            item = _history_item(blob)
            items.append(item)
            backfill.append((sha, item))

    # Backfill legacy rows so they're on the fast path next time (best-effort, async).
    for sha, item in backfill:
        try:
            await put_json(_summary_key(customer_code, sha), item)
        except Exception:  # pragma: no cover
            pass

    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items[:limit]


async def save_preview(customer_code: str, sha256: str, name: str, data: bytes) -> None:
    await put_bytes(_preview_key(customer_code, sha256, name), data, content_type="image/png")


async def load_preview(customer_code: str, sha256: str, name: str) -> Optional[bytes]:
    return await get_bytes(_preview_key(customer_code, sha256, name))
