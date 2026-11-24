"""The compliance frameworks this Prowler version knows, for one provider.

Prowler maps each check to framework requirements and writes the mapping on every
finding (``unmapped.compliance``: ``{"CIS-5.0": ["1.1", ...]}``), keyed
``<Framework>-<Version>``, or ``<Framework>`` when the version is empty. A finding
names requirement ids only; their titles come from here, read from the framework
files Prowler ships (``prowler/compliance/<provider>/*.json``) and keyed the same way.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from runner.ocsf import CHECK_ID
from runner.textutil import clean_text

_cache: dict[tuple[str, str], bytes] = {}
_locks: dict[tuple[str, str], asyncio.Lock] = {}


def framework_key(framework: str, version: str) -> str:
    """The key Prowler uses in a finding's compliance mapping."""
    return f"{framework}-{version}" if version else framework


def _requirement(raw: dict) -> dict | None:
    requirement_id = clean_text(raw.get("Id"), 128)
    if not requirement_id:
        return None
    attributes = raw.get("Attributes")
    first = attributes[0] if isinstance(attributes, list) and attributes and isinstance(attributes[0], dict) else {}
    checks = raw.get("Checks")
    return {
        "id": requirement_id,
        "name": clean_text(raw.get("Name"), 256) or None,
        "description": clean_text(raw.get("Description"), 1000),
        "section": clean_text(first.get("Section"), 256) or None,
        "checks": [check for check in (checks if isinstance(checks, list) else []) if isinstance(check, str) and CHECK_ID.match(check)],
    }


def build_catalog(compliance_dir: Path, provider: str, prowler_version: str | None) -> dict:
    frameworks: list[dict] = []
    skipped_files = 0
    directory = compliance_dir / provider
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            skipped_files += 1
            continue
        if not isinstance(data, dict) or str(data.get("Provider", "")).lower() != provider:
            skipped_files += 1
            continue
        framework = clean_text(data.get("Framework"), 128)
        version = clean_text(data.get("Version"), 64)
        if not framework:
            skipped_files += 1
            continue
        raw_requirements = data.get("Requirements")
        requirements = [
            requirement
            for requirement in (
                _requirement(raw) for raw in (raw_requirements if isinstance(raw_requirements, list) else []) if isinstance(raw, dict)
            )
            if requirement
        ]
        frameworks.append(
            {
                "key": framework_key(framework, version),
                "file": path.stem,
                "framework": framework,
                "version": version,
                "name": clean_text(data.get("Name"), 256),
                "description": clean_text(data.get("Description"), 2000),
                "requirements": requirements,
            },
        )
    return {"provider": provider, "prowler_version": prowler_version, "frameworks": frameworks, "skipped_files": skipped_files}


async def catalog_json(compliance_dir: Path, provider: str, prowler_version: str | None) -> bytes:
    """The catalog as JSON, built once per provider and kept (the files change only with the image)."""
    key = (str(compliance_dir), provider)
    if key in _cache:
        return _cache[key]
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        if key not in _cache:
            catalog = await asyncio.to_thread(build_catalog, compliance_dir, provider, prowler_version)
            _cache[key] = json.dumps(catalog, ensure_ascii=True, separators=(",", ":")).encode()
    return _cache[key]


def clear_cache() -> None:
    _cache.clear()
    _locks.clear()
