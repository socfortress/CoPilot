"""
Thin wrapper around Wazuh Manager's ``PUT /logtest`` endpoint.

What this is for:
The Detections Catalog "Test a log" feature lets analysts paste a raw log
line and asks Wazuh "which rule(s) would have matched this?". Rather than
re-implementing Wazuh's decoder + rule engine in Python (months of work,
guaranteed drift), we use Wazuh's own logtest API — same engine that runs
in production, no semantic gap.

Stateless mode only:
Wazuh's logtest supports stateful sessions (``token`` field) so multi-line
correlated rules can fire across calls. We don't need that for the
catalog's "test one log line" use case, and stateless calls don't leave
session state hanging on the Manager. If we ever want multi-line tests
we can extend with a ``token`` param + a ``DELETE /logtest/sessions/{token}``
cleanup call.

No DB writes, no schema changes — pure HTTP wrapper.
"""

import json
from typing import Any
from typing import Dict
from typing import Optional

from fastapi import HTTPException
from loguru import logger

from app.connectors.wazuh_manager.utils.universal import send_put_request


async def run_logtest(
    event: str,
    log_format: str = "syslog",
    location: str = "logtest",
) -> Dict[str, Any]:
    """
    Run a stateless logtest against the Wazuh Manager.

    Args:
        event: The raw log line to evaluate (single line, no JSON envelope).
        log_format: Wazuh log format. Common values: ``syslog`` (default),
            ``json``, ``snort-full``, ``squid``, ``apache``, ``iis``, etc.
            ``syslog`` is the most permissive and works for most operator-
            captured log lines.
        location: A pseudo-source label Wazuh records on the test. We pass
            ``"logtest"`` by default — Wazuh uses this to scope ``if_*``
            location-based rule conditions, and a generic value avoids
            accidentally matching location-specific rules.

    Returns:
        A dict with keys:
        - ``matched`` (bool): whether any rule matched
        - ``rule`` (dict|None): the matched rule's summary (id, level,
          description, groups, mitre, …) when matched, else None
        - ``alert`` (dict|None): the full Wazuh alert envelope (decoder,
          predecoder, data fields, full_log, …) — kept for the UI's
          "what did Wazuh actually parse?" panel
        - ``raw`` (dict): the unmodified Wazuh response payload, kept for
          debugging when ``matched`` is False but the analyst expects a hit

    Raises:
        HTTPException(400): event is empty / invalid input
        HTTPException(503): Wazuh Manager unreachable / refused the request
    """
    if not event or not event.strip():
        raise HTTPException(status_code=400, detail="event must be a non-empty log line")

    payload = {
        "event": event,
        "log_format": log_format,
        "location": location,
    }

    logger.debug(f"Running Wazuh logtest with format={log_format} location={location}")

    # WAZUH-PUT GOTCHA: send_put_request uses ``requests.put(data=...)`` which
    # form-encodes dicts (key=value&key=value), but the Content-Type header is
    # set to application/json. Wazuh's logtest endpoint then tries to parse
    # the form-encoded body as JSON and 400s with
    # ``Expecting value: line 1 column 1 (char 0)``. Pre-serializing to a JSON
    # string sidesteps it — ``requests`` sends strings as the raw body without
    # form encoding, so Wazuh sees actual JSON. (Cleaner fix would be a
    # ``json_data=True`` flag on send_put_request, but that touches shared
    # connector code used by every other Wazuh integration.)
    response = await send_put_request(endpoint="/logtest", data=json.dumps(payload))

    if not response or not response.get("success"):
        # send_put_request returns a dict with success=False on transport
        # failures; bubble its message up so the UI can show why.
        raise HTTPException(
            status_code=503,
            detail=response.get("message", "Wazuh Manager logtest failed") if response else "Wazuh Manager not reachable",
        )

    # Wazuh logtest wraps everything two layers deep:
    # response["data"]["data"]["output"] holds the actual logtest result.
    # Be defensive — version drift has changed this shape before.
    raw_payload = response.get("data") or {}
    inner = raw_payload.get("data") or {}
    output = inner.get("output") or {}

    rule_summary = _extract_rule_summary(output)
    matched = rule_summary is not None

    return {
        "matched": matched,
        "rule": rule_summary,
        "alert": output if output else None,
        "raw": raw_payload,
    }


def _extract_rule_summary(output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Pull the matched-rule summary out of a Wazuh logtest output, normalizing
    field names so the frontend can render a stable shape.

    Wazuh's logtest output puts the matched rule under ``output.rule`` —
    same structure as a regular alert envelope. If no rule matched the
    ``rule`` key is missing or the rule's id is 0, both of which mean
    "no match" for our purposes.
    """
    rule = output.get("rule")
    if not isinstance(rule, dict):
        return None

    rid = rule.get("id")
    # Wazuh sometimes returns rule.id as a string; normalize to int when possible.
    try:
        rid_int = int(rid) if rid is not None else None
    except (TypeError, ValueError):
        rid_int = None

    # rule.id == 0 / None == no real match (Wazuh's "rule" entry can be a
    # synthetic envelope even when no analyst-facing rule fired).
    if not rid_int:
        return None

    return {
        "id": rid_int,
        "level": rule.get("level"),
        "description": rule.get("description") or "",
        "groups": rule.get("groups") or [],
        "mitre": (rule.get("mitre") or {}).get("id") or [],
        "pci_dss": rule.get("pci_dss") or [],
        "gdpr": rule.get("gdpr") or [],
        "hipaa": rule.get("hipaa") or [],
        "nist_800_53": rule.get("nist_800_53") or [],
        "firedtimes": rule.get("firedtimes"),
    }
