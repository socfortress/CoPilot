"""Prowler's OCSF output, read as a stream and reduced to what CoPilot stores.

``prowler -M json-ocsf`` writes one JSON array of OCSF Detection Findings
(class 2004), each pretty-printed, separated by commas. A large account produces
hundreds of megabytes, so the array is read one finding at a time.

What leaves here:

- a summary: totals, failures by severity, and one entry per check with the check's
  metadata (title, risk, remediation, compliance mapping) and its counts;
- the FAIL and MANUAL findings, one compact object each. PASS findings are only
  counted.

What never leaves: ``resources[].data``, the resource's raw configuration as Prowler
read it. It can hold secrets (an ECS task's environment, a Lambda's variables).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from collections.abc import Iterator
from typing import Any
from typing import TextIO

from runner.textutil import clean_text
from runner.textutil import http_url
from runner.textutil import text_list

STATUSES = ("PASS", "FAIL", "MANUAL")
SEVERITIES = ("critical", "high", "medium", "low", "informational", "unknown")
STORED_STATUSES = ("FAIL", "MANUAL")

CHECK_ID = re.compile(r"^[a-z0-9][a-z0-9_]{0,127}$")
MAX_CHECKS = 5000
MAX_ACCOUNTS = 100
MAX_FRAMEWORKS = 200
MAX_REQUIREMENTS = 500

_WHITESPACE = " \t\r\n"


class OcsfError(ValueError):
    """The file isn't an OCSF array Prowler could have written."""


def iter_json_array(stream: TextIO, chunk_size: int = 1 << 20, max_item_chars: int = 32 << 20) -> Iterator[Any]:
    """Yield the items of the JSON array in `stream` one at a time.

    An empty file is an empty array: Prowler writes nothing when a scan has no findings.
    """
    decoder = json.JSONDecoder()
    buffer = ""
    position = 0
    at_end = False
    state = "start"  # start -> items -> after_item -> ... -> done

    def fill() -> bool:
        nonlocal buffer, position, at_end
        chunk = stream.read(chunk_size)
        if not chunk:
            at_end = True
            return False
        buffer = buffer[position:] + chunk
        position = 0
        return True

    while True:
        while True:
            while position < len(buffer) and buffer[position] in _WHITESPACE:
                position += 1
            if position < len(buffer) or at_end:
                break
            fill()
        if position >= len(buffer):
            if state == "start":
                return
            raise OcsfError("the array ends early")
        character = buffer[position]
        if state == "start":
            if character != "[":
                raise OcsfError("not a JSON array")
            position += 1
            state = "items"
        elif state == "after_item":
            if character == ",":
                position += 1
                state = "items"
            elif character == "]":
                position += 1
                break
            else:
                raise OcsfError("expected ',' or ']' between findings")
        else:  # items
            if character == "]":
                position += 1
                break
            while True:
                try:
                    item, end = decoder.raw_decode(buffer, position)
                    break
                except json.JSONDecodeError as error:
                    if at_end:
                        raise OcsfError("a finding is not valid JSON") from error
                    if len(buffer) - position > max_item_chars:
                        raise OcsfError("a finding is too large") from error
                    fill()
            position = end
            yield item
            state = "after_item"
    # Only whitespace may follow the closing bracket.
    while True:
        if buffer[position:].strip(_WHITESPACE):
            raise OcsfError("data after the array")
        position = len(buffer)
        if not fill():
            return


def _object(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _first_resource(item: dict) -> dict:
    resources = item.get("resources")
    if isinstance(resources, list) and resources:
        return _object(resources[0])
    return {}


def _severity(value: Any) -> str:
    text = value.lower() if isinstance(value, str) else ""
    return text if text in SEVERITIES else "unknown"


def _compliance(value: Any) -> dict[str, list[str]]:
    """framework key ("CIS-5.0") -> requirement ids, cleaned and bounded."""
    result: dict[str, list[str]] = {}
    if not isinstance(value, dict):
        return result
    for framework, requirements in value.items():
        key = clean_text(framework, 128)
        ids = text_list(requirements, 128, MAX_REQUIREMENTS)
        if key and ids and key not in result:
            result[key] = ids
            if len(result) >= MAX_FRAMEWORKS:
                break
    return result


def _urls(value: Any, max_items: int = 10) -> list[str]:
    urls: list[str] = []
    for item in value if isinstance(value, list) else []:
        url = http_url(item)
        if url and url not in urls:
            urls.append(url)
            if len(urls) >= max_items:
                break
    return urls


def normalize_finding(item: Any) -> dict | None:
    """The compact form of one OCSF finding, or None when it isn't a Prowler finding."""
    if not isinstance(item, dict):
        return None
    check_id = _object(item.get("metadata")).get("event_code")
    status = item.get("status_code")
    finding_uid = clean_text(_object(item.get("finding_info")).get("uid"), 512)
    if not isinstance(check_id, str) or not CHECK_ID.match(check_id) or status not in STATUSES or not finding_uid:
        return None
    resource = _first_resource(item)
    cloud = _object(item.get("cloud"))
    account = _object(cloud.get("account"))
    return {
        "finding_uid": finding_uid,
        "check_id": check_id,
        "status": status,
        "severity": _severity(item.get("severity")),
        # OCSF status "Suppressed" (status_id 3) is how Prowler marks a muted finding.
        "muted": item.get("status") == "Suppressed" or item.get("status_id") == 3,
        "status_extended": clean_text(item.get("status_detail"), 2000),
        "service": clean_text(_object(resource.get("group")).get("name"), 64),
        "region": clean_text(resource.get("region") or cloud.get("region"), 64),
        "cloud_account_uid": clean_text(account.get("uid"), 256),
        "cloud_account_name": clean_text(account.get("name"), 256),
        "resource_uid": clean_text(resource.get("uid"), 1024),
        "resource_name": clean_text(resource.get("name"), 512),
        "resource_type": clean_text(resource.get("type"), 128),
        # OCSF labels are "key:value" strings.
        "resource_tags": text_list(resource.get("labels"), 256, 50),
        "time": clean_text(item.get("time_dt"), 64),
    }


def check_entry(item: dict, finding: dict) -> dict:
    """A check's metadata, taken from the first of its findings, with zeroed counts."""
    info = _object(item.get("finding_info"))
    remediation = _object(item.get("remediation"))
    unmapped = _object(item.get("unmapped"))
    return {
        "check_id": finding["check_id"],
        "title": clean_text(info.get("title"), 512),
        "description": clean_text(info.get("desc"), 4000),
        "service": finding["service"],
        "severity": finding["severity"],
        "risk": clean_text(item.get("risk_details"), 4000),
        "remediation": clean_text(remediation.get("desc"), 4000),
        "references": _urls(remediation.get("references")),
        "additional_urls": _urls(unmapped.get("additional_urls")),
        "categories": text_list(unmapped.get("categories"), 64, 20),
        "types": text_list(info.get("types"), 256, 10),
        "compliance": _compliance(unmapped.get("compliance")),
        "pass": 0,
        "fail": 0,
        "manual": 0,
        "muted": 0,
    }


def normalize_stream(stream: TextIO, write_finding: Callable[[dict], None], provider: str) -> dict:
    """Read every finding in `stream`, pass FAIL and MANUAL ones to `write_finding`, and return the summary.

    Counts: ``pass``, ``fail`` and ``manual`` count findings that aren't muted; ``muted``
    counts muted findings whatever their status. ``fail_by_severity`` counts unmuted FAILs.
    """
    checks: dict[str, dict] = {}
    totals: Counter[str] = Counter()
    fail_by_severity: Counter[str] = Counter()
    accounts: list[str] = []
    skipped = 0
    prowler_version = None

    for item in iter_json_array(stream):
        finding = normalize_finding(item)
        if finding is None:
            skipped += 1
            continue
        if prowler_version is None:
            prowler_version = clean_text(_object(_object(item.get("metadata")).get("product")).get("version"), 32) or None
        check = checks.get(finding["check_id"])
        if check is None:
            if len(checks) >= MAX_CHECKS:
                skipped += 1
                continue
            check = checks[finding["check_id"]] = check_entry(item, finding)
        status = finding["status"].lower()
        totals["total"] += 1
        if finding["muted"]:
            totals["muted"] += 1
            check["muted"] += 1
        else:
            totals[status] += 1
            check[status] += 1
            if status == "fail":
                fail_by_severity[finding["severity"]] += 1
        account_uid = finding["cloud_account_uid"]
        if account_uid and account_uid not in accounts and len(accounts) < MAX_ACCOUNTS:
            accounts.append(account_uid)
        if finding["status"] in STORED_STATUSES:
            write_finding(finding)

    return {
        "provider": provider,
        # The version that wrote the findings, from their own metadata (None when there were none).
        "prowler_version": prowler_version,
        "totals": {key: totals[key] for key in ("total", "pass", "fail", "manual", "muted")},
        "fail_by_severity": {severity: fail_by_severity[severity] for severity in SEVERITIES},
        "cloud_accounts": accounts,
        "skipped": skipped,
        "checks": [checks[check_id] for check_id in sorted(checks)],
    }
