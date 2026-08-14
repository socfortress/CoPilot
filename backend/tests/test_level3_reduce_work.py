"""Do less work, rather than moving it (#1072, level 3).

Level 2 measured the thing that reframes all of this: **every statement on this
deployment costs ~135ms regardless of what it does** (p50 134.8ms, p95 146.3ms
over 1033 queries). The lever is therefore the *number* of round-trips per
request, not the SQL inside them.

Two of the three changes here follow directly from that measurement:

* the authenticated user was looked up 214 times in one session — 29.1s, a fifth
  of all time the process spent on the database — because FastAPI caches a
  dependency by callable identity and every `Security(AuthHandler()…)` builds a
  fresh instance;
* `/customers` issued a second statement that read the whole `customers_meta`
  table to compute one boolean per row.

The third, response compression, is unrelated to the database and was simply
absent.

Run with: cd backend && python -m pytest tests/test_level3_reduce_work.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.auth.utils import AuthHandler  # noqa: E402


class _State:
    """Stands in for `request.state`, which is a plain attribute bag."""


def _request():
    return SimpleNamespace(state=_State())


def _user(username="admin"):
    return SimpleNamespace(username=username, id=1, role_id=1)


# ── the user lookup: once per request, however many dependencies ask ────────


def test_the_user_is_looked_up_once_per_request(monkeypatch):
    """214 identical lookups in one session is what this removes."""
    calls = []

    async def fake_find_user(name):
        calls.append(name)
        return _user(name)

    monkeypatch.setattr("app.auth.utils.find_user", fake_find_user)
    handler = AuthHandler()
    request = _request()

    async def scenario():
        # Three dependencies on the same request, as a guarded route with an
        # injected `current_user` produces.
        return [await handler._resolve_user(request, "admin") for _ in range(3)]

    users = asyncio.run(scenario())

    assert calls == ["admin"], f"expected one lookup, got {len(calls)}"
    assert all(u is users[0] for u in users), "every dependency must see the same object"


def test_a_different_request_looks_up_again(monkeypatch):
    """The cache is per request — it must not leak across them."""
    calls = []

    async def fake_find_user(name):
        calls.append(name)
        return _user(name)

    monkeypatch.setattr("app.auth.utils.find_user", fake_find_user)
    handler = AuthHandler()

    async def scenario():
        await handler._resolve_user(_request(), "admin")
        await handler._resolve_user(_request(), "admin")

    asyncio.run(scenario())

    assert len(calls) == 2


def test_a_different_user_on_the_same_request_is_not_served_the_cache(monkeypatch):
    """The dangerous failure: one user served another's record."""

    async def fake_find_user(name):
        return _user(name)

    monkeypatch.setattr("app.auth.utils.find_user", fake_find_user)
    handler = AuthHandler()
    request = _request()

    async def scenario():
        first = await handler._resolve_user(request, "alice")
        second = await handler._resolve_user(request, "bob")
        return first, second

    first, second = asyncio.run(scenario())

    assert first.username == "alice"
    assert second.username == "bob", "the cache must be keyed by username, not just present"


def test_a_missing_user_is_not_cached(monkeypatch):
    """Caching a None would turn one bad lookup into a permanent 401."""
    calls = []

    async def fake_find_user(name):
        calls.append(name)
        return None

    monkeypatch.setattr("app.auth.utils.find_user", fake_find_user)
    handler = AuthHandler()
    request = _request()

    async def scenario():
        await handler._resolve_user(request, "ghost")
        await handler._resolve_user(request, "ghost")

    asyncio.run(scenario())

    assert len(calls) == 2, "a failed lookup must be retried, not remembered"


# ── the customers list: one statement, not two ─────────────────────────────


def test_customers_list_issues_a_single_statement(monkeypatch):
    """The second statement read all of customers_meta for one boolean per row."""
    from app.customers.routes import customers as route_module

    executed = []

    class _Result:
        def all(self):
            return [(SimpleNamespace(customer_code="SOC01"), True)]

    session = MagicMock()

    async def execute(statement):
        executed.append(statement)
        return _Result()

    session.execute = execute

    monkeypatch.setattr(route_module, "apply_search_limit", lambda query, *a, **k: query)

    async def fake_filter(user, sess, query, column):
        return query

    monkeypatch.setattr(route_module.customer_access_handler, "filter_query_by_customer_access", fake_filter)

    # A real schema object: CustomersResponse validates its contents, and a stub
    # would fail on the required fields rather than on what this test is about.
    def _from_orm(cls, obj):
        return route_module.CustomerRequestBody(
            customer_code=obj.customer_code,
            customer_name="Acme",
            contact_last_name="Doe",
            contact_first_name="Jane",
        )

    monkeypatch.setattr(route_module.CustomerRequestBody, "from_orm", classmethod(_from_orm))

    response = asyncio.run(
        route_module.get_customers(
            search_params=SimpleNamespace(search=None, limit=None),
            current_user=_user(),
            session=session,
        ),
    )

    assert len(executed) == 1, f"expected one statement, got {len(executed)}"
    assert response.customers[0].is_provisioned is True


def test_the_provisioning_flag_is_part_of_the_same_query():
    """A correlated EXISTS, not a second round-trip."""
    import inspect

    from app.customers.routes.customers import get_customers

    source = inspect.getsource(get_customers)

    assert ".exists()" in source
    assert "select(CustomersMeta)" not in source, "the full-table read is back"


# ── response compression ───────────────────────────────────────────────────


def test_compression_is_installed_between_the_timer_and_the_app():
    """Ordering matters: the recorded duration must include compressing."""
    import copilot

    names = [m.cls.__name__ for m in copilot.app.user_middleware]

    assert "GZipMiddleware" in names, "responses ship uncompressed"
    assert names.index("RequestTimingMiddleware") < names.index("GZipMiddleware"), (
        "the timer must stay outermost, or it would not measure the cost of the " "compression it was added alongside"
    )


def test_small_responses_are_left_alone():
    """Compressing a 200-byte JSON costs CPU and a header to save nothing."""
    import copilot

    gzip = next(m for m in copilot.app.user_middleware if m.cls.__name__ == "GZipMiddleware")
    minimum = gzip.kwargs.get("minimum_size")

    assert minimum and minimum >= 500, f"minimum_size={minimum} compresses payloads too small to benefit"


@pytest.mark.parametrize("attribute", ["copilot_current_user"])
def test_the_cache_attribute_is_namespaced(attribute):
    """`request.state` is shared with every other middleware and dependency."""
    import inspect

    source = inspect.getsource(AuthHandler._resolve_user)

    assert attribute in source, "a bare name here would collide with anything else using request.state"
