"""The default backend: detonation disabled.

``available()`` is False, so the orchestrator skips Tier 2 entirely and the UI
hides the detonation tabs. Every other method raises :class:`NotEnabled` — calling
them is a programming error, not a runtime condition.
"""
from __future__ import annotations

from typing import Optional

from app.file_analysis.services.sandbox.base import NotEnabled


class NullBackend:
    async def available(self) -> bool:
        return False

    async def find_by_sha256(self, sha256: str) -> Optional[str]:
        return None

    async def submit(self, local_file: str, package: str, customer_code: str, source_flow: str) -> str:
        raise NotEnabled("SANDBOX_BACKEND=none: detonation is disabled")

    async def wait_for_report(self, job_ref: str) -> None:
        raise NotEnabled("SANDBOX_BACKEND=none: detonation is disabled")

    async def get_report(self, job_ref: str) -> dict:
        raise NotEnabled("SANDBOX_BACKEND=none: detonation is disabled")

    async def get_screenshots(self, job_ref: str, limit: int = 24) -> list[bytes]:
        return []
