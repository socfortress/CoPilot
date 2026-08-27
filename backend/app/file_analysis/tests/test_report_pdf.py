"""Tests for the PDF report context builder (services/report_pdf.py).

Pure: exercises build_context() and its helpers against a synthetic result — no
wkhtmltopdf, no CAPE, no MinIO. Guards the analyst-facing report shape so a future
change can't silently drop the verdict, mis-bucket signatures, or stop embedding
screenshots.
"""
from __future__ import annotations

from app.file_analysis.services.report_pdf import _dedup_connections
from app.file_analysis.services.report_pdf import _fmt_verdict
from app.file_analysis.services.report_pdf import build_context


def _result(verdict: str = "malicious") -> dict:
    return {
        "job": {
            "job_id": "J1",
            "customer_code": "00001",
            "verdict": verdict,
            "created_at": "2026-01-01T00:00:00Z",
            "hardened": True,
        },
        "inspector": {
            "filename": "evil.exe",
            "filetype": "pe",
            "magic": "PE32 executable",
            "entropy": 7.9,
            "hashes": {"md5": "m", "sha1": "s1", "sha256": "a" * 64},
            "iocs": {"urls": ["http://x/y"], "ips": [], "domains": []},
            "flags": ["packed"],
            "verdict_hint": "clean",
            "content": {
                "deobfuscated": "X" * 10000,
                "behaviors": [{"attack_id": "T1055", "technique": "Injection", "severity": "malicious", "evidence": "VirtualAlloc"}],
            },
        },
        "sandbox": {
            "task_id": 42,
            "malscore": 10.0,
            "family": "DarkGate",
            "verdict": "malicious",
            "signatures": [
                {"name": "ransomware_file_modifications", "severity": 3},
                {"name": "pe_tls_callbacks", "severity": 2, "low_confidence": True},
                {"name": "queries_user_name", "severity": 1, "noise": True},
            ],
            "connections": [{"proto": "tcp", "dst": "1.2.3.4", "dport": 443} for _ in range(3)],
            "c2_ips": ["1.2.3.4"],
            "screenshots": ["shots/0001.jpg"],
        },
        "reputation": {
            "found": True,
            "malicious": 29,
            "total": 75,
            "intel": {"detection_count": 29, "detections": [{"engine": "X", "result": "Win32/DarkGate", "category": "malicious"}]},
        },
        "verdict_reason": "sandbox: malware config extracted (DarkGate)",
    }


def test_verdict_banner_maps_to_label_and_color():
    ctx = build_context(_result("malicious"))
    assert ctx["verdict"]["label"] == "MALICIOUS"
    assert ctx["verdict"]["color"]  # non-empty
    assert ctx["verdict_reason"].startswith("sandbox:")


def test_fmt_verdict_all_states():
    assert _fmt_verdict("clean")["label"] == "CLEAN"
    assert _fmt_verdict("suspicious")["label"] == "SUSPICIOUS"
    assert _fmt_verdict("malicious")["label"] == "MALICIOUS"
    assert _fmt_verdict(None)["label"] == "UNKNOWN"


def test_signatures_split_into_meaningful_low_and_noise():
    ctx = build_context(_result())
    sigs = ctx["sandbox"]["signatures"]

    def names(group):
        return {s["name"] for s in sigs[group]}

    assert "ransomware_file_modifications" in names("meaningful")
    assert "pe_tls_callbacks" in names("low_confidence")
    assert "queries_user_name" in names("noise")
    # a low-confidence/noise signature must NOT leak into meaningful
    assert "pe_tls_callbacks" not in names("meaningful")
    assert "queries_user_name" not in names("meaningful")


def test_screenshots_are_embedded_as_data_uris():
    ctx = build_context(_result(), screenshots=[b"\xff\xd8\xfffakejpegbytes", b""])
    # one valid byte blob -> one data URI; the empty one is dropped
    assert len(ctx["screenshots"]) == 1
    assert ctx["screenshots"][0].startswith("data:image/jpeg;base64,")


def test_connections_are_deduped_with_counts():
    rows = _dedup_connections([{"proto": "tcp", "dst": "1.2.3.4", "dport": 443} for _ in range(3)])
    assert len(rows) == 1
    assert rows[0]["count"] == 3


def test_long_content_is_clipped():
    ctx = build_context(_result())
    deob = next(h for h in ctx["static"]["highlights"] if h["label"] == "Deobfuscated script")
    assert "more chars" in deob["text"]  # truncation marker present
    assert len(deob["text"]) < 10000


def test_missing_sandbox_and_reputation_are_tolerated():
    r = _result("clean")
    r["sandbox"] = None
    r["reputation"] = None
    ctx = build_context(r)
    assert ctx["sandbox"] is None
    assert ctx["reputation"] is None
    assert ctx["verdict"]["label"] == "CLEAN"
    assert ctx["file"]["hashes"]["sha256"] == "a" * 64
