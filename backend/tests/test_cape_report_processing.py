"""A CAPE report is read into its summary off the event loop (#1361).

The backend runs one event loop. A 59 MB CAPE report parsed on it stalled every request
for seconds, and ``asyncio.to_thread`` doesn't help: ``json.loads`` holds the GIL for the
whole parse. The report now streams into a worker process (``report_process`` /
``report_worker``) and only its summary comes back; the raw-report download relays CAPE's
bytes without parsing them.

No CAPE: the client runs against an ``httpx.MockTransport``. The worker is the real one,
started as a real process.

Run with: cd backend && python -m pytest tests/test_cape_report_processing.py
"""

import asyncio
import json
import os
import time

import httpx
import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")
os.environ.setdefault("MYSQL_PASSWORD", "test-only-password-not-the-default")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "test-only-password-not-the-default")

import app.file_analysis.routes as routes  # noqa: E402
from app.file_analysis.schema.analysis import AnalysisJob  # noqa: E402
from app.file_analysis.services import orchestrator  # noqa: E402
from app.file_analysis.services import sandbox as sandbox_package  # noqa: E402
from app.file_analysis.services.sandbox import report_process  # noqa: E402
from app.file_analysis.services.sandbox.base import ReportUnavailable  # noqa: E402
from app.file_analysis.services.sandbox.cape import CapeBackend  # noqa: E402
from app.file_analysis.services.sandbox.cape import summarize  # noqa: E402
from app.file_analysis.services.sandbox.report_process import (  # noqa: E402
    summarize_stream,
)

MB = 1024 * 1024

REPORT = {
    "info": {"id": 42, "duration": 120, "package": "exe", "machine": {"name": "capewin", "platform": "windows"}},
    "malscore": 9.4,
    "CAPE": {"configs": [{"RedLine": {"c2": ["45.10.20.30:443"]}}]},
    "signatures": [{"name": "injection_createremotethread", "severity": 3, "ttp": [{"attack_id": "T1055"}]}],
    "network": {"hosts": [{"ip": "45.10.20.30"}], "tcp": [{"dst": "45.10.20.30", "dport": 443}]},
    "behavior": {
        "processes": [{"process_name": "a.exe", "process_id": 10, "parent_id": 1, "calls": [{"api": "NtWriteFile"}]}],
        "summary": {"files": ["C:\\a.txt"], "executed_commands": ["a.exe --run"]},
    },
    "dropped": [{"sha256": "a" * 64, "name": "svchost.exe"}],
}
REPORT_BYTES = json.dumps(REPORT).encode()


async def _chunks(data: bytes, size: int = 64 * 1024, *, closed: list = None):
    try:
        for start in range(0, len(data), size):
            yield data[start : start + size]
            await asyncio.sleep(0)
    finally:
        if closed is not None:
            closed.append(True)


def _summarise(data: bytes, **kw):
    return asyncio.run(summarize_stream(_chunks(data), max_bytes=kw.get("max_bytes", 64 * MB), timeout=kw.get("timeout", 60)))


def _large_report(target_mb: int) -> bytes:
    """A report shaped like CAPE's: most of its size is API calls."""
    calls = [
        {
            "timestamp": "2026-11-20 10:00:00,000",
            "api": "NtCreateFile",
            "category": "file",
            "arguments": [{"name": "FileName", "value": f"C:\\Users\\cape\\AppData\\Local\\Temp\\file_{i}.tmp"}],
            "return": "0x00000000",
            "id": i,
        }
        for i in range(20000)
    ]
    one = len(json.dumps(calls))
    processes = [
        {"process_id": 100 + n, "parent_id": 99 + n, "process_name": f"p{n}.exe", "calls": calls}
        for n in range(max(1, target_mb * MB // one))
    ]
    return json.dumps({**REPORT, "behavior": {**REPORT["behavior"], "processes": processes}}).encode()


# --- the worker process ------------------------------------------------------


def test_the_worker_answers_with_the_summary_summarize_makes():
    assert _summarise(REPORT_BYTES) == summarize(REPORT).to_dict()


def test_the_event_loop_keeps_running_while_a_large_report_is_read():
    data = _large_report(40)
    started = time.perf_counter()
    json.loads(data)
    parse_ms = (time.perf_counter() - started) * 1000

    async def scenario():
        worst = 0.0
        done = False

        async def watchdog():
            nonlocal worst
            while not done:
                tick = time.perf_counter()
                await asyncio.sleep(0.01)
                worst = max(worst, (time.perf_counter() - tick - 0.01) * 1000)

        watcher = asyncio.create_task(watchdog())
        summary = await summarize_stream(_chunks(data), max_bytes=256 * MB, timeout=120)
        done = True
        await watcher
        return summary, worst

    summary, worst_stall_ms = asyncio.run(scenario())
    assert summary["task_id"] == 42 and len(summary["processes"]) > 1
    # Parsed here, the same report holds the loop for the whole parse (about half a second).
    assert worst_stall_ms < 150, f"the loop stalled {worst_stall_ms:.0f} ms (parsing in-process takes {parse_ms:.0f} ms)"


def test_a_report_over_the_size_limit_is_refused_and_its_download_closed():
    closed = []

    async def scenario():
        await summarize_stream(_chunks(b" " * (2 * MB), closed=closed), max_bytes=1 * MB, timeout=60)

    with pytest.raises(ReportUnavailable) as refused:
        asyncio.run(scenario())
    assert str(refused.value) == "The CAPE report is larger than CoPilot reads (1 MB, CAPE_REPORT_MAX_MB)."
    assert closed == [True]


def test_a_report_that_is_not_json_says_so():
    with pytest.raises(ReportUnavailable) as refused:
        _summarise(b"<html>CAPE error page</html>")
    assert str(refused.value) == "The CAPE report is not valid JSON."


def test_json_that_is_not_a_report_says_so():
    with pytest.raises(ReportUnavailable) as refused:
        _summarise(b'["not", "a", "report"]')
    assert str(refused.value) == "CAPE's answer is not a report."


def test_a_report_that_takes_too_long_is_given_up_on():
    async def stalls():
        yield REPORT_BYTES[:100]
        await asyncio.sleep(30)
        yield REPORT_BYTES[100:]

    async def scenario():
        await summarize_stream(stalls(), max_bytes=64 * MB, timeout=0.5)

    started = time.perf_counter()
    with pytest.raises(ReportUnavailable) as refused:
        asyncio.run(scenario())
    assert time.perf_counter() - started < 5
    assert str(refused.value) == "Reading the CAPE report took longer than CoPilot waits (0.5 s, CAPE_REPORT_TIMEOUT)."


def test_a_dropped_download_is_raised_as_it_is_so_it_can_be_retried():
    async def drops():
        yield REPORT_BYTES[:50]
        raise httpx.ReadError("connection reset")

    with pytest.raises(httpx.ReadError):
        asyncio.run(summarize_stream(drops(), max_bytes=64 * MB, timeout=60))


def test_a_worker_that_fails_gives_a_fixed_reason():
    assert str(report_process._failure(-9)) == (
        "The process reading the CAPE report was stopped (signal 9); the host may be short of memory."
    )
    assert str(report_process._failure(report_process.EXIT_SUMMARY_FAILED)) == "CoPilot could not summarise the CAPE report."
    assert str(report_process._failure(1)) == "CoPilot could not summarise the CAPE report."


def test_a_summary_over_its_limit_is_refused(monkeypatch):
    monkeypatch.setattr(report_process, "SUMMARY_MAX_BYTES", 100)
    with pytest.raises(ReportUnavailable) as refused:
        _summarise(REPORT_BYTES)
    assert "larger than CoPilot stores" in str(refused.value)


# --- the CAPE client ---------------------------------------------------------


def _cape(handler, **env) -> CapeBackend:
    backend = CapeBackend(transport=httpx.MockTransport(handler))
    backend.base_url = "http://cape.test/apiv2"
    backend.token = "token-for-tests"
    for name, value in env.items():
        setattr(backend, name, value)
    return backend


def test_the_report_is_asked_for_uncompressed_and_summarised():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=REPORT_BYTES, headers={"content-type": "application/json"})

    summary = asyncio.run(_cape(handler).summarize_report("42"))
    assert summary == summarize(REPORT).to_dict()
    assert [r.url.path for r in seen] == ["/apiv2/tasks/get/report/42/json/"]
    assert seen[0].headers["accept-encoding"] == "identity"
    assert seen[0].headers["authorization"] == "Token token-for-tests"


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (httpx.Response(404, json={"error": True}), "CAPE did not return the report (HTTP 404)."),
        (httpx.Response(401), "CAPE refused CoPilot's API token (HTTP 401); check CAPE_API_TOKEN."),
        (
            httpx.Response(200, content=b"\x1f\x8b", headers={"content-encoding": "gzip"}),
            "CAPE sent the report compressed, which CoPilot does not read.",
        ),
        (
            httpx.Response(200, content=b"{}", headers={"content-length": str(300 * MB)}),
            "The CAPE report is larger than CoPilot reads (256 MB, CAPE_REPORT_MAX_MB).",
        ),
    ],
)
def test_what_cape_answers_instead_of_a_report_is_a_reason(response, reason):
    with pytest.raises(ReportUnavailable) as refused:
        asyncio.run(_cape(lambda request: response).summarize_report("42"))
    assert str(refused.value) == reason


def test_the_size_limit_comes_from_cape_report_max_mb(monkeypatch):
    monkeypatch.setenv("CAPE_REPORT_MAX_MB", "1")
    monkeypatch.setenv("CAPE_REPORT_TIMEOUT", "45")
    backend = CapeBackend()
    assert (backend.report_max_bytes, backend.report_timeout) == (1 * MB, 45)
    monkeypatch.setenv("CAPE_REPORT_MAX_MB", "lots")
    assert CapeBackend().report_max_bytes == 256 * MB


def test_a_cape_server_error_is_tried_again():
    answers = [httpx.Response(503), httpx.Response(200, content=REPORT_BYTES)]
    summary = asyncio.run(_cape(lambda request: answers.pop(0)).summarize_report("42"))
    assert summary["task_id"] == 42 and answers == []


def test_a_task_id_that_is_not_a_number_never_reaches_cape():
    def handler(request):
        raise AssertionError("CAPE was asked")

    with pytest.raises(ReportUnavailable) as refused:
        asyncio.run(_cape(handler).summarize_report("42/../../tasks/delete/1"))
    assert str(refused.value) == "The sandbox task id is not valid."


def test_the_raw_report_is_relayed_byte_for_byte():
    raw = b'{"info": {"id": 42},   "behavior": {}}\n'

    async def scenario():
        chunks = await _cape(lambda request: httpx.Response(200, content=raw)).open_report("42")
        return b"".join([chunk async for chunk in chunks])

    assert asyncio.run(scenario()) == raw


@pytest.mark.parametrize(
    ("status", "reason"),
    [(404, "CAPE did not return the report (HTTP 404)."), (503, "CAPE could not serve the report (HTTP 503).")],
)
def test_the_raw_report_refusals_are_reasons(status, reason):
    with pytest.raises(ReportUnavailable) as refused:
        asyncio.run(_cape(lambda request: httpx.Response(status)).open_report("42"))
    assert str(refused.value) == reason


# --- the route and the orchestrator ------------------------------------------


class _Backend:
    """A sandbox backend whose report is fixed bytes, or a refusal."""

    def __init__(self, raw: bytes = REPORT_BYTES, refusal: str = None):
        self.raw = raw
        self.refusal = refusal
        self.asked = []

    async def open_report(self, job_ref):
        self.asked.append(job_ref)
        if self.refusal:
            raise ReportUnavailable(self.refusal)

        async def chunks():
            yield self.raw[:10]
            yield self.raw[10:]

        return chunks()

    async def find_by_sha256(self, sha256):
        return "77"

    async def wait_for_report(self, job_ref):
        return None

    async def summarize_report(self, job_ref):
        self.asked.append(job_ref)
        if self.refusal:
            raise ReportUnavailable(self.refusal)
        return {"task_id": int(job_ref), "verdict": "clean"}


def _serve(monkeypatch, backend, job, result):
    async def load_job(job_id):
        return job

    async def load_result(customer_code, sha256):
        return result

    monkeypatch.setattr(routes.state_store, "load_job", load_job)
    monkeypatch.setattr(routes.state_store, "load_result", load_result)
    monkeypatch.setattr(sandbox_package, "get_backend", lambda: backend)


async def _body(response) -> bytes:
    return b"".join([chunk async for chunk in response.body_iterator])


def test_the_download_route_streams_cape_bytes_without_parsing_them(monkeypatch):
    backend = _Backend(raw=b'{"info":{"id":42}}')
    _serve(monkeypatch, backend, {"customer_code": "acme", "sha256": "f" * 64}, {"sandbox": {"task_id": 42}})

    async def scenario():
        response = await routes.cape_report("0123abcd")
        return response, await _body(response)

    response, body = asyncio.run(scenario())
    assert body == b'{"info":{"id":42}}'
    assert response.media_type == "application/json"
    assert response.headers["content-disposition"] == 'attachment; filename="cape-report-0123abcd.json"'
    assert response.headers["x-content-type-options"] == "nosniff"
    assert backend.asked == ["42"]


def test_a_report_without_a_summary_is_still_downloadable_by_the_jobs_task(monkeypatch):
    backend = _Backend()
    job = {"customer_code": "acme", "sha256": "f" * 64, "dynamic_task_id": "77"}
    _serve(monkeypatch, backend, job, {"sandbox": None})
    asyncio.run(routes.cape_report("0123abcd"))
    assert backend.asked == ["77"]


def test_the_download_route_404s_without_a_task_and_502s_on_a_refusal(monkeypatch):
    _serve(monkeypatch, _Backend(), {"customer_code": "acme", "sha256": "f" * 64}, {"sandbox": None})
    with pytest.raises(HTTPException) as missing:
        asyncio.run(routes.cape_report("0123abcd"))
    assert missing.value.status_code == 404

    _serve(
        monkeypatch,
        _Backend(refusal="CAPE did not return the report (HTTP 404)."),
        {"customer_code": "acme"},
        {"sandbox": {"task_id": 42}},
    )
    with pytest.raises(HTTPException) as refused:
        asyncio.run(routes.cape_report("0123abcd"))
    assert refused.value.status_code == 502
    assert refused.value.detail == "could not fetch the CAPE report: CAPE did not return the report (HTTP 404)."


def _job() -> AnalysisJob:
    return AnalysisJob(job_id="0123abcd", sha256="f" * 64, filename="a.exe", customer_code="acme")


def test_detonation_keeps_the_task_and_returns_the_workers_summary(monkeypatch):
    backend = _Backend()
    monkeypatch.setattr(sandbox_package, "get_backend", lambda: backend)
    job = _job()
    summary = asyncio.run(orchestrator._detonate(b"MZ", {"filename": "a.exe"}, job))
    assert summary == {"task_id": 77, "verdict": "clean"}
    assert (job.dynamic_task_id, job.dynamic_error) == ("77", None)


def test_a_report_that_cannot_be_read_says_why_on_the_job(monkeypatch):
    backend = _Backend(refusal="The CAPE report is larger than CoPilot reads (256 MB, CAPE_REPORT_MAX_MB).")
    monkeypatch.setattr(sandbox_package, "get_backend", lambda: backend)
    job = _job()
    assert asyncio.run(orchestrator._detonate(b"MZ", {"filename": "a.exe"}, job)) is None
    assert job.dynamic_task_id == "77"
    assert job.dynamic_error == "The CAPE report is larger than CoPilot reads (256 MB, CAPE_REPORT_MAX_MB)."
    assert AnalysisJob(**job.model_dump(mode="json")).dynamic_error == job.dynamic_error


def test_an_unrelated_detonation_failure_leaves_no_reason(monkeypatch):
    class Broken(_Backend):
        async def wait_for_report(self, job_ref):
            raise RuntimeError("CAPE task 77 failed: failed_analysis")

    monkeypatch.setattr(sandbox_package, "get_backend", lambda: Broken())
    job = _job()
    assert asyncio.run(orchestrator._detonate(b"MZ", {}, job)) is None
    assert job.dynamic_error is None


def test_the_null_backend_has_no_report():
    from app.file_analysis.services.sandbox.base import NotEnabled
    from app.file_analysis.services.sandbox.null import NullBackend

    for call in (NullBackend().summarize_report("1"), NullBackend().open_report("1")):
        with pytest.raises(NotEnabled):
            asyncio.run(call)
