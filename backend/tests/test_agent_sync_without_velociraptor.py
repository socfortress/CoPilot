"""Regression tests for issue #1045 — agent sync must not 500 without Velociraptor.

A deployment where only the Wazuh Manager connector is verified is supported:
the Wazuh agents are still collected and written to the database, and the
Velociraptor half of the sync is skipped instead of raising.

These are pure unit tests against the sync service — no DB or app wiring; the
connector check and the Velociraptor fetches are monkeypatched.

Run with: cd backend && python -m pytest tests/test_agent_sync_without_velociraptor.py
"""

import asyncio
import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.agents.services.sync as sync  # noqa: E402


def test_sync_velociraptor_skipped_when_connector_unverified(monkeypatch):
    called = {"orgs": False}

    async def fake_verified():
        return False

    async def fake_orgs():
        called["orgs"] = True
        raise AssertionError("Velociraptor must not be queried when unverified")

    monkeypatch.setattr(sync, "is_velociraptor_verified", fake_verified)
    monkeypatch.setattr(sync, "fetch_velociraptor_organizations", fake_orgs)

    response = asyncio.run(sync.sync_agents_velociraptor())

    assert response.success is True
    assert "not verified" in response.message
    assert called["orgs"] is False


def test_sync_velociraptor_skipped_when_org_collection_fails(monkeypatch):
    async def fake_verified():
        return True

    async def fake_orgs():
        raise RuntimeError("gRPC channel unavailable")

    monkeypatch.setattr(sync, "is_velociraptor_verified", fake_verified)
    monkeypatch.setattr(sync, "fetch_velociraptor_organizations", fake_orgs)

    response = asyncio.run(sync.sync_agents_velociraptor())

    assert response.success is True
    assert "gRPC channel unavailable" in response.message
