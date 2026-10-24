"""Shared fixtures for the unit tests (not the e2e scripts, which pytest does not collect)."""
import sys
from pathlib import Path

import pytest

# `pytest` as well as `python -m pytest`: the backend directory holds the `app` package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audit.services import audit as audit_service  # noqa: E402


@pytest.fixture(autouse=True)
def audit_rows(monkeypatch):
    """Every audit row a test's code writes, kept here instead of in a database.

    `record_audit_event` writes in a session of its own on the configured engine, i.e. the
    database `.env` names: a unit test must never reach it. A test asserts on the rows by asking
    for this fixture.
    """
    rows = []

    async def persist(entries):
        rows.extend(entries)

    monkeypatch.setattr(audit_service, "_persist", persist)
    return rows
