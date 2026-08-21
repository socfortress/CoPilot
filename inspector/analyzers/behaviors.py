"""Static malicious-behaviour detection for script content (PowerShell/cmd/VBS/JS).

The obfuscation/IOC passes in ``script.py`` tell us *how hidden* a script is; this
module tells us *what it tries to do*. Each rule is a high-precision regex mapped
to a MITRE ATT&CK technique, tuned to fire on attacker tradecraft that is very
rarely present in benign admin scripts. Two severities:

* ``malicious``  — almost never legitimate on its own (shadow-copy deletion,
                   credential dumping). One hit convicts.
* ``suspicious`` — attacker-favoured but occasionally admin (disable AV/firewall,
                   download-and-exec, persistence). Raises to *suspicious*.

Everything is a pure function of text so it is trivially unit-testable and runs on
the raw script AND every deobfuscated layer (so encoded payloads are covered).
Keeping this data-driven (a table, not scattered ifs) is deliberate — new
techniques are added as rows and the verdict mapping never changes.
"""
from __future__ import annotations

import re
from typing import Any
from typing import Dict
from typing import List

from contract import FLAG_MALICIOUS_BEHAVIOR
from contract import FLAG_SUSPICIOUS_BEHAVIOR

MALICIOUS = "malicious"
SUSPICIOUS = "suspicious"

# (attack_id, technique name, severity, compiled regex)
_RULES = [
    # ---- T1490 Inhibit System Recovery (ransomware hallmark) -----------------
    ("T1490", "Delete volume shadow copies", MALICIOUS,
     re.compile(r"(vssadmin(\.exe)?\s+delete\s+shadows"
                r"|wmic\s+shadowcopy\s+delete"
                r"|Win32_Shadowcopy[^\n]{0,80}\.?\s*[Dd]elete"
                r"|Get-WmiObject\s+Win32_Shadowcopy)", re.IGNORECASE)),
    ("T1490", "Resize shadow storage to evict copies", MALICIOUS,
     re.compile(r"vssadmin(\.exe)?\s+resize\s+shadowstorage", re.IGNORECASE)),
    ("T1490", "Delete backup catalog / system state", MALICIOUS,
     re.compile(r"wbadmin(\.exe)?\s+delete\s+(catalog|systemstatebackup|backup)", re.IGNORECASE)),
    ("T1490", "Disable Windows recovery / boot repair", SUSPICIOUS,
     re.compile(r"bcdedit(\.exe)?[^\n]{0,80}(recoveryenabled\s+no|bootstatuspolicy\s+ignoreallfailures)", re.IGNORECASE)),

    # ---- T1003 OS Credential Dumping ----------------------------------------
    ("T1003", "Mimikatz / LSASS credential access", MALICIOUS,
     re.compile(r"(invoke-mimikatz|sekurlsa::|lsadump::|kerberos::|privilege::debug)", re.IGNORECASE)),
    ("T1003.001", "LSASS memory dump via comsvcs/procdump", MALICIOUS,
     re.compile(r"(comsvcs\.dll[^\n]{0,40}minidump"
                r"|procdump[^\n]{0,40}lsass"
                r"|rundll32[^\n]{0,60}comsvcs[^\n]{0,40}full)", re.IGNORECASE)),

    # ---- T1562 Impair Defenses ----------------------------------------------
    ("T1562.001", "Disable Microsoft Defender", SUSPICIOUS,
     re.compile(r"(set-mppreference\s+-disable\w+"
                r"|add-mppreference\s+-exclusion"
                r"|disableantispyware|disablerealtimemonitoring"
                r"|uninstall-windowsfeature[^\n]{0,30}defender"
                r"|(sc(\.exe)?\s+(stop|config|delete)|stop-service|set-service)[^\n]{0,30}windefend)", re.IGNORECASE)),
    ("T1562.001", "Disable AMSI (script scanning bypass)", SUSPICIOUS,
     re.compile(r"(amsiInitFailed|amsiutils|amsicontext|System\.Management\.Automation\.Amsi)", re.IGNORECASE)),
    ("T1562.004", "Disable host firewall", SUSPICIOUS,
     re.compile(r"(netsh\s+advfirewall\s+set\s+\w+\s+state\s+off"
                r"|set-netfirewallprofile[^\n]{0,40}-enabled\s+false)", re.IGNORECASE)),
    ("T1562.001", "Tamper with security services", SUSPICIOUS,
     re.compile(r"(stop-service|sc(\.exe)?\s+(stop|config))[^\n]{0,30}(wuauserv|sense|wdnissvc|securityhealthservice)", re.IGNORECASE)),

    # ---- T1059.001 / T1105 Download-and-execute ------------------------------
    ("T1059.001", "PowerShell download-and-execute", SUSPICIOUS,
     re.compile(r"((new-object\s+[^\n]{0,20}net\.webclient)[^\n]{0,80}(downloadstring|downloadfile|downloaddata)"
                r"|(downloadstring|downloadfile)\([^\n]{0,120}(iex|invoke-expression)"
                r"|(iex|invoke-expression)\s*\(?\s*\(?\s*(new-object|iwr|curl|wget|invoke-webrequest|invoke-restmethod))", re.IGNORECASE)),
    ("T1105", "Ingress tool transfer via LOLBin", SUSPICIOUS,
     re.compile(r"(certutil(\.exe)?[^\n]{0,60}-urlcache[^\n]{0,60}(-split\s+)?-f"
                r"|bitsadmin(\.exe)?[^\n]{0,60}/transfer"
                r"|start-bitstransfer[^\n]{0,60}-source)", re.IGNORECASE)),

    # ---- T1218 System Binary Proxy Execution (LOLBins) -----------------------
    ("T1218.005", "mshta remote/inline script execution", SUSPICIOUS,
     re.compile(r"mshta(\.exe)?\s+(https?://|javascript:|vbscript:)", re.IGNORECASE)),
    ("T1218.010", "regsvr32 scriptlet execution (Squiblydoo)", SUSPICIOUS,
     re.compile(r"regsvr32(\.exe)?[^\n]{0,60}(/i:https?://|scrobj\.dll)", re.IGNORECASE)),
    ("T1218.011", "rundll32 inline script execution", SUSPICIOUS,
     re.compile(r"rundll32(\.exe)?[^\n]{0,40}(javascript:|vbscript:|mshtml)", re.IGNORECASE)),

    # ---- T1547.001 / T1053 Persistence --------------------------------------
    ("T1547.001", "Registry Run-key persistence", SUSPICIOUS,
     re.compile(r"((reg(\.exe)?\s+add|new-itemproperty|set-itemproperty)[^\n]{0,120}"
                r"(currentversion\\run|\\runonce))", re.IGNORECASE)),
    ("T1053.005", "Scheduled-task persistence", SUSPICIOUS,
     re.compile(r"(schtasks(\.exe)?\s+/create|register-scheduledtask|new-scheduledtask(action|trigger)?)", re.IGNORECASE)),
    ("T1543.003", "Create/modify Windows service", SUSPICIOUS,
     re.compile(r"(new-service\s+-name|sc(\.exe)?\s+create\s+\w+[^\n]{0,60}binpath)", re.IGNORECASE)),

    # ---- T1548 Privilege escalation / UAC bypass -----------------------------
    ("T1548.002", "Known UAC-bypass helper", SUSPICIOUS,
     re.compile(r"(fodhelper|eventvwr|computerdefaults|sdclt)(\.exe)?[^\n]{0,40}(ms-settings|delegateexecute|shell\\open)", re.IGNORECASE)),

    # ---- T1055 Process Injection (shellcode primitives) ----------------------
    ("T1055", "In-memory shellcode injection primitives", MALICIOUS,
     re.compile(r"virtualalloc\w*[^\n]{0,200}(writeprocessmemory|memcpy|copy)[^\n]{0,200}(createremotethread|createthread|queueuserapc)", re.IGNORECASE | re.DOTALL)),
    ("T1620", "Reflective .NET assembly load from bytes", SUSPICIOUS,
     re.compile(r"\[reflection\.assembly\]::load\(\s*\[?\s*(byte\[\]|convert::frombase64)", re.IGNORECASE)),

    # ---- T1070.001 Indicator Removal: clear logs -----------------------------
    ("T1070.001", "Clear Windows event logs", SUSPICIOUS,
     re.compile(r"(wevtutil(\.exe)?\s+(cl|clear-log)|clear-eventlog|remove-eventlog)", re.IGNORECASE)),

    # ---- T1140 Deobfuscate/Decode (dropper staging) --------------------------
    ("T1140", "Decode staged payload via certutil", SUSPICIOUS,
     re.compile(r"certutil(\.exe)?[^\n]{0,40}-decode(hex)?", re.IGNORECASE)),

    # ---- T1136.001 / T1098 Account creation & privilege --------------------
    ("T1136.001", "Create local account", SUSPICIOUS,
     re.compile(r"(net(\.exe)?\s+user\s+\S+\s+\S+\s+/add|new-localuser\s)", re.IGNORECASE)),
    ("T1098", "Add account to Administrators group", SUSPICIOUS,
     re.compile(r"(net(\.exe)?\s+localgroup\s+administrators[^\n]{0,40}/add"
                r"|add-localgroupmember[^\n]{0,40}administrators)", re.IGNORECASE)),

    # ---- T1021.002 Remote/lateral execution ----------------------------------
    ("T1021.002", "Remote execution (PsExec/WinRS/Invoke-Command)", SUSPICIOUS,
     re.compile(r"(psexec(\.exe)?\s+\\\\|winrs(\.exe)?\s+-r:|invoke-command\s+-computername)", re.IGNORECASE)),

    # ---- T1047 WMI process creation ------------------------------------------
    ("T1047", "WMI process creation", SUSPICIOUS,
     re.compile(r"(wmic(\.exe)?[^\n]{0,30}process\s+call\s+create"
                r"|invoke-wmimethod[^\n]{0,40}win32_process"
                r"|Win32_Process[^\n]{0,20}\.?\s*Create\()", re.IGNORECASE)),

    # ---- T1059.005 WSH / macro download-and-run (Office & HTA coverage) ------
    ("T1059.005", "WScript.Shell / URLDownloadToFile execution", SUSPICIOUS,
     re.compile(r"(urldownloadtofile"
                r"|createobject\(\s*['\"]wscript\.shell['\"]\s*\)[^\n]{0,120}\.(run|exec)"
                r"|\.(run|exec)\s*\(?\s*['\"]?[^\n'\"]{0,40}(powershell|cmd(\.exe)?\s|mshta|https?://))", re.IGNORECASE)),
    ("T1059.005", "VBA Shell() to interpreter", SUSPICIOUS,
     re.compile(r"\bshell\s*\(?\s*['\"][^'\"\n]{0,40}(powershell|cmd(\.exe)?\s|mshta|cscript|wscript|regsvr32)", re.IGNORECASE)),

    # ---- T1548.002 / T1562 Weaken UAC / SmartScreen --------------------------
    ("T1548.002", "Disable UAC via registry (EnableLUA=0)", SUSPICIOUS,
     re.compile(r"enablelua[^\n]{0,30}(/d\s+0\b|-value\s+0\b|=\s*0\b)", re.IGNORECASE)),
    ("T1562.001", "Disable SmartScreen", SUSPICIOUS,
     re.compile(r"(smartscreen[^\n]{0,25}(\boff\b|disabled|/d\s+0\b)|disable\w*[^\n]{0,10}smartscreen)", re.IGNORECASE)),
]


def scan(*texts: str) -> List[Dict[str, Any]]:
    """Return the distinct behaviours matched across all given text layers.

    De-duplicated on (attack_id, name); ``evidence`` is a short snippet of the
    first match so an analyst sees exactly what triggered it.
    """
    seen = set()
    out: List[Dict[str, Any]] = []
    for attack_id, name, severity, rx in _RULES:
        for text in texts:
            if not text:
                continue
            m = rx.search(text)
            if not m:
                continue
            key = (attack_id, name)
            if key in seen:
                break
            seen.add(key)
            snippet = m.group(0)
            snippet = re.sub(r"\s+", " ", snippet).strip()[:120]
            out.append({
                "attack_id": attack_id,
                "technique": name,
                "severity": severity,
                "evidence": snippet,
            })
            break
    return out


def worst_severity(behaviors: List[Dict[str, Any]]) -> str:
    """'malicious' if any malicious behaviour, else 'suspicious' if any, else ''."""
    sevs = {b.get("severity") for b in behaviors}
    if MALICIOUS in sevs:
        return MALICIOUS
    if SUSPICIOUS in sevs:
        return SUSPICIOUS
    return ""


def apply(result, *texts: str) -> List[Dict[str, Any]]:
    """Scan ``texts``, merge matches into ``result.content['behaviors']`` and raise
    the appropriate behaviour flag. Reusable by every analyzer that extracts a
    command surface (script bodies, VBA macros, LNK args, HTA/HTML scripts, PE
    strings) so the same ATT&CK ruleset applies across file types. Idempotent and
    additive — safe to call more than once per result. Returns the new matches.
    """
    matched = scan(*texts)
    if not matched:
        return matched
    existing = result.content.get("behaviors") or []
    seen = {(b["attack_id"], b["technique"]) for b in existing}
    for b in matched:
        key = (b["attack_id"], b["technique"])
        if key not in seen:
            existing.append(b)
            seen.add(key)
    result.content["behaviors"] = existing
    worst = worst_severity(existing)
    if worst == MALICIOUS:
        result.add_flag(FLAG_MALICIOUS_BEHAVIOR)
    elif worst == SUSPICIOUS:
        result.add_flag(FLAG_SUSPICIOUS_BEHAVIOR)
    return matched
