"""``get_user_accessible_customers`` is memoized per session, i.e. per request.

A portal endpoint used to query ``user_customer_access`` 3-6 times (list, counts,
per-object checks). The answer now lives in ``session.info`` for the session's
lifetime, which ``get_db`` scopes to one request.

Run with: cd backend && python -m pytest tests/test_accessible_customers_memo.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.middleware.customer_access import CustomerAccessHandler  # noqa: E402


def _session(codes):
    session = AsyncMock()
    session.info = {}
    result = MagicMock()
    result.scalars.return_value.all.return_value = codes
    session.execute = AsyncMock(return_value=result)
    return session


def _user(user_id=7, role_id=4):
    return SimpleNamespace(id=user_id, role_id=role_id)


def _run(coro):
    return asyncio.run(coro)


def test_repeated_lookups_in_one_session_query_once():
    handler, session = CustomerAccessHandler(), _session(["ACME"])

    async def several_checks():
        first = await handler.get_user_accessible_customers(_user(), session)
        await handler.check_customer_access(_user(), "ACME", session)
        await handler.resolve_effective_customers(_user(), ["ACME"], session)
        return first

    assert _run(several_checks()) == ["ACME"]
    assert session.execute.await_count == 1


def test_memo_is_per_user():
    handler, session = CustomerAccessHandler(), _session(["ACME"])
    _run(handler.get_user_accessible_customers(_user(1), session))
    _run(handler.get_user_accessible_customers(_user(2), session))
    assert session.execute.await_count == 2


def test_callers_cannot_corrupt_the_memo():
    handler, session = CustomerAccessHandler(), _session(["ACME"])
    _run(handler.get_user_accessible_customers(_user(), session)).append("OTHER")
    assert _run(handler.get_user_accessible_customers(_user(), session)) == ["ACME"]


def test_unassigned_analyst_wildcard_is_memoized_too():
    handler, session = CustomerAccessHandler(), _session([])
    assert _run(handler.get_user_accessible_customers(_user(role_id=2), session)) == ["*"]
    assert _run(handler.get_user_accessible_customers(_user(role_id=2), session)) == ["*"]
    assert session.execute.await_count == 1


def test_forget_drops_the_memo_after_assignments_change():
    handler, session = CustomerAccessHandler(), _session(["ACME"])
    _run(handler.get_user_accessible_customers(_user(), session))
    handler.forget_accessible_customers(session, 7)
    _run(handler.get_user_accessible_customers(_user(), session))
    assert session.execute.await_count == 2


def test_sessions_do_not_share_the_memo():
    handler = CustomerAccessHandler()
    first, second = _session(["ACME"]), _session(["OTHER"])
    assert _run(handler.get_user_accessible_customers(_user(), first)) == ["ACME"]
    assert _run(handler.get_user_accessible_customers(_user(), second)) == ["OTHER"]
