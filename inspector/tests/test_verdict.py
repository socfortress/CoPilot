"""Verdict-table tests (see CLAUDE.md -> File Analysis)."""
from __future__ import annotations

from analyzers.verdict import compute_verdict
from contract import FLAG_AUTOOPEN_MACRO
from contract import FLAG_ENCODED_POWERSHELL
from contract import InspectorResult


def _result(**kw) -> dict:
    r = InspectorResult(sha256="x", filename="f", customer_code="c")
    for key, value in kw.items():
        setattr(r, key, value)
    return r.to_dict()


def test_clean_by_default():
    assert compute_verdict(_result(filetype="unknown")) == "clean"


def test_av_hit_is_malicious():
    d = _result(filetype="pe")
    d["av"] = {"engine": "clamav", "signature": "Win.Test.EICAR"}
    assert compute_verdict(d) == "malicious"


def test_autoopen_macro_with_shell_is_malicious():
    d = _result(filetype="office", flags=[FLAG_AUTOOPEN_MACRO], content={"macros": "Sub AutoOpen()\n Shell \"x\"\nEnd Sub"})
    assert compute_verdict(d) == "malicious"


def test_single_flag_is_suspicious():
    d = _result(filetype="script", flags=[FLAG_ENCODED_POWERSHELL])
    assert compute_verdict(d) == "suspicious"


def test_extension_mismatch_on_executable_is_suspicious():
    d = _result(filetype="pe", extension_mismatch=True)
    assert compute_verdict(d) == "suspicious"


def test_incomplete_never_clean():
    d = _result(filetype="pdf", analysis_incomplete=True)
    assert compute_verdict(d) == "suspicious"


def test_pe_high_risk_is_suspicious():
    d = _result(
        filetype="pe",
        entropy=7.9,
        content={"signature_present": False, "capabilities": ["inject into process", "persist via registry run key"]},
    )
    assert compute_verdict(d) == "suspicious"
