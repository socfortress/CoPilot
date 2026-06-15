"""
Lightweight build-time bytecode integrity check.

When the backend image is built with ``COMPILE_BYTECODE=true`` (see the
Dockerfile), the licensing / customer-onboarding enforcement modules are
shipped as sourceless ``.pyc`` and a manifest of their hashes is written at
build time. At startup we re-hash those files and compare against the manifest,
so tampering with the compiled enforcement logic inside a running container is
detected (and, when ``INTEGRITY_ENFORCE=true``, blocks boot).

Honest limitations (this is a tripwire, not a lock):
- The repository is public, so the check itself can be removed by anyone
  rebuilding from source. Its value is catching casual in-container edits
  (e.g. editing ``customers.py`` in a running container to drop the seat
  check) and producing a tamper-evident signal.
- Source / development builds carry no manifest, so the check is skipped
  entirely there.
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger

# Backend root: app/middleware/integrity.py -> parents[2] == backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = BACKEND_ROOT / "app" / "middleware" / "integrity_manifest.json"

# Module stems (relative to BACKEND_ROOT, no extension) whose compiled bytecode
# we protect. Keep this scoped to the licensing / customer-onboarding gate.
ENFORCEMENT_MODULES = (
    "app/customers/routes/customers",
    "app/middleware/license",
)


def _resolve(stem: str) -> Optional[Path]:
    """Return the on-disk file for a module stem, preferring compiled .pyc."""
    for ext in (".pyc", ".py"):
        candidate = BACKEND_ROOT / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_hashes() -> Dict[str, str]:
    """Hash the on-disk file backing each enforcement module."""
    hashes: Dict[str, str] = {}
    for stem in ENFORCEMENT_MODULES:
        path = _resolve(stem)
        if path is not None:
            hashes[stem] = _hash_file(path)
    return hashes


def write_manifest() -> None:
    """
    Write the current enforcement-module hashes to the manifest.

    Run at image-build time AFTER bytecode compilation + source strip, so the
    manifest pins the shipped ``.pyc`` files.
    """
    MANIFEST_PATH.write_text(json.dumps(compute_hashes(), indent=2, sort_keys=True))
    logger.info(f"Integrity manifest written to {MANIFEST_PATH}")


def verify() -> List[str]:
    """
    Return the enforcement modules whose hash no longer matches the manifest.

    An empty list means intact OR no manifest present (source build).
    """
    if not MANIFEST_PATH.exists():
        return []
    try:
        expected = json.loads(MANIFEST_PATH.read_text())
    except Exception as e:
        logger.warning(f"Could not read integrity manifest, skipping check: {e}")
        return []
    current = compute_hashes()
    return [stem for stem, digest in expected.items() if current.get(stem) != digest]


def run_integrity_check() -> None:
    """
    Startup hook: verify enforcement-module integrity.

    Logs a warning on mismatch. When ``INTEGRITY_ENFORCE`` is truthy, a mismatch
    raises and prevents the app from booting; otherwise it is report-only.
    """
    if not MANIFEST_PATH.exists():
        logger.debug("No integrity manifest present (source build) - skipping integrity check")
        return

    tampered = verify()
    if not tampered:
        logger.info("Enforcement module integrity verified")
        return

    logger.warning(
        f"Enforcement module integrity check FAILED for: {', '.join(tampered)} - " "the licensing logic may have been modified",
    )
    if os.getenv("INTEGRITY_ENFORCE", "false").lower() in ("1", "true", "yes"):
        raise RuntimeError(f"Integrity enforcement enabled and tampering detected in: {', '.join(tampered)}")
