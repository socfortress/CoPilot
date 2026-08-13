"""Reputation enrichment — VirusTotal (reuses CoPilot's existing VT connector).

Flow:
  1. HASH LOOKUP (``get_file_report``) — asks VT "do you already know this
     sha256?" WITHOUT uploading. For known malware this returns the full
     multi-engine verdict instantly and no bytes leave the host.
  2. If VT has never seen the hash AND submission is enabled
     (``ENRICHMENT_SUBMIT_FILES=true``), UPLOAD the file, wait for the scan to
     finish, then re-fetch the now-enriched report.

Submitting a file publishes it to VT (any subscriber can download it), so it is
gated behind an env flag. Verdict interplay is raise-only — reputation can raise
a verdict but never lowers a static finding.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any
from typing import Dict
from typing import Optional

import httpx
from fastapi import HTTPException
from loguru import logger

from app.db.db_session import get_db_session
from app.threat_intel.services.virustotal_file import get_file_analysis_status
from app.threat_intel.services.virustotal_file import get_file_report
from app.utils import get_connector_attribute

VT_MALICIOUS_THRESHOLD = int(os.getenv("ENRICHMENT_VT_MALICIOUS_THRESHOLD", "5"))
SUBMIT_FILES = os.getenv("ENRICHMENT_SUBMIT_FILES", "false").lower() == "true"
VT_MAX_WAIT = int(os.getenv("ENRICHMENT_VT_MAX_WAIT", "300"))
VT_POLL = int(os.getenv("ENRICHMENT_VT_POLL", "10"))
VT_MAX_UPLOAD_MB = int(os.getenv("ENRICHMENT_VT_MAX_UPLOAD_MB", "32"))


async def _vt_api_key() -> Optional[str]:
    try:
        async with get_db_session() as session:
            key = await get_connector_attribute(
                connector_name="VirusTotal",
                column_name="connector_api_key",
                session=session,
            )
        if key:
            logger.info(f"[reputation] VirusTotal API key found (len={len(key)})")
        else:
            logger.warning("[reputation] VirusTotal connector has NO api_key configured — skipping reputation")
        return key or None
    except Exception as exc:
        logger.warning(f"[reputation] failed to read VirusTotal connector key: {exc}")
        return None


def _parse_report(report, sha256: str) -> Dict[str, Any]:
    attrs = report.data.attributes
    stats = attrs.last_analysis_stats
    malicious = int(getattr(stats, "malicious", 0) or 0) if stats else 0
    suspicious = int(getattr(stats, "suspicious", 0) or 0) if stats else 0
    stats_dict = stats.model_dump() if stats else {}
    total = sum(v for v in stats_dict.values() if isinstance(v, int))

    attrs_dict = attrs.model_dump() if hasattr(attrs, "model_dump") else {}
    family = ""
    ptc = attrs_dict.get("popular_threat_classification")
    if isinstance(ptc, dict):
        family = ptc.get("suggested_threat_label", "") or ""

    return {
        "source": "virustotal",
        "found": True,
        "sha256": sha256,
        "malicious": malicious,
        "suspicious": suspicious,
        "total": total,
        "family": family,
        "meaningful_name": attrs_dict.get("meaningful_name", ""),
        "permalink": f"https://www.virustotal.com/gui/file/{sha256}",
        "submitted": False,
    }


async def _lookup(api_key: str, sha256: str) -> Optional[Dict[str, Any]]:
    """Hash lookup. Returns parsed report, {found:false} on 404, or None on error."""
    try:
        report = await get_file_report(api_key, sha256)
    except HTTPException as exc:
        if exc.status_code == 404:
            return {
                "source": "virustotal",
                "found": False,
                "sha256": sha256,
                "permalink": f"https://www.virustotal.com/gui/file/{sha256}",
                "submitted": False,
            }
        logger.warning(f"VirusTotal lookup failed ({exc.status_code}): {exc.detail}")
        return None
    except Exception as exc:
        logger.warning(f"VirusTotal lookup error: {exc}")
        return None
    return _parse_report(report, sha256)


async def _submit(api_key: str, data: bytes, filename: str) -> Optional[str]:
    """Upload a file to VT (PUBLISHES it). Returns the analysis id, or None."""
    url = "https://www.virustotal.com/api/v3/files"
    headers = {"accept": "application/json", "x-apikey": api_key}
    files = {"file": (filename or "sample", data, "application/octet-stream")}
    logger.info(f"Submitting {filename} ({len(data)} bytes) to VirusTotal for analysis")
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(url, headers=headers, files=files)
            resp.raise_for_status()
            return resp.json()["data"]["id"]
    except Exception as exc:
        logger.warning(f"VirusTotal submit failed: {exc}")
        return None


async def _wait_for_analysis(api_key: str, analysis_id: str) -> bool:
    """Poll until the submitted analysis completes (or times out)."""
    waited = 0
    while waited < VT_MAX_WAIT:
        try:
            status = await get_file_analysis_status(api_key, analysis_id)
            if getattr(status.data.attributes, "status", "") == "completed":
                return True
        except Exception as exc:
            logger.warning(f"VT analysis status check failed: {exc}")
            return False
        await asyncio.sleep(VT_POLL)
        waited += VT_POLL
    logger.warning(f"VT analysis {analysis_id} did not complete within {VT_MAX_WAIT}s")
    return False


async def virustotal_lookup(sha256: str) -> Optional[Dict[str, Any]]:
    """Hash-only lookup (no upload)."""
    api_key = await _vt_api_key()
    if not api_key:
        return None
    return await _lookup(api_key, sha256)


async def virustotal_lookup_only(sha256: str) -> Optional[Dict[str, Any]]:
    """Fast, non-blocking hash lookup (no upload). Used inline by the orchestrator."""
    logger.info(f"[reputation] VirusTotal hash lookup for {sha256[:16]} (submit_enabled={SUBMIT_FILES})")
    api_key = await _vt_api_key()
    if not api_key:
        return None
    rep = await _lookup(api_key, sha256)
    if rep and rep.get("found"):
        logger.info(f"[reputation] VirusTotal hash hit: {rep.get('malicious')}/{rep.get('total')} malicious")
    return rep


async def virustotal_submit_and_wait(sha256: str, sample_bytes: Optional[bytes], filename: str) -> Optional[Dict[str, Any]]:
    """Upload the file to VT and wait for the scan (runs DETACHED — never blocks a job)."""
    api_key = await _vt_api_key()
    if not api_key or not sample_bytes:
        return None
    if len(sample_bytes) > VT_MAX_UPLOAD_MB * 1024 * 1024:
        return {"source": "virustotal", "found": False, "sha256": sha256, "submitted": False,
                "note": f"exceeds {VT_MAX_UPLOAD_MB}MB VT upload cap; not submitted",
                "permalink": f"https://www.virustotal.com/gui/file/{sha256}"}

    logger.info(f"[reputation] VirusTotal submitting {filename} ({len(sample_bytes)} bytes)")
    analysis_id = await _submit(api_key, sample_bytes, filename)
    if not analysis_id:
        return {"source": "virustotal", "found": False, "sha256": sha256, "submitted": False,
                "note": "VirusTotal submission failed", "permalink": f"https://www.virustotal.com/gui/file/{sha256}"}
    await _wait_for_analysis(api_key, analysis_id)

    final = await _lookup(api_key, sha256)
    if final and final.get("found"):
        final["submitted"] = True
        logger.info(f"[reputation] VirusTotal scan complete: {final.get('malicious')}/{final.get('total')} malicious")
        return final
    return {"source": "virustotal", "found": False, "sha256": sha256, "submitted": True,
            "note": "uploaded to VirusTotal — still processing; open the permalink for live results",
            "permalink": f"https://www.virustotal.com/gui/file/{sha256}"}


def verdict_from_reputation(rep: Optional[Dict[str, Any]]) -> str:
    """Map a reputation result to a verdict (raise-only, clean if unknown)."""
    if not rep or not rep.get("found"):
        return "clean"
    if int(rep.get("malicious", 0)) >= VT_MALICIOUS_THRESHOLD:
        return "malicious"
    if int(rep.get("malicious", 0)) >= 1 or int(rep.get("suspicious", 0)) >= 1:
        return "suspicious"
    return "clean"
