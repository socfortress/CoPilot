"""Pluggable sandbox (Tier 2) backend — opt-in, defaults OFF.

``SANDBOX_BACKEND = none | local_vm | remote`` selects the implementation. ``none``
is the default and ships in v1: detonation is entirely dormant. ``local_vm`` and
``remote`` are both CAPEv2 over REST — they differ only in where CAPE runs and how
the network is isolated, not in the client code (see CLAUDE.md -> File Analysis).

This package is pure HTTP + env config — no DB, no CoPilot state.
"""
from __future__ import annotations

import os
import shutil

from loguru import logger

from app.file_analysis.services.sandbox.base import SandboxBackend
from app.file_analysis.services.sandbox.cape import CapeBackend
from app.file_analysis.services.sandbox.null import NullBackend

_PACKAGE_MAP = {
    "pe": "exe",
    "elf": "elf",
    "script": "ps1",
    "pdf": "pdf",
    "office": "doc",
    "lnk": "generic",
    "archive": "zip",
    "email": "generic",
    "html": "html",
    "unknown": "generic",
}


def package_for(filetype: str) -> str:
    """Map a Tier 1 filetype to a CAPE submission package."""
    return _PACKAGE_MAP.get(filetype, "generic")


def _virtualization_available() -> bool:
    """Best-effort check that a hypervisor is present for local_vm."""
    if os.path.exists("/dev/kvm"):
        return True
    # Fallback: some hosts expose virtualization only via cpu flags.
    if shutil.which("kvm-ok") or shutil.which("virsh"):
        return True
    return False


def get_backend() -> SandboxBackend:
    """Return the configured backend. Never silently pretends detonation works."""
    mode = os.getenv("SANDBOX_BACKEND", "none").lower()
    if mode == "none":
        return NullBackend()
    if mode == "remote":
        return CapeBackend()
    if mode == "local_vm":
        if not _virtualization_available():
            logger.error(
                "SANDBOX_BACKEND=local_vm but no hypervisor detected (/dev/kvm absent). "
                "Detonation is VM-based; falling back to 'none'. Use 'remote' or install KVM.",
            )
            return NullBackend()
        return CapeBackend()
    logger.error(f"Unknown SANDBOX_BACKEND={mode!r}; defaulting to 'none'.")
    return NullBackend()
