"""Regression tests for the follow-up to #1050 — scoping that stops at the customer list.

#1050 made ``user_customer_access`` authoritative for analysts and guarded every route
keyed by a literal ``{customer_code}``. The reporter came back with "I'm logged in as
analyst with one customer assigned, and I'm still able to see other customer
information", and the gap is structural: a tenant's data is mostly *not* addressed by
its customer code. It is addressed by an agent id, a hostname, a report id, a job id, a
customer *name* — none of which the ``{customer_code}`` scan could see.

These are unit tests against the middleware primitives that close that gap, with a
mocked session; the end-to-end proof against real routers and a real MySQL lives in
``tests/e2e/analyst_object_scoping_e2e.py``.

Run with: cd backend && python -m pytest tests/test_object_level_customer_scoping.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

from app.auth.models.users import RoleEnum  # noqa: E402
from app.middleware import customer_access as ca  # noqa: E402

MINE = "TENANT_A"
THEIRS = "TENANT_B"


def _user(role_id=RoleEnum.analyst):
    return SimpleNamespace(id=7, username="analyst", role_id=role_id)


def _session(*result_rows):
    """AsyncSession returning ``result_rows[i]`` for the i-th ``execute``."""
    session = AsyncMock()
    results = []
    for row in result_rows:
        result = MagicMock()
        result.scalars.return_value.all.return_value = row if isinstance(row, list) else [row]
        result.scalars.return_value.first.return_value = (
            row[0] if isinstance(row, list) and row else (None if isinstance(row, list) else row)
        )
        results.append(result)
    session.execute = AsyncMock(side_effect=results)
    return session


def _run(coro):
    return asyncio.run(coro)


# ── enforce_owned_object_access: the primitive every object guard is built on ──


def test_scoped_user_reaches_their_own_object():
    # first execute() = the assignment lookup inside get_user_accessible_customers
    session = _session([MINE])
    _run(ca.enforce_owned_object_access(_user(), MINE, session, subject="report 1"))


def test_scoped_user_is_denied_another_tenants_object():
    session = _session([MINE])
    with pytest.raises(HTTPException) as exc:
        _run(ca.enforce_owned_object_access(_user(), THEIRS, session, subject="report 1"))
    assert exc.value.status_code == 403


def test_unattributable_object_is_denied_for_a_scoped_user():
    """An id that resolves to no tenant must fail closed.

    A missing agent row, an orphaned report, a typo'd hostname — none of them are
    evidence that the object is *ours*, and treating "unknown" as "allowed" is how a
    deleted-agent id turns into a cross-tenant read.
    """
    session = _session([MINE])
    with pytest.raises(HTTPException) as exc:
        _run(ca.enforce_owned_object_access(_user(), None, session, subject="agent ghost"))
    assert exc.value.status_code == 403


def test_admin_reaches_any_object_including_unattributable_ones():
    # admin never consults the assignment table, so no execute() is expected
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=AssertionError("admin must not query assignments"))
    _run(ca.enforce_owned_object_access(_user(RoleEnum.admin), THEIRS, session, subject="report 1"))
    _run(ca.enforce_owned_object_access(_user(RoleEnum.admin), None, session, subject="report 1"))


def test_unassigned_analyst_keeps_deployment_wide_reach():
    # the #1050 upgrade compromise must survive here too, or upgrading strips access
    session = _session([])
    _run(ca.enforce_owned_object_access(_user(), THEIRS, session, subject="report 1"))


# ── scoped_customer_codes: aggregates with no customer code in the request ────


def test_scoped_codes_narrows_an_unfiltered_aggregate_to_the_assignment():
    session = _session([MINE])
    assert _run(ca.scoped_customer_codes(_user(), None, session)) == [MINE]


def test_scoped_codes_returns_none_for_wildcard_so_nothing_is_filtered():
    session = _session([])
    assert _run(ca.scoped_customer_codes(_user(), None, session)) is None


def test_scoped_codes_intersects_a_requested_subset_rather_than_trusting_it():
    session = _session([MINE])
    assert _run(ca.scoped_customer_codes(_user(), [THEIRS], session)) == []


def test_empty_list_is_distinct_from_none():
    """``[]`` means "nothing visible" and must not be confused with "no filter".

    Most services read an empty ``customer_codes`` as "every customer", so a route
    that passes ``[]`` straight through would leak the whole deployment. Callers are
    required to short-circuit on it, and this pins the distinction the helper makes.
    """
    session = _session([MINE])
    assert _run(ca.scoped_customer_codes(_user(), [THEIRS], session)) == []
    session = _session([])
    assert _run(ca.scoped_customer_codes(_user(), None, session)) is None
