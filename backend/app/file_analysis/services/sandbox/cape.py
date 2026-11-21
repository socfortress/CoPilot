"""CAPEv2 backend — used by BOTH local_vm and remote (they differ only in host).

Implements the REST interface in CLAUDE.md -> File Analysis:
  health   GET  /cuckoo/status/
  dedup    GET  /tasks/search/sha256/<sha256>/
  submit   POST /tasks/create/file/         (multipart: package, options, custom)
  poll     GET  /tasks/view/<id>/           (until status == reported)
  report   GET  /tasks/get/report/<id>/json/ (streamed: never parsed in this process)

Pure HTTP + env config. No DB, no CoPilot state. httpx with a Token header and
retries on transient errors; a 401 is surfaced clearly (bad/expired token).

The report is the one large answer (59 MB in #1361). It is never parsed, nor held whole,
in the backend's process: ``summarize_report`` streams it into a worker process
(``report_process``) and gets the summary back, and ``open_report`` relays it unparsed
for the raw download.
"""
from __future__ import annotations

import asyncio
import io
import os
import zipfile
from typing import Any
from typing import AsyncIterator
from typing import Dict
from typing import List
from typing import Optional

import httpx
from loguru import logger

from app.file_analysis.services.sandbox.base import CapeSummary
from app.file_analysis.services.sandbox.base import NotEnabled
from app.file_analysis.services.sandbox.base import ReportUnavailable
from app.file_analysis.services.sandbox.report_process import summarize_stream
from app.file_analysis.services.sandbox.report_process import too_large
from app.file_analysis.services.verdict import is_low_confidence_signature
from app.file_analysis.services.verdict import is_noise_signature

_POLL_INTERVAL = int(os.getenv("CAPE_POLL_INTERVAL", "15"))
_POLL_TIMEOUT = int(os.getenv("CAPE_POLL_TIMEOUT", "1800"))
_HTTP_TIMEOUT = int(os.getenv("CAPE_HTTP_TIMEOUT", "60"))
_RETRIES = 3
_REPORT_MAX_MB_DEFAULT = 256
_REPORT_TIMEOUT_DEFAULT = 300

_DOWNLOAD_FAILED = "CoPilot could not download the report from CAPE."


def _env_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value <= 0:
        logger.warning(f"{name}={raw!r} is not a positive whole number; using {default}")
        return default
    return value


class _CapeServerError(Exception):
    """CAPE answered 5xx: worth another try."""

    def __init__(self, status: int) -> None:
        super().__init__(f"CAPE answered {status}")
        self.status = status


class CapeBackend:
    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self.base_url = os.getenv("CAPE_API_URL", "http://cape-host:8000/apiv2").rstrip("/")
        self.token = os.getenv("CAPE_API_TOKEN", "")
        # None is the network; tests hand in an httpx.MockTransport.
        self._transport = transport
        # The largest report read into a summary, and the time to download and summarise it.
        self.report_max_bytes = _env_positive_int("CAPE_REPORT_MAX_MB", _REPORT_MAX_MB_DEFAULT) * 1024 * 1024
        self.report_timeout = _env_positive_int("CAPE_REPORT_TIMEOUT", _REPORT_TIMEOUT_DEFAULT)

    def _headers(self) -> dict:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Token {self.token}"
        return headers

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=_HTTP_TIMEOUT, transport=self._transport)

    async def _request(self, method: str, path: str, **kw) -> httpx.Response:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt in range(_RETRIES):
            try:
                async with self._client() as client:
                    resp = await client.request(method, url, headers=self._headers(), **kw)
                if resp.status_code == 401:
                    raise NotEnabled("CAPE returned 401 — check CAPE_API_TOKEN (token_auth_enabled=yes in api.conf)")
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError("server error", request=resp.request, response=resp)
                return resp
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                await asyncio.sleep(2**attempt)
        raise httpx.TransportError(f"CAPE request failed after {_RETRIES} retries: {last_exc}")

    # --- interface ---------------------------------------------------------
    async def available(self) -> bool:
        try:
            resp = await self._request("GET", "/cuckoo/status/")
            return resp.status_code == 200
        except (httpx.HTTPError, NotEnabled) as exc:
            logger.warning(f"CAPE availability check failed: {exc}")
            return False

    async def find_by_sha256(self, sha256: str) -> Optional[str]:
        try:
            resp = await self._request("GET", f"/tasks/search/sha256/{sha256}/")
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", [])
        if isinstance(data, list):
            # Only reuse a SUCCESSFULLY reported prior task — never a failed/pending
            # one, or a stale failure (e.g. detonated before a matching guest existed)
            # would resurface forever instead of a fresh submit.
            for task in data:
                if isinstance(task, dict) and task.get("status") == "reported":
                    return str(task.get("id") or task.get("task_id") or "")
        return None

    async def submit(self, sample: bytes, filename: str, package: str, customer_code: str, source_flow: str) -> str:
        """Submit the sample bytes straight to CAPE — the file never touches the
        CoPilot host's disk (streamed from memory into the multipart POST)."""
        custom = f"{customer_code}|{source_flow}"
        files = {"file": (filename or "sample", sample)}
        data = {"package": package, "custom": custom, "timeout": os.getenv("CAPE_TASK_TIMEOUT", "120")}
        resp = await self._request("POST", "/tasks/create/file/", files=files, data=data)
        payload = resp.json()
        task_id = payload.get("data", {}).get("task_ids", [None])[0] or payload.get("task_id") or payload.get("data", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"CAPE submit returned no task id: {payload}")
        return str(task_id)

    async def wait_for_report(self, job_ref: str) -> None:
        waited = 0
        while waited < _POLL_TIMEOUT:
            resp = await self._request("GET", f"/tasks/view/{job_ref}/")
            status = resp.json().get("data", {}).get("status", "")
            if status == "reported":
                return
            if status in ("failed_analysis", "failed_processing"):
                raise RuntimeError(f"CAPE task {job_ref} failed: {status}")
            await asyncio.sleep(_POLL_INTERVAL)
            waited += _POLL_INTERVAL
        raise TimeoutError(f"CAPE task {job_ref} not reported within {_POLL_TIMEOUT}s")

    async def summarize_report(self, job_ref: str) -> Dict[str, Any]:
        """The ``CapeSummary`` (as a dict) of the task's report, read off the event loop (#1361).

        The report streams from CAPE into a worker process, which answers with the summary.
        A dropped download or a CAPE 5xx is tried again from the start; anything else is a
        ``ReportUnavailable``.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(_RETRIES):
            try:
                return await summarize_stream(
                    self._report_chunks(job_ref),
                    max_bytes=self.report_max_bytes,
                    timeout=self.report_timeout,
                )
            except (httpx.TransportError, _CapeServerError) as exc:
                last_exc = exc
                if attempt + 1 < _RETRIES:
                    await asyncio.sleep(2**attempt)
        logger.warning(f"CAPE report for task {job_ref} could not be downloaded after {_RETRIES} tries: {last_exc}")
        raise ReportUnavailable(_DOWNLOAD_FAILED)

    async def open_report(self, job_ref: str) -> AsyncIterator[bytes]:
        """CAPE's raw JSON report as it arrives, for relaying unparsed (the raw-report download).

        CAPE's answer is checked before this returns, so a refusal is a ``ReportUnavailable``
        rather than a download that breaks half-way. There is no size cap: nothing is held.
        """
        url = self._report_url(job_ref)
        client = self._client()
        try:
            response = await client.send(client.build_request("GET", url, headers=self._report_headers()), stream=True)
        except httpx.HTTPError as exc:
            await client.aclose()
            logger.warning(f"CAPE report for task {job_ref} could not be fetched: {exc}")
            raise ReportUnavailable(_DOWNLOAD_FAILED) from None
        try:
            self._check_report_response(response, max_bytes=None)
        except _CapeServerError as exc:
            await response.aclose()
            await client.aclose()
            raise ReportUnavailable(f"CAPE could not serve the report (HTTP {exc.status}).") from None
        except BaseException:
            await response.aclose()
            await client.aclose()
            raise
        return self._relay(client, response)

    @staticmethod
    async def _relay(client: httpx.AsyncClient, response: httpx.Response) -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    async def _report_chunks(self, job_ref: str) -> AsyncIterator[bytes]:
        url = self._report_url(job_ref)
        async with self._client() as client:
            async with client.stream("GET", url, headers=self._report_headers()) as response:
                self._check_report_response(response, max_bytes=self.report_max_bytes)
                async for chunk in response.aiter_bytes():
                    yield chunk

    def _report_url(self, job_ref: str) -> str:
        task_id = str(job_ref)
        # CAPE task ids are integers; anything else never reaches the URL path.
        if not task_id.isdigit():
            raise ReportUnavailable("The sandbox task id is not valid.")
        return f"{self.base_url}/tasks/get/report/{task_id}/json/"

    def _report_headers(self) -> dict:
        # Uncompressed only: httpx inflates a compressed body with no limit on what it produces.
        return {**self._headers(), "Accept-Encoding": "identity"}

    @staticmethod
    def _check_report_response(response: httpx.Response, max_bytes: Optional[int]) -> None:
        status = response.status_code
        if status == 401:
            raise ReportUnavailable("CAPE refused CoPilot's API token (HTTP 401); check CAPE_API_TOKEN.")
        if status >= 500:
            raise _CapeServerError(status)
        if status != 200:
            raise ReportUnavailable(f"CAPE did not return the report (HTTP {status}).")
        encoding = response.headers.get("content-encoding", "").strip().lower()
        if encoding not in ("", "identity"):
            raise ReportUnavailable("CAPE sent the report compressed, which CoPilot does not read.")
        length = response.headers.get("content-length", "").strip()
        if max_bytes is not None and length.isdigit() and int(length) > max_bytes:
            raise too_large(max_bytes)

    async def get_screenshots(self, job_ref: str, limit: int = 24) -> List[bytes]:
        """Return up to ``limit`` detonation screenshots as raw JPEG bytes.

        CAPE serves all shots for a task as one zip (`/tasks/get/screenshot/<id>/`);
        we fetch it once and unzip in memory. Best-effort — any failure (no shots,
        backend hiccup) returns an empty list so the report still renders.
        """
        try:
            resp = await self._request("GET", f"/tasks/get/screenshot/{job_ref}/")
            if resp.status_code != 200 or "zip" not in resp.headers.get("content-type", ""):
                return []
            shots: List[bytes] = []
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                for name in sorted(zf.namelist()):
                    if name.lower().endswith((".jpg", ".jpeg", ".png")):
                        shots.append(zf.read(name))
                        if len(shots) >= limit:
                            break
            return shots
        except Exception as exc:  # noqa: BLE001 — screenshots are non-essential
            logger.warning(f"CAPE screenshot fetch failed for task {job_ref}: {exc}")
            return []


def summarize(report: dict) -> CapeSummary:
    """Extract the strongest signals from a CAPE JSON report into a CapeSummary."""
    summary = CapeSummary()
    info = report.get("info", {}) or {}
    summary.task_id = info.get("id")
    try:
        summary.malscore = float(report.get("malscore", info.get("score", 0)) or 0)
    except (TypeError, ValueError):
        summary.malscore = 0.0

    # Config extraction (strongest malicious signal): family + C2.
    cape = report.get("CAPE", {}) or {}
    configs = cape.get("configs", []) if isinstance(cape, dict) else []
    for cfg in configs or []:
        for family, details in cfg.items() if isinstance(cfg, dict) else []:
            if not summary.family:
                summary.family = family
            if isinstance(details, dict):
                for key in ("c2", "address", "cncs", "cnc", "c2_list"):
                    for endpoint in _as_list(details.get(key)):
                        _add_c2(summary, endpoint)
    if not summary.family:
        summary.family = report.get("malfamily", "") or info.get("package", "") and ""

    # Signatures + ATT&CK ids.
    for sig in report.get("signatures", []) or []:
        name = sig.get("name", "")
        summary.signatures.append(
            {
                "name": name,
                "description": sig.get("description", ""),
                "severity": sig.get("severity", 0),
                # Environmental noise = CAPE-monitor/Windows-guest baseline (see verdict.py).
                # low_confidence = static-PE/packer/.NET-JIT heuristics that fire on benign
                # software. Both are tagged so the UI can separate them from real signal.
                "noise": is_noise_signature(name),
                "low_confidence": not is_noise_signature(name) and is_low_confidence_signature(name),
                "mitre": [t.get("attack_id", t) if isinstance(t, dict) else t for t in sig.get("ttp", []) or sig.get("mitre", []) or []],
            },
        )

    # Run metadata (machine, duration, package).
    summary.duration = int(info.get("duration") or 0)
    summary.package = info.get("package") or ""
    machine = info.get("machine") or {}
    if isinstance(machine, dict):
        name = machine.get("name") or machine.get("label") or ""
        plat = machine.get("platform") or ""
        summary.machine = f"{name} ({plat})" if plat else name

    # Network — everything the guest touched. NOTE: these are OBSERVED endpoints,
    # not C2. Most of it is OS telemetry (connectivity checks, update, NTP). Only
    # config-extracted endpoints (``_add_c2`` above) belong in c2_ips/c2_domains,
    # because a "C2 was contacted" signal drives the malicious verdict.
    network = report.get("network", {}) or {}
    for host in network.get("hosts", []) or []:
        ip = host.get("ip") if isinstance(host, dict) else host
        if ip:
            summary.hosts.append(ip)
    for dom in network.get("domains", []) or []:
        domain = dom.get("domain") if isinstance(dom, dict) else dom
        if domain:
            summary.domains.append(domain)
    for q in network.get("dns", []) or []:
        if not isinstance(q, dict):
            continue
        answers = [a.get("data", a) if isinstance(a, dict) else a for a in q.get("answers", []) or []]
        summary.dns.append({"request": q.get("request", ""), "type": q.get("type", ""), "answers": answers})
    for h in network.get("http", []) or []:
        if isinstance(h, dict):
            summary.http.append({"method": h.get("method", ""), "host": h.get("host", ""), "uri": h.get("uri", h.get("path", ""))})
    for proto in ("tcp", "udp"):
        for c in network.get(proto, []) or []:
            if isinstance(c, dict) and c.get("dst"):
                summary.connections.append({"proto": proto, "dst": c.get("dst"), "dport": c.get("dport")})

    # Behavior — processes launched.
    behavior = report.get("behavior", {}) or {}
    for proc in behavior.get("processes", []) or []:
        if not isinstance(proc, dict):
            continue
        # CAPE names these ``process_id`` / ``parent_id``; ``pid``/``ppid`` are only
        # present on some report shapes. Reading the wrong one yields pid=None, which
        # both blanks the UI and collapses the process tree (every node becomes a root).
        environ = proc.get("environ") if isinstance(proc.get("environ"), dict) else {}
        summary.processes.append(
            {
                "name": proc.get("process_name") or proc.get("name") or "",
                "pid": proc.get("process_id") if proc.get("process_id") is not None else proc.get("pid"),
                "ppid": proc.get("parent_id") if proc.get("parent_id") is not None else proc.get("ppid"),
                "command_line": proc.get("command_line") or environ.get("CommandLine", ""),
            },
        )

    # Full behavioural record — literally what the sample touched on the host, so an
    # analyst can judge from evidence, not a score. Straight from CAPE's
    # behaviour.summary categories; capped per category so a pathological run can't
    # bloat the stored result (the raw report stays available for download).
    _BEHAV_CAP = 2000
    behav_summary = behavior.get("summary", {}) or {}
    _behav_map = {
        "files": "files",
        "read_files": "read_files",
        "write_files": "write_files",
        "delete_files": "delete_files",
        "registry_keys": "keys",
        "read_keys": "read_keys",
        "write_keys": "write_keys",
        "delete_keys": "delete_keys",
        "mutexes": "mutexes",
        "executed_commands": "executed_commands",
        "created_services": "created_services",
        "started_services": "started_services",
        "resolved_apis": "resolved_apis",
    }
    for out_key, src_key in _behav_map.items():
        vals = behav_summary.get(src_key) or []
        if vals:
            summary.behavior[out_key] = [str(v) for v in vals][:_BEHAV_CAP]

    # Human-readable event stream (CAPE's "enhanced" behaviour) — a plain-English
    # timeline of the notable actions (create file/key, load lib, connect, …).
    for ev in (behavior.get("enhanced", []) or [])[:_BEHAV_CAP]:
        if isinstance(ev, dict):
            summary.enhanced.append(
                {
                    "event": ev.get("event", ""),
                    "object": ev.get("object", ""),
                    "data": ev.get("data", {}),
                },
            )

    # Endpoints the sample TRIED to reach but that were unreachable (dead) — a strong
    # "attempted C2 / offline infra" tell even when nothing was contacted.
    for dh in network.get("dead_hosts", []) or []:
        if isinstance(dh, (list, tuple)) and dh:
            summary.dead_hosts.append(f"{dh[0]}:{dh[1]}" if len(dh) > 1 else str(dh[0]))
        elif dh:
            summary.dead_hosts.append(str(dh))

    # MITRE ATT&CK (ttps).
    for t in report.get("ttps", []) or []:
        if isinstance(t, dict):
            tid = t.get("ttp") or t.get("id") or ""
            if tid:
                summary.ttps.append({"id": tid, "signature": t.get("signature") or t.get("name") or ""})

    # Extracted payloads (CAPE config/payload dumps).
    for p in cape.get("payloads", []) or []:
        if isinstance(p, dict):
            summary.payloads.append(
                {"name": p.get("name", ""), "sha256": p.get("sha256", ""), "type": p.get("cape_type") or p.get("type", "")},
            )

    # Dropped files + screenshots.
    for dropped in report.get("dropped", []) or []:
        summary.dropped.append({"sha256": dropped.get("sha256", ""), "name": dropped.get("name", ""), "type": dropped.get("type", "")})
    summary.screenshots = [s.get("path", s) if isinstance(s, dict) else s for s in report.get("screenshots", []) or []]

    # CAPE debug errors (diagnostics, esp. for failed runs).
    debug = report.get("debug", {}) or {}
    summary.errors = [str(e) for e in (debug.get("errors", []) or []) if e][:20]

    # Derived verdict — one source of truth with the job-level merge, so the
    # Detonation tab can never disagree with the headline verdict. A bare high
    # malscore is NOT malicious on its own (see services/verdict.py).
    from app.file_analysis.services.verdict import dynamic_verdict_from_report

    summary.verdict = dynamic_verdict_from_report(summary.to_dict())

    # Dedup.
    summary.c2_ips = _dedup(summary.c2_ips)
    summary.c2_domains = _dedup(summary.c2_domains)
    summary.hosts = _dedup(summary.hosts)
    summary.domains = _dedup(summary.domains)
    return summary


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _add_c2(summary: CapeSummary, endpoint) -> None:
    if not endpoint or not isinstance(endpoint, str):
        return
    host = endpoint.split("://")[-1].split("/")[0].split(":")[0]
    if _looks_like_ip(host):
        summary.c2_ips.append(host)
    else:
        summary.c2_domains.append(host)


def _looks_like_ip(host: str) -> bool:
    parts = host.split(".")
    return len(parts) == 4 and all(p.isdigit() for p in parts)


def _dedup(items: list) -> list:
    out = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out
