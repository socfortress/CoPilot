"""Windows shortcut (.lnk) analyzer.

The payload of a malicious shortcut is almost always in its command-line
arguments. LnkParse3 (pure-python) extracts target/args/icon/working-dir; we flag
when the arguments invoke an interpreter with encoded or remote content.
"""
from __future__ import annotations

from analyzers import behaviors as behavior_rules
from analyzers.script import deobfuscate
from common import extract_iocs
from contract import FLAG_LNK_SUSPICIOUS_ARGS
from contract import InspectorResult

_INTERPRETERS = ("powershell", "cmd", "wscript", "cscript", "mshta", "rundll32", "regsvr32", "bitsadmin", "certutil")
_PAYLOAD_MARKERS = ("-enc", "-e ", "http://", "https://", "downloadstring", "frombase64", "invoke-", "iex", "-w hidden", "-nop")


def analyze(sample_path: str, result: InspectorResult) -> None:
    result.filetype = "lnk"
    try:
        from LnkParse3 import lnk_file
    except ImportError:
        result.mark_incomplete()
        return
    try:
        with open(sample_path, "rb") as fh:
            lnk = lnk_file(fh)
            data = lnk.get_json() if hasattr(lnk, "get_json") else {}
    except Exception:
        result.mark_incomplete()
        return

    data = data or {}
    target = _dig(data, "target") or data.get("relative_path", "")
    arguments = _dig(data, "command_line_arguments") or data.get("command_line_arguments", "")
    icon = _dig(data, "icon_location") or data.get("icon_location", "")
    workdir = _dig(data, "working_directory") or data.get("working_directory", "")

    result.content["target"] = str(target or "")
    result.content["arguments"] = str(arguments or "")
    result.content["icon_location"] = str(icon or "")
    result.content["working_dir"] = str(workdir or "")

    combined = (str(target or "") + " " + str(arguments or "")).lower()
    if any(i in combined for i in _INTERPRETERS) and any(m in combined for m in _PAYLOAD_MARKERS):
        result.add_flag(FLAG_LNK_SUSPICIOUS_ARGS)

    for kind, values in extract_iocs(str(arguments or "")).items():
        for value in values:
            result.add_ioc(kind, value)

    # ATT&CK behaviour rules over target+args and anything the args decode to
    # (LNK droppers stage an -enc PowerShell or a certutil download in the args).
    arg_str = str(target or "") + " " + str(arguments or "")
    arg_layers, _, _ = deobfuscate(arg_str)
    behavior_rules.apply(result, arg_str, *arg_layers)


def _dig(data: dict, key: str):
    """LnkParse3 nests some fields under 'data'/'header'; check both."""
    if key in data:
        return data[key]
    for parent in ("data", "header", "link_info"):
        section = data.get(parent)
        if isinstance(section, dict) and key in section:
            return section[key]
    return None
