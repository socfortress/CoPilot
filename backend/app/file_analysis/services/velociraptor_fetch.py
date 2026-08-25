"""Fetch a target file (from a flow, or by collecting it) into local scratch.

Built on CoPilot's existing Velociraptor connector via ``UniversalService`` — it
already loads the connector config, opens the gRPC channel, and runs VQL. This
module only RETRIEVES bytes + hashes; it never opens or executes the fetched file
(see CLAUDE.md -> File Analysis).

File bytes are read with the canonical pyvelociraptor pattern: ``uploads()`` gives
each uploaded file's server-side filestore path in ``file_store``, and
``read_file(accessor='fs')`` reads it over the API. The exact ``uploads()`` row
shape varies across Velociraptor versions (issue #1587) — we log the row keys on a
miss so it can be adapted to the deployed server.
"""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import os
import tempfile
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import pyvelociraptor
from loguru import logger

from app.connectors.velociraptor.utils.universal import UniversalService

CONNECTOR_NAME = "Velociraptor"


@dataclasses.dataclass
class LocalFile:
    path: str
    sha256: str
    md5: str
    original_filename: str
    size: int
    source_host: str
    source_flow: str
    collected_context: Dict[str, Any] = dataclasses.field(default_factory=dict)


class VelociraptorFetchError(Exception):
    """Raised on unrecoverable fetch failures (config, gRPC, missing file)."""


def _local_api_config() -> Optional[str]:
    """A Velociraptor ``api.config.yaml`` on THIS host, used as a fallback when the
    connector's stored path is stale.

    The connector's ``connector_api_key`` is an absolute PATH to the api config; on a
    shared dev DB it frequently reverts to another machine's path (e.g. a previous
    developer's ``/Users/<x>/.../api.config.yaml``) that doesn't exist here, which
    silently breaks live agent status + collection. Prefer ``VELOCIRAPTOR_API_CONFIG``,
    else the conventional ``backend/data/api.config.yaml``.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.getenv("VELOCIRAPTOR_API_CONFIG", ""),
        os.path.abspath(os.path.join(here, "..", "..", "..", "data", "api.config.yaml")),  # backend/data/
        os.path.join(os.getcwd(), "data", "api.config.yaml"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    return None


async def _service() -> UniversalService:
    try:
        return await UniversalService.create(CONNECTOR_NAME)
    except Exception as exc:
        # The connector's stored api-config PATH may not exist on this host (a stale
        # absolute path from another machine). Fall back to a local config so agent
        # status + collection keep working WITHOUT a DB edit (which would just revert).
        local = _local_api_config()
        if local:
            try:
                svc = UniversalService()
                svc.connector_api_key = local
                svc.config = pyvelociraptor.LoadConfigFile(local)
                await svc.setup_grpc_channel_and_stub()
                logger.warning(f"Velociraptor connector config unusable ({exc}); using local config {local}")
                return svc
            except Exception as exc2:
                raise VelociraptorFetchError(f"Velociraptor connect failed (connector + local fallback {local}): {exc2}")
        raise VelociraptorFetchError(f"could not connect to Velociraptor connector: {exc}")


async def resolve_client_id(hostname: str) -> Optional[str]:
    """Resolve a hostname to a client_id; most-recently-seen wins."""
    svc = await _service()
    vql = f"SELECT client_id, last_seen_at FROM clients(search='host:{hostname}') ORDER BY last_seen_at DESC"
    try:
        res = await asyncio.to_thread(svc.execute_query, vql)
    except Exception as exc:
        logger.error(f"resolve_client_id failed for {hostname!r}: {exc}")
        return None
    rows = res.get("results", []) if isinstance(res, dict) else []
    return rows[0]["client_id"] if rows else None


# A client is considered "online" if it checked in within this window. Velociraptor
# has no boolean online flag in clients(); we derive it from last_seen_at (µs).
_ONLINE_WINDOW_US = 15 * 60 * 1_000_000  # 15 minutes


def is_online(last_seen_us: int) -> bool:
    """True if a client's last check-in (µs epoch) is within the online window."""
    if not last_seen_us:
        return False
    return (time.time() * 1_000_000 - float(last_seen_us)) < _ONLINE_WINDOW_US


def bare_client_id(velociraptor_id: str) -> str:
    """The raw Velociraptor client_id (``C.<hex>``) from CoPilot's stored value.

    CoPilot's Agents table stores ``velociraptor_id`` as either the bare id or, for
    multi-org servers, ``<client_id>-<orglabel>`` (e.g. ``C.475d…-OL680``). Client
    ids never contain a dash, so splitting on the first dash yields the raw id.
    """
    if not velociraptor_id:
        return velociraptor_id
    return velociraptor_id.split("-", 1)[0]


async def live_last_seen_map() -> Dict[str, int]:
    """Fresh ``{client_id -> last_seen_at(µs)}`` from Velociraptor, for online status.

    Agent tenancy comes from CoPilot's Agents table, but that table's
    ``velociraptor_last_seen`` lags (only as new as the last sync). Online status is
    derived from this live ``clients()`` query instead so the dropdown dots are real.
    """
    svc = await _service()
    try:
        res = await asyncio.to_thread(svc.execute_query, "SELECT client_id, last_seen_at FROM clients()")
    except Exception as exc:
        logger.warning(f"live_last_seen_map failed: {exc}")
        return {}
    rows = res.get("results", []) if isinstance(res, dict) else []
    return {r.get("client_id"): int(r.get("last_seen_at") or 0) for r in rows if r.get("client_id")}


def _client_os(svc: UniversalService, client_id: str) -> str:
    """Best-effort OS family ('windows' | 'linux' | 'darwin') for a client_id."""
    safe = client_id.replace("'", "''")
    try:
        res = svc.execute_query("SELECT os_info.system AS os FROM clients() WHERE client_id='%s'" % safe)
    except Exception as exc:
        logger.warning(f"_client_os failed for {client_id}: {exc}")
        return ""
    rows = res.get("results", []) if isinstance(res, dict) else []
    return (rows[0].get("os") if rows else "").lower()


async def fetch_from_flow(client_id: str, flow_id: str) -> List[LocalFile]:
    """Fetch every uploaded file from an existing flow (one LocalFile each)."""
    cap = int(os.getenv("FILE_ANALYSIS_MAX_FLOW_FILES", "25"))
    svc = await _service()
    try:
        rows = await asyncio.to_thread(_read_uploads, svc, client_id, flow_id)
    except Exception as exc:
        raise VelociraptorFetchError(f"failed to read flow uploads: {exc}")
    results: List[LocalFile] = []
    for row in rows[:cap]:
        local = await asyncio.to_thread(_download_one, svc, row, flow_id)
        if local:
            results.append(local)
    if len(rows) > cap:
        logger.warning(f"flow {flow_id} had {len(rows)} uploads; truncated to {cap}")
    return results


# OS family -> the built-in FileFinder artifact that can upload a matched file.
# (The old Custom.Sandbox.CollectFile artifact does not exist on stock servers.)
_FINDER_BY_OS = {
    "windows": "Windows.Search.FileFinder",
    "linux": "Linux.Search.FileFinder",
    "darwin": "MacOS.Search.FileFinder",
}


def _finder_artifact(os_name: str) -> str:
    return _FINDER_BY_OS.get(os_name, "Linux.Search.FileFinder")


def _finder_vql(client_id: str, os_name: str, target_path: str, upload: bool) -> str:
    """Build FileFinder collect_client VQL, per OS.

    ``upload=True`` pulls the file bytes (``Upload_File=Y``) for analysis;
    ``upload=False`` only enumerates matches with hashes (``Upload_File=N``) — used
    by the picker so a glob lists candidates without transferring every file.

    Linux/macOS FileFinder take a single ``SearchFilesGlob``; Windows takes a CSV
    ``SearchFilesGlobTable`` (``Glob\\n<path>\\n``), embedded as a VQL backtick raw
    string so the newline is literal.
    """
    artifact = _finder_artifact(os_name)
    up = "Y" if upload else "N"
    if os_name == "windows":
        glob = target_path.replace("`", "")  # backticks would close the raw string
        env = "dict(SearchFilesGlobTable=`Glob\n%s\n`, Upload_File='%s', Calculate_Hash='Y')" % (glob, up)
    else:
        safe = target_path.replace("'", "''")
        env = "dict(SearchFilesGlob='%s', Upload_File='%s', Calculate_Hash='Y')" % (safe, up)
    return "SELECT collect_client(client_id='%s', artifacts=['%s'], env=%s) AS Flow FROM scope()" % (client_id, artifact, env)


def _wait_for_flow(svc: UniversalService, client_id: str, flow_id: str, timeout: int) -> None:
    """Poll ``uploads(flow_id=...)`` until the collected file appears, or timeout.

    This is the only dependable readiness signal across server versions: ``flows()``
    does not reliably expose ``flow_id`` for correlation on all builds (observed
    returning NULL), but ``uploads(flow_id=...)`` returns the row as soon as the
    file is finalized. If nothing shows within ``timeout`` we fall through and let
    the caller's :func:`fetch_from_flow` report "no file" (deleted / glob missed /
    symlink not captured).
    """
    safe = client_id.replace("'", "''")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            res = svc.execute_query("SELECT * FROM uploads(client_id='%s', flow_id='%s')" % (safe, flow_id))
            rows = res.get("results", []) if isinstance(res, dict) else []
            if rows:
                logger.info(f"[velo] flow {flow_id} has {len(rows)} upload(s); ready")
                return
        except Exception as exc:
            logger.warning(f"[velo] upload poll error ({flow_id}): {exc}")
        time.sleep(3)
    logger.warning(f"[velo] flow {flow_id} produced no upload within {timeout}s")


async def collect_and_fetch(client_id: str, target_path: str, customer_code: str) -> Optional[LocalFile]:
    """Collect a specific file from a host, then fetch it. None if the file is gone.

    Picks the correct OS FileFinder automatically, launches the collection, waits
    for the flow, then reuses :func:`fetch_from_flow` to read the uploaded bytes.
    """
    svc = await _service()
    os_name = await asyncio.to_thread(_client_os, svc, client_id)
    vql = _finder_vql(client_id, os_name, target_path, upload=True)
    logger.info(f"[velo] collecting {target_path!r} from {client_id} (os={os_name or 'unknown'})")
    try:
        res = await asyncio.to_thread(svc.execute_query, vql)
    except Exception as exc:
        raise VelociraptorFetchError(f"collect_client failed: {exc}")
    flow_id = _extract_flow_id(res.get("results", []) if isinstance(res, dict) else [])
    if not flow_id:
        raise VelociraptorFetchError("collect_client returned no flow id")

    timeout = int(os.getenv("FILE_ANALYSIS_COLLECT_TIMEOUT", "180"))
    await asyncio.to_thread(_wait_for_flow, svc, client_id, flow_id, timeout)

    files = await fetch_from_flow(client_id, flow_id)
    if not files:
        # Race: dropper deleted the file before collection, or the glob matched
        # nothing (see CLAUDE.md -> File Analysis).
        logger.info(f"collect_and_fetch: no file recovered for {target_path} (deleted or not found)")
        return None
    return files[0]


def _match_from_source_row(row: dict) -> Optional[Dict[str, Any]]:
    """Shape one FileFinder result row into a picker candidate (no bytes)."""
    path = row.get("OSPath") or row.get("_FullPath") or row.get("FullPath") or row.get("Path")
    if not isinstance(path, str) or not path:
        return None
    hashes = row.get("Hash") or {}
    sha256 = hashes.get("SHA256") if isinstance(hashes, dict) else None
    return {
        "path": path,
        "name": os.path.basename(path.replace("\\", "/").rstrip("/")) or path,
        "size": int(row.get("Size") or 0),
        "sha256": sha256 or "",
    }


def _wait_and_read_source(svc: UniversalService, client_id: str, flow_id: str, artifact: str, timeout: int) -> List[dict]:
    """Poll ``source(flow_id=..., artifact=...)`` until the FileFinder rows appear.

    Mirrors :func:`_wait_for_flow` but for enumerate (no upload): the result rows
    are the readiness signal. Returns [] if the glob matched nothing within timeout.
    """
    safe = client_id.replace("'", "''")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            res = svc.execute_query("SELECT * FROM source(client_id='%s', flow_id='%s', artifact='%s')" % (safe, flow_id, artifact))
            rows = res.get("results", []) if isinstance(res, dict) else []
            if rows:
                return rows
        except Exception as exc:
            logger.warning(f"[velo] source poll error ({flow_id}): {exc}")
        time.sleep(2)
    return []


async def enumerate_matches(client_id: str, target_path: str) -> List[Dict[str, Any]]:
    """List files matching ``target_path`` on a host WITHOUT pulling their bytes.

    Runs the OS FileFinder with ``Upload_File=N`` (hashes only) so a glob returns
    every candidate (path/name/size/sha256) for the operator to pick from. The
    chosen paths are then analyzed individually via :func:`collect_and_fetch`.
    """
    svc = await _service()
    os_name = await asyncio.to_thread(_client_os, svc, client_id)
    vql = _finder_vql(client_id, os_name, target_path, upload=False)
    logger.info(f"[velo] enumerating {target_path!r} on {client_id} (os={os_name or 'unknown'})")
    try:
        res = await asyncio.to_thread(svc.execute_query, vql)
    except Exception as exc:
        raise VelociraptorFetchError(f"enumerate collect_client failed: {exc}")
    flow_id = _extract_flow_id(res.get("results", []) if isinstance(res, dict) else [])
    if not flow_id:
        raise VelociraptorFetchError("enumerate returned no flow id")

    cap = int(os.getenv("FILE_ANALYSIS_MAX_FLOW_FILES", "25"))
    timeout = int(os.getenv("FILE_ANALYSIS_ENUM_TIMEOUT", "90"))
    rows = await asyncio.to_thread(_wait_and_read_source, svc, client_id, flow_id, _finder_artifact(os_name), timeout)
    matches = [m for m in (_match_from_source_row(r) for r in rows) if m]
    logger.info(f"[velo] enumerate matched {len(matches)} file(s) for {target_path!r}")
    return matches[:cap]


# --- helpers ---------------------------------------------------------------
# Candidate columns in an uploads() row that hold the SERVER-side filestore path.
# Names vary across Velociraptor versions (issue #1587); we try each until a read
# succeeds, logging the real row shape so it can be pinned for the deployed server.
_PATH_COLUMNS = ("file_store", "_FileStore", "FileStore", "vfs_path", "_Path", "Path", "OSPath")
_READ_ACCESSORS = ("fs", "collector")


def _read_uploads(svc: UniversalService, client_id: str, flow_id: str) -> List[dict]:
    """List the flow's uploaded files (no read_file — done per-row for robustness)."""
    vql = "SELECT * FROM uploads(client_id='%s', flow_id='%s')" % (client_id, flow_id)
    res = svc.execute_query(vql)
    rows = res.get("results", []) if isinstance(res, dict) else []
    logger.info(f"[velo] uploads() returned {len(rows)} row(s) for flow {flow_id}")
    if rows:
        logger.info(f"[velo] uploads() first-row columns: {list(rows[0].keys())}")
    return rows


# Columns that may hold the ORIGINAL filename, in preference order. Newer servers
# expose it as upload_name/Name; the deployed 0.6/0.7 uploads() row only carries the
# source path in client_path (verified live), so we fall back to its basename — this
# preserves the extension that Tier 1 needs for type routing and the UI label.
_NAME_COLUMNS = ("upload_name", "Name", "client_path", "vfs_path", "_Components")


def _upload_name(row: dict) -> str:
    for key in _NAME_COLUMNS:
        val = row.get(key)
        if isinstance(val, list) and val:
            val = val[-1]  # _Components: last element is the filename
        if isinstance(val, str) and val:
            base = os.path.basename(val.replace("\\", "/").rstrip("/"))
            if base:
                return base
    return "sample"


def _candidate_paths(row: dict) -> List[str]:
    paths: List[str] = []
    for key in _PATH_COLUMNS:
        val = row.get(key)
        if isinstance(val, list) and val:
            paths.append(str(val[0]))
        elif isinstance(val, str) and val:
            paths.append(val)
    return paths


def _download_one(svc: UniversalService, row: dict, flow_id: str) -> Optional[LocalFile]:
    """Read one uploaded file's bytes, trying each candidate path + accessor."""
    name = _upload_name(row)
    data = None
    used = ""
    for path in _candidate_paths(row):
        safe = path.replace("'", "''")
        for accessor in _READ_ACCESSORS:
            try:
                res = svc.execute_query(
                    "SELECT read_file(filename='%s', accessor='%s') AS Data FROM scope()" % (safe, accessor),
                )
                out = res.get("results", []) if isinstance(res, dict) else []
                if out and out[0].get("Data"):
                    data, used = out[0]["Data"], f"{accessor}:{path}"
                    break
            except Exception as exc:
                logger.warning(f"[velo] read_file({accessor}, {path}) failed: {exc}")
        if data:
            break

    if not data:
        logger.warning(f"[velo] no bytes for upload '{name}'; row columns={list(row.keys())}")
        return None
    logger.info(f"[velo] read {len(data)} chars for '{name}' via {used}")

    raw = data.encode("latin-1", errors="replace") if isinstance(data, str) else bytes(data)
    scratch = os.getenv("FILE_ANALYSIS_SCRATCH", tempfile.gettempdir())
    fd, path = tempfile.mkstemp(prefix="velo_", dir=scratch)
    with os.fdopen(fd, "wb") as fh:
        fh.write(raw)
    return LocalFile(
        path=path,
        sha256=hashlib.sha256(raw).hexdigest(),
        md5=hashlib.md5(raw).hexdigest(),
        original_filename=str(name),
        size=len(raw),
        source_host="",
        source_flow=flow_id,
        collected_context={},
    )


def _extract_flow_id(rows: List[dict]) -> str:
    for row in rows:
        flow = row.get("Flow")
        if isinstance(flow, dict):
            return flow.get("flow_id", "") or flow.get("FlowId", "")
        if isinstance(flow, str) and flow.startswith("F."):
            return flow
    return ""
