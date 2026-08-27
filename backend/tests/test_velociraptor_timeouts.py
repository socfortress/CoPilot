"""Velociraptor gRPC deadlines are configurable, and flows get their own.

A flow that ran longer than 30 seconds failed with DEADLINE_EXCEEDED even though
the collection was healthy and still running on the Velociraptor server -- the
gRPC deadline was hardcoded at 30s and shared between ordinary VQL and waiting
for a flow to finish. Those are different kinds of wait: a query hits the
server's datastore and should be quick, while a flow takes as long as the
endpoint needs to run the artifact.

Run with: cd backend && python -m pytest tests/test_velociraptor_timeouts.py
"""

import importlib
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.connectors.velociraptor.utils.universal as universal  # noqa: E402


def _reload(monkeypatch, **env):
    """Re-import the module with `env` applied, since the deadlines are read at import."""
    for key in ("VELOCIRAPTOR_QUERY_TIMEOUT", "VELOCIRAPTOR_FLOW_TIMEOUT"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(universal)


def test_defaults_preserve_the_old_query_deadline(monkeypatch):
    """30s stays the default for ordinary VQL -- this change must not make a
    healthy deployment wait longer on queries that were already fine."""
    module = _reload(monkeypatch)

    assert module.QUERY_TIMEOUT_SECONDS == 30


def test_flow_deadline_defaults_well_above_the_query_one(monkeypatch):
    module = _reload(monkeypatch)

    assert module.FLOW_TIMEOUT_SECONDS == 300
    assert module.FLOW_TIMEOUT_SECONDS > module.QUERY_TIMEOUT_SECONDS


def test_both_deadlines_are_configurable(monkeypatch):
    module = _reload(
        monkeypatch,
        VELOCIRAPTOR_QUERY_TIMEOUT="45",
        VELOCIRAPTOR_FLOW_TIMEOUT="1800",
    )

    assert module.QUERY_TIMEOUT_SECONDS == 45
    assert module.FLOW_TIMEOUT_SECONDS == 1800


@pytest.mark.parametrize("bad", ["", "abc", "0", "-5", "30s"])
def test_a_bad_value_falls_back_rather_than_crashing_the_import(monkeypatch, bad):
    """These are read at import time, so a typo in .env must not stop the app
    booting -- and must not turn into a zero/negative deadline, which gRPC would
    treat as "already expired"."""
    module = _reload(monkeypatch, VELOCIRAPTOR_FLOW_TIMEOUT=bad)

    assert module.FLOW_TIMEOUT_SECONDS == 300


def test_timeout_error_names_the_knob_that_raises_it(monkeypatch):
    """The operator's next question is always "how do I give it longer?"."""
    import grpc

    module = _reload(monkeypatch)

    class _DeadlineExceeded(grpc.RpcError):
        def code(self):
            return grpc.StatusCode.DEADLINE_EXCEEDED

        def details(self):
            return "Deadline Exceeded"

    class _Stub:
        def Query(self, request, timeout=None):
            raise _DeadlineExceeded()

    service = module.UniversalService.__new__(module.UniversalService)
    service.stub = _Stub()

    with pytest.raises(HTTPException) as exc:
        service.watch_flow_completion("F.CQMNTHE1CSPKC", org_id="root")

    assert exc.value.status_code == 504
    detail = exc.value.detail
    assert "VELOCIRAPTOR_FLOW_TIMEOUT" in detail
    assert "300s" in detail
    # The flow keeps running server-side; saying so stops an operator re-running it.
    assert "still be running" in detail


def test_a_plain_query_timeout_points_at_the_query_knob(monkeypatch):
    import grpc

    module = _reload(monkeypatch)

    class _DeadlineExceeded(grpc.RpcError):
        def code(self):
            return grpc.StatusCode.DEADLINE_EXCEEDED

        def details(self):
            return "Deadline Exceeded"

    class _Stub:
        def Query(self, request, timeout=None):
            raise _DeadlineExceeded()

    service = module.UniversalService.__new__(module.UniversalService)
    service.stub = _Stub()

    with pytest.raises(HTTPException) as exc:
        service.execute_query("SELECT * FROM clients()")

    assert "VELOCIRAPTOR_QUERY_TIMEOUT" in exc.value.detail


def test_flow_watch_uses_the_flow_deadline_not_the_query_one(monkeypatch):
    """The regression that started this: watch_flow_completion inherited the 30s
    query deadline, so a two-minute collection failed while still running."""
    module = _reload(monkeypatch)
    seen = {}

    class _Stub:
        def Query(self, request, timeout=None):
            seen["timeout"] = timeout
            return iter(())

    service = module.UniversalService.__new__(module.UniversalService)
    service.stub = _Stub()

    service.watch_flow_completion("F.CQMNTHE1CSPKC", org_id="root")

    assert seen["timeout"] == module.FLOW_TIMEOUT_SECONDS


def test_an_ordinary_query_still_uses_the_short_deadline(monkeypatch):
    module = _reload(monkeypatch)
    seen = {}

    class _Stub:
        def Query(self, request, timeout=None):
            seen["timeout"] = timeout
            return iter(())

    service = module.UniversalService.__new__(module.UniversalService)
    service.stub = _Stub()

    service.execute_query("SELECT * FROM clients()")

    assert seen["timeout"] == module.QUERY_TIMEOUT_SECONDS


def test_an_explicit_timeout_overrides_the_default(monkeypatch):
    """Keeps a per-call override available for a caller that knows better."""
    module = _reload(monkeypatch)
    seen = {}

    class _Stub:
        def Query(self, request, timeout=None):
            seen["timeout"] = timeout
            return iter(())

    service = module.UniversalService.__new__(module.UniversalService)
    service.stub = _Stub()

    service.execute_query("SELECT * FROM clients()", timeout=7)

    assert seen["timeout"] == 7
