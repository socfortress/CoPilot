"""Customer admins managing their customers' portal users (#1296), and disabled accounts.

No database, no network: the services' pure rules, the schema, the delivery of a temporary
password, the routes' scopes, and where a disabled account is refused. The SQL and the full flows
run in tests/e2e/customer_portal_tenant_users_e2e.py.

Run with: cd backend && python -m pytest tests/test_customer_portal_tenant_users.py
"""

import asyncio
import datetime
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.security import SecurityScopes  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.auth.models.users import Password  # noqa: E402
from app.auth.services import account_status  # noqa: E402
from app.auth.services import security_admin  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.routes.tenant_users import (  # noqa: E402
    customer_portal_tenant_users_router,
)
from app.customer_portal.schema.tenant_users import InviteRequest  # noqa: E402
from app.customer_portal.services import notifications as portal_notifications  # noqa: E402
from app.customer_portal.services import tenant_users  # noqa: E402
from app.customer_portal.services.tenant_users import REASON_ADMIN  # noqa: E402
from app.customer_portal.services.tenant_users import (  # noqa: E402
    REASON_OTHER_CUSTOMER,
)
from app.customer_portal.services.tenant_users import REASON_SELF  # noqa: E402
from app.customer_portal.services.tenant_users import Member  # noqa: E402
from app.customer_portal.services.tenant_users import manage_refusal  # noqa: E402
from app.customer_portal.services.tenant_users import to_tenant_user  # noqa: E402

CALLER = SimpleNamespace(id=1, username="acme.admin", role_id=4, disabled_at=None)


def user(uid, name="acme.user", **extra):
    fields = dict(
        id=uid,
        username=name,
        email=f"{name}@acme.example",
        role_id=4,
        disabled_at=None,
        must_change_password=False,
        last_login_at=None,
    )
    fields.update(extra)
    return SimpleNamespace(**fields)


# ── Who a customer admin may manage ───────────────────────────────────────────


def test_a_colleague_of_an_administered_customer_can_be_managed():
    assert manage_refusal(CALLER, Member(user(2), {"ACME": False}), {"ACME"}) is None


def test_never_the_caller_themself():
    assert manage_refusal(CALLER, Member(CALLER, {"ACME": True}), {"ACME"}) == REASON_SELF


def test_never_another_customer_admin():
    # The SOC appointed them, so the SOC manages them.
    assert manage_refusal(CALLER, Member(user(2), {"ACME": True}), {"ACME"}) == REASON_ADMIN


def test_never_an_admin_of_a_customer_the_caller_does_not_administer_either():
    assert manage_refusal(CALLER, Member(user(2), {"ACME": False, "BETA": True}), {"ACME"}) == REASON_ADMIN


def test_never_an_account_that_also_belongs_to_another_customer():
    # Disabling it would lock it out of a customer the caller has no say over.
    assert manage_refusal(CALLER, Member(user(2), {"ACME": False, "BETA": False}), {"ACME"}) == REASON_OTHER_CUSTOMER


def test_an_account_of_two_administered_customers_can_be_managed():
    assert manage_refusal(CALLER, Member(user(2), {"ACME": False, "BETA": False}), {"ACME", "BETA"}) is None


# ── What a customer admin is shown ────────────────────────────────────────────


def test_another_customer_is_never_named():
    member = Member(user(2), {"ACME": False, "SECRET": False})
    shown = to_tenant_user(CALLER, member, ["ACME"], {"ACME": "Acme"}, set())
    assert [c.customer_code for c in shown.customers] == ["ACME"]
    assert "SECRET" not in shown.model_dump_json()
    assert (shown.can_manage, shown.managed_by_soc_reason) == (False, REASON_OTHER_CUSTOMER)


def test_the_admin_flag_reads_only_administered_customers():
    # An admin of a customer the caller doesn't administer: not shown as an admin here, but still
    # not manageable (the SOC appointed them there).
    shown = to_tenant_user(CALLER, Member(user(2), {"ACME": False, "BETA": True}), ["ACME"], {"ACME": "Acme"}, set())
    assert shown.is_customer_admin is False
    assert shown.can_manage is False


def test_the_state_of_an_account():
    when = datetime.datetime(2026, 10, 1, 9, 0)
    member = Member(user(2, disabled_at=when, must_change_password=True), {"ACME": False})
    shown = to_tenant_user(CALLER, member, ["ACME"], {"ACME": "Acme"}, {2})
    assert (shown.disabled, shown.disabled_at, shown.must_change_password, shown.totp_enabled) == (True, when, True, True)
    assert (shown.is_self, shown.can_manage, shown.managed_by_soc_reason) == (False, True, None)


# ── An invitation ─────────────────────────────────────────────────────────────


def test_an_invitation_needs_a_valid_username_an_email_and_a_customer():
    ok = InviteRequest(username="  jane.doe ", email="jane@acme.example", customer_codes=["ACME", "ACME", " "])
    assert (ok.username, ok.customer_codes) == ("jane.doe", ["ACME"])
    for bad in ("ab", "-jane", "jane doe", "jane<script>", "x" * 65):
        with pytest.raises(ValidationError):
            InviteRequest(username=bad, email="jane@acme.example", customer_codes=["ACME"])
    with pytest.raises(ValidationError):
        InviteRequest(username="jane", email="not-an-email", customer_codes=["ACME"])
    with pytest.raises(ValidationError):
        InviteRequest(username="jane", email="jane@acme.example", customer_codes=[])


def test_an_invitation_is_refused_for_a_customer_the_caller_does_not_administer():
    body = InviteRequest(username="jane", email="jane@acme.example", customer_codes=["ACME", "BETA"])
    with patch.object(tenant_users, "administered_customer_codes", AsyncMock(return_value=["ACME"])):
        with pytest.raises(HTTPException) as refused:
            asyncio.run(tenant_users.invite(CALLER, body, AsyncMock(), None))
    assert refused.value.status_code == 403


def test_a_portal_user_who_administers_nothing_is_refused():
    with patch.object(tenant_users, "administered_customer_codes", AsyncMock(return_value=[])):
        with pytest.raises(HTTPException) as refused:
            asyncio.run(tenant_users.list_users(CALLER, AsyncMock()))
    assert (refused.value.status_code, refused.value.detail) == (403, tenant_users.NOT_A_CUSTOMER_ADMIN)


def test_only_a_portal_user_administers_anything():
    session = AsyncMock()
    analyst = SimpleNamespace(id=9, role_id=2)
    assert asyncio.run(tenant_users.administered_customer_codes(analyst, session)) == []
    session.execute.assert_not_awaited()


# ── A temporary password ──────────────────────────────────────────────────────

PASSWORD = Password.generate(16)
TARGET = user(2)


def deliver(smtp=True, send=None, render=None):
    with (
        patch.object(security_admin, "smtp_configured", return_value=smtp),
        patch.object(security_admin, "send_email", send or AsyncMock()) as sent,
        patch.object(tenant_users.temp_password_email, "resolve_template", AsyncMock(return_value=None)),
        patch.object(tenant_users.temp_password_email, "customer_name_for", AsyncMock(return_value="Acme")),
        patch.object(tenant_users.temp_password_email, "render_email", render or AsyncMock(return_value=("Subject", "body", None))),
        patch.object(tenant_users, "logger") as logged,
    ):
        outcome = asyncio.run(tenant_users.deliver_temporary_password(AsyncMock(), TARGET, "ACME", PASSWORD))
    return outcome, sent, logged


def test_with_smtp_the_password_is_emailed_and_never_returned():
    outcome, sent, _ = deliver()
    assert (outcome.delivery, outcome.temporary_password, outcome.email_problem) == ("email", None, None)
    assert sent.await_args.kwargs["to_addr"] == TARGET.email


def test_without_smtp_it_is_returned_once():
    outcome, sent, _ = deliver(smtp=False)
    assert (outcome.delivery, outcome.temporary_password) == ("shown", PASSWORD.plain)
    assert outcome.email_problem == "Email is not configured"
    sent.assert_not_awaited()


def test_a_failed_email_falls_back_to_showing_it_and_never_logs_it():
    outcome, _, logged = deliver(send=AsyncMock(side_effect=OSError(f"relay refused {PASSWORD.plain}")))
    assert (outcome.delivery, outcome.temporary_password) == ("shown", PASSWORD.plain)
    assert outcome.email_problem == "The email could not be sent"
    assert all(PASSWORD.plain not in str(call) for call in logged.mock_calls)


def test_a_template_that_fails_to_render_falls_back_too():
    outcome, sent, _ = deliver(render=AsyncMock(side_effect=ValueError("bad template")))
    assert outcome.delivery == "shown"
    sent.assert_not_awaited()


# ── Routes ────────────────────────────────────────────────────────────────────


def _routes():
    return {(next(iter(r.methods)), r.path): r for r in customer_portal_tenant_users_router.routes if isinstance(r, APIRoute)}


def test_every_route_is_for_portal_users_by_token():
    from tests.test_customer_user_write_allowlist import _route_scopes

    routes = _routes()
    assert set(routes) == {
        ("GET", "/users"),
        ("POST", "/users"),
        ("POST", "/users/{user_id}/disable"),
        ("POST", "/users/{user_id}/enable"),
        ("DELETE", "/users/{user_id}/totp"),
        ("POST", "/users/{user_id}/temporary-password"),
    }
    for route in routes.values():
        assert _route_scopes(route.dependant) == {"customer_user"}, route.path


def test_the_routes_are_mounted_under_the_portal_prefix():
    from app.routers.customer_portal import router

    paths = {r.path for r in router.routes if isinstance(r, APIRoute)}
    assert "/customer_portal/users" in paths and "/customer_portal/users/{user_id}/disable" in paths


def test_a_response_carrying_a_password_is_not_stored():
    from fastapi import Response

    from app.customer_portal.routes import tenant_users as routes

    shown = tenant_users.TemporaryPassword(delivery="shown", temporary_password="Tmp-Pass-1234!")
    listed = to_tenant_user(CALLER, Member(user(2), {"ACME": False}), ["ACME"], {"ACME": "Acme"}, set())
    response = Response()
    with patch.object(routes.tenant_users, "issue_temporary_password", AsyncMock(return_value=(listed, shown))):
        body = asyncio.run(routes.issue_tenant_user_password(2, MagicMock(), response, CALLER, AsyncMock()))
    assert response.headers["cache-control"] == "no-store"
    assert body.temporary_password == "Tmp-Pass-1234!"


# ── A disabled account ────────────────────────────────────────────────────────

DISABLED = user(5, "acme.gone", disabled_at=datetime.datetime(2026, 10, 1))


def test_a_disabled_account_is_refused_with_a_401_that_says_why():
    with pytest.raises(HTTPException) as refused:
        account_status.ensure_active(DISABLED)
    assert refused.value.status_code == 401
    assert refused.value.detail == account_status.ACCOUNT_DISABLED
    assert refused.value.headers[account_status.ACCOUNT_DISABLED_HEADER] == "true"
    account_status.ensure_active(user(6))


def test_no_token_is_issued_to_a_disabled_account():
    import app.auth.utils as auth_utils

    with (
        patch.object(auth_utils, "find_user", AsyncMock(return_value=DISABLED)),
        patch.object(auth_utils, "get_role", AsyncMock(return_value="customer_user")),
    ):
        with pytest.raises(HTTPException) as refused:
            asyncio.run(AuthHandler().encode_token(DISABLED.username))
    assert refused.value.status_code == 401


def test_a_session_held_by_an_account_disabled_since_ends_at_its_next_request():
    handler = AuthHandler()
    request = SimpleNamespace(state=SimpleNamespace(), scope={}, url=SimpleNamespace(path="/api/customer_portal/me"))
    with (
        patch.object(handler, "decode_token", return_value=(DISABLED.username, ["customer_user"])),
        patch.object(handler, "_resolve_user", AsyncMock(return_value=DISABLED)),
    ):
        with pytest.raises(HTTPException) as refused:
            asyncio.run(handler.get_current_user(request, SecurityScopes([]), "token"))
        assert refused.value.status_code == 401
        with pytest.raises(HTTPException) as refused_scope:
            asyncio.run(handler.require_any_scope("customer_user")(request, "token"))
        assert refused_scope.value.status_code == 401


def test_a_disabled_sign_in_is_audited_after_the_password_checked_out():
    with patch("app.audit.services.audit.record_audit_event", AsyncMock()) as audited:
        with pytest.raises(HTTPException):
            asyncio.run(account_status.refuse_disabled_login(DISABLED, None, "customer portal"))
        audited.assert_awaited_once()
        assert "Disabled account denied" in audited.await_args.kwargs["details"]
        asyncio.run(account_status.refuse_disabled_login(user(6), None, "customer portal"))
        audited.assert_awaited_once()


def test_a_disabled_account_is_sent_no_portal_notification():
    assert portal_notifications.email_problem(DISABLED) == "The account is disabled"
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    asyncio.run(portal_notifications.portal_users_of("ACME", session))
    sql = str(session.execute.await_args.args[0])
    assert "disabled_at IS NULL" in sql


# ── The SOC side ──────────────────────────────────────────────────────────────


def test_only_a_portal_user_with_access_can_be_made_a_customer_admin():
    analyst = SimpleNamespace(id=9, username="ana", role_id=2)
    with pytest.raises(HTTPException) as refused:
        asyncio.run(security_admin.set_customer_admin(AsyncMock(), "ACME", analyst, True))
    assert refused.value.status_code == 400

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    with pytest.raises(HTTPException) as no_access:
        asyncio.run(security_admin.set_customer_admin(session, "ACME", user(2), True))
    assert no_access.value.status_code == 400


def test_the_soc_disables_portal_users_only_and_says_whether_it_changed():
    analyst = SimpleNamespace(id=9, username="ana", role_id=2, disabled_at=None)
    with pytest.raises(HTTPException):
        asyncio.run(security_admin.set_disabled(AsyncMock(), analyst, True))
    target = user(2)
    session = AsyncMock(add=MagicMock())
    assert asyncio.run(security_admin.set_disabled(session, target, True)) is True
    assert target.disabled_at is not None
    assert asyncio.run(security_admin.set_disabled(session, target, True)) is False
    assert asyncio.run(security_admin.set_disabled(session, target, False)) is True
    assert target.disabled_at is None


def test_the_soc_routes_are_admin_only():
    from app.auth.routes.security_admin import security_admin_router
    from tests.test_customer_user_write_allowlist import _route_scopes

    wanted = {
        ("PUT", "/security/customers/{customer_code}/users/{user_id}/customer-admin"),
        ("POST", "/security/users/{user_id}/disable"),
        ("POST", "/security/users/{user_id}/enable"),
    }
    routes = {(next(iter(r.methods)), r.path): r for r in security_admin_router.routes if isinstance(r, APIRoute)}
    assert wanted <= set(routes)
    for key in wanted:
        assert _route_scopes(routes[key].dependant) == {"admin"}, key


def test_the_second_factor_is_refused_before_a_code_is_spent():
    # Disabled between the password and the second factor: the 2FA completion refuses it, and no
    # TOTP or backup code is consumed.
    import app.auth.routes.totp as totp_routes
    from app.auth.models.totp import TOTPValidateRequest

    body = TOTPValidateRequest(temp_token="temp", code="123456")
    with (
        patch.object(totp_routes, "_decode_temp_token", return_value=DISABLED.username),
        patch.object(totp_routes, "find_user", AsyncMock(return_value=DISABLED)),
        patch.object(totp_routes, "validate_totp", AsyncMock()) as validated,
        patch("app.audit.services.audit.record_audit_event", AsyncMock()),
    ):
        with pytest.raises(HTTPException) as refused:
            asyncio.run(totp_routes.validate_2fa_login(body, MagicMock()))
    assert refused.value.status_code == 401
    validated.assert_not_awaited()
