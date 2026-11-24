"""Connection tests: do these credentials work, before a scan relies on them?

The test is the Prowler SDK's own (``<Provider>.test_connection``), run by
``helpers/test_connection.py`` under Prowler's interpreter in a process of its own.
The credentials reach it on stdin. It answers with one line naming the outcome and,
on failure, the exception's class; Prowler's error message never leaves it.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import signal
import uuid
from pathlib import Path

from runner.commands import connection_test_input
from runner.commands import scan_environment
from runner.errors import MESSAGES
from runner.errors import RunnerError
from runner.errors import classify
from runner.models import M365ScanRequest
from runner.models import ScanRequest
from runner.settings import Settings

HELPER = Path(__file__).resolve().parent / "helpers" / "test_connection.py"
RESULT_PREFIX = "PROWLER_RUNNER_RESULT "
EXCEPTION_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")
MAX_OUTPUT = 1 << 20
MAX_CONCURRENT_TESTS = 4


def _outcome(ok: bool, code: str | None = None, prowler_error: str | None = None) -> dict:
    return {"ok": ok, "code": code, "message": MESSAGES[code] if code else None, "prowler_error": prowler_error}


def parse_result(output: bytes) -> dict:
    """The helper's verdict, from the last result line it printed."""
    for line in reversed(output[-MAX_OUTPUT:].decode("utf-8", "replace").splitlines()):
        if not line.startswith(RESULT_PREFIX):
            continue
        try:
            result = json.loads(line[len(RESULT_PREFIX) :])
        except ValueError:
            break
        if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
            break
        name = result.get("error_class")
        name = name if isinstance(name, str) and EXCEPTION_NAME.match(name) else None
        if result["ok"]:
            return _outcome(True)
        if name in ("ModuleNotFoundError", "ImportError"):
            return _outcome(False, "internal", name)
        return _outcome(False, classify([name] if name else [], default="connection_failed"), name)
    return _outcome(False, "internal")


class ConnectionTester:
    def __init__(self, settings: Settings, helper: Path = HELPER) -> None:
        self.settings = settings
        self.helper = helper
        self._running = 0

    async def test(self, request: ScanRequest) -> dict:
        if isinstance(request, M365ScanRequest) and not request.scope.tenant_domain:
            raise RunnerError(400, "tenant_domain_required")
        if self._running >= MAX_CONCURRENT_TESTS:
            raise RunnerError(429, "busy")
        self._running += 1
        try:
            return await self._run(request)
        finally:
            self._running -= 1

    async def _run(self, request: ScanRequest) -> dict:
        payload = json.dumps(connection_test_input(request)).encode()
        work_dir = self.settings.work_dir / f"conn-{uuid.uuid4().hex}"
        os.mkdir(work_dir, 0o700)
        try:
            process = await asyncio.create_subprocess_exec(
                *self.settings.prowler_python_cmd,
                "-I",
                str(self.helper),
                env=scan_environment(self.settings),
                cwd=str(work_dir),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
            try:
                output, _ = await asyncio.wait_for(process.communicate(payload), self.settings.connection_test_timeout)
            except TimeoutError:
                return _outcome(False, "connection_failed", "TimeoutError")
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                await process.wait()
        finally:
            await asyncio.to_thread(shutil.rmtree, work_dir, True)
        return parse_result(output)
