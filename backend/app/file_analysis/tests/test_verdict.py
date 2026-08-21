"""Noise-aware sandbox verdict — pure, fixture-driven (no network, no DB).

The fixtures are the ACTUAL signature sets recorded from benign detonations on the
live CAPE box (tasks 6 & 7), plus malware-shaped inputs, so these lock in the
false-positive fix: a benign Windows run whose signatures are all environmental
noise must be CLEAN, while genuine evidence (config/C2/high-sev) stays MALICIOUS.
"""
from __future__ import annotations

from app.file_analysis.services.verdict import (
    dynamic_evidence,
    dynamic_verdict_from_report,
    explain_verdict,
    meaningful_signatures,
    noise_stats,
)

# Real task 6 (wintest.ps1 — a benign `whoami; hostname; Get-Process` script): malscore 10,
# 17 signatures, ALL environmental noise.
BENIGN_ALL_NOISE = {
    "malscore": 10.0, "family": "", "c2_ips": [], "c2_domains": [],
    "signatures": [
        {"name": "mountpoint_manager_access", "severity": 3},
        {"name": "enumerates_physical_drives", "severity": 3},
        {"name": "privilege_elevation_check", "severity": 2},
        {"name": "creates_suspended_process", "severity": 2},
        {"name": "reads_memory_remote_process", "severity": 2},
        {"name": "resumethread_remote_process", "severity": 2},
        {"name": "antivm_checks_available_memory", "severity": 1},
        {"name": "queries_locale_api", "severity": 1},
        {"name": "language_check_registry", "severity": 1},
    ],
}

# A run with some non-noise (sample-driven) signatures but nothing conclusive.
SUSPICIOUS_MEANINGFUL = {
    "malscore": 10.0, "family": "", "c2_ips": [], "c2_domains": [],
    "signatures": [
        {"name": "creates_suspended_process", "severity": 2},  # noise
        {"name": "antivm_checks_available_memory", "severity": 1},  # noise
        {"name": "modifies_boot_config", "severity": 2},  # meaningful
    ],
}

# Malware: extracted config + C2.
MALWARE_CONFIG = {"malscore": 8.0, "family": "AgentTesla", "c2_ips": ["1.2.3.4"], "c2_domains": [], "signatures": []}

# Malware: a genuinely high-severity, non-noise behavioural signature.
MALWARE_HIGHSEV = {
    "malscore": 9.0, "family": "", "c2_ips": [], "c2_domains": [],
    "signatures": [{"name": "ransomware_mass_file_encrypt", "severity": 5}],
}


def test_benign_all_noise_is_clean():
    assert dynamic_verdict_from_report(BENIGN_ALL_NOISE) == "clean"
    assert meaningful_signatures(BENIGN_ALL_NOISE) == []
    s = noise_stats(BENIGN_ALL_NOISE)
    assert s["noise"] == s["total"] == 9 and s["meaningful"] == 0
    assert "entirely environmental noise" in explain_verdict("clean", BENIGN_ALL_NOISE)


def test_meaningful_signature_is_suspicious():
    assert dynamic_verdict_from_report(SUSPICIOUS_MEANINGFUL) == "suspicious"
    assert [m["name"] for m in meaningful_signatures(SUSPICIOUS_MEANINGFUL)] == ["modifies_boot_config"]


def test_config_and_c2_is_malicious():
    assert dynamic_verdict_from_report(MALWARE_CONFIG) == "malicious"
    ev = dynamic_evidence(MALWARE_CONFIG)
    assert any("config extracted" in e for e in ev) and any("C2 endpoint" in e for e in ev)


def test_high_severity_meaningful_signature_is_malicious():
    assert dynamic_verdict_from_report(MALWARE_HIGHSEV) == "malicious"


def test_high_severity_but_NOISE_signature_does_not_convict():
    # A noise signature at high severity must NOT be treated as evidence — only
    # meaningful signatures count toward the severity check.
    noisy_highsev = {
        "malscore": 10.0, "family": "", "c2_ips": [], "c2_domains": [],
        "signatures": [{"name": "creates_suspended_process", "severity": 5}],  # noise, even at sev5
    }
    assert dynamic_evidence(noisy_highsev) == []
    assert dynamic_verdict_from_report(noisy_highsev) == "clean"


def test_empty_and_none_are_clean():
    assert dynamic_verdict_from_report({}) == "clean"
    assert dynamic_verdict_from_report(None) == "clean"
    assert dynamic_evidence(None) == []


def test_incomplete_inspection_reads_as_infra_not_content():
    # When Tier-1 could not run (inspector down/timeout), the file is failed
    # closed to a cautious verdict — but the REASON must say the inspection did
    # not complete, NOT "static inspection: suspicious" (which reads as a content
    # finding). This is the WhatsApp-photo false-positive class.
    incomplete = {"analysis_incomplete": True, "verdict_hint": "suspicious",
                  "error": "All connection attempts failed"}
    reason = explain_verdict("suspicious", None, None, incomplete)
    assert "incomplete" in reason.lower()
    assert "All connection attempts failed" in reason
    assert "not a content-based finding" in reason
    # and it must NOT masquerade as a content judgement
    assert "static inspection: suspicious" not in reason


# --- low-confidence static-PE / .NET-JIT calibration (real-world false positives) ---
# Recorded from benign detonations on the live box: a RealVNC viewer (packed, signed)
# and a .NET app (Deceive) both used to read suspicious/malicious purely from these.
BENIGN_PACKED_PE = {
    "malscore": 1.5, "family": "", "c2_ips": [], "c2_domains": [],
    "signatures": [
        {"name": "pe_cert_self_signed", "severity": 3},
        {"name": "pe_tls_callbacks", "severity": 2},
        {"name": "packer_unknown_pe_section_name", "severity": 2},
        {"name": "contains_pe_overlay", "severity": 2},
        {"name": "pe_compile_timestomping", "severity": 3},
    ],
}
BENIGN_DOTNET = {
    "malscore": 8.0, "family": "", "c2_ips": [], "c2_domains": [],
    "signatures": [
        {"name": "unbacked_privilege_escalation", "severity": 3},
        {"name": "unbacked_token_manipulation", "severity": 3},
        {"name": "unbacked_process_creation", "severity": 3},
        {"name": "injection_rwx", "severity": 2},
        {"name": "network_bind", "severity": 3},
        {"name": "static_pe_pdbpath", "severity": 2},
    ],
}


def test_packed_signed_pe_is_clean_not_suspicious():
    # Only static-PE/packer heuristics -> clean, even though there are 5 signatures.
    assert dynamic_verdict_from_report(BENIGN_PACKED_PE) == "clean"
    assert meaningful_signatures(BENIGN_PACKED_PE) == []
    s = noise_stats(BENIGN_PACKED_PE)
    assert s["low_confidence"] == 5 and s["meaningful"] == 0
    assert "static packer" in explain_verdict("clean", BENIGN_PACKED_PE)


def test_dotnet_jit_unbacked_is_clean_even_at_malscore_8():
    # Every managed .NET binary trips unbacked_* — malscore 8 must NOT convict.
    assert dynamic_verdict_from_report(BENIGN_DOTNET) == "clean"
    assert meaningful_signatures(BENIGN_DOTNET) == []


def test_low_confidence_does_not_hide_a_real_behavioural_signal():
    # Static-PE noise PLUS one genuine behavioural signature -> still suspicious.
    mixed = {
        "malscore": 5.0, "family": "", "c2_ips": [], "c2_domains": [],
        "signatures": [
            {"name": "pe_tls_callbacks", "severity": 2},          # low-confidence
            {"name": "packer_unknown_pe_section_name", "severity": 2},  # low-confidence
            {"name": "modifies_boot_config", "severity": 3},      # meaningful
        ],
    }
    assert dynamic_verdict_from_report(mixed) == "suspicious"
    assert [m["name"] for m in meaningful_signatures(mixed)] == ["modifies_boot_config"]


def test_low_confidence_at_high_severity_still_does_not_convict():
    # A low-confidence signature marked sev>=4 must NOT reach the malicious threshold.
    hs = {"malscore": 9.0, "family": "", "c2_ips": [], "c2_domains": [],
          "signatures": [{"name": "injection_rwx", "severity": 5}]}
    assert dynamic_evidence(hs) == []
    assert dynamic_verdict_from_report(hs) == "clean"
