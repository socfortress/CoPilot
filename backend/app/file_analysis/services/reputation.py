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
# Deep intel: after a hash HIT, pull VT's full report detail (per-engine detections,
# threat classification, crowdsourced YARA/Sigma/IDS) AND VT's own sandbox behaviour
# (MITRE + contacted IOCs + dropped files). Two extra hash-keyed GETs — still NO upload,
# so no bytes leave the host. Invaluable when our own detonation is offline.
VT_DEEP = os.getenv("ENRICHMENT_VT_DEEP", "true").lower() == "true"


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


# --- deep intel -----------------------------------------------------------
def _uniq(items) -> list:
    out: list = []
    for x in items or []:
        if x and x not in out:
            out.append(x)
    return out


def _str_list(items, *keys) -> list:
    """Flatten a VT list of strings-or-dicts to unique strings (dicts read via keys)."""
    out: list = []
    for it in items or []:
        if isinstance(it, str):
            out.append(it)
        elif isinstance(it, dict):
            for k in keys:
                v = it.get(k)
                if v:
                    out.append(v if isinstance(v, str) else str(v))
                    break
    return _uniq(out)


def _iso(ts) -> str:
    if not ts:
        return ""
    try:
        from datetime import datetime, timezone

        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except Exception:
        return ""


def _extract_intel(attrs: Dict[str, Any], behaviour: Dict[str, Any]) -> Dict[str, Any]:
    """Extract SOC-useful signals from a VT v3 file report + behaviour summary.

    Pure and defensive: every field is optional across VT's API, so missing keys
    degrade to empty rather than raising. The ``behaviour`` block comes from VT's OWN
    sandboxes — detonation-grade IOCs even when our sandbox is offline.
    """
    attrs = attrs or {}
    behaviour = behaviour or {}

    ptc = attrs.get("popular_threat_classification") or {}
    threat_categories = [c.get("value") for c in (ptc.get("popular_threat_category") or []) if isinstance(c, dict) and c.get("value")]
    threat_names = [n.get("value") for n in (ptc.get("popular_threat_name") or []) if isinstance(n, dict) and n.get("value")]

    detections = []
    for engine, r in (attrs.get("last_analysis_results") or {}).items():
        if isinstance(r, dict) and r.get("category") in ("malicious", "suspicious") and r.get("result"):
            detections.append({"engine": r.get("engine_name") or engine, "result": r.get("result"), "category": r.get("category")})
    detections.sort(key=lambda d: (d["category"] != "malicious", d["engine"].lower()))

    yara = [{"rule": y.get("rule_name", ""), "author": y.get("author", ""), "description": y.get("description", ""), "ruleset": y.get("ruleset_name", "")}
            for y in (attrs.get("crowdsourced_yara_results") or []) if isinstance(y, dict)]
    sigma = [{"title": s.get("rule_title", ""), "level": s.get("rule_level", ""), "source": s.get("rule_source", "")}
             for s in (attrs.get("sigma_analysis_results") or []) if isinstance(s, dict)]
    ids = [{"msg": i.get("rule_msg", ""), "severity": i.get("alert_severity", ""), "category": i.get("rule_category", ""), "source": i.get("rule_source", "")}
           for i in (attrs.get("crowdsourced_ids_results") or []) if isinstance(i, dict)]

    votes = attrs.get("total_votes") or {}
    sig_info = attrs.get("signature_info") or {}

    mitre = []
    for t in behaviour.get("mitre_attack_techniques") or []:
        if isinstance(t, dict) and t.get("id"):
            mitre.append({"id": t.get("id"), "description": t.get("signature_description") or t.get("description") or "", "severity": t.get("severity", "")})

    behaviour_out = {
        "mitre": mitre,
        "contacted_ips": _str_list(behaviour.get("ip_traffic"), "destination_ip", "ip")[:60],
        "contacted_domains": _str_list(behaviour.get("dns_lookups"), "hostname")[:60],
        "contacted_urls": _str_list(behaviour.get("http_conversations"), "url")[:60],
        "dropped_files": [{"name": f.get("path") or f.get("name") or "", "sha256": f.get("sha256", ""), "type": f.get("type", "")}
                          for f in (behaviour.get("files_dropped") or []) if isinstance(f, dict)][:40],
        "processes": _str_list(behaviour.get("processes_created"), "process")[:40],
        "registry_keys": _str_list(behaviour.get("registry_keys_set"), "key")[:40],
        "mutexes": _str_list(behaviour.get("mutexes_created"))[:20],
        "tags": _uniq(behaviour.get("tags") or [])[:20],
    }
    has_behaviour = any(v for k, v in behaviour_out.items() if k != "tags")

    return {
        "threat_label": ptc.get("suggested_threat_label", "") or "",
        "threat_categories": _uniq(threat_categories),
        "threat_names": _uniq(threat_names),
        "type_description": attrs.get("type_description", "") or attrs.get("type_tag", ""),
        "size": attrs.get("size"),
        "reputation": attrs.get("reputation"),
        "harmless_votes": int(votes.get("harmless") or 0),
        "malicious_votes": int(votes.get("malicious") or 0),
        "times_submitted": attrs.get("times_submitted"),
        "first_seen": _iso(attrs.get("first_submission_date")),
        "last_analysis": _iso(attrs.get("last_analysis_date")),
        "signed": bool(sig_info.get("verified") == "Signed" or sig_info.get("product")),
        "signer": sig_info.get("signers") or sig_info.get("product") or "",
        "names": _uniq(attrs.get("names") or [])[:8],
        "detections": detections[:40],
        "detection_count": len(detections),
        "yara": yara[:20],
        "sigma": sigma[:20],
        "ids": ids[:20],
        "behaviour": behaviour_out if has_behaviour else None,
    }


async def _vt_get(api_key: str, path: str) -> Optional[Dict[str, Any]]:
    """Raw VT v3 GET (hash-keyed — no upload). Returns None on 404, raises otherwise."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"https://www.virustotal.com/api/v3{path}", headers={"x-apikey": api_key})
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


async def _fetch_vt_intel(api_key: str, sha256: str) -> Dict[str, Any]:
    report = await _vt_get(api_key, f"/files/{sha256}")
    attrs = ((report or {}).get("data") or {}).get("attributes") or {}
    behaviour: Dict[str, Any] = {}
    try:
        b = await _vt_get(api_key, f"/files/{sha256}/behaviour_summary")
        behaviour = (b or {}).get("data") or {}
    except Exception as exc:  # behaviour is best-effort; a file may have none
        logger.debug(f"[reputation] VT behaviour_summary unavailable for {sha256[:16]}: {exc}")
    return _extract_intel(attrs, behaviour)


async def _attach_intel(api_key: str, rep: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Attach deep VT intel to a found reputation result (best-effort, never fatal)."""
    if not (VT_DEEP and rep and rep.get("found") and rep.get("sha256")):
        return rep
    try:
        rep["intel"] = await _fetch_vt_intel(api_key, rep["sha256"])
    except Exception as exc:
        logger.warning(f"[reputation] VT deep intel failed for {rep.get('sha256', '')[:16]}: {exc}")
    return rep


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


async def virustotal_lookup_only(sha256: str) -> Optional[Dict[str, Any]]:
    """Fast, non-blocking hash lookup (no upload). Used inline by the orchestrator."""
    logger.info(f"[reputation] VirusTotal hash lookup for {sha256[:16]} (submit_enabled={SUBMIT_FILES})")
    api_key = await _vt_api_key()
    if not api_key:
        return None
    rep = await _lookup(api_key, sha256)
    if rep and rep.get("found"):
        logger.info(f"[reputation] VirusTotal hash hit: {rep.get('malicious')}/{rep.get('total')} malicious")
        rep = await _attach_intel(api_key, rep)
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
        return await _attach_intel(api_key, final)
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
