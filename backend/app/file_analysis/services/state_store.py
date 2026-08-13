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
ENGINE_VERSION = 7

_bucket_ready = False


async def _client():
    return await create_session()


async def ensure_bucket() -> None:
    """Create the bucket on first use (idempotent) — avoids editing CoPilot startup."""
    global _bucket_ready
    if _bucket_ready:
        return
    client = await _client()
    if not await client.bucket_exists(BUCKET):
        await client.make_bucket(BUCKET)
        logger.info(f"Created MinIO bucket {BUCKET}")
    _bucket_ready = True


# --- low-level object ops --------------------------------------------------
async def put_json(key: str, obj: Dict[str, Any]) -> None:
    await ensure_bucket()
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    client = await _client()
    await client.put_object(BUCKET, key, io.BytesIO(body), length=len(body), content_type="application/json")


async def get_json(key: str) -> Optional[Dict[str, Any]]:
    await ensure_bucket()
    client = await _client()
    try:
        await client.stat_object(BUCKET, key)
    except Exception:
        return None
    async with aiohttp.ClientSession() as session:
        response = await client.get_object(BUCKET, key, session)
        try:
            data = await response.read()
        finally:
            response.close()
    return json.loads(data.decode("utf-8"))


async def exists(key: str) -> bool:
    await ensure_bucket()
    client = await _client()
    try:
        await client.stat_object(BUCKET, key)
        return True
    except Exception:
        return False


async def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    await ensure_bucket()
    client = await _client()
    await client.put_object(BUCKET, key, io.BytesIO(data), length=len(data), content_type=content_type)


async def get_bytes(key: str) -> Optional[bytes]:
    await ensure_bucket()
    client = await _client()
    try:
        await client.stat_object(BUCKET, key)
    except Exception:
        return None
    async with aiohttp.ClientSession() as session:
        response = await client.get_object(BUCKET, key, session)
        try:
            return await response.read()
        finally:
            response.close()


async def list_prefix(prefix: str) -> List[str]:
    await ensure_bucket()
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


# --- domain helpers --------------------------------------------------------
def _job_key(job_id: str) -> str:
    return f"jobs/{job_id}.json"


def _result_key(customer_code: str, sha256: str) -> str:
    return f"{customer_code}/{sha256}/result.json"


def _preview_key(customer_code: str, sha256: str, name: str) -> str:
    return f"{customer_code}/{sha256}/previews/{name}"


async def save_job(job: Dict[str, Any]) -> None:
    await put_json(_job_key(job["job_id"]), job)


async def load_job(job_id: str) -> Optional[Dict[str, Any]]:
    return await get_json(_job_key(job_id))


async def save_result(customer_code: str, sha256: str, result: Dict[str, Any]) -> None:
    await put_json(_result_key(customer_code, sha256), result)


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


async def list_history(customer_code: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Recent analyses for a customer, newest first (built from stored results).

    Tenant-isolated by the ``{customer_code}/`` key prefix. Reads each result's
    embedded job summary — bounded by a soft cap so a customer with a very large
    history doesn't fan out unboundedly.
    """
    names = await list_prefix(f"{customer_code}/")
    result_keys = [n for n in names if n.endswith("/result.json")]
    items: List[Dict[str, Any]] = []
    for key in result_keys[:250]:
        res = await get_json(key)
        if not res:
            continue
        job = res.get("job") or {}
        insp = res.get("inspector") or {}
        rep = res.get("reputation") or {}
        found = bool(rep.get("found"))
        items.append(
            {
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
        )
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items[:limit]


async def save_preview(customer_code: str, sha256: str, name: str, data: bytes) -> None:
    await put_bytes(_preview_key(customer_code, sha256, name), data, content_type="image/png")


async def load_preview(customer_code: str, sha256: str, name: str) -> Optional[bytes]:
    return await get_bytes(_preview_key(customer_code, sha256, name))
