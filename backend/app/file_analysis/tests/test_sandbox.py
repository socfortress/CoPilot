"""Sandbox backend tests — factory selection, summarize().

Pure: no CAPE server contacted. The report fixture is a trimmed recorded CAPE
JSON shape (see CLAUDE.md -> File Analysis).
"""
from __future__ import annotations

import pytest

from app.file_analysis.services.sandbox import get_backend
from app.file_analysis.services.sandbox import package_for
from app.file_analysis.services.sandbox.cape import CapeBackend
from app.file_analysis.services.sandbox.cape import summarize
from app.file_analysis.services.sandbox.null import NullBackend


def test_factory_defaults_to_null(monkeypatch):
    monkeypatch.delenv("SANDBOX_BACKEND", raising=False)
    assert isinstance(get_backend(), NullBackend)


def test_factory_none_is_null(monkeypatch):
    monkeypatch.setenv("SANDBOX_BACKEND", "none")
    assert isinstance(get_backend(), NullBackend)


def test_local_vm_without_hypervisor_falls_back(monkeypatch):
    monkeypatch.setenv("SANDBOX_BACKEND", "local_vm")
    monkeypatch.setattr("app.file_analysis.services.sandbox._virtualization_available", lambda: False)
    assert isinstance(get_backend(), NullBackend)


def test_remote_selects_cape(monkeypatch):
    monkeypatch.setenv("SANDBOX_BACKEND", "remote")
    assert isinstance(get_backend(), CapeBackend)


@pytest.mark.asyncio
async def test_null_backend_unavailable():
    backend = NullBackend()
    assert await backend.available() is False


def test_package_mapping():
    assert package_for("pe") == "exe"
    assert package_for("office") == "doc"
    assert package_for("script") == "ps1"
    assert package_for("something-else") == "generic"


def test_summarize_extracts_family_c2_mitre():
    report = {
        "info": {"id": 42},
        "malscore": 9.4,
        "CAPE": {"configs": [{"RedLine": {"c2": ["45.10.20.30:443", "evil.example.com"]}}]},
        "signatures": [
            {"name": "Process injection", "severity": 3, "ttp": [{"attack_id": "T1055"}]},
            {"name": "Registry Run key persistence", "ttp": [{"attack_id": "T1547.001"}]},
        ],
        "network": {"hosts": [{"ip": "45.10.20.30"}], "domains": [{"domain": "evil.example.com"}]},
        "dropped": [{"sha256": "a" * 64, "name": "svchost.exe"}],
    }
    summary = summarize(report)
    assert summary.task_id == 42
    assert summary.malscore == 9.4
    assert summary.family == "RedLine"
    assert "45.10.20.30" in summary.c2_ips
    assert "evil.example.com" in summary.c2_domains
    assert any("T1055" in s["mitre"] for s in summary.signatures)
    assert summary.dropped[0]["sha256"] == "a" * 64
