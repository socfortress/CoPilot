"""Thin client to the inspector-runner sidecar.

CoPilot never touches the Docker API (see CLAUDE.md -> File Analysis) —
it POSTs the sample + job JSON to the runner over HTTP and gets back the result
JSON + base64 PNG previews. This module is the entire CoPilot-side surface of
Tier 1.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any
from typing import Dict
from typing import Tuple

import httpx
from loguru import logger

INSPECTOR_URL = os.getenv("INSPECTOR_URL", "http://inspector-runner:9000")
INSPECTOR_TIMEOUT = int(os.getenv("INSPECTOR_HTTP_TIMEOUT", "240"))


async def inspect(sample_bytes: bytes, job: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, bytes]]:
    """Send one job to the runner. Returns (inspector_result, {preview_name: png_bytes}).

    A timeout or 5xx is surfaced as a partial result flagged incomplete — a crashed
    inspector is itself a signal, not a reason to lose the job.
    """
    files = {"sample": ("sample", sample_bytes)}
    data = {"job": json.dumps(job)}
    try:
        async with httpx.AsyncClient(timeout=INSPECTOR_TIMEOUT) as client:
            resp = await client.post(f"{INSPECTOR_URL}/inspect", files=files, data=data)
        if resp.status_code == 429:
            raise InspectorBusy("inspector-runner is busy (429)")
        resp.raise_for_status()
        payload = resp.json()
    except InspectorBusy:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        logger.error(f"inspector call failed: {exc}")
        return (
            {
                "sha256": job.get("sha256", ""),
                "filename": job.get("filename", ""),
                "customer_code": job.get("customer_code", ""),
                "filetype": "unknown",
                "analysis_incomplete": True,
                "flags": ["analysis_incomplete"],
                "verdict_hint": "suspicious",
                "error": str(exc),
            },
            {},
        )

    previews_b64 = payload.pop("previews_b64", {}) or {}
    previews = {name: base64.b64decode(b64) for name, b64 in previews_b64.items()}
    return payload, previews


class InspectorBusy(Exception):
    """Raised when the runner's queue is full (429) — caller should retry with backoff."""
