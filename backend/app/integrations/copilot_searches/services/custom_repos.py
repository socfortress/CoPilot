"""Per-tenant *custom rule repo* pointers, stored in MinIO.

Each client keeps their own detection rules in their own GitHub repo (never a
CoPilot DB). The only CoPilot-side state is a small per-tenant pointer — repo,
branch, optional read token — which we persist in MinIO (reusing existing infra;
no shared-DB schema change). RulesCache reads these to pull each client's rules
the same way it pulls the canonical catalog.

Object layout: bucket ``copilot-searches``, key ``custom-repos/<customer_code>.json``.
"""
from __future__ import annotations

import io
import json
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import aiohttp
from loguru import logger

from app.data_store.data_store_session import create_session

BUCKET = "copilot-searches"
PREFIX = "custom-repos/"


def _object_name(customer_code: str) -> str:
    return f"{PREFIX}{customer_code}.json"


async def _ensure_bucket(client) -> None:
    if not await client.bucket_exists(BUCKET):
        await client.make_bucket(BUCKET)
        logger.info(f"[custom-repos] created MinIO bucket {BUCKET}")


def _normalize(cfg: Dict[str, Any], customer_code: str) -> Dict[str, Any]:
    """Coerce a stored/loaded record into a stable shape."""
    return {
        "customer_code": customer_code,
        "repo": (cfg.get("repo") or "").strip(),  # "owner/name"
        "branch": (cfg.get("branch") or "main").strip() or "main",
        "token": cfg.get("token") or None,  # optional read PAT (private repos)
        "enabled": bool(cfg.get("enabled", True)),
    }


async def set_custom_repo(customer_code: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Create/replace a customer's custom-repo pointer."""
    record = _normalize(cfg, customer_code)
    body = json.dumps(record).encode("utf-8")
    client = await create_session()
    await _ensure_bucket(client)
    await client.put_object(
        bucket_name=BUCKET,
        object_name=_object_name(customer_code),
        data=io.BytesIO(body),
        length=len(body),
        content_type="application/json",
    )
    logger.info(f"[custom-repos] saved pointer for {customer_code}: {record['repo']}@{record['branch']}")
    return record


async def get_custom_repo(customer_code: str) -> Optional[Dict[str, Any]]:
    """One customer's pointer, or None if unset."""
    client = await create_session()
    if not await client.bucket_exists(BUCKET):
        return None
    try:
        await client.stat_object(BUCKET, _object_name(customer_code))
    except Exception:
        return None
    async with aiohttp.ClientSession() as session:
        resp = await client.get_object(BUCKET, _object_name(customer_code), session)
        data = await resp.read()
        resp.close()
    try:
        return _normalize(json.loads(data), customer_code)
    except (ValueError, TypeError):
        return None


async def list_custom_repos() -> List[Dict[str, Any]]:
    """All configured pointers."""
    client = await create_session()
    if not await client.bucket_exists(BUCKET):
        return []
    out: List[Dict[str, Any]] = []
    async with aiohttp.ClientSession() as session:
        objects = client.list_objects(BUCKET, prefix=PREFIX, recursive=True)
        async for obj in objects:
            name = obj.object_name
            if not name.endswith(".json"):
                continue
            code = name[len(PREFIX):-len(".json")]
            try:
                resp = await client.get_object(BUCKET, name, session)
                data = await resp.read()
                resp.close()
                out.append(_normalize(json.loads(data), code))
            except Exception as exc:  # noqa: BLE001 — skip a bad record, keep the rest
                logger.warning(f"[custom-repos] skipping unreadable {name}: {exc}")
    return out


async def delete_custom_repo(customer_code: str) -> None:
    """Remove a customer's pointer (does not touch their GitHub repo)."""
    client = await create_session()
    if not await client.bucket_exists(BUCKET):
        return
    try:
        await client.remove_object(BUCKET, _object_name(customer_code))
        logger.info(f"[custom-repos] deleted pointer for {customer_code}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[custom-repos] delete failed for {customer_code}: {exc}")


async def test_repo_fetch(repo: str, branch: str = "main", token: Optional[str] = None) -> Dict[str, Any]:
    """Dry-run a repo pull: can we reach it, and how many detection YAMLs does it hold?

    Used by the Custom repos UI's "Test" button so a bad repo/branch/token is
    caught at configuration time instead of silently failing at refresh.
    """
    import os

    import httpx

    headers = {"Accept": "application/vnd.github+json"}
    tok = token or os.getenv("GITHUB_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    try:
        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            resp = await client.get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1")
            if resp.status_code == 404:
                return {"ok": False, "rules_found": 0, "error": "Repo or branch not found (or the token lacks access)."}
            if resp.status_code in (401, 403):
                return {"ok": False, "rules_found": 0, "error": f"GitHub rejected the token ({resp.status_code})."}
            resp.raise_for_status()
            tree = resp.json().get("tree", [])
            n = sum(
                1
                for item in tree
                if item.get("type") == "blob"
                and item.get("path", "").startswith("detections/")
                and item.get("path", "").endswith((".yaml", ".yml"))
            )
            return {"ok": True, "rules_found": n, "error": None}
    except httpx.HTTPError as exc:
        return {"ok": False, "rules_found": 0, "error": f"Could not reach GitHub: {exc}"}


def redact(record: Dict[str, Any]) -> Dict[str, Any]:
    """Copy of a record safe to return over the API (token presence, not value)."""
    return {
        "customer_code": record.get("customer_code"),
        "repo": record.get("repo"),
        "branch": record.get("branch"),
        "enabled": record.get("enabled", True),
        "has_token": bool(record.get("token")),
    }
