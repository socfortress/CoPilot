"""The ``ops_finding`` block of ``copilot.notification.v1``: a Talon ops finding as data (talon-analyst
SPEC §5.7 "Notifications", D96; plan OJ-5).

talon-analyst's ops jobs (endpoints gone quiet, log sources gone silent) write findings; CoPilot's
``invoke_talon_ops_notifications`` job polls them and emits one ``talon_ops_finding`` event per finding
and severity, to **internal routes only** (``INTERNAL_TRIGGERS``: the SOC's, never a customer's). The
event carries this block in ``context.ops_finding``; the webhook's structured payload carries it as
``ops_finding`` (with ``ai_report`` null), and templates read ``context.ops_finding``.

**A snapshot.** Unlike ``ai_report``, the block is built when the poller emits the event and stored on
the outbox row with it: it is the finding as it was when it was notified. The Ops page shows it as it
is now (``ops_url``).

**Code's fields and a model's.** ``job``, ``kind``, ``severity``, ``title``, ``customer_code``,
``status``, the times, ``evidence_summary`` and ``artifact`` are code's (talon-analyst's job, then
CoPilot). ``why`` and ``recommendation`` are a model's explanation (``recommendation`` is the job's
fixed hint when ``explained`` is false): **untrusted plain text**. The default message body never
includes them; an HTML template escapes them (autoescape), a Markdown template gets them with every
Markdown character escaped (``markdown_escaped``), and a webhook receiver must treat them as text.

**v1 is append-only.** Fields may be added; none removed, renamed or retyped. ``docs/user/notifications.md``
("The `ops_finding` block") is the receivers' reference: keep it in step with ``build_ops_finding_v1``.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional

from app.notifications.schema.notifications import NotificationSeverity

#: talon-analyst's severities (``info``/``low``/``medium``/``high``) as CoPilot's, so a route's
#: ``min_severity`` applies. An ops finding is never Critical.
OPS_SEVERITY: Dict[str, NotificationSeverity] = {
    "info": NotificationSeverity.INFORMATIONAL,
    "low": NotificationSeverity.LOW,
    "medium": NotificationSeverity.MEDIUM,
    "high": NotificationSeverity.HIGH,
}

TRUNCATION_MARK = "…"
MAX_TITLE_CHARS = 500
MAX_LABEL_CHARS = 64
MAX_EVIDENCE_SUMMARY_CHARS = 1000
MAX_WHY_CHARS = 1000
MAX_RECOMMENDATION_CHARS = 1500
MAX_ARTIFACT_BODY_CHARS = 8000
MAX_URL_CHARS = 512
#: Evidence fields named in the summary, at most.
MAX_SUMMARY_FIELDS = 12
MAX_SUMMARY_VALUE_CHARS = 80
#: The block's bound, measured like the ``ai_report`` block's (``json.dumps`` defaults).
MAX_OPS_FINDING_V1_BYTES = 16 * 1024

#: The fields ``enforce_size`` shortens, longest first, then empties, if the block is over its bound.
_SHRINKABLE = ("artifact.body", "recommendation", "why", "evidence_summary", "title")


def _cap(value: Any, limit: int) -> tuple:
    if value is None:
        return (None, False)
    text = str(value)
    if len(text) <= limit:
        return (text, False)
    return (text[: max(0, limit - len(TRUNCATION_MARK))] + TRUNCATION_MARK, True)


def _iso_utc(value: Any) -> Optional[str]:
    """ISO 8601 in UTC with a ``Z``; a string is parsed first. Anything unreadable is None."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=0).isoformat() + "Z"


def _summary_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        text = " ".join(value.split())
        return _cap(text, MAX_SUMMARY_VALUE_CHARS)[0] if text else None
    if isinstance(value, list) and all(isinstance(v, (str, int, float)) and not isinstance(v, bool) for v in value):
        return _cap(", ".join(str(v) for v in value), MAX_SUMMARY_VALUE_CHARS)[0] if value else None
    return None


def evidence_summary(evidence: Any) -> Optional[str]:
    """One line built in code from the evidence's simple fields, in their order: ``key: value; …``.
    Nested objects, lists of objects and nulls are left out; at most ``MAX_SUMMARY_FIELDS`` fields."""
    if not isinstance(evidence, Mapping):
        return None
    parts: List[str] = []
    for key, value in evidence.items():
        text = _summary_value(value)
        if text is None or not isinstance(key, str):
            continue
        parts.append(f"{key}: {text}")
        if len(parts) >= MAX_SUMMARY_FIELDS:
            break
    return _cap("; ".join(parts), MAX_EVIDENCE_SUMMARY_CHARS)[0] if parts else None


def serialized_size(block: Optional[Dict[str, Any]]) -> int:
    return len(json.dumps(block).encode("utf-8"))


def ops_finding_v1_json(block: Optional[Dict[str, Any]]) -> str:
    """Compact, ASCII-only JSON of the block (``null`` for none): ``context.ops_finding_json``."""
    return json.dumps(block, separators=(",", ":"))


def build_ops_finding_v1(finding: Any, *, ops_url: Optional[str]) -> Dict[str, Any]:
    """The block from a finding CoPilot already parsed and checked (``TalonOpsFinding`` or a mapping
    with its fields). Pure: no I/O."""

    def get(name: str) -> Any:
        return finding.get(name) if isinstance(finding, Mapping) else getattr(finding, name, None)

    truncated: List[str] = []

    def capped(name: str, value: Any, limit: int) -> Optional[str]:
        text, cut = _cap(value, limit)
        if cut:
            truncated.append(name)
        return text

    artifact = get("artifact")
    artifact_type = artifact.get("type") if isinstance(artifact, Mapping) else getattr(artifact, "type", None)
    artifact_body = artifact.get("body") if isinstance(artifact, Mapping) else getattr(artifact, "body", None)
    block: Dict[str, Any] = {
        "id": get("id"),
        "job": capped("job", get("job"), MAX_LABEL_CHARS),
        "kind": capped("kind", get("kind"), MAX_LABEL_CHARS),
        "severity": get("severity"),
        "title": capped("title", get("title"), MAX_TITLE_CHARS),
        "customer_code": get("customer_code"),
        "evidence_summary": capped("evidence_summary", evidence_summary(get("evidence")), MAX_EVIDENCE_SUMMARY_CHARS),
        "why": capped("why", get("why") or None, MAX_WHY_CHARS),
        "recommendation": capped("recommendation", get("recommendation") or None, MAX_RECOMMENDATION_CHARS),
        "explained": bool(get("explained")),
        "artifact": (
            {
                "type": capped("artifact.type", artifact_type, MAX_LABEL_CHARS),
                "body": capped("artifact.body", artifact_body, MAX_ARTIFACT_BODY_CHARS),
            }
            if artifact_type and artifact_body
            else None
        ),
        "status": get("status"),
        "first_seen": _iso_utc(get("first_seen")),
        "last_seen": _iso_utc(get("last_seen")),
        "ops_url": capped("ops_url", ops_url or None, MAX_URL_CHARS),
        "truncated_fields": truncated,
    }
    return enforce_size(block)


def _field(block: Dict[str, Any], path: str) -> tuple:
    target = block
    parts = path.split(".")
    for key in parts[:-1]:
        target = target.get(key) if isinstance(target, dict) else None
        if target is None:
            return (None, parts[-1])
    return (target, parts[-1])


def enforce_size(block: Dict[str, Any], limit: int = MAX_OPS_FINDING_V1_BYTES) -> Dict[str, Any]:
    """Bring the block under ``limit`` bytes: the long texts are halved, longest first, then emptied.
    Every cut is named in ``truncated_fields``; the bound always holds on return."""
    while serialized_size(block) > limit:
        candidates = []
        for path in _SHRINKABLE:
            target, key = _field(block, path)
            if target is not None and target.get(key):
                candidates.append((len(target[key]), path, target, key))
        if not candidates:
            raise AssertionError(f"ops_finding block is {serialized_size(block)} bytes, over {limit}")
        _, path, target, key = max(candidates, key=lambda c: c[0])
        text = target[key]
        target[key] = _cap(text, len(text) // 2)[0] if len(text) > 16 else None
        if path not in block["truncated_fields"]:
            block["truncated_fields"].append(path)
    return block


#: Markdown's special characters (CommonMark's ASCII punctuation that can start or end markup).
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()<>#+\-.!|~>])")


def escape_markdown(text: Optional[str]) -> Optional[str]:
    """``text`` with every Markdown character backslash-escaped, so a Markdown renderer shows it as
    written (no link, image, emphasis or heading the model wrote can render)."""
    if text is None:
        return None
    return _MARKDOWN_SPECIAL.sub(r"\\\1", text)


def markdown_escaped(block: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """A copy of the block for a Markdown template: the model's ``why`` and ``recommendation`` escaped."""
    if not block:
        return block
    copy = json.loads(json.dumps(block))
    copy["why"] = escape_markdown(copy.get("why"))
    copy["recommendation"] = escape_markdown(copy.get("recommendation"))
    return copy


def sample_ops_finding_v1() -> Dict[str, Any]:
    """A synthetic block for the template editor's preview and a test send: a real one's shape, built
    by the same code, with made-up values."""
    return build_ops_finding_v1(
        {
            "id": 1207,
            "job": "quiet_endpoints",
            "kind": "wazuh_quiet",
            "severity": "medium",
            "title": "WKSTN-014: not seen by Wazuh for 5 days",
            "customer_code": "ACME",
            "evidence": {
                "agent_id": "017",
                "agent_name": "WKSTN-014",
                "os": "Windows 11",
                "critical_asset": False,
                "wazuh_last_seen": "2026-10-19T08:12:00+00:00",
                "wazuh_days_quiet": 5.1,
                "conditions": ["wazuh_quiet"],
            },
            "why": "One workstation stopped reporting to Wazuh while Velociraptor still saw it until the same day.",
            "recommendation": "Check the Wazuh agent service on WKSTN-014, then its network path to the manager.",
            "explained": True,
            "artifact": None,
            "status": "open",
            "first_seen": "2026-10-22T06:00:00+00:00",
            "last_seen": "2026-10-24T06:00:00+00:00",
        },
        ops_url="https://copilot.example.com/ai-analyst?tab=ops&finding=1207",
    )
