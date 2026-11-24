"""CoPilot's client for copilot-prowler, the container that runs Prowler (``prowler-runner/``).

The runner's API is ``prowler-runner/runner/main.py``: a bearer token (``PROWLER_RUNNER_TOKEN``,
the same value in both containers' environment), JSON answers, and errors as
``{"detail": <fixed text>, "code": <code>}``. This client:

- sends nothing without a token of at least 32 characters, never follows a redirect, ignores
  the host's proxy settings (the token must not travel through one), and asks for and accepts
  only uncompressed bodies: httpx inflates a compressed body with no limit, before any cap on
  what was read could apply;
- reads every body raw and capped, and turns every failure into a ``RunnerError`` with a
  reason of CoPilot's and, when the runner gave one, the runner's code. A runner's 401 is never
  a CoPilot 401 (the frontend would log the analyst out): routes answer 502;
- checks the shapes it uses and copies only the fields it knows.

``TRANSPORT`` is for the unit tests (an ``httpx.MockTransport``); it is None in a deployment.
"""

import json
import os
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import AsyncIterator
from typing import Dict
from typing import List
from typing import Optional
from urllib.parse import urlsplit

import httpx

URL_ENV = "PROWLER_RUNNER_URL"
TOKEN_ENV = "PROWLER_RUNNER_TOKEN"
DEFAULT_URL = "http://copilot-prowler:8080"
MIN_TOKEN_LENGTH = 32

CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 30.0
#: The runner stops a connection test after PROWLER_CONNECTION_TEST_TIMEOUT (120 s by default).
#: The frontend's nginx gives the test route 180 s (test_cloud_assessment_* keeps them in step).
CONNECTION_TEST_TIMEOUT = 150.0
#: Between two chunks of a findings or report download.
STREAM_READ_TIMEOUT = 120.0

MAX_JSON_BYTES = 1 << 20
MAX_SUMMARY_BYTES = 64 << 20
MAX_CATALOG_BYTES = 32 << 20
MAX_FINDING_LINE_BYTES = 1 << 20
CATALOG_TTL_SECONDS = 3600

JOB_ID = re.compile(r"^[0-9a-f]{32}$")
RUNNER_CODE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
EXCEPTION_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")
PROVIDERS = ("aws", "azure", "gcp", "m365")
JOB_STATUSES = ("running", "normalizing", "completed", "failed", "cancelled")
ARTIFACT_KINDS = ("html", "csv")

#: Set by the unit tests only.
TRANSPORT: Optional[httpx.AsyncBaseTransport] = None

#: What CoPilot says for each reason. Fixed texts: never a URL, a token or the runner's body.
REASONS = {
    "not_configured": "PROWLER_RUNNER_TOKEN is missing from CoPilot's .env, or shorter than 32 characters.",
    "bad_url": "PROWLER_RUNNER_URL must be an http(s) URL with a host and nothing else (no user, query or fragment).",
    "unreachable": "CoPilot couldn't reach copilot-prowler.",
    "timeout": "copilot-prowler didn't answer in time.",
    "token_rejected": "copilot-prowler refused CoPilot's PROWLER_RUNNER_TOKEN: both containers need the same value.",
    "runner_not_configured": "copilot-prowler has no PROWLER_RUNNER_TOKEN of at least 32 characters, so it accepts no requests.",
    "busy": "copilot-prowler is already running as many scans as it may.",
    "not_found": "copilot-prowler doesn't hold that scan.",
    "refused": "copilot-prowler refused the request.",
    "bad_response": "copilot-prowler's answer couldn't be read.",
}


class RunnerError(Exception):
    """copilot-prowler couldn't do what was asked. ``reason`` is CoPilot's (a key of ``REASONS``);
    ``code`` is the runner's own error code, when it answered with one."""

    def __init__(self, reason: str, *, status: Optional[int] = None, code: Optional[str] = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status
        self.code = code

    @property
    def message(self) -> str:
        return REASONS.get(self.reason, REASONS["bad_response"])


@dataclass
class RunnerJob:
    """The fields of a runner job CoPilot reads (``Job.public()`` in the runner)."""

    job_id: str
    status: str
    prowler_version: Optional[str] = None
    error_code: Optional[str] = None
    prowler_errors: List[str] = field(default_factory=list)
    error_lines: int = 0


def _clean_url(raw: str) -> Optional[str]:
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        return None
    return raw.rstrip("/")


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 2**31 else 0


def parse_job(data: Any) -> RunnerJob:
    if not isinstance(data, dict):
        raise RunnerError("bad_response")
    job_id = data.get("job_id")
    status = data.get("status")
    if not isinstance(job_id, str) or not JOB_ID.match(job_id) or status not in JOB_STATUSES:
        raise RunnerError("bad_response")
    version = data.get("prowler_version")
    error = data.get("error") if isinstance(data.get("error"), dict) else {}
    code = error.get("code")
    names = error.get("prowler_errors")
    logs = data.get("logs") if isinstance(data.get("logs"), dict) else {}
    return RunnerJob(
        job_id=job_id,
        status=status,
        prowler_version=version if isinstance(version, str) and 0 < len(version) <= 32 else None,
        error_code=code if isinstance(code, str) and RUNNER_CODE.match(code) else None,
        prowler_errors=[
            name for name in (names if isinstance(names, list) else []) if isinstance(name, str) and EXCEPTION_NAME.match(name)
        ][:10],
        error_lines=_int(logs.get("error_lines")),
    )


async def raw_chunks(response: httpx.Response) -> AsyncIterator[bytes]:
    """The body's raw bytes. A response already read into memory (an in-process transport's, never
    a network one's) is its content, which for an identity body is the raw bytes."""
    if response.is_stream_consumed:
        yield response.content
        return
    async for chunk in response.aiter_raw():
        yield chunk


_catalog_cache: Dict[str, "tuple[float, Dict[str, Any]]"] = {}


def clear_catalog_cache() -> None:
    _catalog_cache.clear()


class RunnerClient:
    """One client per request or job tick: ``async with RunnerClient.from_env() as runner: ...``."""

    def __init__(self, base_url: Optional[str], token: Optional[str], transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self.base_url = base_url
        self.token = token
        headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
        if self.configured:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(
            base_url=base_url or "http://invalid",
            headers=headers,
            timeout=httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT),
            transport=transport,
            trust_env=False,
            follow_redirects=False,
        )

    @classmethod
    def from_env(cls) -> "RunnerClient":
        url = _clean_url((os.environ.get(URL_ENV) or "").strip() or DEFAULT_URL)
        token = (os.environ.get(TOKEN_ENV) or "").strip() or None
        return cls(url, token, transport=TRANSPORT)

    @property
    def configured(self) -> bool:
        return bool(self.base_url) and bool(self.token) and len(self.token) >= MIN_TOKEN_LENGTH

    def problem(self) -> Optional[str]:
        """Why nothing can be sent, as a reason, or None."""
        if not self.base_url:
            return "bad_url"
        if not self.token or len(self.token) < MIN_TOKEN_LENGTH:
            return "not_configured"
        return None

    async def __aenter__(self) -> "RunnerClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    # --- plumbing ------------------------------------------------------------------------------

    def _ensure_configured(self) -> None:
        problem = self.problem()
        if problem:
            raise RunnerError(problem)

    @staticmethod
    def _check_encoding(response: httpx.Response) -> None:
        encoding = response.headers.get("content-encoding", "identity").strip().lower()
        if encoding not in ("", "identity"):
            raise RunnerError("bad_response", status=response.status_code)

    @classmethod
    async def _read(cls, response: httpx.Response, max_bytes: int) -> bytes:
        cls._check_encoding(response)
        body = bytearray()
        async for chunk in raw_chunks(response):
            body.extend(chunk)
            if len(body) > max_bytes:
                raise RunnerError("bad_response", status=response.status_code)
        return bytes(body)

    @staticmethod
    def _error_for(status: int, body: bytes) -> RunnerError:
        code = None
        try:
            data = json.loads(body) if body else None
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("code"), str) and RUNNER_CODE.match(data["code"]):
            code = data["code"]
        if status == 401:
            return RunnerError("token_rejected", status=status, code=code)
        if status == 503 and code == "not_configured":
            return RunnerError("runner_not_configured", status=status, code=code)
        if status == 429:
            return RunnerError("busy", status=status, code=code)
        if status == 404:
            return RunnerError("not_found", status=status, code=code)
        if status in (400, 409, 422):
            return RunnerError("refused", status=status, code=code)
        return RunnerError("bad_response", status=status, code=code)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_bytes: Optional[int] = None,
    ) -> Any:
        self._ensure_configured()
        max_bytes = max_bytes or MAX_JSON_BYTES
        request_timeout = httpx.Timeout(timeout or READ_TIMEOUT, connect=CONNECT_TIMEOUT)
        try:
            async with self._client.stream(method, path, json=body, timeout=request_timeout) as response:
                content = await self._read(response, max_bytes)
                status = response.status_code
        except httpx.TimeoutException as error:
            raise RunnerError("timeout") from error
        except httpx.HTTPError as error:
            raise RunnerError("unreachable") from error
        if not 200 <= status < 300:
            raise self._error_for(status, content)
        if status == 204 or not content:
            return None
        try:
            return json.loads(content)
        except ValueError as error:
            raise RunnerError("bad_response", status=status) from error

    @asynccontextmanager
    async def _stream(self, path: str) -> AsyncIterator[httpx.Response]:
        self._ensure_configured()
        try:
            async with self._client.stream("GET", path, timeout=httpx.Timeout(STREAM_READ_TIMEOUT, connect=CONNECT_TIMEOUT)) as response:
                if response.status_code != 200:
                    raise self._error_for(response.status_code, await self._read(response, MAX_JSON_BYTES))
                self._check_encoding(response)
                yield response
        except httpx.TimeoutException as error:
            raise RunnerError("timeout") from error
        except httpx.HTTPError as error:
            raise RunnerError("unreachable") from error

    @staticmethod
    def _job_path(job_id: str, suffix: str = "") -> str:
        if not isinstance(job_id, str) or not JOB_ID.match(job_id):
            raise RunnerError("not_found")
        return f"/v1/scans/{job_id}{suffix}"

    # --- the API -------------------------------------------------------------------------------

    async def health(self) -> Dict[str, Any]:
        data = await self._request("GET", "/v1/health")
        if not isinstance(data, dict):
            raise RunnerError("bad_response")

        def version(value: Any) -> Optional[str]:
            return value if isinstance(value, str) and 0 < len(value) <= 32 else None

        providers = data.get("providers")
        return {
            "runner_version": version(data.get("runner_version")),
            "prowler_version": version(data.get("prowler_version")),
            "powershell": data.get("powershell") is True,
            "providers": [p for p in (providers if isinstance(providers, list) else []) if p in PROVIDERS],
            "max_concurrent": _int(data.get("max_concurrent")),
            "running": _int(data.get("running")),
        }

    async def connection_test(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """``{"ok", "code", "prowler_error"}``: the runner's verdict on the credentials."""
        data = await self._request("POST", "/v1/connection-test", body=payload, timeout=CONNECTION_TEST_TIMEOUT)
        if not isinstance(data, dict) or not isinstance(data.get("ok"), bool):
            raise RunnerError("bad_response")
        code = data.get("code")
        name = data.get("prowler_error")
        return {
            "ok": data["ok"],
            "code": code if isinstance(code, str) and RUNNER_CODE.match(code) and not data["ok"] else None,
            "prowler_error": name if isinstance(name, str) and EXCEPTION_NAME.match(name) else None,
        }

    async def start_scan(self, payload: Dict[str, Any]) -> RunnerJob:
        return parse_job(await self._request("POST", "/v1/scans", body=payload))

    async def scan_status(self, job_id: str) -> RunnerJob:
        job = parse_job(await self._request("GET", self._job_path(job_id)))
        if job.job_id != job_id:
            raise RunnerError("bad_response")
        return job

    async def summary(self, job_id: str) -> Dict[str, Any]:
        data = await self._request("GET", self._job_path(job_id, "/summary"), timeout=STREAM_READ_TIMEOUT, max_bytes=MAX_SUMMARY_BYTES)
        if not isinstance(data, dict):
            raise RunnerError("bad_response")
        return data

    @asynccontextmanager
    async def findings(self, job_id: str) -> AsyncIterator[AsyncIterator[Any]]:
        """The scan's FAIL and MANUAL findings, one parsed JSON value per line."""
        async with self._stream(self._job_path(job_id, "/findings")) as response:
            yield self._lines(response)

    @staticmethod
    async def _lines(response: httpx.Response) -> AsyncIterator[Any]:
        pending = b""
        async for chunk in raw_chunks(response):
            pending += chunk
            *lines, pending = pending.split(b"\n")
            for line in lines:
                if line.strip():
                    yield _parse_line(line)
            if len(pending) > MAX_FINDING_LINE_BYTES:
                raise RunnerError("bad_response")
        if pending.strip():
            yield _parse_line(pending)

    @asynccontextmanager
    async def artifact(self, job_id: str, kind: str) -> AsyncIterator[httpx.Response]:
        """Prowler's HTML or CSV report, as a response to read raw."""
        if kind not in ARTIFACT_KINDS:
            raise RunnerError("not_found")
        async with self._stream(self._job_path(job_id, f"/artifacts/{kind}")) as response:
            yield response

    async def delete_scan(self, job_id: str) -> None:
        """Stop the job if it runs, and delete its files. A job the runner doesn't hold is already gone."""
        try:
            await self._request("DELETE", self._job_path(job_id))
        except RunnerError as error:
            if error.reason != "not_found":
                raise

    async def compliance_catalog(self, provider: str) -> Dict[str, Any]:
        """The frameworks Prowler knows for ``provider``, kept an hour (they change only with the image)."""
        if provider not in PROVIDERS:
            raise RunnerError("not_found")
        cached = _catalog_cache.get(provider)
        if cached and time.monotonic() - cached[0] < CATALOG_TTL_SECONDS:
            return cached[1]
        data = await self._request("GET", f"/v1/compliance/{provider}", timeout=STREAM_READ_TIMEOUT, max_bytes=MAX_CATALOG_BYTES)
        if not isinstance(data, dict) or not isinstance(data.get("frameworks"), list):
            raise RunnerError("bad_response")
        _catalog_cache[provider] = (time.monotonic(), data)
        return data


def _parse_line(line: bytes) -> Any:
    try:
        return json.loads(line)
    except ValueError:
        return None
