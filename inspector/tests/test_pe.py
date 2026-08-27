"""PE analyzer tests — focus on graceful degradation of optional enrichment.

Regression guard for the false-positive class where a MISSING capa/floss binary
marked the whole analysis incomplete -> every .exe read "suspicious". Optional
enrichment must degrade quietly; only a failed CORE parse marks incomplete.
"""
from __future__ import annotations

from analyzers import pe
from analyzers.verdict import compute_verdict
from contract import FLAG_ANALYSIS_INCOMPLETE
from contract import InspectorResult


def test_missing_capa_and_floss_do_not_mark_incomplete(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("tool not installed")

    monkeypatch.setattr(pe.subprocess, "run", boom)
    r = InspectorResult(sha256="x", filename="app.exe", customer_code="c", filetype="pe")
    pe._capa("/whatever", r)
    pe._floss("/whatever", r)
    d = r.to_dict()
    assert d["analysis_incomplete"] is False
    assert FLAG_ANALYSIS_INCOMPLETE not in d["flags"]
    assert set(d["content"].get("enrichment_skipped", [])) == {"capa", "floss"}
    # a parsed PE with enrichment merely skipped must not read "suspicious"
    assert compute_verdict(d) == "clean"


def test_capa_timeout_degrades_gracefully(monkeypatch):
    import subprocess

    def slow(*a, **k):
        raise subprocess.TimeoutExpired(cmd="capa", timeout=1)

    monkeypatch.setattr(pe.subprocess, "run", slow)
    r = InspectorResult(sha256="x", filename="app.exe", customer_code="c", filetype="pe")
    pe._capa("/whatever", r)
    assert r.to_dict()["analysis_incomplete"] is False
