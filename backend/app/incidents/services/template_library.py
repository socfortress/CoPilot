"""
Service layer for the CoPilot Case-Template **Library** — a read-only catalog
of investigation playbooks authored as YAML in
https://github.com/socfortress/CoPilot-Case-Templates.

The Library is *not* a second template-management system. It is a fetcher +
parser + cache that surfaces YAML-defined playbooks to the admin UI so they
can be imported into the existing ``CaseTemplate`` tables via
``create_template``. Once imported, an entry becomes a normal DB row and is
managed through the existing CRUD endpoints — edits in the UI never flow
back to GitHub, and changes pushed to GitHub never retroactively update
already-imported templates.

Conventions mirrored from
``app.integrations.copilot_searches.services.copilot_searches.RulesCache``:
- In-process cache with a TTL (30 minutes by default).
- ``asyncio.Lock`` around the refresh so concurrent requests don't fire
  duplicate fetches.
- Best-effort YAML validation per file; one bad file does not fail the
  whole library.
- ``GITHUB_TOKEN`` env var (if present) is sent as a Bearer header to dodge
  GitHub's 60/hr unauthenticated rate limit. Same env var the CoPilot
  Searches loader uses.

Library YAML schema (see ``SCHEMA.md`` in the playbook repo):

    key: str            (required, unique across the repo)
    name: str           (required, <= 255 chars)
    description: str    (optional)
    source: str         (optional, <= 50 chars)
    tags: dict          (optional, library-only metadata, not persisted)
    tasks:
      - title: str         (required, <= 500 chars)
        description: str   (optional)
        guidelines: str    (optional)
        mandatory: bool    (optional, default False)
        order_index: int   (required, >= 0)
"""

import asyncio
import os
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import httpx
import yaml
from loguru import logger

# Where the playbook YAMLs live. Owned by SOCFortress; PR-able by anyone with
# repo access. CoPilot only ever reads from this repo — never writes.
GITHUB_REPO = "socfortress/CoPilot-Case-Templates"
GITHUB_BRANCH = "main"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

# Only files matching this prefix-set are treated as library entries. Future
# domain folders (e.g. "linux/", "office365/") can be added here without code
# changes elsewhere.
LIBRARY_PATH_PREFIXES = ("sysmon/",)

# In-memory cache TTL. Matches the CoPilot Searches cache so the operator's
# mental model for "how stale can this be" is the same.
CACHE_TTL_MINUTES = 30


def _github_headers() -> Dict[str, str]:
    """
    Headers sent on every GitHub call. The ``Authorization`` header is added
    only when ``GITHUB_TOKEN`` is set — its absence falls back to the 60/hr
    unauthenticated quota, which is enough for casual use but trips quickly
    on shared dev environments. Same convention as the CoPilot Searches loader.
    """
    headers = {"Accept": "application/vnd.github+json"}
    return headers


class TemplateLibraryCache:
    """In-memory cache of parsed YAML library entries.

    The cache populates lazily on first access (``ensure_loaded``) and refreshes
    after the TTL expires or when ``refresh`` is invoked explicitly (e.g. via
    the ``POST /library/refresh`` admin endpoint).
    """

    def __init__(self) -> None:
        self._entries: Dict[str, Dict[str, Any]] = {}  # key -> parsed dict
        self._invalid_paths: List[str] = []  # paths skipped during last refresh
        self._last_refresh: Optional[datetime] = None
        self._lock = asyncio.Lock()

    # ----- lifecycle -----

    @property
    def is_stale(self) -> bool:
        if self._last_refresh is None:
            return True
        return datetime.utcnow() - self._last_refresh > timedelta(minutes=CACHE_TTL_MINUTES)

    async def ensure_loaded(self) -> None:
        if self.is_stale:
            await self.refresh()

    async def refresh(self) -> int:
        """
        Re-fetch the repo tree and every YAML under a recognised prefix.

        Returns the number of valid entries loaded. Bad YAML files are logged
        and skipped (their paths are recorded in ``invalid_paths``); the
        whole-library refresh never raises on per-file parse errors so a
        single malformed file in the upstream repo doesn't take the feature
        down. Network failures DO bubble up — those should reach the operator.
        """
        async with self._lock:
            logger.info(
                f"Refreshing case-template library from github.com/{GITHUB_REPO}@{GITHUB_BRANCH}",
            )

            entries: Dict[str, Dict[str, Any]] = {}
            invalid: List[str] = []

            async with httpx.AsyncClient(timeout=30.0, headers=_github_headers()) as client:
                tree_url = (
                    f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
                )
                response = await client.get(tree_url)
                response.raise_for_status()
                tree = response.json()

                yaml_paths = [
                    item["path"]
                    for item in tree.get("tree", [])
                    if item.get("type") == "blob"
                    and item.get("path", "").endswith((".yaml", ".yml"))
                    and any(item["path"].startswith(p) for p in LIBRARY_PATH_PREFIXES)
                ]
                logger.info(f"Library tree has {len(yaml_paths)} YAML file(s) to parse")

                # Fan out the per-file fetches; gather lets one slow file
                # block the others without serialising the whole pull.
                tasks = [self._fetch_and_parse(client, p) for p in yaml_paths]
                results = await asyncio.gather(*tasks, return_exceptions=True)

            for path, result in zip(yaml_paths, results):
                if isinstance(result, Exception):
                    logger.warning(f"Library: failed to fetch/parse {path}: {result}")
                    invalid.append(path)
                    continue
                if result is None:
                    invalid.append(path)
                    continue

                entry = result
                key = entry.get("key")
                if not key:
                    logger.warning(f"Library: {path} missing 'key' field, skipping")
                    invalid.append(path)
                    continue
                if key in entries:
                    logger.warning(
                        f"Library: duplicate key '{key}' in {path} "
                        f"(already used by {entries[key].get('_file_path')}), skipping",
                    )
                    invalid.append(path)
                    continue
                entry["_file_path"] = path
                entries[key] = entry

            self._entries = entries
            self._invalid_paths = invalid
            self._last_refresh = datetime.utcnow()
            logger.info(
                f"Library loaded: {len(entries)} valid entr(ies), {len(invalid)} skipped",
            )
            return len(entries)

    async def _fetch_and_parse(
        self,
        client: httpx.AsyncClient,
        path: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch one YAML file, parse it, and run light shape validation."""
        raw_url = f"{GITHUB_RAW_BASE}/{GITHUB_REPO}/{GITHUB_BRANCH}/{path}"
        response = await client.get(raw_url)
        response.raise_for_status()
        try:
            data = yaml.safe_load(response.text)
        except yaml.YAMLError as e:
            logger.warning(f"Library: YAML parse error in {path}: {e}")
            return None

        if not isinstance(data, dict):
            logger.warning(f"Library: {path} top-level is not a mapping, skipping")
            return None

        return _normalize_entry(data)

    # ----- read accessors -----

    @property
    def entries(self) -> Dict[str, Dict[str, Any]]:
        return self._entries

    @property
    def invalid_paths(self) -> List[str]:
        return list(self._invalid_paths)

    @property
    def last_refresh(self) -> Optional[datetime]:
        return self._last_refresh

    def get_entry(self, key: str) -> Optional[Dict[str, Any]]:
        return self._entries.get(key)


# ---------------------------------------------------------------------------
# Normalisation + validation helpers
# ---------------------------------------------------------------------------


def _normalize_entry(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Coerce a raw YAML dict into the canonical library-entry shape. Returns
    ``None`` if the entry is missing required fields, so the caller can skip
    it cleanly. Optional fields are normalised to consistent defaults so the
    downstream Pydantic response model never sees ``None``-vs-missing
    ambiguity.

    Required: ``key``, ``name``, ``tasks`` (may be empty).
    """
    key = data.get("key")
    name = data.get("name")
    if not isinstance(key, str) or not key.strip():
        return None
    if not isinstance(name, str) or not name.strip():
        return None

    raw_tasks = data.get("tasks") or []
    if not isinstance(raw_tasks, list):
        return None

    normalised_tasks: List[Dict[str, Any]] = []
    for raw in raw_tasks:
        if not isinstance(raw, dict):
            continue
        title = raw.get("title")
        order_index = raw.get("order_index")
        if not isinstance(title, str) or not title.strip():
            continue
        if not isinstance(order_index, int) or order_index < 0:
            continue
        normalised_tasks.append(
            {
                "title": title.strip(),
                "description": raw.get("description") or None,
                "guidelines": raw.get("guidelines") or None,
                "mandatory": bool(raw.get("mandatory", False)),
                "order_index": order_index,
            },
        )

    # Sort tasks by their declared order_index up front so import order is
    # deterministic regardless of how the YAML happened to list them.
    normalised_tasks.sort(key=lambda t: t["order_index"])

    tags = data.get("tags")
    if not isinstance(tags, dict):
        tags = {}

    return {
        "key": key.strip(),
        "name": name.strip(),
        "description": data.get("description") or None,
        "source": data.get("source") or None,
        "tags": tags,
        "tasks": normalised_tasks,
    }


# ---------------------------------------------------------------------------
# Module-level singleton + service functions consumed by the routes.
# ---------------------------------------------------------------------------

template_library_cache = TemplateLibraryCache()


async def list_library_entries() -> List[Dict[str, Any]]:
    """Return all library entries currently in cache. Loads on first call."""
    await template_library_cache.ensure_loaded()
    # Sort for a stable display order in the UI; primary key on `key`.
    return sorted(template_library_cache.entries.values(), key=lambda e: e["key"])


async def get_library_entry(key: str) -> Optional[Dict[str, Any]]:
    """Fetch one library entry by its YAML ``key``. Loads on first call."""
    await template_library_cache.ensure_loaded()
    return template_library_cache.get_entry(key)


async def refresh_library() -> Dict[str, Any]:
    """
    Force a re-fetch of the library repo. Returns a small status payload that
    the route layer wraps as the HTTP response.
    """
    count = await template_library_cache.refresh()
    return {
        "loaded": count,
        "invalid_paths": template_library_cache.invalid_paths,
        "last_refresh": template_library_cache.last_refresh,
    }
