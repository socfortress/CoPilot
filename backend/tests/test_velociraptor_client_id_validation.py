"""Tests for Velociraptor client id validation across multi-org deployments (issue #1015).

In a multi-org Velociraptor deployment, `clients()` reports a client's id *within an org*
as "C.<hex>-<ORGID>", and that suffixed form is the one the server matches on. CoPilot's
agent sync stores exactly what `clients()` reports, so every agent outside the root org
carried an id that CoPilot's own validator rejected with 400 on any endpoint that
validates one (`GET /api/flows/{host}` being the visible one).

The widened pattern must accept the suffix without weakening the VQL-injection defence it
was added for (GHSA-5542-j2fc-gqjm): no quote, backtick, brace, backslash, whitespace or
newline may reach an interpolated VQL string.

Pure-function unit tests — no DB or Velociraptor server.

Run with: cd backend && python -m pytest tests/test_velociraptor_client_id_validation.py
"""

import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.connectors.velociraptor.utils.validation import (  # noqa: E402
    validate_client_id,
)


@pytest.mark.parametrize(
    "client_id",
    [
        "C.475df76785008b04",  # root-org client, the pre-#1015 shape
        "C.AAAAAAAAAAAAAAAA",  # uppercase hex
        "server",  # the Velociraptor server itself (Server.Utils.DeleteClient)
    ],
)
def test_accepts_single_org_ids(client_id):
    assert validate_client_id(client_id) == client_id


@pytest.mark.parametrize(
    "client_id",
    [
        "C.aaaaaaaaaaaaaaaa-OXXXXXXX",  # the shape from the issue report
        "C.475df76785008b04-O1234ABCD",  # generated org id
        "C.475df76785008b04-root",  # explicit root suffix
        "C.475df76785008b04-tenant.one",  # dots and dashes are in _ORG_ID_PATTERN's class
        "C.475df76785008b04-tenant_one",
    ],
)
def test_accepts_multi_org_suffixed_ids(client_id):
    """The suffixed id is what sync_agents_velociraptor stores for a non-root org."""
    assert validate_client_id(client_id) == client_id


@pytest.mark.parametrize(
    "payload",
    [
        # Straight breakout attempts on the base id.
        "C.475df76785008b04'",
        "C.475df76785008b04' OR 1=1 --",
        "C.475df76785008b04') FROM scope() SELECT execve(argv=['id'])",
        'C.475df76785008b04"',
        "C.475df76785008b04`",
        "C.475df76785008b04\\",
        "C.475df76785008b04\nSELECT execve(argv=['id']) FROM scope()",
        "C.475df76785008b04 OR 1=1",
        "C.475df76785008b04{}",
        # The same payloads smuggled through the newly-accepted org suffix.
        "C.475df76785008b04-O123'",
        "C.475df76785008b04-O123' OR 1=1 --",
        "C.475df76785008b04-O123`",
        "C.475df76785008b04-O123\\",
        "C.475df76785008b04-O123\nSELECT 1",
        "C.475df76785008b04-O 123",
        "C.475df76785008b04-{O123}",
        # Malformed ids that were never valid.
        "C.zzzz",  # non-hex body
        "C.",  # empty body
        "C.475df76785008b04-",  # dangling separator, empty org
        "-O123",  # suffix with no client id
        "",
        "SERVER",  # the literal is lowercase only
    ],
)
def test_rejects_injection_and_malformed_ids(payload):
    with pytest.raises(HTTPException) as exc:
        validate_client_id(payload)
    assert exc.value.status_code == 400


def test_rejects_non_string():
    with pytest.raises(HTTPException) as exc:
        validate_client_id(None)
    assert exc.value.status_code == 400
