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


@pytest.fixture(autouse=True)
def notifications_stay_off_the_configured_database(monkeypatch):
    """`emit()`'s background task and the outbox open sessions on the configured engine, i.e. the
    database `.env` names: a unit test must never reach it. Here the outbox has no database (its
    writes fail and are logged, as they would with the database down) and the direct-dispatch
    fallback does nothing. A test that wants either points it at its own database."""
    from app.notifications.services import emit as emit_module
    from app.notifications.services import outbox

    class _NoDatabase:
        async def __aenter__(self):
            raise ConnectionRefusedError("unit tests never use the configured database")

        async def __aexit__(self, *exc):
            return False

    async def no_dispatch(event):
        return None

    monkeypatch.setattr(outbox, "new_session", _NoDatabase)
    monkeypatch.setattr(emit_module, "_run", no_dispatch)
