"""The responder role (#1219): an analyst who may also run response actions, on their customers only.

- what a responder's token carries, and that roles are seeded with fixed ids;
- the exact set of routes that name "responder" (every analyst route admits it through
  the analyst scope it also carries) — a new response route, or a responder reaching an
  admin route, fails here until the list is changed on purpose;
- that each response route checks the target's customer before doing anything;
- the customer-assignment rules: analysts and responders always have a customer,
  admins never get one, unknown codes are refused.

No database, no network. Run with: cd backend && python -m pytest tests/test_responder_role.py
"""

import asyncio
import inspect
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402

from app.auth.models.users import CUSTOMER_SCOPED_SOC_ROLES  # noqa: E402
from app.auth.models.users import SOC_ROLES  # noqa: E402
from app.auth.models.users import RoleEnum  # noqa: E402
from app.auth.models.users import effective_roles  # noqa: E402
from app.auth.utils import role_scopes  # noqa: E402

RESPONDER = "responder"

# Every route that names the responder scope. A responder also carries "analyst", so this
# is exactly what it can do that an analyst cannot.
RESPONDER_ROUTES = frozenset(
    {
        # Velociraptor response on an endpoint of their customers.
        ("POST", "/api/artifacts/quarantine"),  # quarantine and remove_quarantine
        ("POST", "/api/artifacts/command"),
        # CoPilot Actions: the catalogue, and invoking one on their customers' agents.
        ("GET", "/api/copilot_action/inventory"),
        ("GET", "/api/copilot_action/inventory/count"),
        ("GET", "/api/copilot_action/inventory/{copilot_action_name}"),
        ("GET", "/api/copilot_action/metrics"),
        ("GET", "/api/copilot_action/technologies"),
        ("POST", "/api/copilot_action/invoke"),
        # Their customers' Sysmon configs: read and deploy (uploading one stays admin).
        ("GET", "/api/sysmon_config"),
        ("GET", "/api/sysmon_config/content/{customer_code}"),
        ("GET", "/api/sysmon_config/{customer_code}"),
        ("POST", "/api/sysmon_config/deploy/{customer_code}"),
    },
)


def _scopes_of(dependant) -> set:
    """Scopes a route requires, from ``require_any_scope`` closures and ``Security(..., scopes=...)``."""
    scopes = set(getattr(dependant, "own_oauth_scopes", None) or [])
    for dependency in dependant.dependencies:
        call = dependency.call
        if call is not None:
            try:
                required = inspect.getclosurevars(call).nonlocals.get("required_scopes")
            except TypeError:
                required = None
            if isinstance(required, tuple):
                scopes |= set(required)
        scopes |= _scopes_of(dependency)
    return scopes


def _routes_naming(scope: str) -> set:
    import copilot

    found = set()
    for route in copilot.app.routes:
        if isinstance(route, APIRoute) and scope in _scopes_of(route.dependant):
            found |= {(method, route.path) for method in route.methods}
    return found


def _run(coro):
    return asyncio.run(coro)


# ── The role ──────────────────────────────────────────────────────────────


def test_a_responder_token_also_carries_the_analyst_scope():
    assert role_scopes("responder") == ["responder", "analyst"]
    assert role_scopes("analyst") == ["analyst"]
    assert role_scopes("admin") == ["admin"]
    assert role_scopes("customer_user") == ["customer_user"]


def test_a_responder_is_an_analyst_in_the_soc_scoped_to_its_customers():
    assert effective_roles(RoleEnum.responder) == [RoleEnum.responder, RoleEnum.analyst]
    assert RoleEnum.responder in SOC_ROLES
    assert CUSTOMER_SCOPED_SOC_ROLES == {RoleEnum.analyst, RoleEnum.responder}


def test_roles_are_seeded_with_their_enum_ids():
    from app.db.db_populate import ROLES

    assert {(role_id, name) for role_id, name, _ in ROLES} == {(role.value, role.name) for role in RoleEnum}


def test_the_roles_migration_seeds_the_same_ids():
    import importlib.util
    from pathlib import Path

    path = next(Path("alembic/versions").glob("c1219a2b3c4d_*.py"))
    spec = importlib.util.spec_from_file_location("roles_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert {(role_id, name) for role_id, name, _ in module.ROLES} == {(role.value, role.name) for role in RoleEnum}


# ── What a responder can do ───────────────────────────────────────────────


def test_scope_extraction_sees_both_kinds_of_guard():
    # require_any_scope (a closure) and Security(get_current_user, scopes=[...]).
    admin_routes = _routes_naming("admin")
    assert ("POST", "/api/auth/register") in admin_routes
    assert ("POST", "/api/wazuh_manager/management/restart") in admin_routes


def test_responder_routes_match_the_list():
    found = _routes_naming(RESPONDER)
    assert sorted(found - RESPONDER_ROUTES) == [], "routes newly open to responders"
    assert sorted(RESPONDER_ROUTES - found) == [], "responder routes no longer open to them"


def test_every_responder_route_still_admits_admins():
    admin_routes = _routes_naming("admin")
    assert RESPONDER_ROUTES <= admin_routes


@pytest.mark.parametrize(
    "route",
    [
        ("POST", "/api/auth/register"),
        ("PUT", "/api/auth/users/{user_id}/role/by-name"),
        ("POST", "/api/auth/users/{user_id}/customers"),
        ("POST", "/api/customers"),
        ("POST", "/api/sysmon_config/upload"),
        ("POST", "/api/wazuh_manager/management/restart"),
    ],
)
def test_administration_stays_admin_only(route):
    assert route not in _routes_naming(RESPONDER)
    assert route not in _routes_naming("analyst")


# ── Each response route checks the target's customer first ───────────────


def _user():
    return SimpleNamespace(id=9, username="resp", role_id=RoleEnum.responder.value)


DENIED = HTTPException(status_code=403, detail="Access denied to agent - insufficient customer permissions")


def test_quarantine_refuses_a_host_of_another_customer_before_anything_runs():
    import app.connectors.velociraptor.routes.artifacts as routes

    artifacts = AsyncMock()
    with patch.object(routes, "enforce_hostname_access", AsyncMock(side_effect=DENIED)), patch.object(
        routes,
        "get_all_artifacts_for_hostname",
        artifacts,
    ):
        body = SimpleNamespace(hostname="OTHER-HOST", artifact_name="Windows.Remediation.Quarantine", action="quarantine")
        with pytest.raises(HTTPException) as exc:
            _run(routes.quarantine(body, MagicMock(), _user(), AsyncMock()))
    assert exc.value.status_code == 403
    artifacts.assert_not_awaited()


def test_a_command_refuses_a_host_of_another_customer_before_anything_runs():
    import app.connectors.velociraptor.routes.artifacts as routes

    artifacts = AsyncMock()
    with patch.object(routes, "enforce_hostname_access", AsyncMock(side_effect=DENIED)), patch.object(
        routes,
        "get_all_artifacts_for_hostname",
        artifacts,
    ):
        body = SimpleNamespace(hostname="OTHER-HOST", artifact_name="Windows.System.PowerShell")
        with pytest.raises(HTTPException) as exc:
            _run(routes.run_command(body, MagicMock(), _user(), AsyncMock()))
    assert exc.value.status_code == 403
    artifacts.assert_not_awaited()


def test_a_copilot_action_refuses_the_whole_request_for_one_foreign_host():
    import app.integrations.copilot_action.routes.copilot_action as routes

    checked = []

    async def enforce(user, hostname, session):
        checked.append(hostname)
        if hostname == "OTHER-HOST":
            raise DENIED

    agents, audit = AsyncMock(), AsyncMock()
    with patch.object(routes, "enforce_hostname_access", enforce), patch.object(routes, "get_agents_by_hostnames", agents), patch.object(
        routes,
        "record_audit_event",
        audit,
    ):
        body = SimpleNamespace(copilot_action_name="Isolate", agent_names=["MY-HOST", "OTHER-HOST"], parameters=None)
        with pytest.raises(HTTPException) as exc:
            _run(routes.invoke_action(body, MagicMock(), _user(), AsyncMock()))
    assert exc.value.status_code == 403
    assert checked == ["MY-HOST", "OTHER-HOST"]
    agents.assert_not_awaited()
    audit.assert_not_awaited()


def test_a_copilot_action_needs_a_target():
    import app.integrations.copilot_action.routes.copilot_action as routes

    body = SimpleNamespace(copilot_action_name="Isolate", agent_names=[], parameters=None)
    with pytest.raises(HTTPException) as exc:
        _run(routes.invoke_action(body, MagicMock(), _user(), AsyncMock()))
    assert exc.value.status_code == 400


def test_sysmon_routes_open_to_responders_check_the_customer_code():
    import copilot
    from app.middleware.customer_access import verify_customer_code_access

    for route in copilot.app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/sysmon_config/") or "{customer_code}" not in route.path:
            continue
        calls = {dependency.call for dependency in route.dependant.dependencies}
        assert verify_customer_code_access in calls, route.path


def test_the_sysmon_list_shows_only_the_callers_customers():
    import app.active_response.routes.sysmon_config as routes

    with patch.object(routes, "list_sysmon_configs", AsyncMock(return_value=["ACME", "GLOBEX"])), patch.object(
        routes,
        "scoped_customer_codes",
        AsyncMock(return_value=["ACME"]),
    ):
        response = _run(routes.get_all_sysmon_configs(_user(), AsyncMock()))
    assert response.customer_codes == ["ACME"]


# ── Customer assignments ──────────────────────────────────────────────────


def _session_with_customers(*codes):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(codes)
    session.execute = AsyncMock(return_value=result)
    return session


def _validate(role, codes, existing=("ACME", "GLOBEX")):
    from app.auth.services.customer_assignment import validate_assignment

    return _run(validate_assignment(role, codes, _session_with_customers(*[c for c in codes if c in existing])))


@pytest.mark.parametrize("role", [RoleEnum.analyst, RoleEnum.responder])
def test_analysts_and_responders_need_a_customer(role):
    with pytest.raises(HTTPException) as exc:
        _validate(role, [])
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException):
        _validate(role, ["  ", ""])
    assert _validate(role, ["ACME", " ACME ", "GLOBEX"]) == ["ACME", "GLOBEX"]


def test_admins_get_no_customers():
    with pytest.raises(HTTPException) as exc:
        _validate(RoleEnum.admin, ["ACME"])
    assert "Admins see every customer" in exc.value.detail
    assert _validate(RoleEnum.admin, []) == []


def test_portal_users_keep_their_rules():
    assert _validate(RoleEnum.customer_user, []) == []


def test_unknown_customers_are_refused():
    with pytest.raises(HTTPException) as exc:
        _validate(RoleEnum.responder, ["ACME", "NOPE"])
    assert "NOPE" in exc.value.detail


def _role_change(target_role, request_codes, existing_codes):
    import app.auth.routes.auth as routes
    from app.auth.schema.auth import UpdateUserRoleRequest

    user = SimpleNamespace(id=4, username="bob", role_id=RoleEnum.admin.value)
    session = AsyncMock()
    session.get = AsyncMock(return_value=user)
    session.add = MagicMock()
    replace = AsyncMock()
    with patch.object(routes, "assigned_codes", AsyncMock(return_value=list(existing_codes))), patch.object(
        routes,
        "validate_assignment",
        AsyncMock(side_effect=lambda role, codes, s: list(codes)),
    ), patch.object(routes, "replace_assignment", replace), patch.object(routes, "record_audit_event", AsyncMock()):
        request = UpdateUserRoleRequest(role_name=target_role, customer_codes=request_codes)
        try:
            result = _run(routes.update_user_role_by_name(4, request, MagicMock(), SimpleNamespace(id=1, username="admin"), session))
        except HTTPException as e:
            result = e
    return result, user, replace, session


def test_becoming_a_responder_without_customers_is_refused_and_changes_nothing():
    error, user, replace, session = _role_change("responder", None, [])
    assert error.status_code == 400
    assert user.role_id == RoleEnum.admin.value
    session.commit.assert_not_awaited()


def test_becoming_a_responder_with_customers_sets_both_at_once():
    result, user, replace, session = _role_change("responder", ["ACME"], [])
    assert user.role_id == RoleEnum.responder.value
    replace.assert_awaited_once_with(4, ["ACME"], session)
    assert result["new_role_name"] == "responder"


def test_a_user_who_already_has_customers_can_become_an_analyst_as_is():
    result, user, replace, _ = _role_change("analyst", None, ["ACME"])
    assert user.role_id == RoleEnum.analyst.value
    replace.assert_not_awaited()


def test_an_admin_keeps_the_stored_customers_untouched():
    result, user, replace, _ = _role_change("admin", None, ["ACME"])
    assert user.role_id == RoleEnum.admin.value
    replace.assert_not_awaited()


def test_me_customers_names_why_a_user_sees_nothing():
    import app.auth.routes.customer_users as routes

    for codes, scope in ((["*"], "deployment"), (["ACME"], "assigned"), ([], "unassigned")):
        with patch.object(routes.customer_access_handler, "get_user_accessible_customers", AsyncMock(return_value=codes)):
            response = _run(routes.get_my_customer_access(_user(), AsyncMock()))
        assert response["scope"] == scope, codes


def test_sso_users_have_a_soc_role():
    from pydantic import ValidationError

    from app.auth.models.sso import SSOAllowedEmailInput

    assert SSOAllowedEmailInput(email="r@example.com", role_id=RoleEnum.responder.value).role_id == 5
    for role in (RoleEnum.scheduler, RoleEnum.customer_user, 42):
        with pytest.raises(ValidationError):
            SSOAllowedEmailInput(email="r@example.com", role_id=int(role))


def test_responder_sends_like_an_analyst():
    from app.notifications.services.manual_send import _require_send_permission

    internal = SimpleNamespace(scope="internal")
    customer = SimpleNamespace(scope="customer")
    _require_send_permission(_user(), internal)
    with pytest.raises(HTTPException) as exc:
        _require_send_permission(_user(), customer)
    assert exc.value.status_code == 403


def _register(role_id, codes):
    """POST /auth/register with a mocked session; the customer lookup finds only ACME."""
    import app.auth.routes.auth as routes
    from app.auth.models.users import UserInput

    created = []

    def add(row):
        row.id = 77
        created.append(row)

    known = MagicMock()
    known.scalars.return_value.all.return_value = [code for code in codes if code == "ACME"]
    session = AsyncMock()
    session.add = MagicMock(side_effect=add)
    session.execute = AsyncMock(return_value=known)
    replace = AsyncMock()
    user = UserInput(username="newbie", password="Str0ng!Passw0rd", email="newbie@example.com", role_id=role_id, customer_codes=codes)
    with patch.object(routes, "select_all_users", AsyncMock(return_value=[])), patch.object(
        routes,
        "replace_assignment",
        replace,
    ), patch.object(
        routes,
        "record_audit_event",
        AsyncMock(),
    ):
        try:
            result = _run(routes.register(user, MagicMock(), SimpleNamespace(id=1, username="admin"), session))
        except HTTPException as e:
            result = e
    return result, created, replace, session


def test_creating_a_responder_without_customers_writes_nothing():
    error, created, replace, session = _register(RoleEnum.responder, [])
    assert error.status_code == 400
    assert created == []
    session.commit.assert_not_awaited()


def test_creating_a_responder_assigns_its_customers_in_the_same_commit():
    result, created, replace, session = _register(RoleEnum.responder, ["ACME"])
    assert result["success"] is True
    assert [row.role_id for row in created] == [RoleEnum.responder.value]
    replace.assert_awaited_once_with(77, ["ACME"], session)
    session.commit.assert_awaited_once()


def test_a_responder_sees_what_the_analyst_role_tags_open():
    from app.incidents.middleware.tag_access import tag_access_handler

    session = AsyncMock()
    rows = MagicMock()
    rows.__iter__ = lambda self: iter([])
    session.execute = AsyncMock(return_value=rows)
    with patch.object(tag_access_handler, "is_tag_rbac_enabled", AsyncMock(return_value=True)):
        _run(tag_access_handler.get_user_accessible_tags(SimpleNamespace(id=9, username="resp", role_id=5), session))
    role_query = session.execute.await_args_list[-1].args[0]
    params = role_query.compile().params
    assert sorted(v for value in params.values() for v in (value if isinstance(value, (list, tuple)) else [value])) == [2, 5]


def _list_users(caller_role):
    import app.auth.routes.auth as routes

    users = [
        SimpleNamespace(id=1, username="admin", email="a@x", role_id=1, role=SimpleNamespace(name="admin"), last_login_at=None),
        SimpleNamespace(id=2, username="resp", email="r@x", role_id=5, role=SimpleNamespace(name="responder"), last_login_at=None),
    ]
    rows = MagicMock()
    rows.all.return_value = [(2, "GLOBEX"), (2, "ACME")]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=rows)
    with patch.object(routes, "select_all_users", AsyncMock(return_value=users)):
        response = _run(routes.get_users(SimpleNamespace(search=None, limit=None), SimpleNamespace(id=9, role_id=caller_role), session))
    return {user.username: user.customer_codes for user in response.users}, session


def test_admins_see_who_serves_which_customer():
    codes, _ = _list_users(RoleEnum.admin.value)
    assert codes == {"admin": [], "resp": ["ACME", "GLOBEX"]}


def test_analysts_do_not():
    codes, session = _list_users(RoleEnum.analyst.value)
    assert codes == {"admin": None, "resp": None}
    session.execute.assert_not_awaited()
