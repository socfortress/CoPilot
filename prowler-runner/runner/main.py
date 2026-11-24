"""The runner's HTTP API. Start it with ``uvicorn --factory runner.main:create_app``.

Every /v1 route needs ``Authorization: Bearer $PROWLER_RUNNER_TOKEN``. Answers are
``no-store``; errors are ``{"detail": <fixed text>, "code": <code>}``.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from runner import PROVIDERS
from runner import __version__
from runner.compliance import catalog_json
from runner.connection import ConnectionTester
from runner.errors import RunnerError
from runner.errors import http_error_handler
from runner.errors import runner_error_handler
from runner.errors import validation_error_handler
from runner.jobs import JobManager
from runner.models import ScanPayload
from runner.security import require_token
from runner.settings import Settings

logger = logging.getLogger("prowler_runner")


async def detect_prowler_version(settings: Settings) -> str | None:
    """Prowler's version, from its own interpreter (``prowler --version`` would ask GitHub)."""
    try:
        process = await asyncio.create_subprocess_exec(
            *settings.prowler_python_cmd,
            "-I",
            "-c",
            "import importlib.metadata as m; print(m.version('prowler'))",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        output, _ = await asyncio.wait_for(process.communicate(), 30)
    except (OSError, TimeoutError):
        return None
    version = output.decode("utf-8", "replace").strip()
    return version if process.returncode == 0 and 0 < len(version) <= 32 else None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not settings.token_configured:
            logger.warning("PROWLER_RUNNER_TOKEN is missing or shorter than 32 characters: every /v1 request will be refused")
        app.state.prowler_version = await detect_prowler_version(settings)
        manager.prowler_version = app.state.prowler_version
        await manager.startup()
        logger.info("prowler runner %s ready (Prowler %s)", __version__, app.state.prowler_version or "unknown")
        yield
        await manager.shutdown()

    manager = JobManager(settings)
    connections = ConnectionTester(settings)
    app = FastAPI(title="CoPilot Prowler runner", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.prowler_version = None
    app.state.jobs = manager
    app.state.connections = connections
    app.add_exception_handler(RunnerError, runner_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)

    @app.middleware("http")
    async def no_store(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    authorized = [Depends(require_token)]

    @app.get("/healthz")
    async def healthz() -> dict:
        """Liveness, for Docker's health check. Says nothing else."""
        return {"status": "ok"}

    @app.get("/v1/health", dependencies=authorized)
    async def health(request: Request) -> dict:
        return {
            "status": "ok",
            "runner_version": __version__,
            "prowler_version": request.app.state.prowler_version,
            "powershell": shutil.which("pwsh", path=settings.scan_path) is not None,
            "providers": list(PROVIDERS),
            "max_concurrent": settings.max_concurrent,
            "running": manager.active_count(),
            "jobs": len(manager.jobs),
        }

    @app.post("/v1/connection-test", dependencies=authorized)
    async def connection_test(payload: ScanPayload) -> dict:
        return await connections.test(payload.root)

    @app.post("/v1/scans", status_code=202, dependencies=authorized)
    async def start_scan(payload: ScanPayload) -> dict:
        job = await manager.start(payload.root)
        return job.public()

    @app.get("/v1/scans/{job_id}", dependencies=authorized)
    async def scan_status(job_id: str) -> dict:
        return manager.get(job_id).public()

    @app.get("/v1/scans/{job_id}/summary", dependencies=authorized)
    async def scan_summary(job_id: str) -> FileResponse:
        return FileResponse(manager.summary_path(manager.completed(job_id)), media_type="application/json")

    @app.get("/v1/scans/{job_id}/findings", dependencies=authorized)
    async def scan_findings(job_id: str) -> FileResponse:
        """The FAIL and MANUAL findings, one JSON object per line."""
        return FileResponse(manager.findings_path(manager.completed(job_id)), media_type="application/x-ndjson")

    @app.get("/v1/scans/{job_id}/artifacts/{kind}", dependencies=authorized)
    async def scan_artifact(job_id: str, kind: str) -> FileResponse:
        path, media_type, download_name = manager.artifact(manager.completed(job_id), kind)
        return FileResponse(path, media_type=media_type, filename=download_name)

    @app.delete("/v1/scans/{job_id}", status_code=204, dependencies=authorized)
    async def delete_scan(job_id: str) -> Response:
        await manager.delete(job_id)
        return Response(status_code=204)

    @app.get("/v1/compliance/{provider}", dependencies=authorized)
    async def compliance(request: Request, provider: str) -> Response:
        if provider not in PROVIDERS:
            raise RunnerError(404, "unknown_provider")
        content = await catalog_json(settings.compliance_dir, provider, request.app.state.prowler_version)
        return Response(content=content, media_type="application/json")

    return app
