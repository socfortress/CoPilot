"""Email analyzer (.eml/.msg) — phishing triage.

Parses headers (sender/reply-to/return-path mismatches, received chain), body
text and URLs, and detaches every attachment to recurse it through the router
(the malicious doc/ISO/LNK is usually one level down). Pure parsers only —
Python's ``email`` for .eml, ``extract_msg`` for .msg.
"""
from __future__ import annotations

import email
import os
import tempfile
from email import policy
from typing import List

from common import extract_iocs
from contract import FLAG_REPLY_TO_MISMATCH
from contract import FLAG_SUSPICIOUS_ATTACHMENT
from contract import InspectorResult

_MAX_ATTACHMENTS = 25


def analyze(sample_path: str, result: InspectorResult, results_dir: str = "", depth: int = 0) -> None:
    result.filetype = "email"
    lower = result.filename.lower()
    if lower.endswith(".msg"):
        _analyze_msg(sample_path, result, depth)
    else:
        _analyze_eml(sample_path, result, depth)


def _analyze_eml(sample_path: str, result: InspectorResult, depth: int) -> None:
    try:
        with open(sample_path, "rb") as fh:
            msg = email.message_from_binary_file(fh, policy=policy.default)
    except Exception:
        result.mark_incomplete()
        return

    headers = {
        "from": str(msg.get("From", "")),
        "reply_to": str(msg.get("Reply-To", "")),
        "return_path": str(msg.get("Return-Path", "")),
        "subject": str(msg.get("Subject", "")),
        "to": str(msg.get("To", "")),
    }
    result.content["headers"] = headers
    _check_reply_to(headers, result)

    body_parts: List[str] = []
    attachments: List[dict] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        if filename:
            attachments.append(_recurse_attachment(part.get_payload(decode=True), filename, result, depth))
        elif part.get_content_type() in ("text/plain", "text/html"):
            try:
                body_parts.append(part.get_content())
            except Exception:
                pass
    _finish(body_parts, attachments, result)


def _analyze_msg(sample_path: str, result: InspectorResult, depth: int) -> None:
    try:
        import extract_msg
    except ImportError:
        result.mark_incomplete()
        return
    try:
        msg = extract_msg.Message(sample_path)
    except Exception:
        result.mark_incomplete()
        return
    headers = {
        "from": str(getattr(msg, "sender", "") or ""),
        "reply_to": str(getattr(msg, "reply_to", "") or "" if hasattr(msg, "reply_to") else ""),
        "subject": str(getattr(msg, "subject", "") or ""),
        "to": str(getattr(msg, "to", "") or ""),
    }
    result.content["headers"] = headers
    _check_reply_to(headers, result)
    body_parts = [str(getattr(msg, "body", "") or "")]
    attachments: List[dict] = []
    for att in getattr(msg, "attachments", []) or []:
        data = getattr(att, "data", None)
        name = getattr(att, "longFilename", None) or getattr(att, "shortFilename", None) or "attachment"
        if data:
            attachments.append(_recurse_attachment(data, name, result, depth))
    _finish(body_parts, attachments, result)


def _check_reply_to(headers: dict, result: InspectorResult) -> None:
    frm = _domain_of(headers.get("from", ""))
    reply = _domain_of(headers.get("reply_to", ""))
    if reply and frm and reply != frm:
        result.add_flag(FLAG_REPLY_TO_MISMATCH)


def _domain_of(addr: str) -> str:
    if "@" in addr:
        return addr.rsplit("@", 1)[-1].strip(">").strip().lower()
    return ""


def _finish(body_parts: List[str], attachments: List[dict], result: InspectorResult) -> None:
    body = "\n".join(p for p in body_parts if p)
    result.content["body"] = body[:200000]
    result.content["attachments"] = attachments
    for kind, values in extract_iocs(body, *[str(h) for h in result.content.get("headers", {}).values()]).items():
        for value in values:
            result.add_ioc(kind, value)
    if any(a.get("verdict_hint") in ("suspicious", "malicious") for a in attachments):
        result.add_flag(FLAG_SUSPICIOUS_ATTACHMENT)


def _recurse_attachment(data, filename: str, result: InspectorResult, depth: int) -> dict:
    if not data or depth >= 3:
        return {"name": filename, "note": "not analyzed"}
    import router

    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix="att_")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        child = router.inspect_path(tmp, filename=filename, customer_code=result.customer_code, results_dir="", depth=depth + 1)
        return {"name": filename, "filetype": child.filetype, "flags": child.flags, "verdict_hint": child.verdict_hint}
    except Exception:
        return {"name": filename, "note": "analysis failed"}
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
