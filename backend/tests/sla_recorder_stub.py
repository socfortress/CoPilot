"""A no-op SLA recorder for incident-route tests that are not about SLA (#1187). Not collected by pytest.

The alert and case routes record SLA milestones through ``SlaLifecycleRecorder``, which
opens a session of its own on the global engine. Tests that call a route inside a
throwaway ``asyncio.run`` loop would leave a pooled connection bound to that closed loop
for whichever test next uses the engine (and would write to whatever database the
environment points at). Import the fixture into such a module to swap the recorder out::

    from tests.sla_recorder_stub import no_sla_recorder  # noqa: F401
"""

from unittest.mock import AsyncMock

import pytest

import app.incidents.routes.db_operations as db_operation_routes


class NoSlaRecorder:
    """Accepts every recorder call and does nothing."""

    def __init__(self, *_args, **_kwargs):
        pass

    def __getattr__(self, _name):
        return AsyncMock()


@pytest.fixture(autouse=True)
def no_sla_recorder(monkeypatch):
    monkeypatch.setattr(db_operation_routes, "SlaLifecycleRecorder", NoSlaRecorder)
