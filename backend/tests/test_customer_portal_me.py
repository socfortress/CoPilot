"""``GET /customer_portal/me``: the portal user and their customers, with names (#1243).

The portal knew its customers only as the codes in the JWT and showed them raw. This
endpoint reads them live (an assignment change shows at the next call, the token is a
login-time copy) and names them. Mocked session; no database.

Run with: cd backend && python -m pytest tests/test_customer_portal_me.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi.routing import APIRoute  # noqa: E402

import app.customer_portal.services.me as me_service  # noqa: E402
from app.customer_portal.routes.me import customer_portal_me_router  # noqa: E402
from app.middleware.customer_access import customer_access_handler  # noqa: E402

PORTAL_USER = SimpleNamespace(id=7, username="acme.viewer", role_id=4, must_change_password=False)


def _session(rows):
    result = MagicMock()
    result.all.return_value = rows
    return AsyncMock(execute=AsyncMock(return_value=result))


def _customers(accessible, rows, administered=()):
    session = _session(rows)
    with (
        patch.object(customer_access_handler, "get_user_accessible_customers", AsyncMock(return_value=accessible)),
        patch.object(me_service, "administered_customer_codes", AsyncMock(return_value=list(administered))),
    ):
        customers = asyncio.run(me_service.portal_customers(PORTAL_USER, session))
    _customers.last = customers
    return [(c.customer_code, c.customer_name) for c in customers], session


def test_each_customer_says_whether_the_user_administers_it():
    # A customer admin manages that customer's portal users (#1296); the flag is per customer.
    _customers(["ACME", "BETA"], [("ACME", "Acme"), ("BETA", "Beta")], administered=["BETA"])
    assert {c.customer_code: c.is_customer_admin for c in _customers.last} == {"ACME": False, "BETA": True}


def test_customers_carry_their_names_sorted_by_name():
    customers, _ = _customers(["ZZ01", "AA01"], [("ZZ01", "Acme Milan"), ("AA01", "Zeta Rome")])
    assert customers == [("ZZ01", "Acme Milan"), ("AA01", "Zeta Rome")]


def test_names_sort_without_regard_to_case():
    customers, _ = _customers(["A", "B"], [("A", "beta"), ("B", "Alpha")])
    assert [name for _, name in customers] == ["Alpha", "beta"]


def test_a_code_without_a_customers_row_is_listed_under_its_code():
    # Hiding it would hide data the user can still reach.
    customers, _ = _customers(["ACME", "GHOST"], [("ACME", "Acme")])
    assert customers == [("ACME", "Acme"), ("GHOST", "GHOST")]


def test_a_blank_name_falls_back_to_the_code():
    customers, _ = _customers(["ACME"], [("ACME", "  ")])
    assert customers == [("ACME", "ACME")]


def test_a_user_with_no_customer_gets_none_without_querying():
    customers, session = _customers([], [])
    assert customers == []
    session.execute.assert_not_awaited()


def test_the_wildcard_is_never_expanded():
    # Only an admin holds it, and the portal is for customer users.
    customers, session = _customers(["*"], [])
    assert customers == []
    session.execute.assert_not_awaited()


def test_only_the_users_customers_are_asked_for():
    _, session = _customers(["ACME", "BETA"], [])
    sql = str(session.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "'ACME'" in sql and "'BETA'" in sql


def test_the_profile_names_the_user_and_role():
    with patch.object(me_service, "portal_customers", AsyncMock(return_value=[])):
        profile = asyncio.run(me_service.get_portal_profile(PORTAL_USER, AsyncMock()))
    assert (profile.username, profile.role, profile.customers) == ("acme.viewer", "customer_user", [])
    assert profile.must_change_password is False


def test_the_profile_says_when_the_password_must_be_replaced():
    # An admin chose it (#1277): the portal holds the user on the change until they do.
    held = SimpleNamespace(id=7, username="acme.viewer", role_id=4, must_change_password=True)
    with patch.object(me_service, "portal_customers", AsyncMock(return_value=[])):
        profile = asyncio.run(me_service.get_portal_profile(held, AsyncMock()))
    assert profile.must_change_password is True


def test_the_route_is_for_portal_users_only():
    from tests.test_customer_user_write_allowlist import _route_scopes

    route = next(r for r in customer_portal_me_router.routes if isinstance(r, APIRoute))
    assert (route.path, route.methods) == ("/me", {"GET"})
    assert _route_scopes(route.dependant) == {"customer_user"}


def test_the_route_is_mounted_under_the_portal_prefix():
    from app.routers.customer_portal import router

    paths = {route.path for route in router.routes if isinstance(route, APIRoute)}
    assert "/customer_portal/me" in paths
