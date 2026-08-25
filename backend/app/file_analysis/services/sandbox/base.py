"""Sandbox backend interface + normalized summary shape.

Pure types — no DB, no HTTP. The ``CapeSummary`` is what ``summarize()`` returns
and is what the UI renders in the Detonation / Network tabs.
"""
from __future__ import annotations

import dataclasses
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Protocol
from typing import runtime_checkable


class NotEnabled(Exception):
    """Raised when a detonation operation is attempted on a disabled backend."""


@dataclasses.dataclass
class CapeSummary:
    """Normalized detonation result surfaced in the Detonation/Network tabs."""

    task_id: Optional[int] = None
    malscore: float = 0.0
    family: str = ""
    signatures: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    # C2 = endpoints recovered from an extracted malware CONFIG only. Never fill these
    # from observed traffic — a "C2 contacted" signal raises the verdict to malicious.
    c2_ips: List[str] = dataclasses.field(default_factory=list)
    c2_domains: List[str] = dataclasses.field(default_factory=list)
    dropped: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    screenshots: List[str] = dataclasses.field(default_factory=list)
    # --- richer fields (populated from the CAPE report) ---
    duration: int = 0  # analysis seconds
    machine: str = ""  # "cape1 (linux)"
    package: str = ""  # CAPE package used
    verdict: str = ""  # clean/suspicious/malicious (derived)
    processes: List[Dict[str, Any]] = dataclasses.field(default_factory=list)  # {name,pid,ppid,command_line}
    hosts: List[str] = dataclasses.field(default_factory=list)  # every contacted IP (observed, NOT C2)
    domains: List[str] = dataclasses.field(default_factory=list)  # every observed domain (observed, NOT C2)
    dns: List[Dict[str, Any]] = dataclasses.field(default_factory=list)  # {request, answers:[...]}
    http: List[Dict[str, Any]] = dataclasses.field(default_factory=list)  # {method, host, uri}
    connections: List[Dict[str, Any]] = dataclasses.field(default_factory=list)  # {proto,dst,dport}
    ttps: List[Dict[str, Any]] = dataclasses.field(default_factory=list)  # {id, signature}
    payloads: List[Dict[str, Any]] = dataclasses.field(default_factory=list)  # {name, sha256, type}
    errors: List[str] = dataclasses.field(default_factory=list)  # CAPE debug errors
    # --- full behavioural record: literally what the sample DID on the host, so an
    #     analyst can judge for themselves rather than trust a score. Each list is a
    #     category from CAPE's behaviour.summary (files/registry/mutexes/services/…).
    behavior: Dict[str, List[str]] = dataclasses.field(default_factory=dict)
    enhanced: List[Dict[str, Any]] = dataclasses.field(default_factory=list)  # human-readable event stream
    dead_hosts: List[str] = dataclasses.field(default_factory=list)  # attempted-but-unreachable endpoints

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@runtime_checkable
class SandboxBackend(Protocol):
    """The pluggable Tier 2 contract (see CLAUDE.md -> File Analysis)."""

    async def available(self) -> bool:
        ...

    async def find_by_sha256(self, sha256: str) -> Optional[str]:
        ...

    async def submit(self, sample: bytes, filename: str, package: str, customer_code: str, source_flow: str) -> str:
        ...

    async def wait_for_report(self, job_ref: str) -> None:
        ...

    async def get_report(self, job_ref: str) -> dict:
        ...

    async def get_screenshots(self, job_ref: str, limit: int = 24) -> list[bytes]:
        ...
