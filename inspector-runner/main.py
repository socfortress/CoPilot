"""inspector-runner — the ONLY component that spawns inspector containers.

CoPilot's backend never touches the Docker API (CLAUDE.md -> File Analysis
section 1.1). It POSTs a sample + job here; this sidecar spawns ONE hardened,
per-job container through an allowlisting socket proxy, returns the result JSON
(+ PNG previews), and destroys the container. It holds no CoPilot secrets — no DB,
no MinIO keys, no JWT.

Two modes:
  container  (production): spawn a fresh hardened container per job.
  service    (DEV ONLY):   run the analyzers in-process, NO isolation. Refuses to
                           start unless FILE_ANALYSIS_DEV_MODE=true and tags every
                           result {"hardened": false}.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import tempfile
from typing import Any
from typing import Dict

from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from loguru import logger

# --- Config (env only; no secrets) -----------------------------------------
INSPECTOR_MODE = os.getenv("INSPECTOR_MODE", "container")
DEV_MODE = os.getenv("FILE_ANALYSIS_DEV_MODE", "false").lower() == "true"
INSPECTOR_IMAGE = os.getenv("INSPECTOR_IMAGE", "ghcr.io/socfortress/copilot-inspector:latest")
DOCKER_HOST = os.getenv("DOCKER_HOST", "tcp://docker-socket-proxy:2375")
JOB_TIMEOUT = int(os.getenv("INSPECTOR_JOB_TIMEOUT", "180"))
MAX_CONCURRENT = int(os.getenv("INSPECTOR_MAX_CONCURRENT", "2"))
MEM_LIMIT = os.getenv("INSPECTOR_MEM_LIMIT", "1g")
PIDS_LIMIT = int(os.getenv("INSPECTOR_PIDS_LIMIT", "256"))
NANO_CPUS = int(float(os.getenv("INSPECTOR_CPUS", "1.0")) * 1_000_000_000)
# Shared jobs dir visible to both this sidecar and the spawned containers (a named
# volume in compose). Sample + results live under {JOBS_DIR}/{job_id}/.
JOBS_DIR = os.getenv("INSPECTOR_JOBS_DIR", "/jobs")

app = FastAPI(title="inspector-runner", version="1")
_semaphore = asyncio.Semaphore(MAX_CONCURRENT)


@app.on_event("startup")
async def _startup() -> None:
    if INSPECTOR_MODE == "service" and not DEV_MODE:
        raise RuntimeError(
            "INSPECTOR_MODE=service runs analyzers with NO container isolation and is "
            "dev-only. Set FILE_ANALYSIS_DEV_MODE=true to allow it, or use "
            "INSPECTOR_MODE=container in production.",
        )
    logger.info(f"inspector-runner starting: mode={INSPECTOR_MODE} dev={DEV_MODE} max_concurrent={MAX_CONCURRENT}")


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Verify we can reach Docker (via the proxy) and the inspector image exists."""
    if INSPECTOR_MODE == "service":
        return {"status": "ok", "mode": "service", "hardened": False}
    try:
        client = _docker_client()
        client.images.get(INSPECTOR_IMAGE)
        proxy_ok = True
    except Exception as exc:  # image missing or proxy unreachable
        logger.warning(f"health: docker/image check failed: {exc}")
        proxy_ok = False
    return {"status": "ok" if proxy_ok else "degraded", "mode": "container", "image_present": proxy_ok}


@app.post("/inspect")
async def inspect(job: str = Form(...), sample: UploadFile = File(...)) -> Dict[str, Any]:
    """Run one inspection job. ``job`` is the JSON contract (see CLAUDE.md -> File Analysis)."""
    try:
        job_dict = json.loads(job)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid job JSON: {exc}")

    sample_bytes = await sample.read()
    if _semaphore.locked() and _semaphore._value <= 0:  # noqa: SLF001 (bounded queue signal)
        raise HTTPException(status_code=429, detail="inspector busy; retry with backoff")

    async with _semaphore:
        if INSPECTOR_MODE == "service":
            return await _run_in_process(job_dict, sample_bytes)
        return await _run_container(job_dict, sample_bytes)


# --- container mode --------------------------------------------------------
def _docker_client():
    import docker

    return docker.DockerClient(base_url=DOCKER_HOST)


async def _run_container(job: Dict[str, Any], sample_bytes: bytes) -> Dict[str, Any]:
    # Everything travels on stdin/stdout — the sample goes IN base64-encoded in the
    # job, previews come OUT base64-encoded in the result. No shared volume, so no
    # sibling-container mount problem and no cross-job filesystem exposure.
    container_job = dict(job)
    container_job["sample_b64"] = base64.b64encode(sample_bytes).decode()

    loop = asyncio.get_event_loop()
    try:
        payload = await asyncio.wait_for(
            loop.run_in_executor(None, _spawn_and_collect, container_job),
            timeout=JOB_TIMEOUT + 15,
        )
    except asyncio.TimeoutError:
        payload = _timeout_payload(job)

    payload.setdefault("previews_b64", {})
    payload["hardened"] = True
    return payload


def _spawn_and_collect(container_job: Dict[str, Any]) -> Dict[str, Any]:
    """Blocking: spawn ONE hardened container, feed the job on stdin, collect stdout.

    Hardening (all explicit, never daemon defaults): no network, read-only root,
    all caps dropped, no-new-privileges, pids/mem/cpu limits, tmpfs scratch, and
    the container is force-removed after every job.
    """
    import docker

    client = _docker_client()
    try:
        container = client.containers.run(
            INSPECTOR_IMAGE,
            stdin_open=True,
            detach=True,
            network_mode="none",
            read_only=True,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            pids_limit=PIDS_LIMIT,
            mem_limit=MEM_LIMIT,
            nano_cpus=NANO_CPUS,
            tmpfs={"/tmp": "size=512m,exec"},
        )
    except docker.errors.APIError as exc:
        return {"error": f"container spawn failed: {exc}", "analysis_incomplete": True, "verdict_hint": "suspicious"}

    try:
        sock = container.attach_socket(params={"stdin": 1, "stream": 1, "stdout": 1})
        raw = sock._sock if hasattr(sock, "_sock") else sock  # noqa: SLF001
        # Length-prefixed frame: "<n>\n<n bytes of JSON>". We do NOT rely on a stdin
        # half-close (raw.shutdown) for EOF — that does not propagate through the
        # HAProxy socket proxy's tunneled attach, so the container would block forever.
        # The entrypoint reads exactly n bytes and proceeds without needing EOF.
        data = json.dumps(container_job).encode("utf-8")
        raw.sendall(f"{len(data)}\n".encode() + data)
        result = container.wait(timeout=JOB_TIMEOUT)
        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
        exit_code = result.get("StatusCode", -1)
    except Exception as exc:
        stdout, exit_code = "", -1
        logger.warning(f"container run error: {exc}")
    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass

    return _parse_stdout(stdout, exit_code)


def _parse_stdout(stdout: str, exit_code: int) -> Dict[str, Any]:
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                payload = json.loads(line)
                payload["container_exit"] = exit_code
                return payload
            except json.JSONDecodeError:
                continue
    return {
        "error": "no JSON on inspector stdout",
        "container_exit": exit_code,
        "analysis_incomplete": True,
        "verdict_hint": "suspicious",
    }


# --- service (dev) mode ----------------------------------------------------
async def _run_in_process(job: Dict[str, Any], sample_bytes: bytes) -> Dict[str, Any]:
    """Dev-only: run analyzers in this process. NO isolation."""
    import sys

    inspector_dir = os.getenv("INSPECTOR_SRC", "/opt/inspector")
    if inspector_dir not in sys.path:
        sys.path.insert(0, inspector_dir)
    import router  # from the inspector source tree

    tmpdir = tempfile.mkdtemp(prefix="devjob_")
    sample_path = os.path.join(tmpdir, "sample")
    results = os.path.join(tmpdir, "results")
    os.makedirs(results, exist_ok=True)
    with open(sample_path, "wb") as fh:
        fh.write(sample_bytes)
    try:
        result = router.inspect_path(
            sample_path,
            filename=job.get("filename", "sample"),
            customer_code=job.get("customer_code", ""),
            results_dir=results,
            depth=0,
            context=job.get("context") or {},
        )
        payload = result.to_dict()
        # Collect the PNG previews the analyzers wrote (same as container mode).
        payload["previews_b64"] = _collect_previews(results)
    finally:
        _cleanup(tmpdir)
    payload["hardened"] = False
    return payload


# --- helpers ---------------------------------------------------------------
def _collect_previews(results_dir: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not os.path.isdir(results_dir):
        return out
    for name in sorted(os.listdir(results_dir)):
        if name.endswith(".png"):
            with open(os.path.join(results_dir, name), "rb") as fh:
                out[name] = base64.b64encode(fh.read()).decode()
    return out


def _timeout_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sha256": job.get("sha256", ""),
        "filename": job.get("filename", ""),
        "analysis_incomplete": True,
        "flags": ["analysis_incomplete"],
        "verdict_hint": "suspicious",
        "error": "inspector job timed out",
    }


def _cleanup(path: str) -> None:
    import shutil

    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass
