"""Analyst PDF report for a File Analysis result.

Renders the full two-tier analysis — file identity, verdict, static (Tier 1)
findings, reputation, and detonation (Tier 2) behaviour — into a shareable PDF.
Follows CoPilot's existing report convention (Jinja2 -> wkhtmltopdf via pdfkit):
we reuse the generic helpers from ``incidents.services.reports_pdf`` rather than
forking the HTML->PDF plumbing.

Security: the report embeds attacker-controlled strings (filenames, script
bodies, IOCs, CAPE signatures). ``render_html_template`` renders with autoescape
ON and a sandboxed environment, so nothing in the context can inject markup or
reach Python internals. Screenshots are embedded as base64 ``data:`` URIs so the
renderer never touches the local filesystem (``disable-local-file-access`` stays
on in the shared converter).
"""
from __future__ import annotations

import base64
import os
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi.responses import FileResponse

from app.file_analysis.services.verdict import is_low_confidence_signature
from app.file_analysis.services.verdict import is_noise_signature
from app.incidents.services.reports_pdf import convert_html_to_pdf
from app.incidents.services.reports_pdf import create_file_response_pdf
from app.incidents.services.reports_pdf import render_html_template

_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "report.html")

# Keep the PDF readable: cap the long free-text / list fields.
_MAX_SNIPPET = 6000
_MAX_LIST = 200
_MAX_STRINGS = 120


def _clip(text: Any, limit: int = _MAX_SNIPPET) -> str:
    s = "" if text is None else str(text)
    if len(s) > limit:
        return s[:limit] + f"\n… (+{len(s) - limit} more chars, see raw report)"
    return s


def _fmt_verdict(v: Optional[str]) -> Dict[str, str]:
    v = (v or "").lower()
    table = {
        "malicious": {"label": "MALICIOUS", "color": "#dc2626", "bg": "#fef2f2", "dark": "#7f1d1d", "soft": "#fecaca"},
        "suspicious": {"label": "SUSPICIOUS", "color": "#d97706", "bg": "#fffbeb", "dark": "#78350f", "soft": "#fde68a"},
        "clean": {"label": "CLEAN", "color": "#16a34a", "bg": "#f0fdf4", "dark": "#14532d", "soft": "#bbf7d0"},
    }
    return table.get(
        v,
        {"label": (v or "UNKNOWN").upper(), "color": "#64748b", "bg": "#f1f5f9", "dark": "#334155", "soft": "#cbd5e1"},
    )


def _dedup_connections(conns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse the connection flood into proto+dst:port rows with a count."""
    seen: Dict[str, Dict[str, Any]] = {}
    for c in conns or []:
        proto = (c.get("proto") or "").lower()
        dst = c.get("dst") or ""
        dport = c.get("dport")
        key = f"{proto}|{dst}|{dport}"
        row = seen.get(key)
        if row:
            row["count"] += 1
        else:
            seen[key] = {"proto": proto, "dst": dst, "dport": dport, "count": 1}
    return sorted(seen.values(), key=lambda r: -r["count"])[:_MAX_LIST]


def _split_signatures(sigs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Meaningful vs low-confidence vs monitor-noise — same split as the UI/verdict."""
    meaningful: List[Dict[str, Any]] = []
    low: List[Dict[str, Any]] = []
    noise: List[Dict[str, Any]] = []
    for s in sigs or []:
        name = s.get("name", "")
        row = {
            "name": name,
            "description": s.get("description") or "",
            "severity": s.get("severity"),
            "mitre": ", ".join(s.get("mitre") or []),
        }
        if s.get("noise") or is_noise_signature(name):
            noise.append(row)
        elif s.get("low_confidence") or is_low_confidence_signature(name):
            low.append(row)
        else:
            meaningful.append(row)

    def keyf(r):
        return -(r.get("severity") or 0)

    return {
        "meaningful": sorted(meaningful, key=keyf),
        "low_confidence": sorted(low, key=keyf),
        "noise": sorted(noise, key=keyf),
    }


def _static_section(inspector: Dict[str, Any]) -> Dict[str, Any]:
    content = inspector.get("content") or {}
    iocs = inspector.get("iocs") or {}
    behaviors = content.get("behaviors") or []
    highlights: List[Dict[str, str]] = []
    for label, key in (
        ("Deobfuscated script", "deobfuscated"),
        ("Extracted macros (VBA)", "macros"),
        ("Embedded JavaScript", "javascript"),
        ("DDE command", "dde"),
        ("LNK target", "target"),
        ("LNK arguments", "arguments"),
    ):
        val = content.get(key)
        if val:
            highlights.append({"label": label, "text": _clip(val)})
    return {
        "filetype": inspector.get("filetype"),
        "magic": inspector.get("magic"),
        "entropy": inspector.get("entropy"),
        "extension_mismatch": inspector.get("extension_mismatch"),
        "analysis_incomplete": inspector.get("analysis_incomplete"),
        "verdict_hint": inspector.get("verdict_hint"),
        "flags": inspector.get("flags") or [],
        "av": inspector.get("av") or None,
        "iocs": {
            "urls": (iocs.get("urls") or [])[:_MAX_LIST],
            "ips": (iocs.get("ips") or [])[:_MAX_LIST],
            "domains": (iocs.get("domains") or [])[:_MAX_LIST],
        },
        "behaviors": [
            {
                "attack_id": b.get("attack_id"),
                "technique": b.get("technique"),
                "severity": b.get("severity"),
                "evidence": _clip(b.get("evidence"), 300),
            }
            for b in behaviors
        ],
        "highlights": highlights,
        "autoexec_keywords": (content.get("autoexec_keywords") or [])[:_MAX_LIST],
        "suspicious_keywords": (content.get("suspicious_keywords") or [])[:_MAX_LIST],
        "capabilities": (content.get("capabilities") or [])[:_MAX_LIST],
        "imports": (content.get("imports") or [])[:_MAX_LIST],
        "import_count": content.get("import_count"),
        "sections": content.get("sections") or [],
        "strings": (content.get("strings") or [])[:_MAX_STRINGS],
        "pdf_metadata": content.get("pdf_metadata") or {},
    }


def _sandbox_section(sandbox: Dict[str, Any]) -> Dict[str, Any]:
    behavior = sandbox.get("behavior") or {}
    behavior_view = {k: (v or [])[:_MAX_LIST] for k, v in behavior.items() if v}
    return {
        "task_id": sandbox.get("task_id"),
        "malscore": sandbox.get("malscore"),
        "family": sandbox.get("family"),
        "verdict": sandbox.get("verdict"),
        "machine": sandbox.get("machine"),
        "duration": sandbox.get("duration"),
        "package": sandbox.get("package"),
        "signatures": _split_signatures(sandbox.get("signatures") or []),
        "c2_ips": sandbox.get("c2_ips") or [],
        "c2_domains": sandbox.get("c2_domains") or [],
        "hosts": (sandbox.get("hosts") or [])[:_MAX_LIST],
        "domains": (sandbox.get("domains") or [])[:_MAX_LIST],
        "dead_hosts": sandbox.get("dead_hosts") or [],
        "dns": (sandbox.get("dns") or [])[:_MAX_LIST],
        "http": (sandbox.get("http") or [])[:_MAX_LIST],
        "connections": _dedup_connections(sandbox.get("connections") or []),
        "processes": (sandbox.get("processes") or [])[:_MAX_LIST],
        "dropped": (sandbox.get("dropped") or [])[:_MAX_LIST],
        "ttps": (sandbox.get("ttps") or [])[:_MAX_LIST],
        "behavior": behavior_view,
        "errors": sandbox.get("errors") or [],
    }


def _reputation_section(rep: Dict[str, Any]) -> Dict[str, Any]:
    intel = rep.get("intel") or {}
    return {
        "skipped": rep.get("skipped"),
        "found": rep.get("found"),
        "malicious": rep.get("malicious"),
        "suspicious": rep.get("suspicious"),
        "total": rep.get("total"),
        "family": rep.get("family"),
        "meaningful_name": rep.get("meaningful_name"),
        "permalink": rep.get("permalink"),
        "submitted": rep.get("submitted"),
        "note": rep.get("note"),
        "threat_label": intel.get("threat_label"),
        "threat_names": (intel.get("threat_names") or [])[:_MAX_LIST],
        "type_description": intel.get("type_description"),
        "reputation": intel.get("reputation"),
        "first_seen": intel.get("first_seen"),
        "last_analysis": intel.get("last_analysis"),
        "signed": intel.get("signed"),
        "signer": intel.get("signer"),
        "detection_count": intel.get("detection_count"),
        "detections": (intel.get("detections") or [])[:_MAX_LIST],
        "yara": (intel.get("yara") or [])[:_MAX_LIST],
        "sigma": (intel.get("sigma") or [])[:_MAX_LIST],
    }


def build_context(
    result: Dict[str, Any],
    generated_at: Optional[str] = None,
    screenshots: Optional[List[bytes]] = None,
) -> Dict[str, Any]:
    """Shape a stored analysis result into the template context.

    ``screenshots`` are raw image bytes (fetched from the sandbox); they are
    embedded as base64 ``data:`` URIs so the renderer needs no filesystem access.
    """
    job = result.get("job") or {}
    inspector = result.get("inspector") or {}
    sandbox = result.get("sandbox") or None
    reputation = result.get("reputation") or None
    hashes = inspector.get("hashes") or {}

    shots: List[str] = []
    for raw in (screenshots or [])[:_MAX_LIST]:
        if raw:
            shots.append("data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii"))

    return {
        "generated_at": generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "job": {
            "job_id": job.get("job_id"),
            "customer_code": job.get("customer_code"),
            "source": job.get("source"),
            "created_at": job.get("created_at"),
            "hardened": job.get("hardened"),
            "sandbox_enabled": job.get("sandbox_enabled"),
        },
        "verdict": _fmt_verdict(job.get("verdict") or inspector.get("verdict_hint")),
        "verdict_reason": result.get("verdict_reason"),
        "engine_version": result.get("engine_version"),
        "file": {
            "name": inspector.get("filename") or job.get("filename"),
            "hashes": {
                "md5": hashes.get("md5"),
                "sha1": hashes.get("sha1"),
                "sha256": hashes.get("sha256") or job.get("sha256"),
                "imphash": hashes.get("imphash"),
            },
        },
        "static": _static_section(inspector),
        "reputation": _reputation_section(reputation) if reputation else None,
        "sandbox": _sandbox_section(sandbox) if sandbox else None,
        "screenshots": shots,
    }


def generate_report_pdf(
    result: Dict[str, Any],
    screenshots: Optional[List[bytes]] = None,
    generated_at: Optional[str] = None,
) -> FileResponse:
    """Render the analyst PDF and return it as a downloadable FileResponse."""
    context = build_context(result, generated_at=generated_at, screenshots=screenshots)
    html_path = render_html_template(os.path.abspath(_TEMPLATE_PATH), context)
    pdf_path = convert_html_to_pdf(
        html_path,
        extra_options={
            "footer-right": "[page]/[topage]",
            "footer-font-size": "7",
            "footer-spacing": "4",
            "margin-top": "14mm",
            "margin-bottom": "16mm",
            "encoding": "UTF-8",
        },
    )
    sha = (result.get("inspector") or {}).get("sha256") or (result.get("job") or {}).get("sha256") or "report"
    return create_file_response_pdf(pdf_path, file_name=f"file-analysis-{sha[:12]}.pdf")
