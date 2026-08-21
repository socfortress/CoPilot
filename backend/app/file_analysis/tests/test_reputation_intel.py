"""VirusTotal deep-intel extraction — pure, fixture-driven (no network, no DB).

Asserts _extract_intel turns a raw VT v3 report + behaviour_summary into the
SOC-useful shape the UI renders, and degrades safely on clean/empty/None input.
"""
from __future__ import annotations

from app.file_analysis.services.reputation import _extract_intel

_ATTRS = {
    "popular_threat_classification": {
        "suggested_threat_label": "trojan.emotet/heur",
        "popular_threat_category": [{"value": "trojan"}, {"value": "banker"}],
        "popular_threat_name": [{"value": "emotet"}, {"value": "heur"}],
    },
    "last_analysis_results": {
        "Microsoft": {"category": "malicious", "result": "Trojan:Win32/Emotet", "engine_name": "Microsoft"},
        "Kaspersky": {"category": "malicious", "result": "Trojan-Banker.Win32.Emotet", "engine_name": "Kaspersky"},
        "SomeAV": {"category": "suspicious", "result": "heuristic.hit", "engine_name": "SomeAV"},
        "CleanAV": {"category": "undetected", "result": None, "engine_name": "CleanAV"},
        "Unsupported": {"category": "type-unsupported", "result": None, "engine_name": "X"},
    },
    "crowdsourced_yara_results": [{"rule_name": "Emotet_Loader", "author": "researcher", "description": "Detects Emotet", "ruleset_name": "malware_rules"}],
    "sigma_analysis_results": [{"rule_title": "Suspicious PowerShell", "rule_level": "high", "rule_source": "Sigma Community"}],
    "crowdsourced_ids_results": [{"rule_msg": "ET MALWARE Emotet CnC", "alert_severity": "high", "rule_category": "malware", "rule_source": "Proofpoint ET"}],
    "total_votes": {"harmless": 2, "malicious": 40},
    "signature_info": {"verified": "Signed", "product": "FakeSigner", "signers": "Evil Corp"},
    "reputation": -55,
    "times_submitted": 1234,
    "first_submission_date": 1500000000,  # 2017-07-14 UTC
    "last_analysis_date": 1600000000,
    "type_description": "Win32 EXE",
    "size": 204800,
    "names": ["invoice.exe", "x.exe", "invoice.exe"],
}

_BEHAVIOUR = {
    "mitre_attack_techniques": [{"id": "T1055", "signature_description": "Process Injection", "severity": "IMPACT_SEVERITY_HIGH"}],
    "ip_traffic": [{"destination_ip": "1.2.3.4", "destination_port": 443}, {"destination_ip": "1.2.3.4"}],
    "dns_lookups": [{"hostname": "evil.example.com", "resolved_ips": ["1.2.3.4"]}],
    "http_conversations": [{"url": "http://evil.example.com/gate.php", "request_method": "POST"}],
    "files_dropped": [{"path": "C:\\Temp\\payload.dll", "sha256": "abcd", "type": "PE"}],
    "processes_created": ["cmd.exe /c whoami", "powershell -enc AAAA"],
    "registry_keys_set": [{"key": "HKCU\\Software\\Run\\evil", "value": "x"}],
    "mutexes_created": ["Global\\EvilMutex"],
    "tags": ["persistence", "injection"],
}


def test_extract_intel_full():
    intel = _extract_intel(_ATTRS, _BEHAVIOUR)
    assert intel["threat_label"] == "trojan.emotet/heur"
    assert intel["threat_categories"] == ["trojan", "banker"]

    engines = [d["engine"] for d in intel["detections"]]
    assert engines[:2] == ["Kaspersky", "Microsoft"]  # malicious first, alpha by engine
    assert "SomeAV" in engines  # suspicious kept
    assert "CleanAV" not in engines and "X" not in engines  # undetected / type-unsupported dropped
    assert intel["detection_count"] == 3

    assert intel["yara"][0]["rule"] == "Emotet_Loader"
    assert intel["sigma"][0]["level"] == "high"
    assert intel["ids"][0]["msg"].startswith("ET MALWARE")
    assert intel["malicious_votes"] == 40 and intel["harmless_votes"] == 2
    assert intel["reputation"] == -55
    assert intel["first_seen"].startswith("2017-")
    assert intel["names"] == ["invoice.exe", "x.exe"]  # deduped, capped

    b = intel["behaviour"]
    assert b is not None
    assert b["mitre"][0]["id"] == "T1055"
    assert b["contacted_ips"] == ["1.2.3.4"]  # deduped
    assert b["contacted_domains"] == ["evil.example.com"]
    assert b["contacted_urls"] == ["http://evil.example.com/gate.php"]
    assert b["dropped_files"][0]["name"].endswith("payload.dll")
    assert "cmd.exe /c whoami" in b["processes"]


def test_extract_intel_clean_file_has_no_behaviour():
    intel = _extract_intel({"last_analysis_results": {"AV": {"category": "undetected", "result": None}}}, {})
    assert intel["threat_label"] == ""
    assert intel["detections"] == []
    assert intel["detection_count"] == 0
    assert intel["behaviour"] is None  # nothing behavioural -> section hidden in UI


def test_extract_intel_handles_none():
    intel = _extract_intel(None, None)
    assert intel["detections"] == []
    assert intel["behaviour"] is None
    assert intel["threat_categories"] == []
